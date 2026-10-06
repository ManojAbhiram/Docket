"""The application value shown beside each extracted value (US-00-006, REQ-022)."""

from datetime import date

import pytest

from app.domain.review import ApplicationValues, application_value

APPLICATION = ApplicationValues(
    full_name="Latha Sharma",
    father_name="Salim Sharma",
    date_of_birth=date(2006, 12, 10),
    board="CBSE",
    roll_number="SYN0945957",
    marks={"English": 59, "Mathematics": 87},
)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("name", "Latha Sharma"),
        ("father_name", "Salim Sharma"),
        ("dob", "2006-12-10"),
        ("board", "CBSE"),
        ("roll_number", "SYN0945957"),
        ("document_number", None),
    ],
)
def test_each_field_is_paired_with_the_application_value_it_is_compared_to(
    field: str, expected: str | None
) -> None:
    assert application_value(field, None, APPLICATION) == expected


def test_a_mark_is_paired_with_the_subject_ignoring_case() -> None:
    assert application_value("marks", "english", APPLICATION) == "59"
    assert application_value("marks", "MATHEMATICS", APPLICATION) == "87"


def test_a_subject_the_application_lacks_has_no_value() -> None:
    assert application_value("marks", "Hindi", APPLICATION) is None
    assert application_value("marks", None, APPLICATION) is None


def test_an_unknown_field_name_has_no_value() -> None:
    assert application_value("mystery", None, APPLICATION) is None
