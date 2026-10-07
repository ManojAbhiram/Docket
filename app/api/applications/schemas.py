"""Response bodies for the application list (api/openapi.yaml: Application, Page)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.types import DocumentType


class ApplicationOut(BaseModel):
    id: UUID
    application_ref: str
    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]
    category: str
    status: Literal["verified", "needs_review", "missing_documents"]
    rejected: bool
    created_at: datetime
    updated_at: datetime
    flag_reason: str | None = Field(
        default=None,
        description="Why a needs_review application is flagged, in a few words. Null otherwise.",
    )


class PageOut(BaseModel):
    next_cursor: str | None
    has_more: bool


class ApplicationListOut(BaseModel):
    data: list[ApplicationOut]
    page: PageOut = Field(description="`next_cursor` is null on the last page.")


class ExtractedFieldOut(BaseModel):
    """One field read from a document, set beside the application value it is compared to."""

    id: int
    field_name: Literal[
        "name", "father_name", "dob", "board", "roll_number", "marks", "document_number"
    ]
    subject: str | None
    value: str
    application_value: str | None
    confidence: float | None
    box: list[float] | None
    match_result: Literal["match", "mismatch", "skipped"] | None
    needs_review: bool
    review_reason: Literal["low_confidence", "format_invalid", "mismatch", "not_extracted"] | None


class DocumentDetailOut(BaseModel):
    id: UUID
    application_id: UUID
    detected_type: DocumentType | None
    status: Literal["uploaded", "processing", "read", "failed"]
    failure_reason: str | None
    is_current: bool
    created_at: datetime
    fields: list[ExtractedFieldOut]


class ApplicationDetailOut(ApplicationOut):
    """The application with its documents, current ones first."""

    documents: list[DocumentDetailOut]
