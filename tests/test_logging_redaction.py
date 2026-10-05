"""No personal data in a log line, and a request id that cannot forge one (threat T-13, T-22, T-28).

The applicants are minors. Every test here fails until `redact_personal_data` exists in
`app/core/logging.py` and the request id is validated in `app/core/middleware.py`.
"""

import json
import re

import pytest
import structlog
from httpx import AsyncClient

from app.core.logging import configure_logging, redact_personal_data

REDACTED = "[redacted]"
PERSONAL_KEYS = [
    "name",
    "full_name",
    "father_name",
    "date_of_birth",
    "dob",
    "roll_number",
    "application_ref",
    "marks",
    "category",
    "value",
    "old_value",
    "new_value",
    "reason",
    "file_name",
    "filename",
    "email",
    "phone",
    "password",
    "token",
    "authorization",
    "cookie",
    "secret",
]


@pytest.mark.parametrize("key", PERSONAL_KEYS)
def test_a_personal_field_is_replaced_before_it_is_written(key: str) -> None:
    cleaned = redact_personal_data(None, "info", {"event": "x", key: "Latha Sharma"})

    assert cleaned[key] == REDACTED


def test_a_key_is_matched_whatever_its_case() -> None:
    cleaned = redact_personal_data(None, "info", {"event": "x", "Full_Name": "Latha Sharma"})

    assert cleaned["Full_Name"] == REDACTED


def test_a_personal_field_inside_a_nested_dict_or_list_is_replaced() -> None:
    event = {
        "event": "x",
        "details": {"name": "Latha Sharma", "count": 3},
        "rows": [{"roll_number": "SYN0945957", "row_number": 4}],
    }

    cleaned = redact_personal_data(None, "info", event)

    assert cleaned["details"] == {"name": REDACTED, "count": 3}
    assert cleaned["rows"] == [{"roll_number": REDACTED, "row_number": 4}]


@pytest.mark.parametrize(
    "key", ["request_id", "status", "duration_ms", "error_type", "document_id", "row_number"]
)
def test_an_id_a_count_or_a_class_name_is_left_as_it_is(key: str) -> None:
    assert redact_personal_data(None, "info", {"event": "x", key: "abc"})[key] == "abc"


def test_the_caller_s_own_dict_is_not_changed() -> None:
    original = {"event": "x", "full_name": "Latha Sharma"}

    redact_personal_data(None, "info", original)

    assert original["full_name"] == "Latha Sharma"


def test_a_real_log_line_carries_the_marker_and_never_the_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("info", "json")

    structlog.get_logger("import").info(
        "import.row_refused", full_name="Zzyzx Qwerty", row_number=7
    )

    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["full_name"] == REDACTED
    assert line["row_number"] == 7


async def test_a_query_string_never_reaches_the_request_log(
    capsys: pytest.CaptureFixture[str], client: AsyncClient
) -> None:
    await client.get("/healthz", params={"name": "Zzyzx Qwerty", "email": "zz@example.test"})

    out = capsys.readouterr().out
    assert "Zzyzx" not in out
    assert "zz@example.test" not in out


async def test_a_valid_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/healthz", headers={"x-request-id": "abc-123_X.y"})

    assert response.headers["x-request-id"] == "abc-123_X.y"


@pytest.mark.parametrize("bad", ["has spaces", "semi;colon", 'quote"mark', "a" * 129])
async def test_a_request_id_with_odd_characters_or_too_long_is_replaced(
    client: AsyncClient, bad: str
) -> None:
    response = await client.get("/healthz", headers={"x-request-id": bad})

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])
