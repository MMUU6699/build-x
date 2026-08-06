import logging
from typing import List, Optional

from sqlalchemy import select

from app.domain.models.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.models.postgres import UserRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


def _row_to_user(row: UserRow) -> User:
    return User(
        id=row.user_id,
        fullname=row.fullname,
        email=row.email,
        role=row.role,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_login_at=row.last_login_at,
    )


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository (profiles table).

    Identity/passwords live in Supabase Auth; this repository only manages
    the application profile row (no password hashes are stored).
    """

    async def create_user(self, user: User) -> User:
        """Create a new user"""
        logger.info(f"Creating user: {user.fullname}")
        async with get_session_factory()() as db:
            db.add(UserRow(
                user_id=user.id,
                fullname=user.fullname,
                email=user.email,
                role=user.role.value if hasattr(user.role, "value") else str(user.role),
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=user.last_login_at,
            ))
            await db.commit()
        logger.info(f"User created successfully: {user.id}")
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        async with get_session_factory()() as db:
            row = await db.get(UserRow, user_id)
            return _row_to_user(row) if row else None

    async def get_user_by_fullname(self, fullname: str) -> Optional[User]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(UserRow).where(UserRow.fullname == fullname)
            )
            row = result.scalar_one_or_none()
            return _row_to_user(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(UserRow).where(UserRow.email == email.lower())
            )
            row = result.scalar_one_or_none()
            return _row_to_user(row) if row else None

    async def update_user(self, user: User) -> User:
        async with get_session_factory()() as db:
            row = await db.get(UserRow, user.id)
            if not row:
                raise ValueError(f"User not found: {user.id}")
            row.fullname = user.fullname
            row.email = user.email
            row.role = user.role.value if hasattr(user.role, "value") else str(user.role)
            row.is_active = user.is_active
            row.last_login_at = user.last_login_at
            row.updated_at = user.updated_at
            await db.commit()
        return user

    async def delete_user(self, user_id: str) -> bool:
        async with get_session_factory()() as db:
            row = await db.get(UserRow, user_id)
            if not row:
                logger.warning(f"User not found for deletion: {user_id}")
                return False
            await db.delete(row)
            await db.commit()
            logger.info(f"User deleted successfully: {user_id}")
            return True

    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(UserRow).order_by(UserRow.created_at).limit(limit).offset(offset)
            )
            return [_row_to_user(r) for r in result.scalars().all()]

    async def fullname_exists(self, fullname: str) -> bool:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(UserRow.user_id).where(UserRow.fullname == fullname)
            )
            return result.first() is not None

    async def email_exists(self, email: str) -> bool:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(UserRow.user_id).where(UserRow.email == email.lower())
            )
            return result.first() is not None
