"""Response bodies for documents (api/openapi.yaml: Document, Page)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.api.applications.schemas import PageOut
from app.api.types import DocumentType


class DocumentOut(BaseModel):
    """A document without its bytes. The image has its own route."""

    id: UUID
    application_id: UUID
    detected_type: DocumentType | None
    status: Literal["uploaded", "processing", "read", "failed"]
    failure_reason: str | None
    is_current: bool
    created_at: datetime
    # What the uploader asked for, what read it, and why the two differ (a safe reason code).
    requested_mode: Literal["free", "vision"]
    read_engine: str | None
    fallback_reason: str | None


class DocumentListOut(BaseModel):
    data: list[DocumentOut]
    page: PageOut
