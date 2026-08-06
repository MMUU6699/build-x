"""Supabase Auth client (REST) and local JWT verification.

Authentication with AUTH_PROVIDER=password delegates to Supabase Auth
(sign-up / sign-in / refresh / logout / admin password updates). The issued
JWT access tokens are verified locally with the project's JWT secret
(``SUPABASE_JWT_SECRET``) with the ``aud=authenticated`` claim.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
import jwt
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseUser(BaseModel):
    """User as returned by Supabase Auth, normalized."""

    id: str
    email: Optional[str] = None
    fullname: Optional[str] = None
    is_active: bool = True
    role: str = "user"


class SupabaseSignInResult(BaseModel):
    access_token: str
    refresh_token: str
    user: SupabaseUser


class SupabaseAuthNotConfiguredError(RuntimeError):
    """Raised when Supabase Auth is used without SUPABASE_URL/keys."""


def verify_supabase_jwt(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """Verify a Supabase-issued JWT locally (HS256, aud=authenticated)."""
    if not secret:
        logger.warning("SUPABASE_JWT_SECRET is not configured, cannot verify tokens")
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Supabase JWT has expired")
        return None
    except jwt.InvalidAudienceError:
        logger.warning("Supabase JWT has invalid audience")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid Supabase JWT: {e}")
        return None


class SupabaseAuthClient:
    """REST client for Supabase Auth endpoints."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.base_url = (settings.supabase_url or "").rstrip("/")
        self.anon_key = settings.supabase_anon_key
        self.service_key = settings.supabase_service_key

    def require_config(self) -> None:
        if not self.base_url or not (self.anon_key or self.service_key):
            raise SupabaseAuthNotConfiguredError(
                "Supabase Auth is not configured (set SUPABASE_URL and "
                "SUPABASE_ANON_KEY/SUPABASE_SERVICE_KEY)"
            )

    def _headers(self, admin: bool = False) -> Dict[str, str]:
        self.require_config()
        key = self.service_key if admin else self.anon_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, json: dict, admin: bool = False) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.post(
                f"{self.base_url}/auth/v1{path}",
                headers=self._headers(admin=admin),
                json=json,
            )

    async def sign_up(self, email: str, password: str, fullname: str) -> SupabaseUser:
        resp = await self._post("/signup", {
            "email": email,
            "password": password,
            "options": {"data": {"fullname": fullname}},
        })
        if resp.status_code >= 400:
            data = resp.json()
            msg = data.get("error_description") or data.get("msg") or data.get("error") or resp.text
            logger.warning(f"Supabase signup failed ({resp.status_code}): {msg}")
            raise RuntimeError(str(msg))
        user = resp.json().get("user", {})
        metadata = user.get("user_metadata") or {}
        return SupabaseUser(
            id=user.get("id"),
            email=user.get("email") or email,
            fullname=metadata.get("fullname") or fullname,
            is_active=True,
            role=metadata.get("role", "user"),
        )

    async def sign_in(self, email: str, password: str) -> SupabaseSignInResult:
        resp = await self._post("/token?grant_type=password", {
            "email": email,
            "password": password,
        })
        if resp.status_code >= 400:
            data = resp.json()
            msg = data.get("error_description") or data.get("msg") or data.get("error") or resp.text
            logger.warning(f"Supabase signin failed ({resp.status_code}): {msg}")
            raise RuntimeError(str(msg))
        data = resp.json()
        user = data.get("user", {})
        metadata = user.get("user_metadata") or {}
        return SupabaseSignInResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            user=SupabaseUser(
                id=user.get("id"),
                email=user.get("email") or email,
                fullname=metadata.get("fullname"),
                is_active=True,
                role=metadata.get("role", "user"),
            ),
        )

    async def get_user(self, access_token: str) -> SupabaseUser:
        """Fetch the user profile for an access token (GET /auth/v1/user).

        Raises RuntimeError when the token is invalid/expired.
        """
        self.require_config()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/auth/v1/user",
                headers={
                    "apikey": self.anon_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        if resp.status_code >= 400:
            data = resp.json()
            msg = data.get("msg") or data.get("error_description") or data.get("error") or resp.text
            logger.warning(f"Supabase get_user failed ({resp.status_code}): {msg}")
            raise RuntimeError(str(msg))
        data = resp.json()
        metadata = data.get("user_metadata") or {}
        return SupabaseUser(
            id=data.get("id"),
            email=data.get("email"),
            fullname=metadata.get("full_name") or metadata.get("fullname") or metadata.get("user_name"),
            is_active=data.get("banned_until") is None,
            role=metadata.get("role", "user"),
        )

    async def sign_out(self, access_token: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{self.base_url}/auth/v1/logout",
                headers={
                    "apikey": self.anon_key,
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={},
            )

    async def refresh_token(self, refresh_token: str) -> SupabaseSignInResult:
        resp = await self._post("/token?grant_type=refresh_token", {
            "refresh_token": refresh_token,
        })
        if resp.status_code >= 400:
            raise RuntimeError("Failed to refresh Supabase session")
        data = resp.json()
        return SupabaseSignInResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            user=SupabaseUser(id=(data.get("user") or {}).get("id", "")),
        )

    async def exchange_oauth_code(self, code: str, redirect_uri: str) -> SupabaseSignInResult:
        """Exchange an OAuth authorization code for a Supabase session.

        Uses ``grant_type=authorization_code`` with the service_key so the
        backend can complete the token exchange without a PKCE code_verifier
        (the verifier is only required for browser-initiated PKCE flows).
        """
        resp = await self._post(
            "/token?grant_type=authorization_code",
            {"code": code, "redirect_uri": redirect_uri},
            admin=True,
        )
        if resp.status_code >= 400:
            data = resp.json()
            msg = data.get("error_description") or data.get("msg") or data.get("error") or resp.text
            logger.warning(f"Supabase oauth code exchange failed ({resp.status_code}): {msg}")
            raise RuntimeError(str(msg))
        data = resp.json()
        user = data.get("user", {})
        metadata = user.get("user_metadata") or {}
        return SupabaseSignInResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            user=SupabaseUser(
                id=user.get("id", ""),
                email=user.get("email"),
                fullname=(
                    metadata.get("full_name")
                    or metadata.get("fullname")
                    or metadata.get("user_name")
                ),
                is_active=True,
                role=metadata.get("role", "user"),
            ),
        )


    async def admin_update_user_password(self, user_id: str, new_password: str) -> None:
        resp = await self._post(f"/admin/users/{user_id}", {"password": new_password}, admin=True)
        if resp.status_code >= 400:
            data = resp.json()
            msg = data.get("msg") or data.get("error_description") or resp.text
            logger.warning(f"Supabase admin password update failed ({resp.status_code}): {msg}")
            raise RuntimeError(str(msg))

    async def admin_delete_user(self, user_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{self.base_url}/auth/v1/admin/users/{user_id}",
                headers=self._headers(admin=True),
            )
        if resp.status_code >= 400:
            logger.warning(f"Supabase admin user delete failed ({resp.status_code}): {resp.text}")
