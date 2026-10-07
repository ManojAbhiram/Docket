"""The short reason a flagged application shows in the review queue (ISSUE-004 [NOTASK-2]).

The queue row used to show an empty "why flagged" cell. The reason is the most serious thing wrong:
an unreadable document, then a mismatch, a bad format, low confidence, a value not found.
"""

from app.domain.flag import FlaggedField, flag_reason


def field(name: str, reason: str, subject: str | None = None) -> FlaggedField:
    return FlaggedField(field_name=name, subject=subject, review_reason=reason)


def test_nothing_flagged_gives_no_reason() -> None:
    assert flag_reason([], failed_documents=0) is None


def test_a_document_that_could_not_be_read_comes_first() -> None:
    assert flag_reason([field("name", "mismatch")], failed_documents=1) == (
        "A document could not be read, and 1 more"
    )


def test_a_mismatch_names_the_field() -> None:
    assert flag_reason([field("name", "mismatch")], failed_documents=0) == "Name does not match"


def test_low_confidence_names_the_field() -> None:
    assert flag_reason([field("board", "low_confidence")], failed_documents=0) == (
        "Low confidence on board"
    )


def test_a_bad_format_and_a_missing_value_have_their_own_words() -> None:
    assert flag_reason([field("dob", "format_invalid")], failed_documents=0) == (
        "Date of birth is not in the expected format"
    )
    assert flag_reason([field("roll_number", "not_extracted")], failed_documents=0) == (
        "Roll number was not found"
    )


def test_a_mark_names_its_subject() -> None:
    assert flag_reason([field("marks", "mismatch", "Science")], failed_documents=0) == (
        "Marks: Science does not match"
    )


def test_the_most_serious_reason_wins_and_the_rest_are_counted() -> None:
    fields = [
        field("board", "low_confidence"),
        field("name", "mismatch"),
        field("roll_number", "not_extracted"),
    ]

    assert flag_reason(fields, failed_documents=0) == "Name does not match, and 2 more"
