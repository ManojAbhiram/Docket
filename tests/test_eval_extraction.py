"""The extraction scorer compares what the app extracts with what a document prints."""

from app.domain.extract import ExtractedField
from evals.extraction import expected_values, score_document
from seed.dataset import DocumentRecord, build_dataset


def _field(name: str, value: str, subject: str | None = None) -> ExtractedField:
    return ExtractedField(
        field_name=name,
        subject=subject,
        value=value,
        confidence=0.99,
        box=None,
        needs_review=False,
        review_reason=None,
    )


def _doc(doc_type: str) -> DocumentRecord:
    return next(d for d in build_dataset().documents if d.doc_type == doc_type)


def _perfect(doc: DocumentRecord) -> list[ExtractedField]:
    return [_field(n, v, s) for (n, s), v in expected_values(doc).items()]


def test_a_marksheet_expects_every_printed_value_per_field_and_subject() -> None:
    doc = _doc("10th_marksheet")

    expected = expected_values(doc)

    assert expected[("name", None)] == doc.printed_name
    assert expected[("roll_number", None)] == doc.printed_roll_number
    for subject, mark in (doc.printed_marks or {}).items():
        assert expected[("marks", subject)] == str(mark)


def test_an_id_proof_expects_its_document_number_and_no_marks() -> None:
    doc = _doc("id_proof")

    expected = expected_values(doc)

    assert expected[("document_number", None)] == doc.printed_id_number
    assert not any(name == "marks" for name, _ in expected)


def test_a_perfect_extraction_scores_every_field_correct() -> None:
    doc = _doc("10th_marksheet")

    score = score_document(doc, "10th_marksheet", _perfect(doc))

    assert score.type_ok
    assert all(score.correct.values())


def test_names_are_compared_ignoring_case_and_word_order() -> None:
    doc = _doc("10th_marksheet")
    swapped_name = _field("name", " ".join(reversed(doc.printed_name.upper().split())))
    fields = [f for f in _perfect(doc) if f.field_name != "name"] + [swapped_name]

    score = score_document(doc, "10th_marksheet", fields)

    assert score.correct[("name", None)]


def test_a_missing_field_is_incorrect() -> None:
    doc = _doc("10th_marksheet")
    fields = [f for f in _perfect(doc) if f.field_name != "board"]

    score = score_document(doc, "10th_marksheet", fields)

    assert score.correct[("board", None)] is False


def test_a_wrong_value_is_incorrect() -> None:
    doc = _doc("10th_marksheet")
    fields = [f for f in _perfect(doc) if f.field_name != "roll_number"]
    fields.append(_field("roll_number", "WRONG"))

    score = score_document(doc, "10th_marksheet", fields)

    assert score.correct[("roll_number", None)] is False


def test_a_wrong_document_type_is_recorded_and_still_scores_fields() -> None:
    doc = _doc("10th_marksheet")

    score = score_document(doc, "unknown", [])

    assert score.type_ok is False
    assert score.predicted_type == "unknown"
    assert not any(score.correct.values())
