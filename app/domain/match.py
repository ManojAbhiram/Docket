"""Compare what a document says with what the application says (US-00-004).

Pure functions: text and numbers in, a yes or no out. Dates are read day first, which is how the
Indian marksheets in the seed print them (assumption, question Q-011).
"""

from datetime import UTC, date, datetime
from difflib import SequenceMatcher

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d-%b-%Y", "%d %b %Y")

_MARKSHEET_FIELDS = frozenset({"name", "father_name", "dob", "board", "roll_number", "marks"})
_FIELDS_BY_TYPE: dict[str, frozenset[str]] = {
    "10th_marksheet": _MARKSHEET_FIELDS,
    "12th_marksheet": _MARKSHEET_FIELDS,
    "id_proof": frozenset({"name", "dob", "document_number"}),
    "transfer_certificate": frozenset({"name", "father_name", "dob", "document_number"}),
}


def names_match(document: str, application: str, *, threshold: float) -> bool:
    """Token-sorted similarity: the same words in any order, case and spacing, at the threshold."""
    similarity = SequenceMatcher(None, _sorted_tokens(document), _sorted_tokens(application))
    return similarity.ratio() >= threshold


def parse_printed_date(printed: str) -> date | None:
    """Read a date in any of the formats the marksheets print, or None if it is unreadable."""
    text = printed.strip()
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    return None


def dates_match(printed: str, application: date) -> bool:
    """Exact after the printed format is normalised. An unreadable date never matches."""
    return parse_printed_date(printed) == application


def roll_numbers_match(document: str, application: str) -> bool:
    """Exact, apart from spaces around the value."""
    return document.strip() == application.strip()


def marks_match(document: dict[str, int], application: dict[str, int]) -> bool:
    """Exact in every subject, ignoring the case of the subject name. A missing subject fails."""
    return _by_subject(document) == _by_subject(application)


def fields_for(document_type: str) -> frozenset[str]:
    """The fields a document type carries. Others are skipped, not counted as a mismatch."""
    return _FIELDS_BY_TYPE.get(document_type, frozenset())


def _sorted_tokens(text: str) -> str:
    return " ".join(sorted(text.casefold().split()))


def _by_subject(marks: dict[str, int]) -> dict[str, int]:
    return {subject.casefold(): value for subject, value in marks.items()}
