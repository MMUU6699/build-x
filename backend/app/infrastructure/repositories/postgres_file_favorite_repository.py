import logging
from typing import Set
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.domain.repositories.file_favorite_repository import FileFavoriteRepository
from app.infrastructure.models.postgres import FileFavoriteRow
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


class PostgresFileFavoriteRepository(FileFavoriteRepository):
    """PostgreSQL implementation of FileFavoriteRepository"""

    async def set_favorite(self, user_id: str, file_id: str, is_favorite: bool) -> None:
        async with get_session_factory()() as db:
            if is_favorite:
                result = await db.execute(
                    select(FileFavoriteRow.id).where(
                        FileFavoriteRow.user_id == user_id,
                        FileFavoriteRow.file_id == file_id,
                    )
                )
                if result.first():
                    return
                db.add(FileFavoriteRow(
                    user_id=user_id,
                    file_id=file_id,
                    created_at=datetime.now(timezone.utc),
                ))
                logger.info("File %s favorited by user %s", file_id, user_id)
            else:
                result = await db.execute(
                    delete(FileFavoriteRow).where(
                        FileFavoriteRow.user_id == user_id,
                        FileFavoriteRow.file_id == file_id,
                    )
                )
                if (result.rowcount or 0) > 0:
                    logger.info("File %s unfavorited by user %s", file_id, user_id)
            await db.commit()

    async def list_favorite_file_ids(self, user_id: str) -> Set[str]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(FileFavoriteRow.file_id).where(FileFavoriteRow.user_id == user_id)
            )
            return {row[0] for row in result.all()}
