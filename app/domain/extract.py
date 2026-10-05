"""Turn recognised words into typed fields with a confidence (US-00-003, ADR-0002, ADR-0005).

Rules over the OCR boxes: a label on the left, its value on the same row to the right, then a
marks table under a "Subject" header. Every field the document type carries comes back, found or
not, so nothing is silently dropped (AC-US-00-003-5).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.match import fields_for, parse_printed_date
from app.gateway import OcrWord

ReviewReason = Literal["low_confidence", "format_invalid", "not_extracted"]
Box = tuple[float, float, float, float]

_LABELS = {
    "name": "name",
    "father's name": "father_name",
    "date of birth": "dob",
    "board": "board",
    "roll number": "roll_number",
    "id number": "document_number",
    "tc number": "document_number",
}
_ORDER = ("name", "father_name", "dob", "board", "roll_number", "document_number", "marks")
_CODE = re.compile(r"^[A-Za-z0-9-]{4,30}$")
_MARK = re.compile(r"^\d{1,3}$")
_MAX_MARK = 100
_SUBJECT_AND_MARK = 2
_CURLY_APOSTROPHE = chr(0x2019)


@dataclass(frozen=True)
class ExtractedField:
    """One field read from a document. A field nobody found has an empty value and confidence 0."""

    field_name: str
    subject: str | None
    value: str
    confidence: float
    box: Box | None
    needs_review: bool
    review_reason: ReviewReason | None


def extract_fields(
    words: Sequence[OcrWord], document_type: str, *, confidence_cutoff: float
) -> tuple[ExtractedField, ...]:
    """Every field `document_type` carries, each marked for review when it cannot be trusted."""
    wanted = fields_for(document_type)
    fields: list[ExtractedField] = []
    for name in _ORDER:
        if name not in wanted:
            continue
        if name == "marks":
            fields.extend(_marks(words, confidence_cutoff))
        else:
            fields.append(_labelled(words, name, confidence_cutoff))
    return tuple(fields)


def _labelled(words: Sequence[OcrWord], name: str, cutoff: float) -> ExtractedField:
    for label in words:
        if _LABELS.get(_normalise(label.text)) != name:
            continue
        value = _value_on_row(words, label)
        if value is not None:
            return _judge(name, None, value, cutoff)
    return _not_found(name, None)


def _marks(words: Sequence[OcrWord], cutoff: float) -> list[ExtractedField]:
    header = next((w for w in words if _normalise(w.text) == "subject"), None)
    if header is None:
        return [_not_found("marks", None)]
    below = sorted((w for w in words if w.box[1] > header.box[1] + _tolerance(header)), key=_row)
    found: list[ExtractedField] = []
    for row in _rows(below):
        if len(row) >= _SUBJECT_AND_MARK:
            found.append(_judge("marks", row[0].text.strip(), row[-1], cutoff))
    return found or [_not_found("marks", None)]


def _judge(name: str, subject: str | None, value: OcrWord, cutoff: float) -> ExtractedField:
    text = value.text.strip()
    reason: ReviewReason | None = None
    if not _valid(name, text):
        reason = "format_invalid"
    elif value.confidence < cutoff:
        reason = "low_confidence"
    return ExtractedField(
        field_name=name,
        subject=subject,
        value=text,
        confidence=value.confidence,
        box=value.box,
        needs_review=reason is not None,
        review_reason=reason,
    )


def _valid(name: str, text: str) -> bool:
    if name == "dob":
        return parse_printed_date(text) is not None
    if name in {"roll_number", "document_number"}:
        return bool(_CODE.match(text))
    if name == "marks":
        return bool(_MARK.match(text)) and int(text) <= _MAX_MARK
    return bool(text)


def _not_found(name: str, subject: str | None) -> ExtractedField:
    return ExtractedField(name, subject, "", 0.0, None, True, "not_extracted")


def _value_on_row(words: Sequence[OcrWord], label: OcrWord) -> OcrWord | None:
    label_right = label.box[0] + label.box[2]
    candidates = [
        w
        for w in words
        if w is not label
        and abs(w.box[1] - label.box[1]) <= _tolerance(label)
        and w.box[0] >= label_right
    ]
    return min(candidates, key=lambda w: w.box[0], default=None)


def _rows(words: Sequence[OcrWord]) -> list[list[OcrWord]]:
    rows: list[list[OcrWord]] = []
    for word in words:
        if rows and abs(word.box[1] - rows[-1][0].box[1]) <= _tolerance(word):
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w.box[0]) for row in rows]


def _row(word: OcrWord) -> tuple[float, float]:
    return (word.box[1], word.box[0])


def _tolerance(word: OcrWord) -> float:
    return word.box[3] / 2


def _normalise(text: str) -> str:
    return " ".join(text.replace(_CURLY_APOSTROPHE, "'").casefold().split())
