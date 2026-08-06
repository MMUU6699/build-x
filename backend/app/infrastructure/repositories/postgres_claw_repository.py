import logging
from typing import Optional, List
from datetime import datetime, UTC

from sqlalchemy import delete, select

from app.domain.models.claw import Claw, ClawMessage, ClawAttachment
from app.infrastructure.models.postgres import ClawRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


def _row_to_claw(row: ClawRow) -> Claw:
    return Claw(
        id=row.claw_id,
        user_id=row.user_id,
        container_name=row.container_name,
        container_ip=row.container_ip,
        api_key=row.api_key,
        status=row.status,
        error_message=row.error_message,
        expires_at=row.expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_messages(row: ClawRow) -> List[ClawMessage]:
    messages = []
    for m in row.messages or []:
        try:
            messages.append(ClawMessage.model_validate(m))
        except Exception:
            logger.debug("Skipping malformed claw message", exc_info=True)
    return messages


class PostgresClawRepository:
    """PostgreSQL repository for Claw instances"""

    async def get_by_user_id(self, user_id: str) -> Optional[Claw]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ClawRow).where(ClawRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            return _row_to_claw(row) if row else None

    async def get_by_id(self, claw_id: str) -> Optional[Claw]:
        async with get_session_factory()() as db:
            row = await db.get(ClawRow, claw_id)
            return _row_to_claw(row) if row else None

    async def get_by_api_key(self, api_key: str) -> Optional[Claw]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ClawRow).where(ClawRow.api_key == api_key)
            )
            row = result.scalar_one_or_none()
            return _row_to_claw(row) if row else None

    async def create(self, claw: Claw) -> Claw:
        async with get_session_factory()() as db:
            db.add(ClawRow(
                claw_id=claw.id,
                user_id=claw.user_id,
                container_name=claw.container_name,
                container_ip=claw.container_ip,
                api_key=claw.api_key,
                status=claw.status.value if hasattr(claw.status, "value") else str(claw.status),
                error_message=claw.error_message,
                expires_at=claw.expires_at,
                messages=[],
                created_at=claw.created_at,
                updated_at=claw.updated_at,
            ))
            await db.commit()
        return claw

    async def update(self, claw: Claw) -> Claw:
        async with get_session_factory()() as db:
            row = await db.get(ClawRow, claw.id)
            if not row:
                raise ValueError(f"Claw not found: {claw.id}")
            row.container_name = claw.container_name
            row.container_ip = claw.container_ip
            row.api_key = claw.api_key
            row.status = claw.status.value if hasattr(claw.status, "value") else str(claw.status)
            row.error_message = claw.error_message
            row.expires_at = claw.expires_at
            row.updated_at = datetime.now(UTC)
            await db.commit()
        return claw

    async def delete_by_user_id(self, user_id: str) -> bool:
        async with get_session_factory()() as db:
            result = await db.execute(
                delete(ClawRow).where(ClawRow.user_id == user_id)
            )
            await db.commit()
            return (result.rowcount or 0) > 0

    async def get_messages(self, user_id: str) -> List[ClawMessage]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ClawRow).where(ClawRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            return _row_to_messages(row) if row else []

    async def append_message(
        self, user_id: str, role: str, content: str = "",
        attachments: Optional[List[ClawAttachment]] = None,
    ) -> None:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ClawRow).where(ClawRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return
            msg = ClawMessage(
                role=role,
                content=content,
                timestamp=int(datetime.now(UTC).timestamp()),
                attachments=attachments,
            )
            messages = list(row.messages or [])
            messages.append(msg.model_dump(mode="json"))
            row.messages = messages
            row.updated_at = datetime.now(UTC)
            await db.commit()

    async def clear_messages(self, user_id: str) -> None:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ClawRow).where(ClawRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return
            row.messages = []
            row.updated_at = datetime.now(UTC)
            await db.commit()
