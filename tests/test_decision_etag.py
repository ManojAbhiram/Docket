"""The version of an application a verifier saw, carried in the ETag and If-Match (US-00-007)."""

from datetime import UTC, datetime

import pytest

from app.api.decisions.etag import InvalidEtagError, etag_for, parse_etag

STAMP = datetime(2026, 10, 6, 9, 30, 15, 123456, tzinfo=UTC)


def test_the_etag_is_a_quoted_timestamp_that_reads_back_to_the_same_instant() -> None:
    header = etag_for(STAMP)

    assert header.startswith('"')
    assert header.endswith('"')
    assert parse_etag(header) == STAMP


def test_an_etag_without_quotes_is_accepted_too() -> None:
    assert parse_etag(STAMP.isoformat()) == STAMP


@pytest.mark.parametrize(
    "header", ["", "  ", "not-a-version", '"2026-13-45"', '"2026-10-06T09:00:00"']
)
def test_an_etag_that_is_not_ours_or_has_no_timezone_is_refused(header: str) -> None:
    with pytest.raises(InvalidEtagError):
        parse_etag(header)
