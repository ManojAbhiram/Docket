"""Compare every extracted field with the application record (US-00-004, REQ-012 to REQ-016).

Rules by field (the field map is an assumption until Q-003, Q-011 and Q-017 are answered):
- name and father_name: token-sorted similarity at the configured threshold.
- dob: exact after the printed format is normalised; an unreadable date never matches.
- roll_number: exact, apart from spaces around the value.
- marks: one row per subject, exact against the application's mark for that subject, ignoring the
  case of the subject. A subject the application lacks, or a mark that is not a whole number, is a
  mismatch.
- board: exact, ignoring case and surrounding spaces. Assumption: the CSV and the marksheet name
  the board the same way; a different spelling goes to review rather than being guessed at.
- document_number: the application has no such value, so it is skipped.
- A field the document type does not carry is skipped and never counted as a mismatch.

A carried field with no value (the engine found nothing) is a mismatch, never a match: an empty
string must not be able to stand in for evidence, and a missing field is what a person has to look
at. Without this a document where nothing was read would count as "every field matched".
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.domain.match import (
    dates_match,
    fields_for,
    names_match,
    roll_numbers_match,
)

MatchResult = Literal["match", "mismatch", "skipped"]

_NAME_FIELDS = frozenset({"name", "father_name"})


@dataclass(frozen=True)
class ApplicationValues:
    """What the application record says, as the comparison needs it."""

    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]


@dataclass(frozen=True)
class FieldToCompare:
    """One extracted field: its row id, its name, the subject for a mark, and the value read."""

    field_id: int
    name: str
    subject: str | None
    value: str


def compare_fields(
    document_type: str,
    fields: Sequence[FieldToCompare],
    application: ApplicationValues,
    *,
    name_threshold: float,
) -> list[tuple[int, MatchResult]]:
    """One result per field, in the order given."""
    carried = fields_for(document_type)
    return [
        (
            f.field_id,
            _compare_one(f, application, name_threshold) if f.name in carried else "skipped",
        )
        for f in fields
    ]


def _compare_one(
    field: FieldToCompare, application: ApplicationValues, name_threshold: float
) -> MatchResult:
    if field.name == "document_number":
        return "skipped"
    value = field.value.strip()
    if not value:
        return "mismatch"
    if field.name in _NAME_FIELDS:
        expected = application.full_name if field.name == "name" else application.father_name
        return _result(names_match(value, expected, threshold=name_threshold))
    if field.name == "dob":
        return _result(dates_match(value, application.date_of_birth))
    if field.name == "roll_number":
        return _result(roll_numbers_match(value, application.roll_number))
    if field.name == "board":
        return _result(value.casefold() == application.board.strip().casefold())
    if field.name == "marks":
        return _result(_mark_matches(field.subject, value, application.marks))
    return "skipped"


def _mark_matches(subject: str | None, value: str, marks: dict[str, int]) -> bool:
    if subject is None or not value.isdecimal():
        return False
    expected = {name.casefold(): mark for name, mark in marks.items()}.get(
        subject.strip().casefold()
    )
    return expected is not None and int(value) == expected


def _result(matched: bool) -> MatchResult:
    return "match" if matched else "mismatch"


def review_reason_after(result: MatchResult, earlier: str | None) -> str | None:
    """The review reason a field carries once it has been compared.

    A field holds one reason (the table allows one). This step owns only `mismatch`: another
    step's reason, such as `low_confidence`, is kept, and a `mismatch` set by an earlier run is
    cleared when the field now matches, so a run after a correction gives a first run's rows.
    """
    if result == "mismatch":
        return earlier or "mismatch"
    return None if earlier == "mismatch" else earlier
