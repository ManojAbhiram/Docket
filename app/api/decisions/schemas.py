"""Response bodies for the decision log (api/openapi.yaml: Decision, Page)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.api.applications.schemas import PageOut


class DecisionOut(BaseModel):
    """One log entry. The old and new value of a correction stay in the log table, not here.

    `application_status` is the status right after the decision. It is given when the decision is
    made and is null when an old entry is read back, because the table does not keep it.
    """

    id: UUID
    application_id: UUID
    action: Literal["approve", "correct", "reject"]
    reason: str | None
    extracted_field_id: int | None
    decided_by: str
    created_at: datetime
    application_status: Literal["verified", "needs_review", "missing_documents"] | None


class DecisionListOut(BaseModel):
    data: list[DecisionOut]
    page: PageOut
