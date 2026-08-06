"""PostgreSQL message queue (replaces Redis Streams).

Each row in ``task_streams`` is one message. The identity ``id`` column is
the monotonic cursor exposed as the queue message id (``str(id)``), so
``get(start_id)`` keeps Redis-stream cursor semantics. ``pop()`` uses a
single ``DELETE ... FOR UPDATE SKIP LOCKED`` for concurrency safety across
processes (no distributed lock key needed).
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional, Tuple
from datetime import datetime, UTC

from sqlalchemy import delete, func, select, text

from app.domain.external.message_queue import MessageQueue
from app.infrastructure.models.postgres import TaskStreamRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 0.2


class PostgresStreamQueue(MessageQueue):
    """Postgres implementation of the message queue."""

    def __init__(self, stream_name: str):
        self._stream_name = stream_name

    async def put(self, message: Any) -> str:
        async with get_session_factory()() as db:
            row = TaskStreamRow(stream_name=self._stream_name, data=message)
            db.add(row)
            await db.commit()
            await db.refresh(row)
            message_id = str(row.id)
        logger.debug(f"Put message {message_id} into stream ({self._stream_name})")
        return message_id

    async def _fetch_after(self, start_id: str, db) -> Any:
        """Select the first message strictly after the cursor."""
        if start_id is None or start_id in ("", "0", "-"):
            start_id = "0"
        cursor = int(start_id) if str(start_id).isdigit() else 0
        stmt = (
            select(TaskStreamRow)
            .where(
                TaskStreamRow.stream_name == self._stream_name,
                TaskStreamRow.id > cursor,
            )
            .order_by(TaskStreamRow.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, start_id: str = "0", block_ms: Optional[int] = None) -> Tuple[str, Any]:
        deadline = None
        if block_ms:
            deadline = asyncio.get_running_loop().time() + block_ms / 1000.0
        while True:
            async with get_session_factory()() as db:
                row = await self._fetch_after(start_id, db)
            if row:
                return str(row.id), row.data
            if deadline is None:
                return None, None
            if asyncio.get_running_loop().time() >= deadline:
                return None, None
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    async def get_range(self, start_id: str = "-", end_id: str = "+", count: int = 100) -> AsyncGenerator[Tuple[str, Any], None]:
        async with get_session_factory()() as db:
            stmt = select(TaskStreamRow).where(TaskStreamRow.stream_name == self._stream_name)
            if start_id and start_id != "-" and str(start_id).isdigit():
                stmt = stmt.where(TaskStreamRow.id > int(start_id))
            if end_id and end_id != "+" and str(end_id).isdigit():
                stmt = stmt.where(TaskStreamRow.id <= int(end_id))
            stmt = stmt.order_by(TaskStreamRow.id).limit(count)
            result = await db.execute(stmt)
            rows = result.scalars().all()
        for row in rows:
            yield str(row.id), row.data

    async def get_latest_id(self) -> str:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(func.max(TaskStreamRow.id)).where(
                    TaskStreamRow.stream_name == self._stream_name
                )
            )
            latest = result.scalar_one_or_none()
            return str(latest) if latest else "0"

    async def clear(self) -> None:
        async with get_session_factory()() as db:
            await db.execute(
                delete(TaskStreamRow).where(TaskStreamRow.stream_name == self._stream_name)
            )
            await db.commit()

    async def is_empty(self) -> bool:
        return await self.size() == 0

    async def size(self) -> int:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(func.count()).select_from(TaskStreamRow).where(
                    TaskStreamRow.stream_name == self._stream_name
                )
            )
            return int(result.scalar_one())

    async def delete_message(self, message_id: str) -> bool:
        try:
            async with get_session_factory()() as db:
                result = await db.execute(
                    delete(TaskStreamRow).where(
                        TaskStreamRow.stream_name == self._stream_name,
                        TaskStreamRow.id == int(message_id),
                    )
                )
                await db.commit()
                return (result.rowcount or 0) > 0
        except Exception:
            return False

    async def pop(self) -> Tuple[str, Any]:
        """Atomically delete and return the first unclaimed message."""
        async with get_session_factory()() as db:
            selected = (
                select(TaskStreamRow.id)
                .where(TaskStreamRow.stream_name == self._stream_name)
                .order_by(TaskStreamRow.id)
                .limit(1)
                .with_for_update(skip_locked=True)
                .cte("selected")
            )
            stmt = (
                delete(TaskStreamRow)
                .where(TaskStreamRow.id.in_(select(selected.c.id)))
                .returning(TaskStreamRow.id, TaskStreamRow.data)
            )
            result = await db.execute(stmt)
            await db.commit()
            row = result.one_or_none()
        if row is None:
            return None, None
        return str(row[0]), row[1]
