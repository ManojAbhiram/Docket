"""Verifier decisions in Postgres (US-00-007). SQL for the decision log and its effects lives here.

One transaction does the whole decision: it locks the application row, refuses a stale version or an
application that is not in review, makes the change, recomputes the status and writes the log entry.
If anything refuses, nothing is written. Choices recorded for the open questions:

* Q-005 (a): a correction edits the extracted value of the named field. The flag the engine raised
  on that field is cleared, because a person has now read the page, and the comparison is run again
  for that document, so a corrected value that still disagrees is flagged `mismatch` again.
* Q-006 (c): approve makes the application Verified, but only through the status rules with the
  approval standing, so a document that was never uploaded cannot be approved away. Reject keeps
  `needs_review`, sets `rejected_at` and takes the application out of the queue; it is final here.

`updated_at` is the version the ETag carries, so every decision moves it. Timestamps use
`clock_timestamp()` so entries made in one transaction still have an order.

List index decision (database rules): `idx_decisions_application_id (application_id, created_at)`
serves the newest-first read of one application's log.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ConflictError, NotFoundError
from app.db.repositories.comparison import compare_in_session
from app.db.repositories.statuses import recompute_in_session
from app.domain.decisions import DecisionRequest
from app.domain.paging import decode_cursor, encode_cursor
from app.domain.status import VerificationNotAllowedError

_EXISTS = text("SELECT 1 FROM applications WHERE id = :id AND erased_at IS NULL")
_LOCK = text(
    "SELECT status::text, rejected_at IS NOT NULL, updated_at FROM applications "
    "WHERE id = :id AND erased_at IS NULL FOR UPDATE"
)
_FIELD = text(
    "SELECT f.id, f.document_id, f.field_name::text, f.subject, f.value FROM extracted_fields f "
    "JOIN documents d ON d.id = f.document_id "
    "WHERE f.id = :field_id AND d.application_id = :application_id FOR UPDATE OF f"
)
_CORRECT = text(
    "UPDATE extracted_fields SET value = :value, needs_review = false, review_reason = NULL, "
    "updated_at = clock_timestamp() WHERE id = :id"
)
_REJECT = text("UPDATE applications SET rejected_at = clock_timestamp() WHERE id = :id")
_TOUCH = text("UPDATE applications SET updated_at = clock_timestamp() WHERE id = :id")
_INSERT = text(
    "INSERT INTO decisions (application_id, decided_by, extracted_field_id, action, reason, "
    "field_name, subject, old_value, new_value, created_at) VALUES (:application_id, :decided_by, "
    ":field_id, CAST(:action AS decision_action), :reason, CAST(:field_name AS field_name), "
    ":subject, :old_value, :new_value, clock_timestamp()) RETURNING id, created_at"
)
_DECIDER = text("SELECT display_name FROM users WHERE id = :id")
_LIST = text(
    "SELECT d.id, d.application_id, d.action::text, d.reason, d.extracted_field_id, "
    "u.display_name, d.created_at FROM decisions d JOIN users u ON u.id = d.decided_by "
    "WHERE d.application_id = :application_id "
    "AND (CAST(:cursor_at AS timestamptz) IS NULL "
    "OR (d.created_at, d.id) < (CAST(:cursor_at AS timestamptz), CAST(:cursor_id AS uuid))) "
    "ORDER BY d.created_at DESC, d.id DESC LIMIT :fetch"
)


@dataclass(frozen=True)
class DecisionRecord:
    """A log entry as the API shows it. The values a correction changed stay in the table."""

    id: UUID
    application_id: UUID
    action: str
    reason: str | None
    extracted_field_id: int | None
    decided_by: str
    created_at: datetime
    application_status: str | None


@dataclass(frozen=True)
class DecisionPage:
    data: tuple[DecisionRecord, ...]
    next_cursor: str | None


async def decide_in_session(
    session: AsyncSession,
    application_id: UUID,
    decided_by: UUID,
    request: DecisionRequest,
    *,
    etag: datetime,
    name_threshold: float,
) -> DecisionRecord:
    """Make one decision inside a transaction the caller owns. Raises, and writes nothing, if the
    application is unknown, changed since `etag`, is not in review, or cannot be verified."""
    row = (await session.execute(_LOCK, {"id": application_id})).first()
    if row is None:
        msg = "no such application"
        raise NotFoundError(msg)
    status, rejected, updated_at = row
    if updated_at != etag:
        msg = "the application changed since you opened it"
        raise ConflictError(msg)
    if status != "needs_review" or rejected:
        msg = "the application is not in review"
        raise ConflictError(msg)
    field: tuple[int, str, str | None, str] | None = None
    after: str = status
    if request.action == "approve":
        after = await recompute_in_session(session, application_id, approved=True)
        if after != "verified":
            msg = "the application cannot be verified from this evidence"
            raise VerificationNotAllowedError(msg)
    elif request.action == "reject":
        await session.execute(_REJECT, {"id": application_id})
    else:
        field = await _correct(session, application_id, request, name_threshold)
        after = await recompute_in_session(session, application_id)
    await session.execute(_TOUCH, {"id": application_id})
    return await _log(session, application_id, decided_by, request, field, after)


async def _correct(
    session: AsyncSession, application_id: UUID, request: DecisionRequest, name_threshold: float
) -> tuple[int, str, str | None, str]:
    """Edit the value and compare the document again. Returns the field and its old value."""
    found = (
        await session.execute(
            _FIELD, {"field_id": request.extracted_field_id, "application_id": application_id}
        )
    ).first()
    if found is None:
        msg = "no such field on this application"
        raise NotFoundError(msg)
    field_id, document_id, name, subject, old_value = found
    await session.execute(_CORRECT, {"id": field_id, "value": (request.new_value or "").strip()})
    await compare_in_session(session, document_id, name_threshold=name_threshold)
    return field_id, name, subject, old_value


async def _log(
    session: AsyncSession,
    application_id: UUID,
    decided_by: UUID,
    request: DecisionRequest,
    field: tuple[int, str, str | None, str] | None,
    status: str,
) -> DecisionRecord:
    field_id, name, subject, old_value = field if field is not None else (None, None, None, None)
    inserted = (
        await session.execute(
            _INSERT,
            {
                "application_id": application_id,
                "decided_by": decided_by,
                "field_id": field_id,
                "action": request.action,
                "reason": request.reason.strip() if request.reason else None,
                "field_name": name,
                "subject": subject,
                "old_value": old_value,
                "new_value": (request.new_value or "").strip() if field is not None else None,
            },
        )
    ).one()
    display = (await session.execute(_DECIDER, {"id": decided_by})).scalar_one()
    return DecisionRecord(
        id=inserted[0],
        application_id=application_id,
        action=request.action,
        reason=request.reason.strip() if request.reason else None,
        extracted_field_id=field_id,
        decided_by=display,
        created_at=inserted[1],
        application_status=status,
    )


class SqlDecisionStore:
    """The decision log and the decisions that write to it."""

    def __init__(self, factory: async_sessionmaker[AsyncSession], *, name_threshold: float) -> None:
        self._factory = factory
        self._name_threshold = name_threshold

    async def application_exists(self, application_id: UUID) -> bool:
        async with self._factory() as session:
            found = (await session.execute(_EXISTS, {"id": application_id})).first()
        return found is not None

    async def decide(
        self,
        application_id: UUID,
        decided_by: UUID,
        request: DecisionRequest,
        *,
        etag: datetime,
    ) -> DecisionRecord:
        """One decision, all or nothing."""
        async with self._factory.begin() as session:
            return await decide_in_session(
                session,
                application_id,
                decided_by,
                request,
                etag=etag,
                name_threshold=self._name_threshold,
            )

    async def list_page(
        self, application_id: UUID, *, limit: int, cursor: str | None
    ) -> DecisionPage:
        """One page of the log, newest first."""
        cursor_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        async with self._factory() as session:
            rows = (
                await session.execute(
                    _LIST,
                    {
                        "application_id": application_id,
                        "cursor_at": cursor_at,
                        "cursor_id": str(cursor_id) if cursor_id else None,
                        "fetch": limit + 1,
                    },
                )
            ).all()
        records = tuple(
            DecisionRecord(
                id=r[0],
                application_id=r[1],
                action=r[2],
                reason=r[3],
                extracted_field_id=r[4],
                decided_by=r[5],
                created_at=r[6],
                application_status=None,
            )
            for r in rows
        )
        page = records[:limit]
        more = len(records) > limit
        return DecisionPage(
            data=page,
            next_cursor=encode_cursor(page[-1].created_at, page[-1].id) if more else None,
        )
