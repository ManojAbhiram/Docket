"""The verified list as CSV text (US-00-009, PS-06).

A spreadsheet runs a cell that starts with `=`, `+`, `-` or `@` as a formula, and a leading tab or
carriage return can hide one. Every cell is prefixed with an apostrophe in those cases, so the
file shows the text instead of running it. No decision column and no verified-at time: the decision
log arrives with US-00-007, and nothing before it records either.
"""

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

HEADER = (
    "application_id",
    "name",
    "date_of_birth",
    "board",
    "roll_number",
    "category",
    "status",
)
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class VerifiedRow:
    """One verified application as the export shows it."""

    application_ref: str
    full_name: str
    date_of_birth: date
    board: str
    roll_number: str
    category: str


def neutralise(cell: str) -> str:
    """The cell, prefixed so a spreadsheet shows it as text when it could run as a formula."""
    return f"'{cell}" if cell.startswith(_FORMULA_STARTS) else cell


def render_verified_csv(rows: Sequence[VerifiedRow]) -> str:
    """The header line, then one line per verified application."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow(
            [
                neutralise(row.application_ref),
                neutralise(row.full_name),
                row.date_of_birth.isoformat(),
                neutralise(row.board),
                neutralise(row.roll_number),
                neutralise(row.category),
                "verified",
            ]
        )
    return out.getvalue()
