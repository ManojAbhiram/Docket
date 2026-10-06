"""Verifier decisions on flagged applications (api/openapi.yaml: /applications/{id}/decisions).

Deciding is for the verifier role only, with the CSRF header and an allowed origin, and carries the
`If-Match` version the verifier saw. The log is read-only for both roles: there is no route that
changes or removes an entry, and the table refuses it too.
"""

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, Query

from app.api.applications.schemas import PageOut
from app.api.auth.deps import current_user, require_role, verify_csrf
from app.api.decisions.deps import get_decision_store
from app.api.decisions.etag import parse_etag
from app.api.decisions.schemas import DecisionListOut, DecisionOut
from app.core.errors import ErrorEnvelope, NotFoundError
from app.db.repositories.decisions import SqlDecisionStore
from app.domain.auth import SessionUser
from app.domain.decisions import DecisionRequest

log = structlog.get_logger()
router = APIRouter(tags=["decisions"])


@router.post(
    "/applications/{application_id}/decisions",
    status_code=201,
    response_model=DecisionOut,
    responses={code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422)},
)
async def create_decision(
    application_id: UUID,
    body: DecisionRequest,
    user: Annotated[SessionUser, Depends(require_role("verifier"))],
    _: Annotated[None, Depends(verify_csrf)],
    store: Annotated[SqlDecisionStore, Depends(get_decision_store)],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> DecisionOut:
    """Approve, correct or reject. All or nothing, and logged with who, when, what and why."""
    record = await store.decide(application_id, user.id, body, etag=parse_etag(if_match))
    log.info(
        "decision.made",
        decision_id=str(record.id),
        application_id=str(application_id),
        action=record.action,
        status_after=record.application_status,
    )
    return DecisionOut.model_validate(asdict(record))


@router.get(
    "/applications/{application_id}/decisions",
    response_model=DecisionListOut,
    dependencies=[Depends(current_user)],
    responses={code: {"model": ErrorEnvelope} for code in (401, 404, 422)},
)
async def list_decisions(
    application_id: UUID,
    store: Annotated[SqlDecisionStore, Depends(get_decision_store)],
    cursor: Annotated[str | None, Query(max_length=300)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DecisionListOut:
    """The decision log of one application, newest first."""
    if not await store.application_exists(application_id):
        raise NotFoundError("no such application")
    page = await store.list_page(application_id, limit=limit, cursor=cursor)
    return DecisionListOut(
        data=[DecisionOut.model_validate(asdict(record)) for record in page.data],
        page=PageOut(next_cursor=page.next_cursor, has_more=page.next_cursor is not None),
    )
