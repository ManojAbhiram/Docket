"""The decision store against a scripted session, with no database (US-00-007).

`tests/integration/api/test_decisions.py` runs the same code on Postgres. These check the order of
events and the refusals where a unit run can see them: what is locked, what is written, and that a
refused decision writes nothing at all.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ConflictError, NotFoundError
from app.db.repositories.decisions import SqlDecisionStore
from app.domain.decisions import DecisionRequest
from app.domain.status import VerificationNotAllowedError

APPLICATION = uuid4()
VERIFIER = uuid4()
SEEN = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
LATER = SEEN + timedelta(minutes=5)


class Rows:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def one(self) -> tuple[Any, ...]:
        return self._rows[0]

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows

    def scalar_one(self) -> Any:
        return self._rows[0][0]


def doc(doc_type: str, *results: tuple[str, bool]) -> list[tuple[Any, ...]]:
    document_id = uuid4()
    return [(document_id, doc_type, "read", match, flag) for match, flag in results]


COMPLETE = (
    doc("10th_marksheet", ("match", False))
    + doc("12th_marksheet", ("mismatch", True))
    + doc("id_proof", ("match", False))
)
MISSING_ONE = doc("10th_marksheet", ("match", False)) + doc("12th_marksheet", ("mismatch", True))


class ScriptedSession:
    """Answers each statement the store sends, and records every write by its first words."""

    def __init__(
        self,
        *,
        row: tuple[Any, ...] | None = ("needs_review", False, SEEN),
        facts: list[tuple[Any, ...]] = COMPLETE,
        field: tuple[Any, ...] | None = None,
    ) -> None:
        self.row = row
        self.facts = facts
        self.field = field
        self.writes: list[str] = []
        self.decision: dict[str, Any] = {}

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Rows:
        sql = str(statement)
        params = params or {}
        if "SELECT status::text, rejected_at IS NOT NULL, updated_at" in sql:
            return Rows([self.row] if self.row else [])
        if "SELECT status::text, rejected_at IS NOT NULL FROM applications" in sql:
            return Rows([(self.row[0], self.row[1])] if self.row else [])
        if "FOR UPDATE OF f" in sql:
            return Rows([self.field] if self.field else [])
        if "FROM decisions d WHERE d.application_id" in sql:
            return Rows([(False,)])
        if "INSERT INTO decisions" in sql:
            self.decision = params
            self.writes.append("decision")
            return Rows([(uuid4(), SEEN + timedelta(minutes=10))])
        if "SELECT display_name" in sql:
            return Rows([("Demo verifier",)])
        if sql.startswith("UPDATE"):
            self.writes.append(" ".join(sql.split()[:4]))
            return Rows([])
        if "FROM documents d LEFT JOIN extracted_fields" in sql:
            return Rows(self.facts)
        return Rows([])


class ScriptedFactory:
    def __init__(self, session: ScriptedSession) -> None:
        self.session = session

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[ScriptedSession]:
        yield self.session


def store_for(session: ScriptedSession) -> SqlDecisionStore:
    typed = cast("async_sessionmaker[AsyncSession]", ScriptedFactory(session))
    return SqlDecisionStore(typed, name_threshold=0.85)


async def decide(session: ScriptedSession, request: DecisionRequest, etag: datetime = SEEN) -> Any:
    return await store_for(session).decide(APPLICATION, VERIFIER, request, etag=etag)


async def test_a_rejection_sets_the_flag_moves_the_version_and_logs_the_reason() -> None:
    session = ScriptedSession()

    record = await decide(session, DecisionRequest(action="reject", reason="  Wrong person.  "))

    assert record.application_status == "needs_review"
    assert record.reason == "Wrong person."
    assert record.decided_by == "Demo verifier"
    assert session.writes == [
        "UPDATE applications SET rejected_at",
        "UPDATE applications SET updated_at",
        "decision",
    ]
    assert session.decision["action"] == "reject"
    assert session.decision["decided_by"] == VERIFIER


async def test_an_approval_with_every_required_document_present_is_verified_and_logged() -> None:
    session = ScriptedSession()

    record = await decide(session, DecisionRequest(action="approve"))

    assert record.application_status == "verified"
    assert "decision" in session.writes
    assert "UPDATE applications SET status" in session.writes


async def test_an_approval_with_a_required_document_missing_is_refused_and_logs_nothing() -> None:
    session = ScriptedSession(facts=MISSING_ONE)

    with pytest.raises(VerificationNotAllowedError):
        await decide(session, DecisionRequest(action="approve"))

    assert "decision" not in session.writes


async def test_a_decision_on_a_version_that_changed_is_refused_before_anything_is_written() -> None:
    session = ScriptedSession()

    with pytest.raises(ConflictError, match="changed"):
        await decide(session, DecisionRequest(action="approve"), etag=SEEN - timedelta(seconds=1))

    assert session.writes == []


@pytest.mark.parametrize("row", [("verified", False, SEEN), ("needs_review", True, SEEN)])
async def test_an_application_not_in_review_or_already_rejected_is_refused(
    row: tuple[Any, ...],
) -> None:
    session = ScriptedSession(row=row)

    with pytest.raises(ConflictError, match="not in review"):
        await decide(session, DecisionRequest(action="approve"))

    assert session.writes == []


async def test_an_unknown_application_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        await decide(ScriptedSession(row=None), DecisionRequest(action="approve"))


async def test_a_correction_of_a_field_that_is_not_on_this_application_is_not_found() -> None:
    request = DecisionRequest(action="correct", extracted_field_id=5, new_value="x")

    with pytest.raises(NotFoundError):
        await decide(ScriptedSession(field=None), request)


async def test_a_correction_edits_the_value_and_logs_the_old_and_new_one() -> None:
    document_id: UUID = uuid4()
    session = ScriptedSession(field=(5, document_id, "name", None, "Meera Nair"))
    request = DecisionRequest(action="correct", extracted_field_id=5, new_value=" Latha Sharma ")

    record = await decide(session, request)

    assert record.extracted_field_id == 5
    assert session.decision["old_value"] == "Meera Nair"
    assert session.decision["new_value"] == "Latha Sharma"
    assert session.decision["field_name"] == "name"
    assert "UPDATE extracted_fields SET value" in session.writes
