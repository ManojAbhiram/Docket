"""The verified export as CSV text (US-00-009, PS-06). Cells never run as spreadsheet formulas."""

import csv
import io
from datetime import UTC, date, datetime

import pytest

from app.domain.export import HEADER, VerifiedRow, neutralise, render_verified_csv


def row(
    *, full_name: str = "Latha Sharma", board: str = "CBSE", application_ref: str = "SYN-APP-004"
) -> VerifiedRow:
    return VerifiedRow(
        application_ref=application_ref,
        full_name=full_name,
        date_of_birth=date(2006, 12, 10),
        board=board,
        roll_number="SYN0945957",
        category="General",
    )


def parsed(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_no_rows_gives_the_header_line_only() -> None:
    assert parsed(render_verified_csv([])) == [list(HEADER)]


def test_one_row_per_application_with_an_iso_date_and_the_status() -> None:
    result = parsed(render_verified_csv([row()]))

    assert result[0] == list(HEADER)
    assert result[1] == [
        "SYN-APP-004",
        "Latha Sharma",
        "2006-12-10",
        "CBSE",
        "SYN0945957",
        "General",
        "verified",
        "",
        "",
        "",
    ]
    assert len(result) == 2


# ISSUE-007 [NOTASK-2]: the export now names the verifier's decision. An automatic verification has
# no decision, so those three cells stay empty rather than invent a time.
def test_a_decided_application_names_the_decision_the_verifier_and_the_time() -> None:
    decided = VerifiedRow(
        application_ref="SYN-APP-004",
        full_name="Latha Sharma",
        date_of_birth=date(2006, 12, 10),
        board="CBSE",
        roll_number="SYN0945957",
        category="General",
        decision="approve",
        decided_by="Demo Verifier",
        decided_at=datetime(2026, 10, 7, 7, 40, 25, tzinfo=UTC),
    )

    result = parsed(render_verified_csv([decided]))

    assert result[1][7:] == ["approve", "Demo Verifier", "2026-10-07T07:40:25+00:00"]


def test_a_verifier_name_that_looks_like_a_formula_is_neutralised() -> None:
    decided = VerifiedRow(
        application_ref="SYN-APP-004",
        full_name="Latha Sharma",
        date_of_birth=date(2006, 12, 10),
        board="CBSE",
        roll_number="SYN0945957",
        category="General",
        decision="approve",
        decided_by="=CMD()",
        decided_at=datetime(2026, 10, 7, 7, 40, 25, tzinfo=UTC),
    )

    assert parsed(render_verified_csv([decided]))[1][8] == "'=CMD()"


@pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
def test_a_cell_that_starts_like_a_formula_is_prefixed_so_it_shows_as_text(lead: str) -> None:
    assert neutralise(f"{lead}SUM(A1)") == f"'{lead}SUM(A1)"


def test_an_ordinary_cell_is_left_alone() -> None:
    assert neutralise("Latha Sharma") == "Latha Sharma"
    assert neutralise("") == ""


def test_a_malicious_name_is_neutralised_in_the_file() -> None:
    result = parsed(render_verified_csv([row(full_name='=HYPERLINK("http://x","click")')]))

    assert result[1][1] == '\'=HYPERLINK("http://x","click")'


def test_commas_and_quotes_inside_a_cell_stay_one_cell() -> None:
    result = parsed(render_verified_csv([row(board='State, "Special" Board')]))

    assert result[1][3] == 'State, "Special" Board'
    assert len(result[1]) == len(HEADER)
