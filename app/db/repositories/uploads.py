"""Uploaded documents in Postgres (US-00-002). The queue the worker reads is `documents.py`.

An upload takes a transaction-scoped advisory lock on its application, so two uploads of the same
bytes cannot both pass the "already stored" check. List index decision (database rules): documents
per application are a handful, so the application index is enough for the newest-first read.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.statuses import recompute_status
from app.domain.paging import decode_cursor, encode_cursor
from app.domain.uploads import StoredImage

_APPLICATION_EXISTS = text("SELECT 1 FROM applications WHERE id = :id AND erased_at IS NULL")
_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text), 0))")
_BY_HASH = text(
    "SELECT id, application_id, detected_type::text, status::text, failure_reason, is_current, "
    "created_at FROM documents WHERE application_id = :application_id AND sha256 = :sha256"
)
_INSERT_DOCUMENT = text(
    "INSERT INTO documents (application_id, uploaded_by, source_content_type, sha256, size_bytes) "
    "VALUES (:application_id, :uploaded_by, :source_content_type, :sha256, :size_bytes) "
    "RETURNING id, application_id, detected_type::text, status::text, failure_reason, is_current, "
    "created_at"
)
_INSERT_BLOB = text(
    "INSERT INTO document_blobs (document_id, content_type, content) "
    "VALUES (:document_id, :content_type, :content)"
)
_LIST = text(
    "SELECT id, application_id, detected_type::text, status::text, failure_reason, is_current, "
    "created_at FROM documents WHERE application_id = :application_id "
    "AND (CAST(:cursor_at AS timestamptz) IS NULL "
    "OR (created_at, id) < (CAST(:cursor_at AS timestamptz), CAST(:cursor_id AS uuid))) "
    "ORDER BY created_at DESC, id DESC LIMIT :fetch"
)


@dataclass(frozen=True)
class DocumentRecord:
    id: UUID
    application_id: UUID
    detected_type: str | None
    status: str
    failure_reason: str | None
    is_current: bool
    created_at: datetime


@dataclass(frozen=True)
class DocumentPage:
    data: tuple[DocumentRecord, ...]
    next_cursor: str | None


def _record(row: Row[Any]) -> DocumentRecord:
    return DocumentRecord(
        id=row[0],
        application_id=row[1],
        detected_type=row[2],
        status=row[3],
        failure_reason=row[4],
        is_current=row[5],
        created_at=row[6],
    )


class SqlUploadStore:
    """The `documents` and `document_blobs` tables, as the upload and list routes use them."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def application_exists(self, application_id: UUID) -> bool:
        async with self._factory() as session:
            found = (await session.execute(_APPLICATION_EXISTS, {"id": application_id})).first()
        return found is not None

    async def add_document(
        self,
        application_id: UUID,
        uploaded_by: UUID,
        *,
        source_content_type: str,
        sha256: str,
        size_bytes: int,
        stored: StoredImage,
    ) -> tuple[DocumentRecord, bool]:
        """Store the page image, or return the document that already holds these exact bytes."""
        async with self._factory.begin() as session:
            await session.execute(_LOCK, {"id": str(application_id)})
            existing = (
                await session.execute(
                    _BY_HASH, {"application_id": application_id, "sha256": sha256}
                )
            ).first()
            if existing is not None:
                return _record(existing), False
            created = (
                await session.execute(
                    _INSERT_DOCUMENT,
                    {
                        "application_id": application_id,
                        "uploaded_by": uploaded_by,
                        "source_content_type": source_content_type,
                        "sha256": sha256,
                        "size_bytes": size_bytes,
                    },
                )
            ).one()
            record = _record(created)
            await session.execute(
                _INSERT_BLOB,
                {
                    "document_id": record.id,
                    "content_type": stored.content_type,
                    "content": stored.data,
                },
            )
        return record, True

    async def recompute_status(self, application_id: UUID) -> str:
        """Set the application's status again from its documents, now that one more exists."""
        return await recompute_status(self._factory, application_id)

    async def list_documents(
        self, application_id: UUID, *, limit: int, cursor: str | None
    ) -> DocumentPage:
        """One page of an application's documents, newest first."""
        cursor_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        async with self._factory() as session:
            rows = (
                await session.execute(
                    _LIST,
                    {
                        "application_id": application_id,
                        "cursor_at": cursor_at,
                        "cursor_id": str(cursor_id) if cursor_id else None,
                        "fetch": limit + 1,
                    },
                )
            ).all()
        records = tuple(_record(r) for r in rows)
        page = records[:limit]
        more = len(records) > limit
        return DocumentPage(
            data=page,
            next_cursor=encode_cursor(page[-1].created_at, page[-1].id) if more else None,
        )
