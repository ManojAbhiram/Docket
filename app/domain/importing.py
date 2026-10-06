"""Read the applications CSV staff import (US-00-001, REQ-001 to REQ-003).

A bad row never stops the file: it is listed with its row number, its column and a reason code.
The value that failed is never kept, because the applicants are minors.
"""

import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.core.errors import DomainError

COLUMNS = (
    "application_id",
    "name",
    "father_name",
    "date_of_birth",
    "board",
    "roll_number",
    "marks_by_subject",
    "category",
)
_MAX_LENGTH = {
    "application_id": 40,
    "name": 120,
    "father_name": 120,
    "board": 80,
    "roll_number": 30,
    "category": 40,
}
_EARLIEST_BIRTH = date(1950, 1, 1)
_LATEST_BIRTH = date(2020, 12, 31)
_MAX_MARK = 100


@dataclass(frozen=True)
class ApplicationRow:
    """One valid CSV row."""

    application_ref: str
    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]
    category: str


@dataclass(frozen=True)
class RowError:
    """Why a row was refused. There is no value field on purpose."""

    row_number: int
    column_name: str | None
    reason_code: str


@dataclass(frozen=True)
class ImportOutcome:
    rows: tuple[ApplicationRow, ...]
    errors: tuple[RowError, ...]
    rows_read: int


@dataclass(frozen=True)
class SavedImport:
    """What an import left behind: its id, the counts and every refused row."""

    id: UUID
    rows_read: int
    rows_created: int
    errors: tuple[RowError, ...]

    @property
    def rows_rejected(self) -> int:
        return len(self.errors)


class ImportTooLargeError(DomainError):
    """The file is over the size or row cap."""

    status_code = 413
    code = "payload_too_large"


class ImportFileError(DomainError):
    """The file as a whole cannot be read: not text, or a required column is missing."""

    status_code = 422
    code = "validation_error"


def parse_applications(
    data: bytes,
    *,
    max_bytes: int = 5_000_000,
    max_rows: int = 20_000,
    existing_refs: frozenset[str] = frozenset(),
) -> ImportOutcome:
    """Parse the file. Valid rows and refused rows come back together."""
    if len(data) > max_bytes:
        msg = "the file is over the size cap"
        raise ImportTooLargeError(msg)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        msg = "the file is not UTF-8 text"
        raise ImportFileError(msg) from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader, [])
    for column in COLUMNS:
        if column not in header:
            msg = "the file is missing a required column"
            raise ImportFileError(msg, details={"column": column})
    position = {name: header.index(name) for name in COLUMNS}

    rows: list[ApplicationRow] = []
    errors: list[RowError] = []
    seen = set(existing_refs)
    rows_read = 0
    for cells in reader:
        if not cells:
            continue
        rows_read += 1
        if rows_read > max_rows:
            msg = "the file has more rows than the cap"
            raise ImportTooLargeError(msg)
        if len(cells) != len(header):
            errors.append(RowError(rows_read, None, "malformed_row"))
            continue
        values = {name: cells[index].strip() for name, index in position.items()}
        failure = _first_failure(values, seen)
        if failure is not None:
            errors.append(RowError(rows_read, failure[0], failure[1]))
            continue
        row = _to_row(values)
        seen.add(row.application_ref)
        rows.append(row)
    return ImportOutcome(rows=tuple(rows), errors=tuple(errors), rows_read=rows_read)


def _first_failure(values: dict[str, str], seen: set[str]) -> tuple[str, str] | None:
    for column in COLUMNS:
        if not values[column]:
            return (column, "missing_value")
    for column, limit in _MAX_LENGTH.items():
        if len(values[column]) > limit:
            return (column, "too_long")
    born = _parse_date(values["date_of_birth"])
    if born is None:
        return ("date_of_birth", "bad_date")
    if not _EARLIEST_BIRTH <= born <= _LATEST_BIRTH:
        return ("date_of_birth", "out_of_range")
    if _parse_marks(values["marks_by_subject"]) is None:
        return ("marks_by_subject", "bad_marks")
    if values["application_id"] in seen:
        return ("application_id", "duplicate_application_ref")
    return None


def _to_row(values: dict[str, str]) -> ApplicationRow:
    born = _parse_date(values["date_of_birth"])
    marks = _parse_marks(values["marks_by_subject"])
    if born is None or marks is None:
        msg = "a validated row failed to parse again"
        raise ImportFileError(msg)
    return ApplicationRow(
        application_ref=values["application_id"],
        full_name=values["name"],
        father_name=values["father_name"],
        date_of_birth=born,
        board=values["board"],
        roll_number=values["roll_number"],
        marks=marks,
        category=values["category"],
    )


def _parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_marks(text: str) -> dict[str, int] | None:
    try:
        parsed: object = json.loads(text)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    marks: dict[str, int] = {}
    for subject, mark in parsed.items():
        valid = isinstance(mark, int) and not isinstance(mark, bool) and 0 <= mark <= _MAX_MARK
        if not isinstance(subject, str) or not valid:
            return None
        marks[subject] = mark
    return marks
