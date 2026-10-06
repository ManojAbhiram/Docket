"""One application with its documents and fields, and a document's stored image (US-00-006).

Read only. Erased applications are never shown, and neither are their documents. Index decision
(database rules): every query here is by primary key or by `application_id` / `document_id`, which
the foreign-key indexes already serve.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.review import ApplicationValues, application_value

_APPLICATION = text(
    "SELECT id, application_ref, full_name, father_name, date_of_birth, board, roll_number, marks, "
    "category, status::text, rejected_at IS NOT NULL, created_at, updated_at FROM applications "
    "WHERE id = :id AND erased_at IS NULL"
)
_DOCUMENTS = text(
    "SELECT id, application_id, detected_type::text, status::text, failure_reason, is_current, "
    "created_at FROM documents WHERE application_id = :id "
    "ORDER BY is_current DESC, created_at DESC, id DESC"
)
_FIELDS = text(
    "SELECT f.id, f.document_id, f.field_name::text, f.subject, f.value, f.confidence, f.box, "
    "f.match_result::text, f.needs_review, f.review_reason FROM extracted_fields f "
    "JOIN documents d ON d.id = f.document_id WHERE d.application_id = :id ORDER BY f.id"
)
_IMAGE = text(
    "SELECT b.content_type, b.content FROM document_blobs b "
    "JOIN documents d ON d.id = b.document_id JOIN applications a ON a.id = d.application_id "
    "WHERE b.document_id = :id AND a.erased_at IS NULL"
)


@dataclass(frozen=True)
class FieldRecord:
    id: int
    field_name: str
    subject: str | None
    value: str
    application_value: str | None
    confidence: float | None
    box: list[float] | None
    match_result: str | None
    needs_review: bool
    review_reason: str | None


@dataclass(frozen=True)
class DocumentDetail:
    id: UUID
    application_id: UUID
    detected_type: str | None
    status: str
    failure_reason: str | None
    is_current: bool
    created_at: datetime
    fields: tuple[FieldRecord, ...]


@dataclass(frozen=True)
class ApplicationDetail:
    id: UUID
    application_ref: str
    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]
    category: str
    status: str
    rejected: bool
    created_at: datetime
    updated_at: datetime
    documents: tuple[DocumentDetail, ...]


@dataclass(frozen=True)
class StoredPage:
    content_type: str
    content: bytes


class SqlReviewStore:
    """Reads for the review screen: the detail of one application and one document's image."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def get_detail(self, application_id: UUID) -> ApplicationDetail | None:
        async with self._factory() as session:
            row = (await session.execute(_APPLICATION, {"id": application_id})).first()
            if row is None:
                return None
            documents = (await session.execute(_DOCUMENTS, {"id": application_id})).all()
            fields = (await session.execute(_FIELDS, {"id": application_id})).all()
        values = ApplicationValues(
            full_name=row[2],
            father_name=row[3],
            date_of_birth=row[4],
            board=row[5],
            roll_number=row[6],
            marks=row[7],
        )
        by_document: dict[UUID, list[FieldRecord]] = {}
        for field in fields:
            by_document.setdefault(field[1], []).append(_field(field, values))
        return ApplicationDetail(
            id=row[0],
            application_ref=row[1],
            full_name=values.full_name,
            father_name=values.father_name,
            date_of_birth=values.date_of_birth,
            board=values.board,
            roll_number=values.roll_number,
            marks=values.marks,
            category=row[8],
            status=row[9],
            rejected=row[10],
            created_at=row[11],
            updated_at=row[12].astimezone(UTC),
            documents=tuple(
                DocumentDetail(
                    id=d[0],
                    application_id=d[1],
                    detected_type=d[2],
                    status=d[3],
                    failure_reason=d[4],
                    is_current=d[5],
                    created_at=d[6],
                    fields=tuple(by_document.get(d[0], ())),
                )
                for d in documents
            ),
        )

    async def get_image(self, document_id: UUID) -> StoredPage | None:
        async with self._factory() as session:
            row = (await session.execute(_IMAGE, {"id": document_id})).first()
        if row is None:
            return None
        return StoredPage(content_type=row[0], content=bytes(row[1]))


def _field(row: Row[Any], application: ApplicationValues) -> FieldRecord:
    return FieldRecord(
        id=row[0],
        field_name=row[2],
        subject=row[3],
        value=row[4],
        application_value=application_value(row[2], row[3], application),
        confidence=row[5],
        box=row[6],
        match_result=row[7],
        needs_review=row[8],
        review_reason=row[9],
    )
