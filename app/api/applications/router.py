"""The application list (api/openapi.yaml: /applications). Either signed-in role may read it."""

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.applications.deps import get_application_store
from app.api.applications.schemas import ApplicationListOut, ApplicationOut, PageOut
from app.api.auth.deps import current_user
from app.core.errors import ErrorEnvelope
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
