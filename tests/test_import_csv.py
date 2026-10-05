"""Import applications from a CSV (US-00-001, REQ-001 to REQ-003).

Every test here fails until `app/domain/importing.py` exists. The happy path uses the synthetic CSV
the seed writes, so the parser is tested against the same file staff would import.
"""

import csv
import io
import json
from dataclasses import asdict
from datetime import date

import pytest

from app.domain.importing import (
    ImportFileError,
    ImportTooLargeError,
    parse_applications,
)
from seed.dataset import CSV_COLUMNS, applications_csv, build_dataset

GOOD_ROW = {
    "application_id": "SYN-APP-900",
    "name": "Zzyzx Qwerty",
    "father_name": "Plugh Qwerty",
    "date_of_birth": "2006-12-10",
    "board": "CBSE",
    "roll_number": "SYN1234567",
    "marks_by_subject": json.dumps({"English": 59, "Hindi": 77}),
    "category": "General",
}


def csv_bytes(*rows: dict[str, str], columns: tuple[str, ...] = CSV_COLUMNS) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def test_the_seed_file_imports_every_row_with_every_value_kept() -> None:
    dataset = build_dataset()

    outcome = parse_applications(applications_csv(dataset).encode("utf-8"))

    assert outcome.rows_read == 20
    assert outcome.errors == ()
    first, expected = outcome.rows[0], dataset.applications[0]
    assert (first.application_ref, first.full_name, first.date_of_birth) == (
        expected.application_id,
        expected.name,
        expected.dob,
    )
    assert first.marks == expected.marks
    assert first.category == expected.category


def test_a_file_with_a_byte_order_mark_and_windows_line_endings_reads_the_same() -> None:
    plain = csv_bytes(GOOD_ROW)
    windows = b"\xef\xbb\xbf" + plain.replace(b"\n", b"\r\n")

    assert parse_applications(windows).rows == parse_applications(plain).rows


@pytest.mark.parametrize("column", ["application_id", "name", "roll_number", "category"])
def test_a_row_missing_a_required_value_is_refused_with_its_row_number_and_column(
    column: str,
) -> None:
    outcome = parse_applications(csv_bytes(GOOD_ROW, {**GOOD_ROW, column: ""}))

    assert outcome.rows_read == 2
    assert len(outcome.rows) == 1
    assert [(e.row_number, e.column_name, e.reason_code) for e in outcome.errors] == [
        (2, column, "missing_value")
    ]


def test_an_unreadable_date_is_refused() -> None:
    outcome = parse_applications(csv_bytes({**GOOD_ROW, "date_of_birth": "10th Dec"}))

    assert [(e.column_name, e.reason_code) for e in outcome.errors] == [
        ("date_of_birth", "bad_date")
    ]


def test_a_date_of_birth_outside_1950_to_2020_is_refused() -> None:
    outcome = parse_applications(csv_bytes({**GOOD_ROW, "date_of_birth": "2061-12-10"}))

    assert [e.reason_code for e in outcome.errors] == ["out_of_range"]


@pytest.mark.parametrize(
    "marks",
    ["not json", '["English", 59]', '{"English": "fifty"}', '{"English": 101}', '{"English": -1}'],
)
def test_marks_that_are_not_a_subject_to_whole_number_object_from_0_to_100_are_refused(
    marks: str,
) -> None:
    outcome = parse_applications(csv_bytes({**GOOD_ROW, "marks_by_subject": marks}))

    assert [(e.column_name, e.reason_code) for e in outcome.errors] == [
        ("marks_by_subject", "bad_marks")
    ]


def test_a_value_longer_than_the_column_allows_is_refused() -> None:
    outcome = parse_applications(csv_bytes({**GOOD_ROW, "name": "A" * 121}))

    assert [(e.column_name, e.reason_code) for e in outcome.errors] == [("name", "too_long")]


def test_a_row_with_the_wrong_number_of_columns_is_refused() -> None:
    raw = csv_bytes(GOOD_ROW) + b"SYN-APP-901,Only Two\n"

    outcome = parse_applications(raw)

    assert [(e.row_number, e.reason_code) for e in outcome.errors] == [(2, "malformed_row")]


def test_a_repeated_application_id_in_the_file_is_refused_not_overwritten() -> None:
    outcome = parse_applications(csv_bytes(GOOD_ROW, {**GOOD_ROW, "name": "Someone Else"}))

    assert [r.full_name for r in outcome.rows] == ["Zzyzx Qwerty"]
    assert [(e.row_number, e.reason_code) for e in outcome.errors] == [
        (2, "duplicate_application_ref")
    ]


def test_an_application_id_already_in_the_database_is_refused() -> None:
    outcome = parse_applications(csv_bytes(GOOD_ROW), existing_refs=frozenset({"SYN-APP-900"}))

    assert outcome.rows == ()
    assert [e.reason_code for e in outcome.errors] == ["duplicate_application_ref"]


def test_valid_rows_are_created_and_malformed_rows_are_listed_with_reasons() -> None:
    rows = [
        {**GOOD_ROW, "application_id": "SYN-APP-901"},
        {**GOOD_ROW, "application_id": "SYN-APP-902", "date_of_birth": "bad"},
        {**GOOD_ROW, "application_id": "SYN-APP-903"},
    ]

    outcome = parse_applications(csv_bytes(*rows))

    assert [r.application_ref for r in outcome.rows] == ["SYN-APP-901", "SYN-APP-903"]
    assert [(e.row_number, e.reason_code) for e in outcome.errors] == [(2, "bad_date")]
    assert outcome.rows_read == 3


def test_a_refused_row_never_carries_the_value_that_failed() -> None:
    outcome = parse_applications(csv_bytes({**GOOD_ROW, "date_of_birth": "Zzyzx-not-a-date"}))

    assert "Zzyzx" not in repr(asdict(outcome.errors[0]))
    assert "Qwerty" not in repr(outcome.errors)


def test_a_missing_column_refuses_the_whole_file_and_names_the_column() -> None:
    columns = tuple(c for c in CSV_COLUMNS if c != "roll_number")

    with pytest.raises(ImportFileError) as raised:
        parse_applications(csv_bytes(GOOD_ROW, columns=columns))

    assert raised.value.details == {"column": "roll_number"}


def test_a_file_that_is_not_utf8_text_is_refused() -> None:
    with pytest.raises(ImportFileError):
        parse_applications(b"\xff\xfe\x00\x01 not text")


def test_a_file_over_the_size_cap_is_refused_before_it_is_read() -> None:
    with pytest.raises(ImportTooLargeError):
        parse_applications(csv_bytes(GOOD_ROW), max_bytes=10)


def test_a_file_with_more_rows_than_the_cap_is_refused() -> None:
    rows = [{**GOOD_ROW, "application_id": f"SYN-APP-{n:03d}"} for n in range(3)]

    with pytest.raises(ImportTooLargeError):
        parse_applications(csv_bytes(*rows), max_rows=2)


def test_the_parsed_date_is_a_date() -> None:
    outcome = parse_applications(csv_bytes(GOOD_ROW))

    assert outcome.rows[0].date_of_birth == date(2006, 12, 10)
