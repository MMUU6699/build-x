"""Celery-backed Task implementation.

The API process only enqueues tasks and reads/writes Postgres: agent
execution happens in Celery worker processes (see celery_worker.py).
Cross-process state lives entirely in Postgres:

- ``task:input:{id}`` / ``task:output:{id}``  — stream queue rows for messages/events
- ``task_meta`` row                             — task status + runner params (JSON)
- ``task_cancel`` row                           — cancellation flag polled by the worker

This makes tasks visible from any API replica and survives API restarts,
unlike the in-process registry of PostgresStreamTask.
"""
import uuid
import logging
from typing import Any, Dict, Optional
from datetime import datetime, UTC

from sqlalchemy import delete

from app.domain.external.task import Task, TaskRunnerFactory
from app.infrastructure.external.message_queue.postgres_stream_queue import PostgresStreamQueue, MessageQueue
from app.infrastructure.models.postgres import TaskCancelRow, TaskMetaRow
from app.infrastructure.storage.postgres import get_session_factory
from app.infrastructure.external.task.celery_app import celery_app, AGENT_TASK_NAME

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"


async def read_meta(task_id: str) -> Optional[Dict[str, Any]]:
    async with get_session_factory()() as db:
        row = await db.get(TaskMetaRow, task_id)
        if row is None:
            return None
        return {"status": row.status, "params": row.params}


async def write_meta(task_id: str, status: str, params: Optional[Dict[str, Any]] = None) -> None:
    async with get_session_factory()() as db:
        row = await db.get(TaskMetaRow, task_id)
        if row is None:
            row = TaskMetaRow(task_id=task_id, status=status, params=params)
            db.add(row)
        else:
            row.status = status
            if params is not None:
                row.params = params
            row.updated_at = datetime.now(UTC)
        await db.commit()


async def request_cancel(task_id: str) -> None:
    async with get_session_factory()() as db:
        row = await db.get(TaskCancelRow, task_id)
        if row is None:
            db.add(TaskCancelRow(task_id=task_id))
            await db.commit()


async def is_cancel_requested(task_id: str) -> bool:
    async with get_session_factory()() as db:
        row = await db.get(TaskCancelRow, task_id)
        return row is not None


async def clear_cancel(task_id: str) -> None:
    async with get_session_factory()() as db:
        await db.execute(delete(TaskCancelRow).where(TaskCancelRow.task_id == task_id))
        await db.commit()


class CeleryTask(Task):
    """Task handle that enqueues agent execution onto Celery workers."""

    _runner_factory: Optional[TaskRunnerFactory] = None

    def __init__(self, task_id: str, params: Optional[Dict[str, Any]] = None):
        self._id = task_id
        self._params = params
        self._input_stream = PostgresStreamQueue(f"task:input:{task_id}")
        self._output_stream = PostgresStreamQueue(f"task:output:{task_id}")

    @property
    def id(self) -> str:
        """Task ID."""
        return self._id

    @property
    def input_stream(self) -> MessageQueue:
        """Input stream."""
        return self._input_stream

    @property
    def output_stream(self) -> MessageQueue:
        """Output stream."""
        return self._output_stream

    async def is_done(self) -> bool:
        """Check if the task is done (from Postgres metadata)."""
        meta = await read_meta(self._id)
        if meta is None:
            return True
        return meta.get("status") == STATUS_DONE

    async def run(self) -> None:
        """Enqueue the task onto a Celery worker if it is not already running."""
        meta = await read_meta(self._id)
        status = meta.get("status") if meta else None
        if self._params is None and meta:
            self._params = meta.get("params")

        if status in (None, STATUS_DONE):
            if self._params is None:
                raise RuntimeError(f"Task {self._id} has no runner params to run with")
            await clear_cancel(self._id)
            await write_meta(self._id, STATUS_PENDING, self._params)
            celery_app.send_task(AGENT_TASK_NAME, args=[self._id, self._params], task_id=self._id)
            logger.info(f"Task {self._id} enqueued to Celery")

    async def cancel(self) -> bool:
        """Request cancellation of the task.

        The worker that owns the task polls the cancel flag and cancels the
        agent coroutine, which emits a DoneEvent and completes the session.

        Returns:
            bool: True if cancellation was requested, False if already done
        """
        if await self.is_done():
            return False
        await request_cancel(self._id)
        logger.info(f"Task {self._id} cancellation requested")
        return True

    @classmethod
    def set_runner_factory(cls, factory: TaskRunnerFactory) -> None:
        """Register the factory used by workers to rebuild task runners."""
        cls._runner_factory = factory

    @classmethod
    def get_runner_factory(cls) -> TaskRunnerFactory:
        if cls._runner_factory is None:
            raise RuntimeError("No TaskRunnerFactory registered for CeleryTask")
        return cls._runner_factory

    @classmethod
    async def get(cls, task_id: str) -> Optional["CeleryTask"]:
        """Get a task handle by its ID (from Postgres metadata)."""
        meta = await read_meta(task_id)
        if meta is None:
            return None
        return cls(task_id, params=meta.get("params"))

    @classmethod
    def create(cls, params: Dict[str, Any]) -> "CeleryTask":
        """Create a new task handle from serializable runner parameters."""
        return cls(str(uuid.uuid4()), params=params)

    @classmethod
    async def destroy(cls) -> None:
        """Destroy all task instances.

        Tasks are owned by Celery workers, not the API process, so API
        shutdown intentionally leaves them running.
        """
        logger.info("CeleryTask.destroy: tasks are owned by workers, nothing to do")

    def __repr__(self) -> str:
        return f"CeleryTask(id={self._id})"
