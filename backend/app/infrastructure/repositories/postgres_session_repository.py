import json
import logging
from typing import Any, Optional, List
from datetime import datetime, UTC

from sqlalchemy import cast, delete, select, update
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import TypeAdapter

from app.domain.models.session import Session, SessionStatus, SessionSummary, TaskMode
from app.domain.models.file import FileInfo
from app.domain.repositories.session_repository import SessionRepository
from app.domain.models.event import AgentEvent, BaseEvent
from app.infrastructure.models.postgres import SessionRow
from app.infrastructure.storage.postgres import get_session_factory
from app.infrastructure.external.session_list import (
    publish_session_remove,
    publish_session_upsert,
)

logger = logging.getLogger(__name__)

_AGENT_EVENT_ADAPTER = TypeAdapter(AgentEvent)

SUMMARY_COLUMNS = [
    SessionRow.session_id,
    SessionRow.user_id,
    SessionRow.title,
    SessionRow.unread_message_count,
    SessionRow.latest_message,
    SessionRow.latest_message_at,
    SessionRow.status,
    SessionRow.is_shared,
    SessionRow.is_favorite,
    SessionRow.is_pinned,
    SessionRow.project_id,
    SessionRow.task_mode,
]


def _event_json(event: BaseEvent) -> dict:
    return event.model_dump(mode="json")


def _normalize_events(raw: Any) -> list[dict]:
    """Normalize legacy event storage: JSONB array of objects (or of strings)."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str):
            try:
                out.append(json.loads(item))
            except json.JSONDecodeError:
                pass
    return out


def _row_to_session(row: SessionRow) -> Session:
    return Session(
        id=row.session_id,
        user_id=row.user_id,
        sandbox_id=row.sandbox_id,
        agent_id=row.agent_id,
        task_id=row.task_id,
        title=row.title,
        unread_message_count=row.unread_message_count,
        latest_message=row.latest_message,
        latest_message_at=row.latest_message_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        events=[_AGENT_EVENT_ADAPTER.validate_python(e) for e in _normalize_events(row.events)],
        files=[FileInfo.model_validate(f) for f in (row.files or [])],
        status=SessionStatus(row.status) if row.status else SessionStatus.PENDING,
        is_shared=row.is_shared,
        is_favorite=row.is_favorite,
        is_pinned=row.is_pinned,
        project_id=row.project_id,
        task_mode=TaskMode(row.task_mode) if row.task_mode else TaskMode.AGENT,
    )


def _row_to_summary(row) -> SessionSummary:
    return SessionSummary(
        id=row.session_id,
        user_id=row.user_id,
        title=row.title,
        unread_message_count=row.unread_message_count,
        latest_message=row.latest_message,
        latest_message_at=row.latest_message_at,
        status=SessionStatus(row.status) if row.status else SessionStatus.PENDING,
        is_shared=row.is_shared,
        is_favorite=row.is_favorite,
        is_pinned=row.is_pinned,
        project_id=row.project_id,
        task_mode=TaskMode(row.task_mode) if row.task_mode else TaskMode.AGENT,
    )


class PostgresSessionRepository(SessionRepository):
    """PostgreSQL implementation of SessionRepository"""

    async def save(self, session: Session) -> None:
        """Save or update a session"""
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session.id)
            if row is None:
                db.add(SessionRow(
                    session_id=session.id,
                    user_id=session.user_id,
                    sandbox_id=session.sandbox_id,
                    agent_id=session.agent_id,
                    task_id=session.task_id,
                    title=session.title,
                    unread_message_count=session.unread_message_count,
                    latest_message=session.latest_message,
                    latest_message_at=session.latest_message_at,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    events=[_event_json(e) for e in session.events],
                    files=[f.model_dump(mode="json") for f in session.files],
                    status=session.status.value,
                    is_shared=session.is_shared,
                    is_favorite=session.is_favorite,
                    is_pinned=session.is_pinned,
                    project_id=session.project_id,
                    task_mode=session.task_mode.value,
                ))
            else:
                row.user_id = session.user_id
                row.sandbox_id = session.sandbox_id
                row.agent_id = session.agent_id
                row.task_id = session.task_id
                row.title = session.title
                row.unread_message_count = session.unread_message_count
                row.latest_message = session.latest_message
                row.latest_message_at = session.latest_message_at
                row.updated_at = session.updated_at
                row.events = [_event_json(e) for e in session.events]
                row.files = [f.model_dump(mode="json") for f in session.files]
                row.status = session.status.value
                row.is_shared = session.is_shared
                row.is_favorite = session.is_favorite
                row.is_pinned = session.is_pinned
                row.project_id = session.project_id
                row.task_mode = session.task_mode.value
            await db.commit()
        await publish_session_upsert(session.user_id, session.id)

    async def _notify_upsert(self, session_id: str) -> None:
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session_id)
            user_id = row.user_id if row else None
        if user_id:
            await publish_session_upsert(user_id, session_id)

    async def find_by_id(self, session_id: str) -> Optional[Session]:
        """Find a session by its ID"""
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session_id)
            return _row_to_session(row) if row else None

    async def find_by_user_id(self, user_id: str) -> List[Session]:
        """Find all sessions for a specific user"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(SessionRow)
                .where(SessionRow.user_id == user_id)
                .order_by(SessionRow.latest_message_at.desc().nullslast())
            )
            return [_row_to_session(r) for r in result.scalars().all()]

    async def find_summaries_by_user_id(self, user_id: str) -> List[SessionSummary]:
        """Find lightweight session summaries for a user (excludes events/files)"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(*SUMMARY_COLUMNS)
                .where(SessionRow.user_id == user_id)
                .order_by(SessionRow.latest_message_at.desc().nullslast())
            )
            return [_row_to_summary(r) for r in result.all()]

    async def find_summary_by_id_and_user_id(
        self, session_id: str, user_id: str
    ) -> Optional[SessionSummary]:
        """Find a lightweight session summary by ID for a specific user"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(*SUMMARY_COLUMNS).where(
                    SessionRow.session_id == session_id,
                    SessionRow.user_id == user_id,
                )
            )
            row = result.one_or_none()
            return _row_to_summary(row) if row else None

    async def find_by_id_and_user_id(self, session_id: str, user_id: str) -> Optional[Session]:
        """Find a session by ID and user ID (for authorization)"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(SessionRow).where(
                    SessionRow.session_id == session_id,
                    SessionRow.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            return _row_to_session(row) if row else None

    async def _update(self, session_id: str, **values) -> bool:
        async with get_session_factory()() as db:
            result = await db.execute(
                update(SessionRow)
                .where(SessionRow.session_id == session_id)
                .values(**values, updated_at=datetime.now(UTC))
            )
            await db.commit()
            return (result.rowcount or 0) > 0

    async def update_title(self, session_id: str, title: str) -> None:
        """Update the title of a session"""
        if not await self._update(session_id, title=title):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_latest_message(self, session_id: str, message: str, timestamp: datetime) -> None:
        """Update the latest message of a session"""
        if not await self._update(session_id, latest_message=message, latest_message_at=timestamp):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def add_event(self, session_id: str, event: BaseEvent) -> None:
        """Add an event to a session"""
        async with get_session_factory()() as db:
            result = await db.execute(
                update(SessionRow)
                .where(SessionRow.session_id == session_id)
                .values(
                    events=SessionRow.events.op("||")(
                        cast([_event_json(event)], JSONB)
                    ),
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Session {session_id} not found")

    async def add_file(self, session_id: str, file_info: FileInfo) -> None:
        """Add a file to a session"""
        async with get_session_factory()() as db:
            result = await db.execute(
                update(SessionRow)
                .where(SessionRow.session_id == session_id)
                .values(
                    files=SessionRow.files.op("||")(
                        cast([file_info.model_dump(mode="json")], JSONB)
                    ),
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Session {session_id} not found")

    async def remove_file(self, session_id: str, file_id: str) -> None:
        """Remove a file from a session"""
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session_id)
            if not row:
                raise ValueError(f"Session {session_id} not found")
            files = [f for f in (row.files or []) if f.get("file_id") != file_id]
            row.files = files
            row.updated_at = datetime.now(UTC)
            await db.commit()

    async def get_file_by_path(self, session_id: str, file_path: str) -> Optional[FileInfo]:
        """Get file by path from a session"""
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session_id)
            if not row:
                raise ValueError(f"Session {session_id} not found")
            for file_info in row.files or []:
                if file_info.get("file_path") == file_path:
                    return FileInfo.model_validate(file_info)
            return None

    async def delete(self, session_id: str) -> None:
        """Delete a session"""
        async with get_session_factory()() as db:
            row = await db.get(SessionRow, session_id)
            if not row:
                return
            user_id = row.user_id
            await db.delete(row)
            await db.commit()
        await publish_session_remove(user_id, session_id)

    async def get_all(self) -> List[Session]:
        """Get all sessions"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(SessionRow).order_by(SessionRow.latest_message_at.desc().nullslast())
            )
            return [_row_to_session(r) for r in result.scalars().all()]

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """Update the status of a session"""
        if not await self._update(session_id, status=status.value):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_unread_message_count(self, session_id: str, count: int) -> None:
        """Update the unread message count of a session"""
        if not await self._update(session_id, unread_message_count=count):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def increment_unread_message_count(self, session_id: str) -> None:
        """Atomically increment the unread message count of a session"""
        async with get_session_factory()() as db:
            result = await db.execute(
                update(SessionRow)
                .where(SessionRow.session_id == session_id)
                .values(
                    unread_message_count=SessionRow.unread_message_count + 1,
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def decrement_unread_message_count(self, session_id: str) -> None:
        """Atomically decrement the unread message count of a session"""
        async with get_session_factory()() as db:
            result = await db.execute(
                update(SessionRow)
                .where(SessionRow.session_id == session_id)
                .values(
                    unread_message_count=SessionRow.unread_message_count - 1,
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_shared_status(self, session_id: str, is_shared: bool) -> None:
        """Update the shared status of a session"""
        if not await self._update(session_id, is_shared=is_shared):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_favorite_status(self, session_id: str, is_favorite: bool) -> None:
        """Update the favorite status of a session"""
        if not await self._update(session_id, is_favorite=is_favorite):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_pin_status(self, session_id: str, is_pinned: bool) -> None:
        """Update the pin status of a session"""
        if not await self._update(session_id, is_pinned=is_pinned):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def update_project_id(self, session_id: str, project_id: Optional[str]) -> None:
        """Assign or clear project association for a session"""
        if not await self._update(session_id, project_id=project_id):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)

    async def clear_project_id(self, project_id: str) -> None:
        """Clear project_id from all sessions belonging to a project"""
        async with get_session_factory()() as db:
            result = await db.execute(
                select(SessionRow.session_id, SessionRow.user_id).where(
                    SessionRow.project_id == project_id
                )
            )
            affected = result.all()
            await db.execute(
                update(SessionRow)
                .where(SessionRow.project_id == project_id)
                .values(project_id=None, updated_at=datetime.now(UTC))
            )
            await db.commit()
        for user_id, session_id in [(r[1], r[0]) for r in affected]:
            await publish_session_upsert(user_id, session_id)

    async def update_task_mode(self, session_id: str, task_mode: str) -> None:
        """Update session task mode (agent | chat)"""
        if not await self._update(session_id, task_mode=task_mode):
            raise ValueError(f"Session {session_id} not found")
        await self._notify_upsert(session_id)
