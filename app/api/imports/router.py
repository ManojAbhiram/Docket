"""Import applications from a CSV (api/openapi.yaml: /imports). Staff only, CSRF checked.

The route declares no body parameter on purpose: the file is read after the session, role and CSRF
checks, with a byte cap (`app/api/uploads.py`).
"""

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request

from app.api.applications.deps import get_application_store
from app.api.auth.deps import get_settings_from_app, require_role, verify_csrf
from app.api.imports.schemas import ImportResultOut, ImportRowErrorOut
from app.api.uploads import read_one_file
from app.core.config import Settings
from app.core.errors import ErrorEnvelope
from app.db.repositories.applications import SqlApplicationStore
from app.domain.auth import SessionUser
from app.domain.importing import ImportOutcome, parse_applications
from app.domain.uploads import UnsupportedUploadError

log = structlog.get_logger()
router = APIRouter(tags=["imports"])

_CSV_TYPES = frozenset({"text/csv", "application/csv", "application/vnd.ms-excel"})
_MAX_NAME = 255


@router.post(
    "/imports",
    status_code=201,
    response_model=ImportResultOut,
    responses={code: {"model": ErrorEnvelope} for code in (401, 403, 413, 415, 422)},
)
async def create_import(
    request: Request,
    user: Annotated[SessionUser, Depends(require_role("staff"))],
    _: Annotated[None, Depends(verify_csrf)],
    store: Annotated[SqlApplicationStore, Depends(get_application_store)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> ImportResultOut:
    """Create the valid rows and list the refused ones by row number, column and reason."""
    upload = await read_one_file(request, cap=settings.import_max_bytes)
    if upload.content_type.split(";")[0].strip().lower() not in _CSV_TYPES:
        msg = "send the applications as a CSV file"
        raise UnsupportedUploadError(msg)

    def parse(existing: frozenset[str]) -> ImportOutcome:
        return parse_applications(
            upload.data,
            max_bytes=settings.import_max_bytes,
            max_rows=settings.import_max_rows,
            existing_refs=existing,
        )

    saved = await store.run_import(user.id, _source_name(upload.name), parse)
    log.info(
        "import.done",
        import_id=str(saved.id),
        rows_read=saved.rows_read,
        rows_created=saved.rows_created,
        rows_rejected=saved.rows_rejected,
    )
    return ImportResultOut(
        id=saved.id,
        rows_read=saved.rows_read,
        rows_created=saved.rows_created,
        rows_rejected=saved.rows_rejected,
        errors=[
            ImportRowErrorOut(
                row_number=e.row_number, column_name=e.column_name, reason_code=e.reason_code
            )
            for e in saved.errors
        ],
    )


def _source_name(name: str) -> str:
    """The file name without any directory the client sent, cut to the column length."""
    base = PurePosixPath(PureWindowsPath(name).name).name
    return (base or "upload.csv")[:_MAX_NAME]
