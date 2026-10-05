"""Score OCR text against what a synthetic document prints.

This checks whether each printed value is present in the OCR text. It is an upper
bound on extraction: no field extractor exists yet, so a hit does not prove the
value would be assigned to the right field. Names are order-free, dates tolerate
different separators, and marks must follow their subject.
"""

import re
from dataclasses import dataclass

from seed.dataset import DocumentRecord

FIELD_TYPES = ("name", "father_name", "dob", "roll_number", "marks", "board")


@dataclass(frozen=True)
class FieldScore:
    hits: int
    total: int


def score_document(doc: DocumentRecord, text: str) -> dict[str, FieldScore]:
    """Hits and totals per field type for one document. Absent fields are left out."""
    scores = {
        "name": _single(_all_tokens_present(doc.printed_name, text)),
        "dob": _single(_date_present(doc.printed_dob, text)),
    }
    if doc.printed_father_name is not None:
        scores["father_name"] = _single(_all_tokens_present(doc.printed_father_name, text))
    if doc.printed_roll_number is not None:
        scores["roll_number"] = _single(_squash(doc.printed_roll_number) in _squash(text))
    if doc.printed_board is not None:
        scores["board"] = _single(_squash(doc.printed_board) in _squash(text))
    if doc.printed_marks is not None:
        found = [_mark_present(subject, mark, text) for subject, mark in doc.printed_marks.items()]
        scores["marks"] = FieldScore(hits=sum(found), total=len(found))
    return scores


def accuracy_by_field(per_document: list[dict[str, FieldScore]]) -> dict[str, float]:
    """Hit rate per field type over all documents that carry that field."""
    accuracy: dict[str, float] = {}
    for field in FIELD_TYPES:
        hits = sum(scores[field].hits for scores in per_document if field in scores)
        total = sum(scores[field].total for scores in per_document if field in scores)
        if total:
            accuracy[field] = hits / total
    return accuracy


def approx_distance(needle: str, haystack: str) -> int:
    """Smallest edit distance between `needle` and any substring of `haystack`.

    Insertions, deletions and substitutions cost 1 each (Sellers' variant of the
    Levenshtein table: a match may start anywhere in the text for free).
    """
    if not needle:
        return 0
    previous = list(range(len(needle) + 1))
    best = previous[-1]
    for char in haystack:
        current = [0]
        for i, expected in enumerate(needle, start=1):
            substitution = previous[i - 1] + (expected != char)
            current.append(min(substitution, previous[i] + 1, current[i - 1] + 1))
        previous = current
        best = min(best, previous[-1])
    return best


def field_cer(doc: DocumentRecord, text: str) -> float:
    """Character error rate over the values a document prints, in 0..1.

    Each printed value is searched for in the OCR text; its error is the edit distance
    to the closest passage divided by its length. The score is the mean over values, so
    extra text on the page does not count against the engine. Case and whitespace are
    ignored.
    """
    haystack = _normalise(text)
    rates = [
        approx_distance(value, haystack) / len(value)
        for value in (_normalise(raw) for raw in _printed_values(doc))
        if value
    ]
    return sum(rates) / len(rates) if rates else 0.0


def all_fields_found(scores: dict[str, FieldScore]) -> bool:
    return all(score.hits == score.total for score in scores.values())


def _single(hit: bool) -> FieldScore:
    return FieldScore(hits=int(hit), total=1)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text.casefold())


def _printed_values(doc: DocumentRecord) -> list[str]:
    values = [doc.printed_name, doc.printed_dob]
    for optional in (doc.printed_father_name, doc.printed_board, doc.printed_roll_number):
        if optional is not None:
            values.append(optional)
    values.extend(f"{subject}{mark}" for subject, mark in (doc.printed_marks or {}).items())
    return values


def _squash(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.casefold())


def _all_tokens_present(printed: str, text: str) -> bool:
    squashed = _squash(text)
    return all(_squash(token) in squashed for token in printed.split())


def _date_present(printed: str, text: str) -> bool:
    day, month, year = printed.split("/")
    pattern = rf"{day}\s*[/.\-]?\s*{month}\s*[/.\-]?\s*{year}"
    return re.search(pattern, text) is not None


def _mark_present(subject: str, mark: int, text: str) -> bool:
    pattern = rf"{re.escape(subject.casefold())}\D{{0,12}}{mark}(?!\d)"
    return re.search(pattern, text.casefold()) is not None
