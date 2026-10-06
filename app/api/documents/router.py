"""Upload and list an application's documents (api/openapi.yaml: /applications/{id}/documents).

Upload is staff only and CSRF checked. Like the import, the route declares no body parameter: the
file is read after the checks, with a byte cap, then its first bytes must agree with its declared
type (ADR-0008). Images are re-encoded without metadata and a PDF keeps only its first page, as a
JPEG (ADR-0010, ADR-0007). Nothing here reads the document: it is queued with status `uploaded`.
"""

import asyncio
from dataclasses import asdict
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.applications.schemas import PageOut
from app.api.auth.deps import current_user, get_settings_from_app, require_role, verify_csrf
from app.api.documents.deps import get_rasteriser, get_upload_store
from app.api.documents.schemas import DocumentListOut, DocumentOut
from app.api.uploads import read_one_file
from app.core.config import Settings
from app.core.errors import ErrorEnvelope, NotFoundError
from app.db.repositories.uploads import SqlUploadStore
from app.domain.auth import SessionUser
from app.domain.uploads import (
    Rasteriser,
    StoredImage,
    check_declared_type,
    first_page_image,
    normalise_image,
    sha256_hex,
)

log = structlog.get_logger()
router = APIRouter(tags=["documents"])


@router.post(
    "/applications/{application_id}/documents",
    status_code=202,
    response_model=DocumentOut,
    responses={code: {"model": ErrorEnvelope} for code in (401, 403, 404, 413, 415, 422)},
)
async def upload_document(
    application_id: UUID,
    request: Request,
    response: Response,
    user: Annotated[SessionUser, Depends(require_role("staff"))],
    _: Annotated[None, Depends(verify_csrf)],
    store: Annotated[SqlUploadStore, Depends(get_upload_store)],
    rasteriser: Annotated[Rasteriser, Depends(get_rasteriser)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> DocumentOut:
    """Store one page image against the application, or return the one already stored."""
    if not await store.application_exists(application_id):
        raise NotFoundError("no such application")
    upload = await read_one_file(request, cap=settings.upload_max_bytes)
    declared = check_declared_type(upload.content_type.split(";")[0].strip().lower(), upload.data)
    stored = await asyncio.to_thread(_page_image, upload.data, declared, rasteriser)
    record, created = await store.add_document(
        application_id,
        user.id,
        source_content_type=declared,
        sha256=sha256_hex(upload.data),
        size_bytes=len(upload.data),
        stored=stored,
    )
    log.info(
        "document.uploaded",
        document_id=str(record.id),
        application_id=str(application_id),
        content_type=declared,
        created=created,
    )
    if created:
        await store.recompute_status(application_id)
    else:
        response.status_code = 200
    return DocumentOut.model_validate(asdict(record))


@router.get(
    "/applications/{application_id}/documents",
    response_model=DocumentListOut,
    dependencies=[Depends(current_user)],
    responses={code: {"model": ErrorEnvelope} for code in (401, 404, 422)},
)
async def list_documents(
    application_id: UUID,
    store: Annotated[SqlUploadStore, Depends(get_upload_store)],
    cursor: Annotated[str | None, Query(max_length=300)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListOut:
    """The application's documents, newest first."""
    if not await store.application_exists(application_id):
        raise NotFoundError("no such application")
    page = await store.list_documents(application_id, limit=limit, cursor=cursor)
    return DocumentListOut(
        data=[DocumentOut.model_validate(asdict(record)) for record in page.data],
        page=PageOut(next_cursor=page.next_cursor, has_more=page.next_cursor is not None),
    )


def _page_image(data: bytes, declared: str, rasteriser: Rasteriser) -> StoredImage:
    """The form that is stored: a PDF's first page, or the image itself without metadata."""
    if declared == "application/pdf":
        return first_page_image(data, rasteriser)
    return normalise_image(data, "image/png" if declared == "image/png" else "image/jpeg")
