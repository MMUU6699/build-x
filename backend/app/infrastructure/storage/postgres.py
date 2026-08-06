"""PostgreSQL storage layer (SQLAlchemy 2.0 async + asyncpg).

Owns the async engine/session factory used by all repositories and the
dedicated asyncpg pool used for LISTEN/NOTIFY (session-list pub/sub).

Schema is defined in ``app.infrastructure.models.postgres`` (ORM) and the
canonical DDL lives in ``backend/supabase_schema.sql`` (applied via the
Supabase SQL editor or the migration script for hosted instances).
"""
import logging
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_notify_pool: Optional[asyncpg.Pool] = None


def _asyncpg_dsn() -> str:
    """Strip the SQLAlchemy driver prefix for direct asyncpg use."""
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("PostgreSQL engine not initialized")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("PostgreSQL session factory not initialized")
    return _session_factory


async def get_notify_pool() -> asyncpg.Pool:
    """Dedicated asyncpg pool used for LISTEN/NOTIFY (session list pub/sub)."""
    global _notify_pool
    if _notify_pool is None:
        _notify_pool = await asyncpg.create_pool(
            dsn=_asyncpg_dsn(),
            min_size=1,
            max_size=10,
        )
    return _notify_pool


async def initialize() -> None:
    """Create the async engine, session factory, and tables (dev only)."""
    global _engine, _session_factory
    settings = get_settings()
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("PostgreSQL engine initialized")

    # Attempt to create tables. On hosted Supabase the schema must be applied
    # via supabase_schema.sql (the app role may lack DDL privileges); failure
    # here is non-fatal, the app will surface missing-table errors otherwise.
    try:
        from app.infrastructure.models import postgres as models  # noqa: F401
        from sqlalchemy import text

        async with _engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("PostgreSQL schema ensured (create_all)")
    except Exception as e:
        logger.warning(f"PostgreSQL create_all skipped/failed (run supabase_schema.sql): {e}")


async def shutdown() -> None:
    """Dispose the engine and close the notify pool."""
    global _engine, _session_factory, _notify_pool
    if _notify_pool is not None:
        try:
            await _notify_pool.close()
        except Exception as e:
            logger.warning(f"Failed to close notify pool: {e}")
        _notify_pool = None
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception as e:
            logger.warning(f"Failed to dispose engine: {e}")
        _engine = None
        _session_factory = None
    logger.info("PostgreSQL engine shut down")


async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session with commit-on-exit semantics."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
