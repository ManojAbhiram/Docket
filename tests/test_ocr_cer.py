"""Character error rate: how far the OCR text is from each printed value."""

import pytest

from evals.scoring import approx_distance, field_cer, score_document
from seed.dataset import DocumentRecord, build_dataset


@pytest.fixture(scope="module")
def doc() -> DocumentRecord:
    """A marksheet with no deliberate mismatch, so every printed value is real."""
    dataset = build_dataset(seed=1)
    return next(
        d
        for d in dataset.documents
        if d.doc_type not in ("id_proof", "transfer_certificate") and d.mismatch_field is None
    )


@pytest.fixture(scope="module")
def certificate() -> DocumentRecord:
    dataset = build_dataset(seed=1)
    return next(d for d in dataset.documents if d.doc_type == "transfer_certificate")


def _text(doc: DocumentRecord, roll: str | None = None) -> str:
    marks = doc.printed_marks or {}
    marks_lines = "\n".join(f"{subject}{mark}" for subject, mark in marks.items())
    return (
        f"{doc.printed_name}\n"
        f"{doc.printed_father_name}\n"
        f"{doc.printed_dob}\n"
        f"{roll if roll is not None else doc.printed_roll_number}\n"
        f"{doc.printed_board}\n"
        f"{marks_lines}"
    )


def test_an_exact_substring_has_distance_zero() -> None:
    assert approx_distance("roll", "the roll number") == 0


def test_one_substituted_character_has_distance_one() -> None:
    assert approx_distance("roll", "the rolx number") == 1


def test_a_needle_against_an_empty_haystack_costs_its_whole_length() -> None:
    assert approx_distance("SYN123", "") == 6


def test_one_deleted_character_in_the_haystack_copy_has_distance_one() -> None:
    assert approx_distance("SYN1234", "x SYN134 y") == 1


def test_extra_text_around_the_needle_does_not_change_the_distance() -> None:
    bare = approx_distance("Aarav", "Aarau")
    padded = approx_distance("Aarav", "lots of words before Aarau and more after")

    assert padded == bare == 1


def test_text_holding_every_printed_value_has_zero_cer(doc: DocumentRecord) -> None:
    assert field_cer(doc, _text(doc)) == 0.0


def test_empty_text_has_a_cer_of_one(doc: DocumentRecord) -> None:
    assert field_cer(doc, "") == 1.0


def test_one_wrong_roll_number_character_gives_a_small_positive_cer(doc: DocumentRecord) -> None:
    roll = doc.printed_roll_number or ""
    wrong = roll[:-1] + str((int(roll[-1]) + 1) % 10)

    cer = field_cer(doc, _text(doc, roll=wrong))

    assert 0.0 < cer < 0.1


def test_whitespace_and_letter_case_in_the_text_do_not_change_the_score(
    doc: DocumentRecord,
) -> None:
    plain = _text(doc)
    disturbed = plain.upper().replace(" ", "  \t ")

    assert field_cer(doc, disturbed) == field_cer(doc, plain)


def test_a_transfer_certificate_is_scored_on_name_father_name_and_dob_only(
    certificate: DocumentRecord,
) -> None:
    scores = score_document(certificate, "")

    assert set(scores) == {"name", "father_name", "dob"}
