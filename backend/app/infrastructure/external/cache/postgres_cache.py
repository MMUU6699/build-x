"""PostgreSQL implementation of the Cache interface (replaces RedisCache).

Values live in ``cache_entries`` as JSONB with an optional absolute
``expires_at``. Key patterns use Redis-style ``*``/``?`` wildcards, translated
to SQL ``LIKE``.
"""

import json
import logging
import re
from typing import Optional, Any
from datetime import datetime, timedelta, UTC

from sqlalchemy import delete, select, update

from app.domain.external.cache import Cache
from app.infrastructure.models.postgres import CacheRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


def _redis_pattern_to_like(pattern: str) -> str:
    """Translate Redis KEYS pattern (``*``, ``?``) into SQL LIKE pattern."""
    like = re.escape(pattern)
    like = like.replace(r"\*", "%").replace(r"\?", "_")
    return like


class PostgresCache:
    """Postgres implementation of the Cache interface."""

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now(UTC) + timedelta(seconds=max(1, ttl))
            async with get_session_factory()() as db:
                row = await db.get(CacheRow, key)
                if row:
                    row.value = json.loads(json.dumps(value, default=str))
                    row.expires_at = expires_at
                else:
                    db.add(CacheRow(
                        cache_key=key,
                        value=json.loads(json.dumps(value, default=str)),
                        expires_at=expires_at,
                    ))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        try:
            async with get_session_factory()() as db:
                row = await db.get(CacheRow, key)
                if not row:
                    return None
                if row.expires_at and row.expires_at <= datetime.now(UTC):
                    await db.delete(row)
                    await db.commit()
                    return None
                return row.value
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        try:
            async with get_session_factory()() as db:
                result = await db.execute(
                    delete(CacheRow).where(CacheRow.cache_key == key)
                )
                await db.commit()
                return result.rowcount and result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            async with get_session_factory()() as db:
                row = await db.get(CacheRow, key)
                if not row:
                    return False
                if row.expires_at and row.expires_at <= datetime.now(UTC):
                    await db.delete(row)
                    await db.commit()
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to check existence of cache key {key}: {str(e)}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        try:
            async with get_session_factory()() as db:
                row = await db.get(CacheRow, key)
                if not row or not row.expires_at:
                    return None
                remaining = int((row.expires_at - datetime.now(UTC)).total_seconds())
                if remaining <= 0:
                    await db.delete(row)
                    await db.commit()
                    return None
                return remaining
        except Exception as e:
            logger.error(f"Failed to get TTL for cache key {key}: {str(e)}")
            return None

    async def keys(self, pattern: str) -> list[str]:
        try:
            like = _redis_pattern_to_like(pattern)
            async with get_session_factory()() as db:
                now = datetime.now(UTC)
                result = await db.execute(
                    select(CacheRow.cache_key).where(
                        CacheRow.cache_key.like(like),
                        (CacheRow.expires_at.is_(None)) | (CacheRow.expires_at > now),
                    )
                )
                return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {str(e)}")
            return []

    async def clear_pattern(self, pattern: str) -> int:
        try:
            like = _redis_pattern_to_like(pattern)
            async with get_session_factory()() as db:
                result = await db.execute(
                    delete(CacheRow).where(CacheRow.cache_key.like(like))
                )
                await db.commit()
                return result.rowcount or 0
        except Exception as e:
            logger.error(f"Failed to clear keys with pattern {pattern}: {str(e)}")
            return 0
