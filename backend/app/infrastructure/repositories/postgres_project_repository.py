import logging
from typing import Optional, List
from datetime import datetime, UTC

from app.domain.models.project import Project
from app.domain.repositories.project_repository import ProjectRepository
from app.infrastructure.models.postgres import ProjectRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


def _row_to_project(row: ProjectRow) -> Project:
    return Project(
        id=row.project_id,
        user_id=row.user_id,
        name=row.name,
        instruction=row.instruction,
        is_pinned=row.is_pinned,
        sort_order=row.sort_order,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresProjectRepository(ProjectRepository):
    """PostgreSQL implementation of ProjectRepository"""

    async def save(self, project: Project) -> None:
        async with get_session_factory()() as db:
            row = await db.get(ProjectRow, project.id)
            if row is None:
                db.add(ProjectRow(
                    project_id=project.id,
                    user_id=project.user_id,
                    name=project.name,
                    instruction=project.instruction,
                    is_pinned=project.is_pinned,
                    sort_order=project.sort_order,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                ))
            else:
                row.user_id = project.user_id
                row.name = project.name
                row.instruction = project.instruction
                row.is_pinned = project.is_pinned
                row.sort_order = project.sort_order
                row.updated_at = datetime.now(UTC)
            await db.commit()

    async def find_by_id(self, project_id: str) -> Optional[Project]:
        async with get_session_factory()() as db:
            row = await db.get(ProjectRow, project_id)
            return _row_to_project(row) if row else None

    async def find_by_id_and_user_id(self, project_id: str, user_id: str) -> Optional[Project]:
        from sqlalchemy import select
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ProjectRow).where(
                    ProjectRow.project_id == project_id,
                    ProjectRow.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            return _row_to_project(row) if row else None

    async def find_by_user_id(self, user_id: str) -> List[Project]:
        from sqlalchemy import select
        async with get_session_factory()() as db:
            result = await db.execute(
                select(ProjectRow)
                .where(ProjectRow.user_id == user_id)
                .order_by(
                    ProjectRow.is_pinned.desc(),
                    ProjectRow.sort_order.asc(),
                    ProjectRow.updated_at.desc(),
                )
            )
            return [_row_to_project(r) for r in result.scalars().all()]

    async def delete(self, project_id: str) -> None:
        async with get_session_factory()() as db:
            row = await db.get(ProjectRow, project_id)
            if row:
                await db.delete(row)
                await db.commit()

    async def update_pin(self, project_id: str, is_pinned: bool) -> None:
        from sqlalchemy import update
        async with get_session_factory()() as db:
            result = await db.execute(
                update(ProjectRow)
                .where(ProjectRow.project_id == project_id)
                .values(is_pinned=is_pinned, updated_at=datetime.now(UTC))
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Project {project_id} not found")

    async def update_name(self, project_id: str, name: str, instruction: Optional[str] = None) -> None:
        from sqlalchemy import update
        values = {"name": name, "updated_at": datetime.now(UTC)}
        if instruction is not None:
            values["instruction"] = instruction
        async with get_session_factory()() as db:
            result = await db.execute(
                update(ProjectRow).where(ProjectRow.project_id == project_id).values(**values)
            )
            await db.commit()
            if not (result.rowcount or 0):
                raise ValueError(f"Project {project_id} not found")
