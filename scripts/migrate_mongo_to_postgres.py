"""One-off migration from the legacy MongoDB stack to PostgreSQL.

Reads the legacy Beanie collections (users/agents/sessions/projects/
file_favorites/claws) plus GridFS metadata (fs.files) and writes them into
the new PostgreSQL schema (see backend/supabase_schema.sql and
app/infrastructure/models/postgres.py).

Legacy Redis-only data (auth sessions, cache entries, task streams, task
meta/cancel flags) is intentionally NOT migrated — those are transient.

Object blobs live in Supabase Storage, not the files table; this script only
re-creates the metadata rows so downloads keep working once objects are
re-uploaded to {bucket}/{user_id}/{file_id}.

Usage:
    pip install pymongo psycopg2-binary
    python scripts/migrate_mongo_to_postgres.py \
        --mongo-uri mongodb://localhost:27017 \
        --mongo-db build_x \
        --database-url postgresql+psycopg2://build_x:build_x@localhost:5432/build_x
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BATCH_SIZE = 1000


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _load_dotenv() -> None:
    for env_file in (REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _rows_to_jsonb(docs: Iterable[Dict[str, Any]]) -> Optional[Any]:
    """JSONB-safe value; falls back to str for ObjectId/date/bytes."""
    try:
        return json.loads(json.dumps(list(docs), default=str))
    except Exception:
        return None


def _insert_or_ignore(session: Any, model: Any, rows: List[Dict[str, Any]]) -> int:
    from sqlalchemy.dialects.postgresql import insert

    if not rows:
        return 0
    stmt = insert(model).values(rows).on_conflict_do_nothing(index_elements=model.__table__.primary_key.columns.keys())
    result = session.execute(stmt)
    return result.rowcount or 0


def migrate_users(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import UserRow

    rows = [
        {
            "user_id": doc.get("user_id", ""),
            "fullname": doc.get("fullname") or doc.get("email") or "user",
            "email": doc.get("email", ""),
            "role": "user",
            "is_active": bool(doc.get("is_active", True)),
            "created_at": _utc(doc.get("created_at")),
            "updated_at": _utc(doc.get("updated_at")),
            "last_login_at": _utc(doc.get("last_login_at")),
        }
        for doc in db["users"].find()
        if doc.get("user_id")
    ]
    return _insert_or_ignore(session, UserRow, rows)


def migrate_agents(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import AgentRow

    rows = []
    for doc in db["agents"].find():
        if not doc.get("agent_id"):
            continue
        rows.append(
            {
                "agent_id": doc["agent_id"],
                "model_name": doc.get("model_name") or "",
                "temperature": float(doc.get("temperature", 0.7)),
                "max_tokens": int(doc.get("max_tokens", 2000)),
                "memories": _rows_to_jsonb([doc.get("memories") or {}]) or {},
                "created_at": _utc(doc.get("created_at")),
                "updated_at": _utc(doc.get("updated_at")),
            }
        )
    return _insert_or_ignore(session, AgentRow, rows)


def migrate_sessions(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import SessionRow

    rows = []
    for doc in db["sessions"].find():
        if not doc.get("session_id"):
            continue
        rows.append(
            {
                "session_id": doc["session_id"],
                "user_id": doc.get("user_id", ""),
                "sandbox_id": doc.get("sandbox_id"),
                "agent_id": doc.get("agent_id", ""),
                "task_id": doc.get("task_id"),
                "title": doc.get("title"),
                "unread_message_count": int(doc.get("unread_message_count", 0)),
                "latest_message": doc.get("latest_message"),
                "latest_message_at": _utc(doc.get("latest_message_at")),
                "created_at": _utc(doc.get("created_at")),
                "updated_at": _utc(doc.get("updated_at")),
                "events": _rows_to_jsonb(doc.get("events") or []) or [],
                "files": _rows_to_jsonb(doc.get("files") or []) or [],
                "status": "done",
                "is_shared": bool(doc.get("is_shared", False)),
                "is_favorite": bool(doc.get("is_favorite", False)),
                "is_pinned": bool(doc.get("is_pinned", False)),
                "project_id": doc.get("project_id"),
                "task_mode": doc.get("task_mode") or "agent",
            }
        )
    return _insert_or_ignore(session, SessionRow, rows)


def migrate_projects(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import ProjectRow

    rows = [
        {
            "project_id": doc["project_id"],
            "user_id": doc.get("user_id", ""),
            "name": doc.get("name") or "Untitled",
            "instruction": doc.get("instruction"),
            "is_pinned": bool(doc.get("is_pinned", False)),
            "sort_order": int(doc.get("sort_order", 0)),
            "created_at": _utc(doc.get("created_at")),
            "updated_at": _utc(doc.get("updated_at")),
        }
        for doc in db["projects"].find()
        if doc.get("project_id")
    ]
    return _insert_or_ignore(session, ProjectRow, rows)


def migrate_file_favorites(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import FileFavoriteRow

    rows = [
        {"user_id": doc.get("user_id", ""), "file_id": doc.get("file_id", "")}
        for doc in db["file_favorites"].find()
        if doc.get("file_id")
    ]
    return _insert_or_ignore(session, FileFavoriteRow, rows)


def migrate_claws(session: Any, db: Any) -> int:
    from app.infrastructure.models.postgres import ClawRow

    rows = []
    for doc in db["claws"].find():
        if not doc.get("claw_id"):
            continue
        rows.append(
            {
                "claw_id": doc["claw_id"],
                "user_id": doc.get("user_id", ""),
                "container_name": doc.get("container_name"),
                "container_ip": doc.get("container_ip"),
                "api_key": doc.get("api_key", ""),
                "status": "running",
                "error_message": doc.get("error_message"),
                "expires_at": _utc(doc.get("expires_at")),
                "messages": _rows_to_jsonb(doc.get("messages") or []) or [],
                "created_at": _utc(doc.get("created_at")),
                "updated_at": _utc(doc.get("updated_at")),
            }
        )
    return _insert_or_ignore(session, ClawRow, rows)


def migrate_files(session: Any, db: Any, bucket: str) -> int:
    from app.infrastructure.models.postgres import FileRow

    rows = []
    for doc in db["fs.files"].find():
        file_id = str(doc.get("_id", ""))
        if not file_id:
            continue
        metadata = doc.get("metadata") or {}
        user_id = str(metadata.get("user_id", ""))
        rows.append(
            {
                "file_id": file_id,
                "storage_path": f"{bucket}/{user_id}/{file_id}",
                "filename": doc.get("filename", f"file_{file_id}"),
                "content_type": metadata.get("contentType"),
                "size": int(doc.get("length", 0)),
                "upload_date": _utc(doc.get("uploadDate")) or datetime.now(timezone.utc),
                "metadata": metadata,
                "user_id": user_id,
            }
        )
    return _insert_or_ignore(session, FileRow, rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--mongo-db", default=os.environ.get("MONGODB_DATABASE", "build_x"))
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql+psycopg2://build_x:build_x@localhost:5432/build_x"),
        help="SQLAlchemy URL (sync driver, e.g. postgresql+psycopg2://...)",
    )
    parser.add_argument("--bucket", default=os.environ.get("SUPABASE_STORAGE_BUCKET", "files"))
    parser.add_argument("--no-files", action="store_true", help="Skip GridFS metadata migration")
    args = parser.parse_args()

    _load_dotenv()

    try:
        import pymongo
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
    except ImportError as e:
        print(f"Missing dependency: {e}\nRun: pip install pymongo psycopg2-binary sqlalchemy")
        return 1

    mongo = pymongo.MongoClient(args.mongo_uri, serverSelectionTimeoutMS=10000)
    db = mongo[args.mongo_db]
    engine = create_engine(args.database_url, pool_pre_ping=True)

    counts: Dict[str, int] = {}
    with Session(engine) as session:
        counts["users"] = migrate_users(session, db)
        counts["agents"] = migrate_agents(session, db)
        counts["sessions"] = migrate_sessions(session, db)
        counts["projects"] = migrate_projects(session, db)
        counts["file_favorites"] = migrate_file_favorites(session, db)
        counts["claws"] = migrate_claws(session, db)
        if not args.no_files:
            counts["files"] = migrate_files(session, db, args.bucket)
        session.commit()

    mongo.close()
    engine.dispose()

    print("Migration summary (rows inserted, skips on existing keys):")
    for name, count in counts.items():
        print(f"  {name:16s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
