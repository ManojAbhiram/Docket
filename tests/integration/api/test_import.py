"""POST /api/imports and GET /api/applications against a real Postgres (US-00-001).

Needs `make db` and `make migrate`. Rows in the CSV are synthetic. A refused row is reported by
number, column and reason code, never by value, so the tests also check that no cell value comes
back in a response or lands in `import_row_errors`.
"""

import csv
import io
import json

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.helpers import SAME_ORIGIN, csrf_header, seed_user, sign_in

pytestmark = pytest.mark.integration

COLUMNS = (
    "application_id",
    "name",
    "father_name",
    "date_of_birth",
    "board",
    "roll_number",
    "marks_by_subject",
    "category",
)


def row(number: int, **overrides: str) -> dict[str, str]:
    base = {
        "application_id": f"SYN-APP-{number:03d}",
        "name": f"Applicant Number{number}",
        "father_name": f"Parent Number{number}",
        "date_of_birth": "2006-12-10",
        "board": "CBSE",
        "roll_number": f"SYN{number:07d}",
        "marks_by_subject": json.dumps({"English": 59, "Hindi": 77}),
        "category": "General",
    }
    return base | overrides


def make_csv(*rows: dict[str, str]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


async def upload(
    client: AsyncClient,
    data: bytes,
    *,
    content_type: str = "text/csv",
    headers: dict[str, str] | None = None,
) -> Response:
    return await client.post(
        "/api/imports",
        files={"file": ("applications.csv", data, content_type)},
        headers=headers if headers is not None else csrf_header(client),
    )


async def staff(client: AsyncClient, connection: AsyncConnection) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")


async def test_valid_rows_become_applications_holding_the_values_in_the_file(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(row(1), row(2)))

    assert response.status_code == 201
    body = response.json()
    assert (body["rows_read"], body["rows_created"], body["rows_rejected"]) == (2, 2, 0)
    assert body["errors"] == []
    listed = (await api.get("/api/applications")).json()["data"]
    first = next(a for a in listed if a["application_ref"] == "SYN-APP-001")
    assert first["full_name"] == "Applicant Number1"
    assert first["father_name"] == "Parent Number1"
    assert first["date_of_birth"] == "2006-12-10"
    assert first["board"] == "CBSE"
    assert first["roll_number"] == "SYN0000001"
    assert first["marks"] == {"English": 59, "Hindi": 77}
    assert first["category"] == "General"
    assert first["status"] == "missing_documents"
    assert first["rejected"] is False


async def test_a_row_with_a_missing_value_or_unreadable_date_is_not_created_and_is_listed(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(row(1, name=""), row(2, date_of_birth="10/12/2006")))

    body = response.json()
    assert body["rows_created"] == 0
    assert body["errors"] == [
        {"row_number": 1, "column_name": "name", "reason_code": "missing_value"},
        {"row_number": 2, "column_name": "date_of_birth", "reason_code": "bad_date"},
    ]
    assert (await api.get("/api/applications")).json()["data"] == []


async def test_valid_rows_are_created_and_malformed_rows_listed_in_one_import(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(row(1), row(2, marks_by_subject="not json"), row(3)))

    body = response.json()
    assert (body["rows_read"], body["rows_created"], body["rows_rejected"]) == (3, 2, 1)
    assert body["errors"] == [
        {"row_number": 2, "column_name": "marks_by_subject", "reason_code": "bad_marks"}
    ]


async def test_no_cell_value_comes_back_or_is_stored_with_a_refused_row(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(row(1, date_of_birth="31-02-2006")))

    assert "31-02-2006" not in response.text
    stored = (
        await connection.execute(
            text("SELECT row_number, column_name, reason_code FROM import_row_errors")
        )
    ).all()
    assert [tuple(r) for r in stored] == [(1, "date_of_birth", "bad_date")]


async def test_the_import_is_recorded_with_who_ran_it_and_the_file_name(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")

    await upload(api, make_csv(row(1), row(2, name="")))

    stored = (
        await connection.execute(
            text(
                "SELECT uploaded_by, source_name, rows_read, rows_created, rows_rejected "
                "FROM imports"
            )
        )
    ).one()
    assert tuple(stored) == (user_id, "applications.csv", 2, 1, 1)


async def test_importing_the_same_file_again_refuses_every_row_as_a_duplicate(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    await upload(api, make_csv(row(1), row(2)))

    again = await upload(api, make_csv(row(1), row(2)))

    assert again.json()["rows_created"] == 0
    assert {e["reason_code"] for e in again.json()["errors"]} == {"duplicate_application_ref"}
    assert len((await api.get("/api/applications")).json()["data"]) == 2


async def test_a_verifier_may_not_import_and_an_anonymous_caller_gets_401(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    anonymous = await upload(api, make_csv(row(1)), headers=SAME_ORIGIN)
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")

    refused = await upload(api, make_csv(row(1)))

    assert anonymous.status_code == 401
    assert refused.status_code == 403
    assert (await api.get("/api/applications")).json()["data"] == []


async def test_an_import_without_the_csrf_token_is_refused(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(row(1)), headers=SAME_ORIGIN)

    assert response.status_code == 403
    assert (await api.get("/api/applications")).json()["data"] == []


async def test_a_file_that_is_not_csv_is_refused_with_415(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, b"<html></html>", content_type="text/html")

    assert response.status_code == 415


async def test_a_file_over_the_size_cap_is_refused_with_413_and_creates_nothing(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await upload(api, make_csv(*[row(n) for n in range(1, 60)]))

    assert response.status_code == 413
    assert (await api.get("/api/applications")).json()["data"] == []


async def test_a_file_missing_a_required_column_or_not_utf8_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    no_column = await upload(api, b"application_id,name\nA1,B\n")
    binary = await upload(api, b"\xff\xfe\x00\x01")

    assert no_column.status_code == binary.status_code == 422


async def test_a_request_with_no_file_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await api.post("/api/imports", headers=csrf_header(api))

    assert response.status_code == 422


async def seed_applications(connection: AsyncConnection, count: int) -> None:
    for number in range(1, count + 1):
        await connection.execute(
            text(
                "INSERT INTO applications (application_ref, full_name, father_name, "
                "date_of_birth, board, roll_number, marks, category, status, updated_at) "
                "VALUES (:ref, 'A B', 'C D', '2006-01-01', 'CBSE', :roll, '{}', 'General', "
                "CAST(:status AS application_status), now() + make_interval(mins => :n))"
            ),
            {
                "ref": f"SYN-LIST-{number:03d}",
                "roll": f"R{number}",
                "status": "needs_review" if number % 2 else "verified",
                "n": number,
            },
        )


async def test_the_list_needs_a_session_and_either_role_may_read_it(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    assert (await api.get("/api/applications")).status_code == 401
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")

    assert (await api.get("/api/applications")).status_code == 200


async def test_the_list_is_newest_change_first_and_pages_without_gaps_or_repeats(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    await seed_applications(connection, 5)

    first = (await api.get("/api/applications", params={"limit": 2})).json()
    second = (
        await api.get(
            "/api/applications", params={"limit": 2, "cursor": first["page"]["next_cursor"]}
        )
    ).json()
    third = (
        await api.get(
            "/api/applications", params={"limit": 2, "cursor": second["page"]["next_cursor"]}
        )
    ).json()

    refs = [a["application_ref"] for p in (first, second, third) for a in p["data"]]
    assert refs == [f"SYN-LIST-{n:03d}" for n in (5, 4, 3, 2, 1)]
    assert [first["page"]["has_more"], second["page"]["has_more"], third["page"]["has_more"]] == [
        True,
        True,
        False,
    ]
    assert third["page"]["next_cursor"] is None


async def test_the_list_filters_by_status_and_hides_erased_applications(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    await seed_applications(connection, 4)
    await connection.execute(
        text("UPDATE applications SET erased_at = now() WHERE application_ref = 'SYN-LIST-001'")
    )

    review = (await api.get("/api/applications", params={"filter[status]": "needs_review"})).json()[
        "data"
    ]
    everything = (await api.get("/api/applications")).json()["data"]

    assert [a["application_ref"] for a in review] == ["SYN-LIST-003"]
    assert len(everything) == 3


async def test_the_review_queue_filter_leaves_out_rejected_applications(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    await seed_applications(connection, 3)
    await connection.execute(
        text("UPDATE applications SET rejected_at = now() WHERE application_ref = 'SYN-LIST-003'")
    )

    queue = (
        await api.get(
            "/api/applications",
            params={"filter[status]": "needs_review", "filter[rejected]": "false"},
        )
    ).json()["data"]
    rejected = (
        await api.get(
            "/api/applications",
            params={"filter[status]": "needs_review", "filter[rejected]": "true"},
        )
    ).json()["data"]

    assert [a["application_ref"] for a in queue] == ["SYN-LIST-001"]
    assert [a["application_ref"] for a in rejected] == ["SYN-LIST-003"]
    assert rejected[0]["rejected"] is True


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"filter[status]": "done"}, {"cursor": "not-a-cursor"}],
)
async def test_a_bad_list_parameter_is_a_422_not_a_500(
    api: AsyncClient, connection: AsyncConnection, params: dict[str, str | int]
) -> None:
    await staff(api, connection)

    assert (await api.get("/api/applications", params=params)).status_code == 422
