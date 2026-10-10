"""The document queue in Postgres (ADR-0011). SQL lives here and nowhere else.

A claim takes the oldest `uploaded` document with `FOR UPDATE SKIP LOCKED`. Every later write is
conditional on `status = 'processing'`, so a read that finishes after the sweeper gave up changes
nothing. Comparing fields with the application and recomputing its status is the next service.
"""

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.processing import ProcessedDocument
from app.jobs.worker import ClaimedDocument

_CLAIM = text(
    """
    UPDATE documents SET status = 'processing', updated_at = now()
    WHERE id = (
        SELECT id FROM documents WHERE status = 'uploaded'
        ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
    )
    RETURNING id
    """
)
_IMAGE = text("SELECT content FROM document_blobs WHERE document_id = :id")
_LOCK_DOCUMENT = text(
    "SELECT application_id, created_at FROM documents "
    "WHERE id = :id AND status = 'processing' FOR UPDATE"
)
_LOCK_APPLICATION = text("SELECT id FROM applications WHERE id = :id FOR UPDATE")
_NEWER_CURRENT = text(
    "SELECT 1 FROM documents WHERE application_id = :app AND detected_type = "
    "CAST(:doc_type AS document_type) AND is_current AND created_at > :created AND id <> :id"
)
_DEMOTE_OLDER = text(
    "UPDATE documents SET is_current = false WHERE application_id = :app AND detected_type = "
    "CAST(:doc_type AS document_type) AND is_current AND created_at < :created AND id <> :id"
)
_MARK_READ = text(
    "UPDATE documents SET status = 'read', detected_type = CAST(:doc_type AS document_type), "
    "is_current = :current, updated_at = now() WHERE id = :id"
)
_INSERT_FIELD = text(
    "INSERT INTO extracted_fields (document_id, field_name, subject, value, confidence, box, "
    "needs_review, review_reason) VALUES (:id, CAST(:field_name AS field_name), :subject, :value, "
    ":confidence, CAST(:box AS jsonb), :needs_review, :review_reason)"
)
_FAIL = text(
    "UPDATE documents SET status = 'failed', failure_reason = :reason, updated_at = now() "
    "WHERE id = :id AND status = 'processing' RETURNING id"
)
_SWEEP = text(
    "UPDATE documents SET status = 'failed', failure_reason = 'interrupted', updated_at = now() "
    "WHERE status = 'processing' AND updated_at < now() - make_interval(secs => :seconds) "
    "RETURNING id"
)


class SqlDocumentStore:
    """`DocumentStore` over the `documents`, `document_blobs` and `extracted_fields` tables."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def claim_next(self) -> ClaimedDocument | None:
        async with self._factory.begin() as session:
            claimed = (await session.execute(_CLAIM)).scalar_one_or_none()
            if claimed is None:
                return None
            image = (await session.execute(_IMAGE, {"id": claimed})).scalar_one()
            return ClaimedDocument(id=claimed, image=bytes(image))

    async def complete(self, document_id: UUID, result: ProcessedDocument) -> bool:
        async with self._factory.begin() as session:
            row = (await session.execute(_LOCK_DOCUMENT, {"id": document_id})).first()
            if row is None:
                return False
            application_id, created_at = row
            await session.execute(_LOCK_APPLICATION, {"id": application_id})
            current = True
            if result.doc_type != "unknown":
                keys = {
                    "app": application_id,
                    "doc_type": result.doc_type,
                    "created": created_at,
                    "id": document_id,
                }
                current = (await session.execute(_NEWER_CURRENT, keys)).first() is None
                await session.execute(_DEMOTE_OLDER, keys)
            await session.execute(
                _MARK_READ, {"id": document_id, "doc_type": result.doc_type, "current": current}
            )
            for field in result.fields:
                await session.execute(
                    _INSERT_FIELD,
                    {
                        "id": document_id,
                        "field_name": field.field_name,
                        "subject": field.subject,
                        "value": field.value,
                        "confidence": field.confidence,
                        "box": None if field.box is None else json.dumps(field.box),
                        "needs_review": field.needs_review,
                        "review_reason": field.review_reason,
                    },
                )
            return True

    async def fail(self, document_id: UUID, reason: str) -> bool:
        async with self._factory.begin() as session:
            result = await session.execute(_FAIL, {"id": document_id, "reason": reason})
            return result.first() is not None

    async def sweep_stale(self, older_than_seconds: int) -> int:
        async with self._factory.begin() as session:
            result = await session.execute(_SWEEP, {"seconds": older_than_seconds})
            return len(result.all())
