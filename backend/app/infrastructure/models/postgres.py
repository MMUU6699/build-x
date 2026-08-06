"""SQLAlchemy ORM models for PostgreSQL (replaces Beanie documents).

Canonical DDL: ``backend/supabase_schema.sql`` (hand-editable for hosted
Supabase); ``Base.metadata.create_all`` covers local development.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.storage.postgres import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json(obj: Any) -> Any:
    """Serialize an object to a JSON-safe value (fallback for non-JSON types)."""
    if obj is None:
        return None
    return json.loads(json.dumps(obj, default=str))


class UserRow(Base):
    """User profile row (identity lives in Supabase Auth; no hashes stored)."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fullname: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentRow(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    memories: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SessionRow(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_latest", "user_id", "latest_message_at"),
        Index("ix_sessions_user_favorite", "user_id", "is_favorite"),
        Index("ix_sessions_user_pinned_latest", "user_id", "is_pinned", "latest_message_at"),
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sandbox_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unread_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latest_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    events: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    files: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="agent")


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_user_pinned_sort", "user_id", "is_pinned", "sort_order", "updated_at"),
    )

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class FileFavoriteRow(Base):
    __tablename__ = "file_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "file_id", name="uq_file_favorites_user_file"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class ClawRow(Base):
    __tablename__ = "claws"

    claw_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    container_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    container_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="creating")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    messages: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class AuthSessionRow(Base):
    """Opaque server-side auth sessions (replaces Redis session keys)."""

    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    client: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    rotated_from: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class CacheRow(Base):
    __tablename__ = "cache_entries"

    cache_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class TaskStreamRow(Base):
    """Message queue rows (replaces Redis Streams).

    ``id`` is the monotonic cursor: queue message ids are ``str(id)``.
    ``claimed_at``/``claimed_by`` support concurrency-safe pops.
    """

    __tablename__ = "task_streams"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    stream_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class TaskMetaRow(Base):
    """Cross-process task metadata (status + runner params)."""

    __tablename__ = "task_meta"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    params: Mapped[Any] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class TaskCancelRow(Base):
    """Cancellation flags polled by Celery workers."""

    __tablename__ = "task_cancel"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class FileRow(Base):
    """File metadata rows (object content lives in Supabase Storage)."""

    __tablename__ = "files"

    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
