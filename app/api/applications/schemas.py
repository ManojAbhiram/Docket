"""Response bodies for the application list (api/openapi.yaml: Application, Page)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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


class PageOut(BaseModel):
    next_cursor: str | None
    has_more: bool


class ApplicationListOut(BaseModel):
    data: list[ApplicationOut]
    page: PageOut = Field(description="`next_cursor` is null on the last page.")
