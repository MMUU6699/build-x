"""PostgreSQL implementation of SessionStore for opaque auth sessions.

Replaces the Redis-backed store: ``auth_sessions`` rows with TTLs expressed
as absolute ``expires_at`` timestamps.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from sqlalchemy import delete, select, update

from app.domain.models.auth_session import AuthSession
from app.infrastructure.models.postgres import AuthSessionRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


def _client_value(client: object) -> str:
    return getattr(client, "value", client) if client is not None else "unknown"


class PostgresSessionStore:
    """Postgres-backed auth session store with per-user index for revoke-all."""

    async def create(self, session: AuthSession, ttl_seconds: int) -> None:
        async with get_session_factory()() as db:
            db.add(AuthSessionRow(
                session_id=session.session_id,
                user_id=session.user_id,
                client=_client_value(session.client),
                created_at=session.created_at,
                expires_at=session.expires_at,
                last_seen_at=session.last_seen_at,
                ip=session.ip,
                user_agent=session.user_agent,
                rotated_from=session.rotated_from,
            ))
            await db.commit()

    async def get(self, session_id: str) -> Optional[AuthSession]:
        async with get_session_factory()() as db:
            row = await db.get(AuthSessionRow, session_id)
            if not row:
                return None
            if row.expires_at and row.expires_at <= datetime.now(UTC):
                await db.delete(row)
                await db.commit()
                return None
            return self._row_to_session(row)

    async def touch(self, session_id: str, ttl_seconds: int) -> Optional[AuthSession]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=max(1, ttl_seconds))
        async with get_session_factory()() as db:
            row = await db.get(AuthSessionRow, session_id)
            if not row or (row.expires_at and row.expires_at <= now):
                if row:
                    await db.delete(row)
                    await db.commit()
                return None
            row.last_seen_at = now
            row.expires_at = expires_at
            await db.commit()
            return self._row_to_session(row)

    async def delete(self, session_id: str) -> bool:
        async with get_session_factory()() as db:
            row = await db.get(AuthSessionRow, session_id)
            if not row:
                return False
            await db.delete(row)
            await db.commit()
            return True

    async def delete_all_for_user(self, user_id: str) -> int:
        async with get_session_factory()() as db:
            result = await db.execute(
                delete(AuthSessionRow).where(AuthSessionRow.user_id == user_id)
            )
            await db.commit()
            return result.rowcount or 0

    async def list_ids_for_user(self, user_id: str) -> list[str]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(AuthSessionRow.session_id).where(AuthSessionRow.user_id == user_id)
            )
            return [row[0] for row in result.all()]

    def _row_to_session(self, row: AuthSessionRow) -> AuthSession:
        return AuthSession(
            session_id=row.session_id,
            user_id=row.user_id,
            client=row.client,
            created_at=row.created_at,
            expires_at=row.expires_at,
            last_seen_at=row.last_seen_at,
            ip=row.ip,
            user_agent=row.user_agent,
            rotated_from=row.rotated_from,
        )
