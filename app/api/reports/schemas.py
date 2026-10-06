"""The dashboard body (api/openapi.yaml: Dashboard)."""

from pydantic import BaseModel, Field


class DashboardOut(BaseModel):
    """Counts only. No applicant data."""

    verified: int = Field(ge=0)
    needs_review: int = Field(ge=0, description="Includes the rejected ones.")
    missing_documents: int = Field(ge=0)
    rejected: int = Field(ge=0, description="A subset of needs_review.")
