"""Supabase Storage file storage (replaces GridFS).

Objects are stored at ``{bucket}/{user_id}/{file_id}``; metadata lives in the
``files`` table (Postgres). Downloads for the frontend keep flowing through
the existing signed-URL flow (``/api/v1/files/{id}``), which streams from
this storage.
"""
import io
import logging
import uuid
from typing import BinaryIO, Optional, Dict, Any, Tuple
from datetime import datetime, UTC

import httpx

from app.domain.external.file import FileStorage
from app.domain.models.file import FileInfo
from app.core.config import get_settings
from app.infrastructure.models.postgres import FileRow
from app.infrastructure.storage.postgres import get_session_factory
from functools import lru_cache

logger = logging.getLogger(__name__)


class SupabaseStorageNotConfiguredError(RuntimeError):
    """Raised when Supabase Storage is used without SUPABASE_URL/keys."""


class SupabaseFileStorage(FileStorage):
    """Supabase Storage implementation of the file storage interface."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (self.settings.supabase_url or "").rstrip("/")
        self.service_key = self.settings.supabase_service_key
        self.bucket = self.settings.supabase_storage_bucket or "files"

    def _require_config(self) -> None:
        if not self.base_url or not self.service_key:
            raise SupabaseStorageNotConfiguredError(
                "Supabase Storage is not configured (set SUPABASE_URL and "
                "SUPABASE_SERVICE_KEY)"
            )

    def _admin_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_path(self, user_id: str, file_id: str) -> str:
        return f"{user_id}/{file_id}"

    def _row_to_file_info(self, row: FileRow) -> FileInfo:
        return FileInfo(
            file_id=row.file_id,
            filename=row.filename,
            content_type=row.content_type,
            size=row.size,
            upload_date=row.upload_date,
            metadata=dict(row.metadata_ or {}),
            user_id=row.user_id,
        )

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        user_id: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileInfo:
        """Upload file to Supabase Storage + record metadata in Postgres."""
        try:
            self._require_config()
            data = file_data.read()
            file_id = uuid.uuid4().hex
            path = self._object_path(user_id, file_id)

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                    headers=self._admin_headers(
                        content_type or "application/octet-stream"
                    ),
                    content=data,
                    params={"upsert": "true"},
                )
            if resp.status_code >= 400:
                logger.error(
                    f"Supabase storage upload failed ({resp.status_code}): {resp.text}"
                )
                raise RuntimeError(f"Storage upload failed: {resp.text[:200]}")

            file_metadata = {
                "filename": filename,
                "user_id": user_id,
                **(metadata or {}),
            }
            upload_date = datetime.now(UTC)
            async with get_session_factory()() as db:
                db.add(FileRow(
                    file_id=file_id,
                    storage_path=path,
                    filename=filename,
                    content_type=content_type,
                    size=len(data),
                    upload_date=upload_date,
                    metadata=file_metadata,
                    user_id=user_id,
                ))
                await db.commit()

            logger.info(f"File uploaded successfully: {filename} (ID: {file_id}) for user {user_id}")
            return FileInfo(
                file_id=file_id,
                filename=filename,
                size=len(data),
                content_type=content_type,
                upload_date=upload_date,
                metadata=file_metadata,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Failed to upload file {filename} for user {user_id}: {str(e)}")
            raise

    async def _get_file_row(self, db, file_id: str) -> Optional[FileRow]:
        return await db.get(FileRow, file_id)

    async def download_file(self, file_id: str, user_id: Optional[str] = None) -> Tuple[BinaryIO, FileInfo]:
        """Download file by file ID from Supabase Storage."""
        self._require_config()
        async with get_session_factory()() as db:
            row = await self._get_file_row(db, file_id)
            if not row:
                raise FileNotFoundError(f"File not found with ID: {file_id}")
            if user_id is not None and row.user_id != user_id:
                raise PermissionError(f"Access denied: file {file_id} does not belong to user {user_id}")
            info = self._row_to_file_info(row)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{row.storage_path}",
                headers=self._admin_headers(),
            )
        if resp.status_code >= 400:
            raise FileNotFoundError(f"File not found in storage: {file_id}")

        stream = io.BytesIO(resp.content)
        stream.seek(0)
        return stream, info

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from Supabase Storage + Postgres metadata."""
        self._require_config()
        async with get_session_factory()() as db:
            row = await self._get_file_row(db, file_id)
            if not row:
                return False
            if row.user_id != user_id:
                logger.warning(f"Delete access denied: file {file_id} does not belong to user {user_id}")
                return False
            path = row.storage_path

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.delete(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers=self._admin_headers(),
            )

        async with get_session_factory()() as db:
            row = await self._get_file_row(db, file_id)
            if row:
                await db.delete(row)
                await db.commit()

        if resp.status_code >= 400:
            logger.warning(f"Storage object delete returned {resp.status_code}: {resp.text}")
        logger.info(f"File deleted successfully: {file_id} by user {user_id}")
        return True

    async def get_file_info(self, file_id: str, user_id: Optional[str] = None) -> Optional[FileInfo]:
        """Get file metadata from the files table."""
        async with get_session_factory()() as db:
            row = await self._get_file_row(db, file_id)
            if not row:
                return None
            if user_id is not None and row.user_id != user_id:
                logger.warning(f"Access denied: file {file_id} does not belong to user {user_id}")
                return None
            return self._row_to_file_info(row)


@lru_cache()
def get_file_storage() -> FileStorage:
    """Get file storage instance."""
    return SupabaseFileStorage()
