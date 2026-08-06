import hashlib
import secrets
from typing import Optional
from datetime import datetime, timedelta, UTC
from app.domain.models.user import User, UserRole
from app.domain.repositories.user_repository import UserRepository
from app.domain.external.session_store import SessionStore
from app.domain.models.auth_session import (
    AuthSession,
    AuthClientType,
    CredentialSource,
    ResolvedCredentials,
)
from app.application.errors.exceptions import UnauthorizedError, ValidationError, BadRequestError
from app.core.config import get_settings
from app.application.services.token_service import TokenService
from app.domain.models.auth import AuthToken
from app.infrastructure.external.supabase.supabase_auth_client import (
    SupabaseAuthClient,
    SupabaseAuthNotConfiguredError,
)
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service handling user authentication and authorization"""

    def __init__(
        self,
        user_repository: UserRepository,
        token_service: TokenService,
        session_store: SessionStore,
    ):
        self.user_repository = user_repository
        self.settings = get_settings()
        self.token_service = token_service
        self.session_store = session_store
        self.supabase = SupabaseAuthClient()

    def _hash_password(self, password: str) -> str:
        salt = self.settings.password_salt or ''
        return self._pbkdf2_sha256(password, salt)

    def _pbkdf2_sha256(self, password: str, salt: str) -> str:
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        rounds = self.settings.password_hash_rounds or 10
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, rounds)
        return salt + hash_bytes.hex()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        try:
            generated_hash = self._hash_password(password)
            logger.info(f"Generated hash: {generated_hash} vs expected hash: {password_hash}")
            return generated_hash == password_hash
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def _generate_user_id(self) -> str:
        return secrets.token_urlsafe(16)

    def _generate_session_id(self) -> str:
        return secrets.token_urlsafe(32)

    def _ttl_seconds_for_client(self, client: AuthClientType) -> int:
        if client in (AuthClientType.IOS, AuthClientType.ANDROID):
            return max(1, self.settings.session_app_ttl_days * 24 * 3600)
        return max(1, self.settings.session_web_ttl_days * 24 * 3600)

    def parse_client(self, raw: Optional[str]) -> AuthClientType:
        if not raw:
            return AuthClientType.UNKNOWN
        try:
            return AuthClientType(raw.lower())
        except ValueError:
            return AuthClientType.UNKNOWN

    async def create_auth_session(
        self,
        user: User,
        client: AuthClientType = AuthClientType.WEB,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        rotated_from: Optional[str] = None,
    ) -> AuthSession:
        now = datetime.now(UTC)
        ttl = self._ttl_seconds_for_client(client)
        session = AuthSession(
            session_id=self._generate_session_id(),
            user_id=user.id,
            client=client,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            last_seen_at=now,
            ip=ip,
            user_agent=user_agent,
            rotated_from=rotated_from,
        )
        await self.session_store.create(session, ttl)
        return session

    async def _user_from_id(self, user_id: str) -> Optional[User]:
        if self.settings.auth_provider in ("password", "supabase"):
            user = await self.user_repository.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None
            return user
        if self.settings.auth_provider == "local" and user_id == "local_admin":
            return User(
                id="local_admin",
                fullname="Local Admin",
                email=self.settings.local_auth_email,
                role=UserRole.ADMIN,
                is_active=True,
            )
        return None

    async def resolve_session_token(self, token: str) -> Optional[ResolvedCredentials]:
        session = await self.session_store.get(token)
        if not session:
            return None
        ttl = self._ttl_seconds_for_client(session.client)
        await self.session_store.touch(token, ttl)
        return ResolvedCredentials(
            session_id=session.session_id,
            user_id=session.user_id,
            source=CredentialSource.BEARER,
        )

    async def resolve_jwt_grace(self, token: str) -> Optional[ResolvedCredentials]:
        if not self.settings.session_jwt_grace_enabled:
            return None
        payload = self.token_service.verify_token(token)
        if not payload:
            return None
        if payload.get("type", "access") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return ResolvedCredentials(
            session_id=None,
            user_id=user_id,
            source=CredentialSource.JWT_GRACE,
            jwt_payload=payload,
        )

    async def resolve_credentials(
        self,
        bearer_token: Optional[str] = None,
        cookie_session_id: Optional[str] = None,
    ) -> Optional[ResolvedCredentials]:
        """Resolve credentials: Bearer session/JWT → Cookie session_id."""
        if bearer_token:
            resolved = await self.resolve_session_token(bearer_token)
            if resolved:
                resolved.source = CredentialSource.BEARER
                return resolved
            resolved = await self.resolve_jwt_grace(bearer_token)
            if resolved:
                return resolved

        if cookie_session_id:
            resolved = await self.resolve_session_token(cookie_session_id)
            if resolved:
                resolved.source = CredentialSource.COOKIE
                return resolved

        return None

    async def user_from_resolved(self, resolved: ResolvedCredentials) -> Optional[User]:
        if resolved.source == CredentialSource.JWT_GRACE and resolved.jwt_payload:
            if self.settings.auth_provider in ("password", "supabase"):
                return await self._user_from_id(resolved.user_id)
            return User(
                id=resolved.jwt_payload.get("sub"),
                fullname=resolved.jwt_payload.get("fullname") or "user",
                email=resolved.jwt_payload.get("email"),
                role=UserRole(resolved.jwt_payload.get("role", "user")),
                is_active=resolved.jwt_payload.get("is_active", True),
            )
        return await self._user_from_id(resolved.user_id)

    async def register_user(
        self, fullname: str, password: str, email: str, role: UserRole = UserRole.USER
    ) -> User:
        logger.info(f"Registering user: {email}")

        if self.settings.auth_provider != "password":
            raise BadRequestError("Registration is not allowed")

        if not fullname or len(fullname.strip()) < 2:
            raise ValidationError("Full name must be at least 2 characters long")
        if not email or '@' not in email:
            raise ValidationError("Valid email is required")
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        if await self.user_repository.email_exists(email):
            raise ValidationError("Email already exists")

        try:
            supabase_user = await self.supabase.sign_up(
                email=email.lower(), password=password, fullname=fullname.strip()
            )
        except SupabaseAuthNotConfiguredError as e:
            raise BadRequestError(str(e))
        except RuntimeError as e:
            message = str(e).lower()
            if "already registered" in message or "already" in message and "exist" in message:
                raise ValidationError("Email already exists")
            raise ValidationError(f"Registration failed: {e}")

        user = User(
            id=supabase_user.id,
            fullname=fullname.strip(),
            email=email.lower(),
            password_hash=None,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created_user = await self.user_repository.create_user(user)
        logger.info(f"User registered successfully: {created_user.id}")
        return created_user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        logger.debug(f"Authenticating user: {email}")

        if self.settings.auth_provider == "none":
            return User(
                id="anonymous",
                fullname="anonymous",
                email="anonymous@localhost",
                role=UserRole.USER,
                is_active=True,
            )

        if self.settings.auth_provider == "local":
            if (
                email == self.settings.local_auth_email
                and password == self.settings.local_auth_password
            ):
                return User(
                    id="local_admin",
                    fullname="Local Admin",
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            logger.warning(f"Local authentication failed for user: {email}")
            return None

        if self.settings.auth_provider == "password":
            try:
                sign_in_result = await self.supabase.sign_in(email=email, password=password)
            except SupabaseAuthNotConfiguredError as e:
                logger.error(f"Supabase Auth not configured: {e}")
                return None
            except RuntimeError as e:
                logger.warning(f"Authentication failed for user {email}: {e}")
                return None
            user = await self.user_repository.get_user_by_email(email)
            if not user:
                # Valid Supabase credentials but no profile row yet: create one.
                user = User(
                    id=sign_in_result.user.id,
                    fullname=sign_in_result.user.fullname or email.split("@")[0],
                    email=email.lower(),
                    role=UserRole.USER,
                    is_active=True,
                )
                user = await self.user_repository.create_user(user)
                return user
            if not user.is_active:
                logger.warning(f"User account is inactive: {email}")
                return None
            user.update_last_login()
            await self.user_repository.update_user(user)
            logger.info(f"User authenticated successfully: {email}")
            return user

        raise ValueError(f"Unsupported auth provider: {self.settings.auth_provider}")

    async def login_with_session(
        self,
        email: str,
        password: str,
        client: AuthClientType = AuthClientType.WEB,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthToken:
        user = await self.authenticate_user(email, password)
        if not user:
            raise UnauthorizedError("Invalid email or password")

        session = await self.create_auth_session(
            user, client=client, ip=ip, user_agent=user_agent
        )
        return AuthToken(
            access_token=session.session_id,
            refresh_token=session.session_id,
            token_type="bearer",
            user=user,
        )

    async def login_with_tokens(self, email: str, password: str) -> AuthToken:
        """Backward-compatible alias — issues Postgres auth sessions, not JWTs."""
        return await self.login_with_session(email, password, client=AuthClientType.WEB)

    async def login_with_supabase_token(
        self,
        access_token: str,
        client: AuthClientType = AuthClientType.WEB,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthToken:
        """Log in a user whose identity was verified by Supabase Auth (OAuth).

        The frontend exchanges the OAuth PKCE code for a Supabase access
        token, then hands it to us. We validate it against Supabase, find or
        create the local profile, and mint an opaque auth session.
        """
        if self.settings.auth_provider == "none":
            raise BadRequestError("Authentication is not available")

        try:
            supabase_user = await self.supabase.get_user(access_token)
        except SupabaseAuthNotConfiguredError as e:
            raise BadRequestError(str(e))
        except RuntimeError as e:
            logger.warning(f"Supabase token rejected: {e}")
            raise UnauthorizedError("Invalid Supabase session")

        if not supabase_user.id:
            raise UnauthorizedError("Invalid Supabase session")

        user = await self.user_repository.get_user_by_id(supabase_user.id)
        if not user:
            user = User(
                id=supabase_user.id,
                fullname=supabase_user.fullname
                or (supabase_user.email or "user").split("@")[0],
                email=supabase_user.email or "",
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user = await self.user_repository.create_user(user)
            logger.info(f"User created from Supabase OAuth login: {user.id}")
        elif not user.is_active:
            raise UnauthorizedError("User account is inactive")
        else:
            user.update_last_login()
            await self.user_repository.update_user(user)

        session = await self.create_auth_session(
            user, client=client, ip=ip, user_agent=user_agent
        )
        return AuthToken(
            access_token=session.session_id,
            refresh_token=session.session_id,
            token_type="bearer",
            user=user,
        )

    async def login_with_oauth_code(
        self,
        code: str,
        redirect_uri: str,
        client: AuthClientType = AuthClientType.WEB,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthToken:
        """Exchange a raw OAuth authorization code for a local session.

        The backend calls Supabase ``/token?grant_type=authorization_code``
        with the service_key — no browser PKCE code_verifier required.
        """
        if self.settings.auth_provider == "none":
            raise BadRequestError("Authentication is not available")

        try:
            sign_in_result = await self.supabase.exchange_oauth_code(code, redirect_uri)
        except SupabaseAuthNotConfiguredError as e:
            raise BadRequestError(str(e))
        except RuntimeError as e:
            logger.warning(f"OAuth code exchange failed: {e}")
            raise UnauthorizedError("OAuth login failed — invalid or expired code")

        supabase_user = sign_in_result.user
        if not supabase_user.id:
            raise UnauthorizedError("OAuth login failed — no user returned")

        user = await self.user_repository.get_user_by_id(supabase_user.id)
        if not user:
            user = User(
                id=supabase_user.id,
                fullname=supabase_user.fullname
                or (supabase_user.email or "user").split("@")[0],
                email=supabase_user.email or "",
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user = await self.user_repository.create_user(user)
            logger.info(f"User created from OAuth code exchange: {user.id}")
        elif not user.is_active:
            raise UnauthorizedError("User account is inactive")
        else:
            user.update_last_login()
            await self.user_repository.update_user(user)

        session = await self.create_auth_session(
            user, client=client, ip=ip, user_agent=user_agent
        )
        return AuthToken(
            access_token=session.session_id,
            refresh_token=session.session_id,
            token_type="bearer",
            user=user,
        )


    async def refresh_access_token(
        self,
        refresh_token: Optional[str] = None,
        cookie_session_id: Optional[str] = None,
        rotate: bool = False,
    ) -> AuthToken:
        token = refresh_token or cookie_session_id
        if not token:
            raise UnauthorizedError("Missing session credentials")

        session = await self.session_store.get(token)
        if session:
            user = await self._user_from_id(session.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError("User not found or inactive")

            if rotate:
                await self.session_store.delete(token)
                new_session = await self.create_auth_session(
                    user,
                    client=session.client,
                    ip=session.ip,
                    user_agent=session.user_agent,
                    rotated_from=token,
                )
                return AuthToken(
                    access_token=new_session.session_id,
                    refresh_token=new_session.session_id,
                    token_type="bearer",
                )

            ttl = self._ttl_seconds_for_client(session.client)
            await self.session_store.touch(token, ttl)
            return AuthToken(
                access_token=token,
                refresh_token=token,
                token_type="bearer",
            )

        if not self.settings.session_jwt_grace_enabled:
            raise UnauthorizedError("Invalid refresh token")

        payload = self.token_service.verify_token(token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")

        user_id = payload.get("sub")
        user = await self.user_repository.get_user_by_id(user_id) if user_id else None
        if not user or not user.is_active:
            if self.settings.auth_provider != "password" and user_id:
                user = User(
                    id=user_id,
                    fullname=payload.get("fullname") or "user",
                    email=None,
                    role=UserRole.USER,
                    is_active=True,
                )
            else:
                raise UnauthorizedError("User not found or inactive")

        new_session = await self.create_auth_session(user, client=AuthClientType.UNKNOWN)
        return AuthToken(
            access_token=new_session.session_id,
            refresh_token=new_session.session_id,
            token_type="bearer",
        )

    async def verify_token(self, token: str) -> Optional[User]:
        resolved = await self.resolve_session_token(token)
        if resolved:
            return await self.user_from_resolved(resolved)
        resolved = await self.resolve_jwt_grace(token)
        if resolved:
            return await self.user_from_resolved(resolved)
        return None

    async def logout(self, token: str) -> bool:
        if self.settings.auth_provider == "none":
            raise BadRequestError("Logout is not allowed")
        deleted = await self.session_store.delete(token)
        if deleted:
            return True
        return self.token_service.revoke_token(token)

    async def logout_all(self, user_id: str) -> int:
        if self.settings.auth_provider == "none":
            raise BadRequestError("Logout is not allowed")
        return await self.session_store.delete_all_for_user(user_id)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        logger.info(f"Changing password for user: {user_id}")
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        if not new_password or len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")
        if self.settings.auth_provider == "password":
            try:
                await self.supabase.sign_in(email=user.email, password=old_password)
            except SupabaseAuthNotConfiguredError as e:
                raise BadRequestError(str(e))
            except RuntimeError:
                raise UnauthorizedError("Invalid old password")
            try:
                await self.supabase.admin_update_user_password(user_id, new_password)
            except SupabaseAuthNotConfiguredError as e:
                raise BadRequestError(str(e))
            except RuntimeError as e:
                raise ValidationError(f"Failed to update password: {e}")
            user.updated_at = datetime.utcnow()
            await self.user_repository.update_user(user)
            logger.info(f"Password changed successfully for user: {user_id}")
            return True
        raise BadRequestError("Password change is not available")

    async def change_fullname(self, user_id: str, new_fullname: str) -> User:
        logger.info(f"Changing fullname for user: {user_id}")
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        if not new_fullname or len(new_fullname.strip()) < 2:
            raise ValidationError("Full name must be at least 2 characters long")
        user.fullname = new_fullname.strip()
        user.updated_at = datetime.utcnow()
        updated_user = await self.user_repository.update_user(user)
        logger.info(f"Fullname changed successfully for user: {user_id}")
        return updated_user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        return await self.user_repository.get_user_by_id(user_id)

    async def deactivate_user(self, user_id: str) -> bool:
        logger.info(f"Deactivating user: {user_id}")
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        user.deactivate()
        await self.user_repository.update_user(user)
        logger.info(f"User deactivated successfully: {user_id}")
        return True

    async def activate_user(self, user_id: str) -> bool:
        logger.info(f"Activating user: {user_id}")
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        user.activate()
        await self.user_repository.update_user(user)
        logger.info(f"User activated successfully: {user_id}")
        return True

    async def reset_password(self, email: str, new_password: str) -> bool:
        logger.info(f"Resetting password for user: {email}")
        if self.settings.auth_provider != "password":
            raise BadRequestError("Password reset is not allowed")
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise ValidationError("User not found")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        if not new_password or len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")
        try:
            await self.supabase.admin_update_user_password(user.id, new_password)
        except SupabaseAuthNotConfiguredError as e:
            raise BadRequestError(str(e))
        except RuntimeError as e:
            raise ValidationError(f"Failed to reset password: {e}")
        user.updated_at = datetime.utcnow()
        await self.user_repository.update_user(user)
        logger.info(f"Password reset successfully for user: {email}")
        return True
