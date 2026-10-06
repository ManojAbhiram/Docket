"""The application list (api/openapi.yaml: /applications). Either signed-in role may read it."""

from dataclasses import asdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.applications.deps import get_application_store, get_review_store
from app.api.applications.schemas import (
    ApplicationDetailOut,
    ApplicationListOut,
    ApplicationOut,
    PageOut,
)
from app.api.auth.deps import current_user
from app.api.decisions.etag import etag_for
from app.core.errors import ErrorEnvelope, NotFoundError
from app.db.repositories.application_detail import SqlReviewStore
from app.db.repositories.applications import SqlApplicationStore

router = APIRouter(tags=["applications"], dependencies=[Depends(current_user)])


@router.get(
    "/applications",
    response_model=ApplicationListOut,
    responses={401: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}},
)
async def list_applications(
    store: Annotated[SqlApplicationStore, Depends(get_application_store)],
    cursor: Annotated[str | None, Query(max_length=300)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[
        Literal["verified", "needs_review", "missing_documents"] | None,
        Query(alias="filter[status]"),
    ] = None,
    rejected: Annotated[bool | None, Query(alias="filter[rejected]")] = None,
) -> ApplicationListOut:
    """Newest change first. The review queue is needs_review with rejected=false."""
    page = await store.list_page(limit=limit, cursor=cursor, status=status, rejected=rejected)
    return ApplicationListOut(
        data=[ApplicationOut.model_validate(asdict(record)) for record in page.data],
        page=PageOut(next_cursor=page.next_cursor, has_more=page.next_cursor is not None),
    )


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationDetailOut,
    responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
async def get_application(
    application_id: UUID,
    response: Response,
    store: Annotated[SqlReviewStore, Depends(get_review_store)],
) -> ApplicationDetailOut:
    """The application with each document value beside the application value, failures marked.

    The `ETag` is the application's `updated_at`: a decision sends it back as `If-Match`.
    """
    detail = await store.get_detail(application_id)
    if detail is None:
        raise NotFoundError("no such application")
    response.headers["ETag"] = etag_for(detail.updated_at)
    return ApplicationDetailOut.model_validate(asdict(detail))
