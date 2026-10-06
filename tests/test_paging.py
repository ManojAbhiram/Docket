"""Opaque list cursors (US-00-001, US-00-002). A cursor not made by this API is a 422, not a 500."""

import base64
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.paging import InvalidCursorError, decode_cursor, encode_cursor

STAMP = datetime(2026, 10, 6, 9, 30, 15, 123456, tzinfo=UTC)
ROW = UUID("0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b")


def test_a_cursor_decodes_to_the_time_and_id_it_was_made_from() -> None:
    assert decode_cursor(encode_cursor(STAMP, ROW)) == (STAMP, ROW)


def test_a_cursor_is_url_safe_text_without_padding() -> None:
    token = encode_cursor(STAMP, ROW)

    assert "=" not in token
    assert token.replace("-", "").replace("_", "").isalnum()


@pytest.mark.parametrize(
    "token",
    [
        "not-a-cursor",
        "",
        base64.urlsafe_b64encode(b"[1, 2]").decode(),
        base64.urlsafe_b64encode(b'{"u": "yesterday", "i": "x"}').decode(),
        base64.urlsafe_b64encode(b'{"u": "2026-10-06T09:00:00+00:00"}').decode(),
    ],
)
def test_a_cursor_that_is_not_ours_is_refused(token: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(token)
