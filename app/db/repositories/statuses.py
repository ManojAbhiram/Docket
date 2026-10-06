"""An application's status in Postgres, set from its current documents (US-00-005, REQ-017 to 020).

Two entry points call the pure rules in `app/domain/status.py`. `recompute_status` is what the
pipeline calls after a comparison or an upload. `request_status` is the guarded write for a caller
that names the status it wants: Verified is refused unless every field matched or `approved` is set
(AC-US-00-005-4), so no route can write Verified around the rules.

Only current documents count: an older document of a type is kept but replaced for matching
(AC-US-00-002-4). A field with no `match_result` has not been compared yet, so it maps to
`FieldFacts(match=None, needs_review=True)`: it neither matches nor mismatches, and it keeps the
application out of Verified until the comparison has run. The application row is locked
(`FOR UPDATE`) for the whole read and write, so two recomputes cannot interleave and a recompute
that waited sees a comparison that committed meanwhile.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NotFoundError
from app.domain.status import (
    DocumentFacts,
    DocumentState,
    FieldFacts,
    Status,
    StatusNotAllowedError,
    assert_can_verify,
    compute_status,
)

_STATUSES: frozenset[str] = frozenset({"verified", "needs_review", "missing_documents"})
_LOCK = text(
    "SELECT status::text, rejected_at IS NOT NULL FROM applications "
    "WHERE id = :id AND erased_at IS NULL FOR UPDATE"
)
_FACTS = text(
    "SELECT d.id, d.detected_type::text, d.status::text, f.match_result::text, f.needs_review "
    "FROM documents d LEFT JOIN extracted_fields f ON f.document_id = d.id "
    "WHERE d.application_id = :id AND d.is_current ORDER BY d.created_at, d.id, f.id"
)
_APPROVAL_STANDS = text(
    "SELECT EXISTS (SELECT 1 FROM decisions d WHERE d.application_id = :id "
    "AND d.action = 'approve' AND d.created_at > coalesce((SELECT max(greatest(doc.created_at, "
    "doc.updated_at, coalesce(f.updated_at, doc.updated_at))) FROM documents doc "
    "LEFT JOIN extracted_fields f ON f.document_id = doc.id WHERE doc.application_id = :id), "
    "'-infinity'::timestamptz))"
)
_WRITE = text(
    "UPDATE applications SET status = CAST(:status AS application_status), updated_at = now() "
    "WHERE id = :id AND status <> CAST(:status AS application_status)"
)


async def recompute_status(
    factory: async_sessionmaker[AsyncSession],
    application_id: UUID,
    *,
    approved: bool | None = None,
) -> str:
    """Set the status the evidence gives and return it. A rejected one stays needs_review.

    `approved` left as None is read from the decision log (see `recompute_in_session`).
    """
    async with factory.begin() as session:
        return await recompute_in_session(session, application_id, approved=approved)


async def recompute_in_session(
    session: AsyncSession, application_id: UUID, *, approved: bool | None = None
) -> str:
    """The same recompute inside a transaction the caller owns, so a decision and the status it
    leads to commit or roll back together.

    A verifier's approval stands in for a field that did not match only while no evidence has
    changed since it: `approved` None means "the newest approval is newer than every document and
    field". New evidence (an upload, a read, a correction) makes the approval stale, and the status
    comes from the evidence again. Pass True or False to override the log.
    """
    stored, rejected = await _lock(session, application_id)
    if rejected:
        return stored
    standing = await _approval_stands(session, application_id) if approved is None else approved
    computed = compute_status(await _facts(session, application_id), approved=standing)
    await _write(session, application_id, computed, stored)
    return computed


async def request_status(
    factory: async_sessionmaker[AsyncSession],
    application_id: UUID,
    requested: str,
    *,
    approved: bool,
) -> str:
    """Write `requested` only if the evidence gives it, and return it.

    Verified without every field matching and without `approved` raises
    `VerificationNotAllowedError`. Any other request must equal what the evidence gives.
    """
    async with factory.begin() as session:
        stored, rejected = await _lock(session, application_id)
        facts = await _facts(session, application_id)
        if requested not in _STATUSES:
            msg = "that is not one of the three statuses"
            raise StatusNotAllowedError(msg)
        if requested == "verified":
            assert_can_verify(facts, approved=approved)
        computed = stored if rejected else compute_status(facts, approved=approved)
        if requested != computed:
            msg = "the evidence does not give that status"
            raise StatusNotAllowedError(msg)
        await _write(session, application_id, computed, stored)
        return computed


async def _lock(session: AsyncSession, application_id: UUID) -> tuple[Status, bool]:
    row = (await session.execute(_LOCK, {"id": application_id})).first()
    if row is None:
        msg = "no such application"
        raise NotFoundError(msg)
    status: Status = row[0]
    return status, bool(row[1])


async def _approval_stands(session: AsyncSession, application_id: UUID) -> bool:
    """True if an approve decision is newer than every document and extracted field."""
    return bool((await session.execute(_APPROVAL_STANDS, {"id": application_id})).scalar_one())


async def _write(session: AsyncSession, application_id: UUID, status: Status, stored: str) -> None:
    """Change the row, and its `updated_at`, only when the status actually changes."""
    if status != stored:
        await session.execute(_WRITE, {"id": application_id, "status": status})


async def _facts(session: AsyncSession, application_id: UUID) -> list[DocumentFacts]:
    rows = (await session.execute(_FACTS, {"id": application_id})).all()
    documents: dict[UUID, tuple[str | None, DocumentState, list[FieldFacts]]] = {}
    for document_id, doc_type, state, match_result, needs_review in rows:
        _, _, fields = documents.setdefault(document_id, (doc_type, state, []))
        if match_result is None and needs_review is None:
            continue  # a document with no fields at all
        fields.append(_field(match_result, bool(needs_review)))
    return [
        DocumentFacts(doc_type=doc_type, state=state, fields=tuple(fields))
        for doc_type, state, fields in documents.values()
    ]


def _field(match_result: str | None, needs_review: bool) -> FieldFacts:
    if match_result is None:
        return FieldFacts(match=None, needs_review=True)
    return FieldFacts(
        match=None if match_result == "skipped" else match_result == "match",
        needs_review=needs_review,
    )
