"""The status entry points against a scripted session, with no database (US-00-005).

The integration tests in `tests/integration/test_application_status.py` run the same entry points on
Postgres. These check the order of events and the refusals where a unit run can see them: what is
locked, what is written, and that nothing is written when nothing changes.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NotFoundError
from app.db.repositories.statuses import recompute_status, request_status
from app.domain.status import StatusNotAllowedError, VerificationNotAllowedError

APPLICATION = uuid4()


class Rows:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows

    def scalar_one(self) -> Any:
        return self._rows[0][0]


class ScriptedSession:
    """Answers the three statements the store sends, and records the writes."""

    def __init__(
        self,
        *,
        stored: str,
        rejected: bool,
        facts: list[tuple[Any, ...]],
        exists: bool = True,
        approval_stands: bool = False,
    ) -> None:
        self.stored = stored
        self.rejected = rejected
        self.facts = facts
        self.exists = exists
        self.approval_stands = approval_stands
        self.asked_the_log = False
        self.writes: list[dict[str, Any]] = []

    async def execute(self, statement: Any, params: dict[str, Any]) -> Rows:
        sql = str(statement)
        if "FOR UPDATE" in sql:
            return Rows([(self.stored, self.rejected)] if self.exists else [])
        if sql.startswith("UPDATE"):
            self.writes.append(params)
            return Rows([])
        if "FROM decisions" in sql:
            self.asked_the_log = True
            return Rows([(self.approval_stands,)])
        return Rows(self.facts)


class ScriptedFactory:
    def __init__(self, session: ScriptedSession) -> None:
        self.session = session

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[ScriptedSession]:
        yield self.session


def factory_for(session: ScriptedSession) -> async_sessionmaker[AsyncSession]:
    """The scripted factory, typed as the real one: the store only calls `begin()` on it."""
    return cast("async_sessionmaker[AsyncSession]", ScriptedFactory(session))


def doc(
    document_id: UUID, doc_type: str, *results: tuple[str | None, bool]
) -> list[tuple[Any, ...]]:
    return [(document_id, doc_type, "read", match, flag) for match, flag in results]


def complete(match: str | None = "match") -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for doc_type in ("10th_marksheet", "12th_marksheet", "id_proof"):
        rows += doc(uuid4(), doc_type, (match, False), ("skipped", False))
    return rows


async def run(session: ScriptedSession, **kwargs: Any) -> str:
    return await recompute_status(factory_for(session), APPLICATION, **kwargs)


async def test_a_changed_status_is_written_once_with_the_new_value() -> None:
    session = ScriptedSession(stored="missing_documents", rejected=False, facts=complete())

    assert await run(session) == "verified"
    assert session.writes == [{"id": APPLICATION, "status": "verified"}]


async def test_an_unchanged_status_writes_nothing() -> None:
    session = ScriptedSession(stored="verified", rejected=False, facts=complete())

    assert await run(session) == "verified"
    assert session.writes == []


async def test_a_rejected_application_answers_its_stored_status_and_is_not_read_again() -> None:
    session = ScriptedSession(stored="needs_review", rejected=True, facts=complete())

    assert await run(session) == "needs_review"
    assert session.writes == []


async def test_a_field_with_no_comparison_yet_keeps_the_application_out_of_verified() -> None:
    session = ScriptedSession(stored="missing_documents", rejected=False, facts=complete(None))

    assert await run(session) == "needs_review"


async def test_a_document_with_no_fields_at_all_is_still_counted() -> None:
    facts = [(uuid4(), "unknown", "read", None, None)]
    session = ScriptedSession(stored="missing_documents", rejected=False, facts=facts)

    assert await run(session) == "needs_review"


async def test_an_unknown_application_is_not_found() -> None:
    session = ScriptedSession(stored="x", rejected=False, facts=[], exists=False)

    with pytest.raises(NotFoundError):
        await run(session)


async def test_an_approval_passed_to_recompute_lets_a_mismatch_stand_as_verified() -> None:
    session = ScriptedSession(stored="needs_review", rejected=False, facts=complete("mismatch"))

    assert await run(session, approved=True) == "verified"


async def test_a_request_for_verified_without_evidence_is_refused_and_writes_nothing() -> None:
    session = ScriptedSession(stored="needs_review", rejected=False, facts=complete("mismatch"))

    with pytest.raises(VerificationNotAllowedError):
        await request_status(
            factory_for(session),
            APPLICATION,
            "verified",
            approved=False,
        )

    assert session.writes == []


async def test_a_request_that_matches_the_evidence_is_written() -> None:
    session = ScriptedSession(stored="missing_documents", rejected=False, facts=complete())

    result = await request_status(
        factory_for(session),
        APPLICATION,
        "verified",
        approved=False,
    )

    assert result == "verified"
    assert session.writes == [{"id": APPLICATION, "status": "verified"}]


async def test_a_request_that_differs_from_the_evidence_or_names_no_status_is_refused() -> None:
    session = ScriptedSession(stored="missing_documents", rejected=False, facts=complete())
    factory = factory_for(session)

    with pytest.raises(StatusNotAllowedError):
        await request_status(factory, APPLICATION, "needs_review", approved=False)
    with pytest.raises(StatusNotAllowedError):
        await request_status(factory, APPLICATION, "done", approved=False)


async def test_a_rejected_application_cannot_be_asked_for_verified_even_with_an_approval() -> None:
    session = ScriptedSession(stored="needs_review", rejected=True, facts=complete())

    with pytest.raises(StatusNotAllowedError):
        await request_status(
            factory_for(session),
            APPLICATION,
            "verified",
            approved=True,
        )

    assert session.writes == []


async def test_a_standing_approval_in_the_log_keeps_a_mismatching_application_verified() -> None:
    mismatch = (
        complete()[:1]
        + doc(uuid4(), "12th_marksheet", ("mismatch", True))
        + doc(uuid4(), "id_proof", ("match", False))
    )
    session = ScriptedSession(
        stored="needs_review", rejected=False, facts=mismatch, approval_stands=True
    )

    assert await run(session) == "verified"
    assert session.asked_the_log is True


async def test_with_no_approval_in_the_log_the_same_application_stays_in_review() -> None:
    mismatch = (
        complete()[:1]
        + doc(uuid4(), "12th_marksheet", ("mismatch", True))
        + doc(uuid4(), "id_proof", ("match", False))
    )
    session = ScriptedSession(stored="needs_review", rejected=False, facts=mismatch)

    assert await run(session) == "needs_review"


async def test_an_explicit_approval_flag_overrides_the_log_and_the_log_is_not_asked() -> None:
    session = ScriptedSession(stored="needs_review", rejected=False, facts=complete())

    await run(session, approved=False)

    assert session.asked_the_log is False
