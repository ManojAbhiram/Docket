"""The dashboard counts and the verified export (api/openapi.yaml: /dashboard, /exports).

Either signed-in role reads the counts, which carry no personal data. Only staff export the list,
and every export leaves an audit row (who, when, how many).
"""

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response

from app.api.auth.deps import current_user, get_clock, require_role
from app.api.reports.deps import get_report_store
from app.api.reports.schemas import DashboardOut
from app.core.errors import ErrorEnvelope
from app.db.repositories.reports import SqlReportStore
from app.domain.auth import SessionUser
from app.domain.export import render_verified_csv

log = structlog.get_logger()
router = APIRouter(tags=["reports"])


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    dependencies=[Depends(current_user)],
    responses={401: {"model": ErrorEnvelope}},
)
async def dashboard(
    store: Annotated[SqlReportStore, Depends(get_report_store)],
) -> DashboardOut:
    """How many applications are in each status. Erased applications are not counted."""
    return DashboardOut.model_validate(asdict(await store.dashboard_counts()))


@router.get(
    "/exports/verified.csv",
    response_class=Response,
    responses={
        200: {"content": {"text/csv": {"schema": {"type": "string"}}}},
        401: {"model": ErrorEnvelope},
        403: {"model": ErrorEnvelope},
    },
)
async def export_verified(
    user: Annotated[SessionUser, Depends(require_role("staff"))],
    store: Annotated[SqlReportStore, Depends(get_report_store)],
    clock: Annotated[Callable[[], datetime], Depends(get_clock)],
) -> Response:
    """The verified applications as CSV. The audit row is written with the read."""
    rows = await store.export_verified(user.id)
    log.info("export.done", rows=len(rows))
    stamp = clock().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=render_verified_csv(rows),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="verified-{stamp}.csv"',
            "Cache-Control": "no-store",
        },
    )
