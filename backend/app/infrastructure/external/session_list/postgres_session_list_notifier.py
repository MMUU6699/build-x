"""Postgres LISTEN/NOTIFY notifier for the session list WebSocket.

Replaces the Redis pub/sub implementation. Each subscriber (WebSocket) owns
a dedicated asyncpg connection running ``LISTEN`` and receives notifications
through asyncpg's callback-based listener API (``add_listener``), which works
on any PostgreSQL 9.5+, including Supabase and local Postgres.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Callable, Literal, Optional

from app.infrastructure.storage.postgres import get_notify_pool

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "session_list:"


def channel_for_user(user_id: str) -> str:
    """Postgres channel identifiers are limited to 63 bytes."""
    return f"{CHANNEL_PREFIX}{user_id}"[:63]


async def publish_session_upsert(user_id: str, session_id: str) -> None:
    await _publish(user_id, {"op": "upsert", "session_id": session_id})


async def publish_session_remove(user_id: str, session_id: str) -> None:
    await _publish(user_id, {"op": "remove", "session_id": session_id})


async def _publish(user_id: str, payload: dict[str, Any]) -> None:
    try:
        pool = await get_notify_pool()
        await pool.execute(
            "SELECT pg_notify($1, $2)",
            channel_for_user(user_id),
            json.dumps(payload),
        )
    except Exception as e:
        logger.warning("Failed to publish session list notify for user %s: %s", user_id, e)


def parse_notify_payload(raw: str) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    op: Literal["upsert", "remove"] | None = data.get("op")
    session_id = data.get("session_id")
    if op not in ("upsert", "remove") or not session_id:
        return None
    return data


async def subscribe_session_list(
    user_id: str,
    keepalive_seconds: float = 20.0,
) -> AsyncGenerator[Optional[dict[str, Any]], None]:
    """Yield session-list notifications for the user.

    Yields ``None`` as a keepalive heartbeat when no notification arrived
    within ``keepalive_seconds``, so callers can send WS pings.
    """
    pool = await get_notify_pool()
    conn = await pool.acquire()
    channel = channel_for_user(user_id)
    queue: asyncio.Queue[Optional[dict[str, Any]]] = asyncio.Queue()

    def _on_notification(_conn: Any, _pid: int, _channel: str, payload: str) -> None:
        parsed = parse_notify_payload(payload)
        if parsed is not None:
            queue.put_nowait(parsed)

    await conn.add_listener(channel, _on_notification)
    logger.debug("Session list listener started for user %s (channel %s)", user_id, channel)
    last_ping = time.monotonic()
    try:
        while True:
            remaining = keepalive_seconds - (time.monotonic() - last_ping)
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=max(remaining, 0.0))
            except asyncio.TimeoutError:
                last_ping = time.monotonic()
                yield None
                continue
            last_ping = time.monotonic()
            yield payload
    finally:
        try:
            await conn.remove_listener(channel, _on_notification)
        except Exception:
            logger.debug("Failed to remove listener for %s", channel, exc_info=True)
        await pool.release(conn)
