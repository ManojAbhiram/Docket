"""Compare what a document says with what the application says (US-00-004, REQ-012 to REQ-016).

Every test here fails until `app/domain/match.py` exists. The functions are pure: text and
numbers in, a yes or no out, so no database or engine is involved.
"""

from datetime import date

import pytest

from app.domain.match import (
    dates_match,
    fields_for,
    marks_match,
    names_match,
    roll_numbers_match,
)

APPLICATION_DOB = date(2006, 12, 10)


# Names: token-sorted similarity against a configured threshold (AC-US-00-004-1).


def test_the_same_words_in_another_order_match() -> None:
    assert names_match("Sharma Latha", "Latha Sharma", threshold=0.9)


def test_case_and_extra_spaces_do_not_change_a_name() -> None:
    assert names_match("  LATHA   sharma ", "Latha Sharma", threshold=0.9)


def test_a_different_name_does_not_match() -> None:
    assert not names_match("Ravi Menon", "Latha Sharma", threshold=0.5)


def test_a_one_letter_slip_matches_at_a_loose_threshold_and_not_at_a_strict_one() -> None:
    assert names_match("Latha Sharmaa", "Latha Sharma", threshold=0.85)
    assert not names_match("Latha Sharmaa", "Latha Sharma", threshold=0.99)


# Dates: exact after normalising the printed format (AC-US-00-004-2).


@pytest.mark.parametrize(
    "printed",
    ["2006-12-10", "10/12/2006", "10-12-2006", "10 December 2006", "10-Dec-2006", "10 Dec 2006"],
)
def test_the_same_date_in_any_printed_format_matches(printed: str) -> None:
    assert dates_match(printed, APPLICATION_DOB)


@pytest.mark.parametrize("printed", ["2006-12-09", "2006-12-11", "11/12/2006", "10 January 2007"])
def test_a_date_one_day_or_more_away_does_not_match(printed: str) -> None:
    assert not dates_match(printed, APPLICATION_DOB)


def test_an_unreadable_date_does_not_match() -> None:
    assert not dates_match("tenth of Decemb", APPLICATION_DOB)


# Roll numbers: exact (AC-US-00-004-3).


def test_the_same_roll_number_matches_and_surrounding_spaces_are_ignored() -> None:
    assert roll_numbers_match(" SYN0945957 ", "SYN0945957")


def test_a_roll_number_one_character_away_does_not_match() -> None:
    assert not roll_numbers_match("SYN0945958", "SYN0945957")


# Marks: exact in every subject (AC-US-00-004-4).

APPLICATION_MARKS = {"English": 59, "Hindi": 77, "Mathematics": 87}


def test_equal_marks_match_and_the_subject_name_ignores_case() -> None:
    assert marks_match({"english": 59, "HINDI": 77, "Mathematics": 87}, APPLICATION_MARKS)


def test_marks_that_differ_by_one_in_any_subject_do_not_match() -> None:
    assert not marks_match({"English": 59, "Hindi": 77, "Mathematics": 88}, APPLICATION_MARKS)


def test_a_subject_missing_from_the_document_does_not_match() -> None:
    assert not marks_match({"English": 59, "Hindi": 77}, APPLICATION_MARKS)


def test_an_extra_subject_on_the_document_does_not_match() -> None:
    extra = {**APPLICATION_MARKS, "Science": 74}

    assert not marks_match(extra, APPLICATION_MARKS)


# A field the document type does not carry is skipped, not counted as a mismatch (AC-US-00-004-5).


def test_a_marksheet_carries_every_compared_field() -> None:
    assert {"name", "father_name", "dob", "board", "roll_number", "marks"} <= fields_for(
        "10th_marksheet"
    )


def test_an_id_proof_carries_a_name_and_a_date_of_birth_but_no_marks_or_roll_number() -> None:
    carried = fields_for("id_proof")

    assert {"name", "dob"} <= carried
    assert "marks" not in carried
    assert "roll_number" not in carried


def test_an_unknown_document_type_carries_nothing() -> None:
    assert fields_for("unknown") == frozenset()
