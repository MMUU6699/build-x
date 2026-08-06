"""Celery application shared by the API process (producer) and workers (consumer).

The broker defaults to the same PostgreSQL instance used for streams/caching
(SQLAlchemy transport), and can be overridden with the CELERY_BROKER_URL
setting. Results are not stored in a Celery result backend: task state is
tracked in Postgres metadata rows (see celery_task.py), and all agent events
flow through the Postgres stream queue.
"""
import logging

from celery import Celery

from app.core.config import get_settings

logger = logging.getLogger(__name__)

AGENT_TASK_NAME = "build_x.agent.run"


def _build_postgres_broker_url() -> str:
    """Derive a sync SQLAlchemy broker URL from the async DATABASE_URL."""
    settings = get_settings()
    url = settings.database_url or ""
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        return f"db+{url}"
    raise RuntimeError(
        "TASK_BACKEND=celery requires a postgresql DATABASE_URL or CELERY_BROKER_URL"
    )


def _create_celery_app() -> Celery:
    settings = get_settings()
    broker_url = settings.celery_broker_url or _build_postgres_broker_url()
    app = Celery("build_x", broker=broker_url)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        # Task state is tracked via Postgres metadata rows, not a result backend
        task_ignore_result=True,
        # Agent tasks are long-running; don't prefetch more than one per worker process
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = _create_celery_app()
