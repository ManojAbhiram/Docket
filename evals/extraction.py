"""Score the app's real extraction against what a synthetic document prints.

Unlike evals/scoring.py, which only checks that a printed value appears somewhere in the OCR
text, this compares the value the extractor assigned to each field. Names ignore case and word
order, dates and roll numbers ignore case and spacing, marks compare as integers.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.extract import ExtractedField
from seed.dataset import DocumentRecord

type Key = tuple[str, str | None]


@dataclass(frozen=True)
class DocumentScore:
    document_id: str
    doc_type: str
    predicted_type: str
    type_ok: bool
    correct: dict[Key, bool]


def expected_values(doc: DocumentRecord) -> dict[Key, str]:
    """What the document prints, keyed the way the extractor names its fields."""
    expected: dict[Key, str] = {("name", None): doc.printed_name, ("dob", None): doc.printed_dob}
    optional = {
        "father_name": doc.printed_father_name,
        "board": doc.printed_board,
        "roll_number": doc.printed_roll_number,
        "document_number": doc.printed_id_number,
    }
    for name, value in optional.items():
        if value is not None:
            expected[(name, None)] = value
    for subject, mark in (doc.printed_marks or {}).items():
        expected[("marks", subject)] = str(mark)
    return expected


def score_document(
    doc: DocumentRecord, predicted_type: str, fields: Sequence[ExtractedField]
) -> DocumentScore:
    """One boolean per expected field. A field the extractor did not return is incorrect."""
    found = {(f.field_name, f.subject): f.value for f in fields}
    correct = {
        key: key in found and _same(key[0], found[key], value)
        for key, value in expected_values(doc).items()
    }
    return DocumentScore(
        document_id=doc.document_id,
        doc_type=doc.doc_type,
        predicted_type=predicted_type,
        type_ok=predicted_type == doc.doc_type,
        correct=correct,
    )


def _same(name: str, got: str, want: str) -> bool:
    if name in {"name", "father_name"}:
        return sorted(got.casefold().split()) == sorted(want.casefold().split())
    if name == "marks":
        return got.strip().isdigit() and int(got) == int(want)
    return _squash(got) == _squash(want)


def _squash(text: str) -> str:
    return re.sub(r"[\s/.\-]", "", text).casefold()
