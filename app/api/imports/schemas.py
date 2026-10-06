"""The result of an import (api/openapi.yaml: ImportResult, ImportRowError)."""

from uuid import UUID

from pydantic import BaseModel


class ImportRowErrorOut(BaseModel):
    """Row number, column and reason code. The value that failed is never part of it."""

    row_number: int
    column_name: str | None
    reason_code: str


class ImportResultOut(BaseModel):
    id: UUID
    rows_read: int
    rows_created: int
    rows_rejected: int
    errors: list[ImportRowErrorOut]
