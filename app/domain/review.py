"""What a verifier sees beside each extracted value (US-00-006, REQ-022).

Each extracted field is compared with one value on the application. This pairs them for display,
using the same map the comparison uses: the name fields with the full and father's names, the date
of birth with the application's date, a mark with the application's mark for that subject. A
document number has nothing on the application to be set beside.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ApplicationValues:
    """The application's own values, as the admissions office supplied them."""

    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]


def application_value(
    field_name: str, subject: str | None, application: ApplicationValues
) -> str | None:
    """The application value a field is set beside, or None when there is none."""
    if field_name == "name":
        return application.full_name
    if field_name == "father_name":
        return application.father_name
    if field_name == "dob":
        return application.date_of_birth.isoformat()
    if field_name == "board":
        return application.board
    if field_name == "roll_number":
        return application.roll_number
    if field_name == "marks" and subject is not None:
        by_subject = {name.casefold(): mark for name, mark in application.marks.items()}
        mark = by_subject.get(subject.casefold())
        return None if mark is None else str(mark)
    return None
