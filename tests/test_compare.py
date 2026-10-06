"""Compare every extracted field with the application (US-00-004, AC-US-00-004-1 to -5).

Pure: fields and application values in, one result per field out. No database or engine.
"""

from datetime import date

from app.domain.compare import (
    ApplicationValues,
    FieldToCompare,
    compare_fields,
    review_reason_after,
)

THRESHOLD = 0.85

APPLICATION = ApplicationValues(
    full_name="Latha Sharma",
    father_name="Salim Sharma",
    date_of_birth=date(2006, 12, 10),
    board="Karnataka State Board",
    roll_number="SYN0945957",
    marks={"English": 59, "Hindi": 77},
)


def field(field_id: int, name: str, value: str, subject: str | None = None) -> FieldToCompare:
    return FieldToCompare(field_id=field_id, name=name, subject=subject, value=value)


def compare(document_type: str, *fields: FieldToCompare) -> dict[int, str]:
    return dict(compare_fields(document_type, fields, APPLICATION, name_threshold=THRESHOLD))


def test_a_name_with_the_same_words_in_another_order_matches_and_a_different_name_does_not() -> (
    None
):
    result = compare(
        "10th_marksheet", field(1, "name", "Sharma Latha"), field(2, "father_name", "Ravi Menon")
    )

    assert result == {1: "match", 2: "mismatch"}


def test_dates_match_after_normalising_the_print_format_and_a_day_off_does_not() -> None:
    result = compare(
        "10th_marksheet",
        field(1, "dob", "10/12/2006"),
        field(2, "dob", "10 December 2006"),
        field(3, "dob", "11/12/2006"),
        field(4, "dob", "not a date"),
    )

    assert result == {1: "match", 2: "match", 3: "mismatch", 4: "mismatch"}


def test_a_roll_number_one_character_off_does_not_match() -> None:
    result = compare(
        "10th_marksheet",
        field(1, "roll_number", "SYN0945957"),
        field(2, "roll_number", "SYN0945958"),
    )

    assert result == {1: "match", 2: "mismatch"}


def test_marks_are_exact_per_subject_and_a_difference_of_one_does_not_match() -> None:
    result = compare(
        "10th_marksheet",
        field(1, "marks", "59", subject="English"),
        field(2, "marks", "78", subject="Hindi"),
        field(3, "marks", "59", subject="english"),
    )

    assert result == {1: "match", 2: "mismatch", 3: "match"}


def test_a_subject_the_application_does_not_have_or_a_mark_that_is_not_a_number_is_a_mismatch() -> (
    None
):
    result = compare(
        "10th_marksheet",
        field(1, "marks", "80", subject="Mathematics"),
        field(2, "marks", "fifty", subject="English"),
    )

    assert result == {1: "mismatch", 2: "mismatch"}


def test_the_board_matches_ignoring_case_and_surrounding_spaces() -> None:
    result = compare(
        "12th_marksheet",
        field(1, "board", "  karnataka state board "),
        field(2, "board", "CBSE"),
    )

    assert result == {1: "match", 2: "mismatch"}


def test_a_field_the_document_type_does_not_carry_is_skipped_not_a_mismatch() -> None:
    result = compare(
        "id_proof",
        field(1, "name", "Latha Sharma"),
        field(2, "roll_number", "WRONG"),
        field(3, "marks", "1", subject="English"),
        field(4, "board", "Other Board"),
    )

    assert result == {1: "match", 2: "skipped", 3: "skipped", 4: "skipped"}


def test_a_document_number_has_no_application_value_so_it_is_skipped() -> None:
    result = compare("id_proof", field(1, "document_number", "SYNID12345678"))

    assert result == {1: "skipped"}


def test_a_carried_field_that_was_not_extracted_never_matches() -> None:
    result = compare(
        "10th_marksheet",
        field(1, "name", ""),
        field(2, "dob", "  "),
        field(3, "marks", "", subject="English"),
    )

    assert result == {1: "mismatch", 2: "mismatch", 3: "mismatch"}


def test_an_unknown_document_type_carries_nothing_so_everything_is_skipped() -> None:
    result = compare("unknown", field(1, "name", "Latha Sharma"))

    assert result == {1: "skipped"}


def test_every_field_given_gets_a_result() -> None:
    fields = [field(n, "name", "Latha Sharma") for n in range(1, 6)]

    assert set(compare("10th_marksheet", *fields)) == {1, 2, 3, 4, 5}


def test_a_mismatch_is_flagged_unless_the_field_already_has_another_reason() -> None:
    assert review_reason_after("mismatch", None) == "mismatch"
    assert review_reason_after("mismatch", "low_confidence") == "low_confidence"
    assert review_reason_after("mismatch", "mismatch") == "mismatch"


def test_a_match_clears_the_mismatch_flag_but_keeps_another_steps_reason() -> None:
    assert review_reason_after("match", "mismatch") is None
    assert review_reason_after("match", "low_confidence") == "low_confidence"
    assert review_reason_after("skipped", None) is None
