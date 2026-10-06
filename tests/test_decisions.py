"""A verifier's decision and the log entry it leaves (US-00-007, REQ-023 to REQ-027).

Every test here fails until `app/domain/decisions.py` exists. The append-only guarantee itself
lives in the database trigger and is covered by the integration tests with the migration.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.decisions import DecisionRequest, log_entry

NOW = datetime(2026, 10, 5, 10, 1, tzinfo=UTC)


def test_approve_needs_no_reason() -> None:
    request = DecisionRequest(action="approve")

    assert request.action == "approve"


def test_reject_with_a_reason_is_accepted() -> None:
    request = DecisionRequest(action="reject", reason="Name does not match the marksheet.")

    assert request.reason == "Name does not match the marksheet."


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_reject_without_a_reason_is_refused(reason: str | None) -> None:
    with pytest.raises(ValidationError):
        DecisionRequest(action="reject", reason=reason)


def test_correct_needs_the_field_and_the_new_value() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest(action="correct", new_value="Latha Sharma")
    with pytest.raises(ValidationError):
        DecisionRequest(action="correct", extracted_field_id=4012)


def test_an_unknown_action_is_refused() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate({"action": "delete"})


def test_an_unexpected_field_is_refused() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate({"action": "approve", "status": "verified"})


def test_a_reason_over_one_thousand_characters_is_refused() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest(action="reject", reason="x" * 1001)


def test_the_log_entry_holds_who_when_what_and_why() -> None:
    verifier = uuid4()
    request = DecisionRequest(action="reject", reason="Name does not match.")

    entry = log_entry(request, decided_by=verifier, decided_at=NOW)

    assert (entry.decided_by, entry.decided_at, entry.action, entry.reason) == (
        verifier,
        NOW,
        "reject",
        "Name does not match.",
    )


def test_a_correction_logs_the_old_and_the_new_value_and_which_field() -> None:
    request = DecisionRequest(action="correct", extracted_field_id=4012, new_value="Latha Sharma")

    entry = log_entry(request, decided_by=uuid4(), decided_at=NOW, old_value="Latha Sharmaa")

    assert (entry.extracted_field_id, entry.old_value, entry.new_value) == (
        4012,
        "Latha Sharmaa",
        "Latha Sharma",
    )


def test_a_log_entry_cannot_be_changed_after_it_is_made() -> None:
    entry = log_entry(DecisionRequest(action="approve"), decided_by=uuid4(), decided_at=NOW)

    with pytest.raises(FrozenInstanceError):
        entry.action = "reject"  # type: ignore[misc]  # the point of the test


def test_a_decision_time_without_a_timezone_is_refused() -> None:
    naive = NOW.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone"):
        log_entry(DecisionRequest(action="approve"), decided_by=uuid4(), decided_at=naive)


def test_a_correction_with_a_blank_new_value_is_refused() -> None:
    with pytest.raises(ValueError, match="new value"):
        DecisionRequest(action="correct", extracted_field_id=3, new_value="   ")
