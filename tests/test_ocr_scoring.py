"""OCR scoring: a printed value counts only when the OCR text really holds it."""

import pytest

from evals.scoring import (
    FIELD_TYPES,
    FieldScore,
    accuracy_by_field,
    all_fields_found,
    score_document,
)
from seed.dataset import DocumentRecord, build_dataset


@pytest.fixture(scope="module")
def doc() -> DocumentRecord:
    """A marksheet with no deliberate mismatch, so every printed field is present."""
    dataset = build_dataset(seed=1)
    return next(
        d
        for d in dataset.documents
        if d.doc_type in ("10th_marksheet", "12th_marksheet") and d.mismatch_field is None
    )


def _marks_text(doc: DocumentRecord, bump: str | None = None) -> str:
    marks = doc.printed_marks or {}
    return "\n".join(
        f"{subject} {mark + 1 if subject == bump else mark}" for subject, mark in marks.items()
    )


def _text(doc: DocumentRecord, marks: str | None = None) -> str:
    return (
        f"Name {doc.printed_name}\n"
        f"Father's name {doc.printed_father_name}\n"
        f"Date of birth {doc.printed_dob}\n"
        f"Board {doc.printed_board}\n"
        f"Roll number {doc.printed_roll_number}\n"
        f"{marks if marks is not None else _marks_text(doc)}"
    )


def test_text_holding_every_printed_value_scores_full_marks(doc: DocumentRecord) -> None:
    scores = score_document(doc, _text(doc))

    assert set(scores) == set(FIELD_TYPES)
    assert all_fields_found(scores)


def test_empty_text_scores_zero_hits_but_keeps_the_totals(doc: DocumentRecord) -> None:
    full = score_document(doc, _text(doc))
    empty = score_document(doc, "")

    assert {k: v.total for k, v in empty.items()} == {k: v.total for k, v in full.items()}
    assert all(score.hits == 0 for score in empty.values())


def test_a_name_in_reverse_order_still_counts(doc: DocumentRecord) -> None:
    reversed_name = " ".join(reversed(doc.printed_name.split()))
    text = _text(doc).replace(doc.printed_name, reversed_name)

    assert score_document(doc, text)["name"].hits == 1


def test_a_date_with_other_separators_still_counts(doc: DocumentRecord) -> None:
    text = _text(doc).replace(doc.printed_dob, doc.printed_dob.replace("/", "-"))

    assert score_document(doc, text)["dob"].hits == 1


def test_a_changed_mark_is_a_miss_for_that_subject_only(doc: DocumentRecord) -> None:
    subject = next(iter(doc.printed_marks or {}))
    text = _text(doc, marks=_marks_text(doc, bump=subject))

    marks = score_document(doc, text)["marks"]

    assert marks.hits == marks.total - 1


def test_a_roll_number_with_one_wrong_digit_is_a_miss(doc: DocumentRecord) -> None:
    roll = doc.printed_roll_number or ""
    wrong = roll[:-1] + str((int(roll[-1]) + 1) % 10)
    text = _text(doc).replace(roll, wrong)

    assert score_document(doc, text)["roll_number"].hits == 0


def test_accuracy_is_the_hit_rate_over_all_documents_carrying_the_field() -> None:
    per_document = [
        {"name": FieldScore(hits=1, total=1), "marks": FieldScore(hits=3, total=5)},
        {"name": FieldScore(hits=0, total=1)},
    ]

    accuracy = accuracy_by_field(per_document)

    assert accuracy == {"name": 0.5, "marks": 0.6}
