"""The short reason a flagged application shows in the review queue (ISSUE-004).

It names the most serious thing wrong, in the verifier's words: an unreadable document first, then a
mismatch, a bad format, low confidence and a value not found. Anything else flagged is counted.
"""

from collections.abc import Sequence
from dataclasses import dataclass

_LABELS = {
    "name": "name",
    "father_name": "father's name",
    "dob": "date of birth",
    "board": "board",
    "roll_number": "roll number",
    "marks": "marks",
    "document_number": "document number",
}
# Most serious first. A reason this list does not know sorts last and reads as "needs a look".
_ORDER = ("mismatch", "format_invalid", "low_confidence", "not_extracted")


@dataclass(frozen=True)
class FlaggedField:
    """One extracted field that needs a look, and why."""

    field_name: str
    subject: str | None
    review_reason: str


def _label(item: FlaggedField) -> str:
    label = _LABELS.get(item.field_name, item.field_name)
    return f"{label}: {item.subject}" if item.subject else label


def _sentence(item: FlaggedField) -> str:
    label = _label(item)
    capital = label[:1].upper() + label[1:]
    if item.review_reason == "mismatch":
        return f"{capital} does not match"
    if item.review_reason == "format_invalid":
        return f"{capital} is not in the expected format"
    if item.review_reason == "low_confidence":
        return f"Low confidence on {label}"
    if item.review_reason == "not_extracted":
        return f"{capital} was not found"
    return f"{capital} needs a look"


def _rank(item: FlaggedField) -> int:
    return _ORDER.index(item.review_reason) if item.review_reason in _ORDER else len(_ORDER)


def flag_reason(fields: Sequence[FlaggedField], *, failed_documents: int) -> str | None:
    """The one-line reason, or None when nothing is flagged."""
    count = len(fields) + failed_documents
    if count == 0:
        return None
    first = (
        "A document could not be read" if failed_documents else _sentence(min(fields, key=_rank))
    )
    return first if count == 1 else f"{first}, and {count - 1} more"
