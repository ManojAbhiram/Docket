"""Turn recognised words into typed fields, each with a confidence (US-00-003, REQ-010, REQ-011).

Every test here fails until `app/domain/extract.py` exists. Words are laid out the way the
synthetic pages print them: a label on the left and its value on the same row, then a marks table.
"""

import pytest

from app.domain.extract import ExtractedField, extract_fields
from app.gateway import OcrWord

CUTOFF = 0.95


def word(text: str, x: float, y: float, confidence: float = 0.99) -> OcrWord:
    return OcrWord(text=text, confidence=confidence, box=(x, y, 10.0 * len(text), 22.0))


def labelled(label: str, value: str, y: float, confidence: float = 0.99) -> list[OcrWord]:
    return [word(label, 10, y), word(value, 220, y, confidence)]


def marksheet(**overrides: str) -> list[OcrWord]:
    values = {
        "name": "Latha Sharma",
        "father": "Salim Sharma",
        "dob": "10/12/2006",
        "board": "CBSE",
        "roll": "SYN0945957",
    } | overrides
    return [
        word("Secondary School Examination, Class X: Statement of Marks", 10, 0),
        *labelled("Name", values["name"], 60),
        *labelled("Father's name", values["father"], 100),
        *labelled("Date of birth", values["dob"], 140),
        *labelled("Board", values["board"], 180),
        *labelled("Roll number", values["roll"], 220),
        word("Subject", 10, 270),
        word("Marks", 220, 270),
        *labelled("English", "59", 310),
        *labelled("Mathematics", "87", 350),
        word("SAMPLE, SYNTHETIC DOCUMENT, NOT A REAL RECORD (SYN-APP-004)", 10, 420),
    ]


def by_key(fields: tuple[ExtractedField, ...]) -> dict[tuple[str, str | None], ExtractedField]:
    return {(field.field_name, field.subject): field for field in fields}


def test_each_labelled_field_is_read_with_its_value_confidence_and_box() -> None:
    fields = by_key(extract_fields(marksheet(), "10th_marksheet", confidence_cutoff=CUTOFF))

    name = fields[("name", None)]
    assert (name.value, name.confidence, name.needs_review) == ("Latha Sharma", 0.99, False)
    assert name.box == (220.0, 60.0, 120.0, 22.0)
    assert fields[("roll_number", None)].value == "SYN0945957"
    assert fields[("dob", None)].value == "10/12/2006"


def test_the_marks_table_gives_one_field_per_subject() -> None:
    fields = by_key(extract_fields(marksheet(), "10th_marksheet", confidence_cutoff=CUTOFF))

    assert fields[("marks", "English")].value == "59"
    assert fields[("marks", "Mathematics")].value == "87"


def test_the_title_and_the_footer_are_not_read_as_fields() -> None:
    fields = extract_fields(marksheet(), "10th_marksheet", confidence_cutoff=CUTOFF)

    assert {field.field_name for field in fields} == {
        "name",
        "father_name",
        "dob",
        "board",
        "roll_number",
        "marks",
    }


def test_a_label_is_matched_ignoring_case() -> None:
    words = [word("DATE OF BIRTH", 10, 140), word("10/12/2006", 220, 140)]

    fields = by_key(extract_fields(words, "id_proof", confidence_cutoff=CUTOFF))

    assert fields[("dob", None)].value == "10/12/2006"


def test_a_value_is_taken_from_the_labels_own_row_not_a_neighbouring_one() -> None:
    words = [
        *labelled("Name", "Latha Sharma", 60),
        *labelled("Father's name", "Salim Sharma", 90),
    ]

    fields = by_key(extract_fields(words, "transfer_certificate", confidence_cutoff=CUTOFF))

    assert fields[("name", None)].value == "Latha Sharma"
    assert fields[("father_name", None)].value == "Salim Sharma"


def test_a_field_below_the_confidence_cutoff_goes_to_review_with_its_reason() -> None:
    words = marksheet()
    words[2] = word("Latha Sharma", 220, 60, confidence=0.80)

    name = by_key(extract_fields(words, "10th_marksheet", confidence_cutoff=CUTOFF))[("name", None)]

    assert (name.needs_review, name.review_reason) == (True, "low_confidence")


def test_a_field_exactly_at_the_cutoff_is_not_sent_to_review() -> None:
    words = marksheet()
    words[2] = word("Latha Sharma", 220, 60, confidence=CUTOFF)

    name = by_key(extract_fields(words, "10th_marksheet", confidence_cutoff=CUTOFF))[("name", None)]

    assert name.needs_review is False


@pytest.mark.parametrize("bad_date", ["tenth December", "32/13/2006"])
def test_an_unreadable_date_fails_its_format_check_whatever_the_confidence(bad_date: str) -> None:
    fields = extract_fields(marksheet(dob=bad_date), "10th_marksheet", confidence_cutoff=CUTOFF)

    dob = by_key(fields)[("dob", None)]
    assert (dob.needs_review, dob.review_reason) == (True, "format_invalid")


def test_a_roll_number_with_symbols_fails_its_format_check() -> None:
    fields = extract_fields(marksheet(roll="SYN09@5"), "10th_marksheet", confidence_cutoff=CUTOFF)

    roll = by_key(fields)[("roll_number", None)]
    assert (roll.needs_review, roll.review_reason) == (True, "format_invalid")


@pytest.mark.parametrize("mark", ["5x", "101", "-3"])
def test_a_mark_that_is_not_a_whole_number_from_0_to_100_fails_its_format_check(mark: str) -> None:
    words = marksheet()
    words[14] = word(mark, 220, 310)

    english = by_key(extract_fields(words, "10th_marksheet", confidence_cutoff=CUTOFF))[
        ("marks", "English")
    ]

    assert (english.needs_review, english.review_reason) == (True, "format_invalid")


def test_a_field_the_engine_did_not_find_is_kept_for_review_not_dropped() -> None:
    words = [w for w in marksheet() if w.text not in {"Board", "CBSE"}]

    board = by_key(extract_fields(words, "10th_marksheet", confidence_cutoff=CUTOFF))[
        ("board", None)
    ]

    assert (board.value, board.confidence, board.needs_review, board.review_reason) == (
        "",
        0.0,
        True,
        "not_extracted",
    )


def test_a_document_type_is_only_asked_for_the_fields_it_carries() -> None:
    words = [*labelled("Name", "Latha Sharma", 60), *labelled("Date of birth", "10/12/2006", 100)]

    names = {f.field_name for f in extract_fields(words, "id_proof", confidence_cutoff=CUTOFF)}

    assert names == {"name", "dob", "document_number"}


def test_an_unknown_document_type_yields_no_fields() -> None:
    assert extract_fields(marksheet(), "unknown", confidence_cutoff=CUTOFF) == ()
