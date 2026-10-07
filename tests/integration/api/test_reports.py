"""The dashboard counts and the verified export against a real Postgres (US-00-008, US-00-009).

Needs `make db` and `make migrate`. Applications are synthetic. The counts must equal the stored
rows, and every export leaves one audit row that holds no applicant data.
"""

import csv
import io
import logging
from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.helpers import seed_user, sign_in

pytestmark = pytest.mark.integration


async def add_application(
    connection: AsyncConnection,
    ref: str,
    status: str,
    *,
    name: str = "Latha Sharma",
    rejected: bool = False,
    erased: bool = False,
    born: str = "2006-12-10",
) -> None:
    await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category, status, rejected_at, erased_at) "
            "VALUES (:ref, :name, 'Salim Sharma', :born, 'CBSE', :roll, '{}', "
            "'General', CAST(:status AS application_status), "
            "CASE WHEN :rejected THEN now() END, CASE WHEN :erased THEN now() END)"
        ),
        {
            "ref": ref,
            "name": name,
            "born": date.fromisoformat(born),
            "roll": f"R-{ref}",
            "status": status,
            "rejected": rejected,
            "erased": erased,
        },
    )


async def seed_mix(connection: AsyncConnection) -> None:
    for number in range(1, 4):
        await add_application(connection, f"SYN-V-{number}", "verified")
    for number in range(1, 3):
        await add_application(connection, f"SYN-N-{number}", "needs_review")
    await add_application(connection, "SYN-R-1", "needs_review", rejected=True)
    for number in range(1, 5):
        await add_application(connection, f"SYN-M-{number}", "missing_documents")
    await add_application(connection, "SYN-E-V", "verified", erased=True)
    await add_application(connection, "SYN-E-N", "needs_review", erased=True)


async def as_role(client: AsyncClient, connection: AsyncConnection, role: str) -> None:
    await seed_user(connection, f"{role}.demo", role)
    await sign_in(client, f"{role}.demo")


async def audit_rows(connection: AsyncConnection) -> list[tuple[object, int]]:
    result = await connection.execute(
        text("SELECT exported_by, row_count FROM export_audit ORDER BY id")
    )
    return [(r[0], r[1]) for r in result.all()]


def table(response_text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response_text)))


async def test_each_status_shows_a_count_equal_to_the_stored_records(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_mix(connection)
    await as_role(api, connection, "staff")

    response = await api.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json() == {
        "verified": 3,
        "needs_review": 3,
        "missing_documents": 4,
        "rejected": 1,
    }


async def test_a_verifier_approving_one_application_moves_a_count_from_review_to_verified(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_mix(connection)
    await as_role(api, connection, "staff")
    before = (await api.get("/api/dashboard")).json()

    await connection.execute(
        text("UPDATE applications SET status = 'verified' WHERE application_ref = 'SYN-N-1'")
    )
    after = (await api.get("/api/dashboard")).json()

    assert after["verified"] == before["verified"] + 1
    assert after["needs_review"] == before["needs_review"] - 1


async def test_the_dashboard_carries_counts_only_and_no_applicant_data(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_mix(connection)
    await as_role(api, connection, "staff")

    body = (await api.get("/api/dashboard")).text

    assert "Latha" not in body
    assert "SYN-" not in body


async def test_the_dashboard_is_zero_when_there_are_no_applications(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_role(api, connection, "staff")

    response = await api.get("/api/dashboard")

    assert response.json() == {
        "verified": 0,
        "needs_review": 0,
        "missing_documents": 0,
        "rejected": 0,
    }


async def test_a_verifier_may_read_the_dashboard_and_an_anonymous_caller_gets_401(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    assert (await api.get("/api/dashboard")).status_code == 401
    await as_role(api, connection, "verifier")

    assert (await api.get("/api/dashboard")).status_code == 200


async def test_the_export_holds_one_row_per_verified_application_and_none_for_others(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_mix(connection)
    await as_role(api, connection, "staff")

    response = await api.get("/api/exports/verified.csv")

    assert response.status_code == 200
    rows = table(response.text)
    assert [r[0] for r in rows[1:]] == ["SYN-V-1", "SYN-V-2", "SYN-V-3"]
    assert {r[6] for r in rows[1:]} == {"verified"}
    assert "SYN-E-V" not in response.text


async def test_the_export_gives_the_documented_columns_with_an_iso_date(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await add_application(connection, "SYN-V-1", "verified", born="2007-02-25")
    await as_role(api, connection, "staff")

    rows = table((await api.get("/api/exports/verified.csv")).text)

    assert rows[0] == [
        "application_id",
        "name",
        "date_of_birth",
        "board",
        "roll_number",
        "category",
        "status",
        "decision",
        "decided_by",
        "decided_at",
    ]
    assert rows[1] == [
        "SYN-V-1",
        "Latha Sharma",
        "2007-02-25",
        "CBSE",
        "R-SYN-V-1",
        "General",
        "verified",
        "",
        "",
        "",
    ]


# ISSUE-007 [NOTASK-2]: a verifier's decision shows in the export, and the latest one wins.
async def test_the_export_names_the_decision_the_verifier_and_the_time(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await add_application(connection, "SYN-V-1", "verified")
    await add_application(connection, "SYN-V-2", "verified")
    verifier_id = await seed_user(connection, "verifier.demo", "verifier")
    await as_role(api, connection, "staff")
    application_id = (
        await connection.execute(
            text("SELECT id FROM applications WHERE application_ref = 'SYN-V-1'")
        )
    ).scalar_one()
    for at in (
        datetime(2026, 10, 7, 7, 0, 0, tzinfo=UTC),
        datetime(2026, 10, 7, 7, 40, 25, tzinfo=UTC),
    ):
        await connection.execute(
            text(
                "INSERT INTO decisions (application_id, decided_by, action, created_at) "
                "VALUES (:a, :u, 'approve', :at)"
            ),
            {"a": application_id, "u": verifier_id, "at": at},
        )

    rows = table((await api.get("/api/exports/verified.csv")).text)

    assert rows[1][7:] == ["approve", "Demo verifier", "2026-10-07T07:40:25+00:00"]
    assert rows[2][7:] == ["", "", ""]


async def test_with_no_verified_application_the_export_is_the_header_row_only(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await add_application(connection, "SYN-N-1", "needs_review")
    await as_role(api, connection, "staff")

    response = await api.get("/api/exports/verified.csv")

    assert response.status_code == 200
    assert len(table(response.text)) == 1


async def test_the_file_is_csv_an_attachment_and_not_cached(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_role(api, connection, "staff")

    response = await api.get("/api/exports/verified.csv")

    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="verified-')
    assert response.headers["content-disposition"].endswith('.csv"')
    assert response.headers["cache-control"] == "no-store"


async def test_a_name_that_looks_like_a_formula_is_exported_as_text(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await add_application(
        connection, "SYN-V-1", "verified", name='=HYPERLINK("http://example.test","x")'
    )
    await as_role(api, connection, "staff")

    rows = table((await api.get("/api/exports/verified.csv")).text)

    assert rows[1][1].startswith("'=")


async def test_every_export_writes_one_audit_row_with_who_and_how_many(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_mix(connection)
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")

    await api.get("/api/exports/verified.csv")
    await api.get("/api/exports/verified.csv")

    assert await audit_rows(connection) == [(user_id, 3), (user_id, 3)]


async def test_an_empty_export_is_audited_too(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")

    await api.get("/api/exports/verified.csv")

    assert await audit_rows(connection) == [(user_id, 0)]


async def test_the_audit_row_has_no_column_that_could_hold_applicant_data(
    api: AsyncClient, connection: AsyncConnection, caplog: pytest.LogCaptureFixture
) -> None:
    await add_application(connection, "SYN-V-1", "verified")
    await as_role(api, connection, "staff")
    caplog.set_level(logging.DEBUG)

    await api.get("/api/exports/verified.csv")

    columns = (
        (
            await connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'export_audit' ORDER BY column_name"
                )
            )
        )
        .scalars()
        .all()
    )
    assert columns == ["created_at", "exported_by", "id", "row_count"]
    assert "Latha" not in caplog.text
    assert "SYN-V-1" not in caplog.text


async def test_a_verifier_is_refused_the_export_and_nothing_is_audited(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await add_application(connection, "SYN-V-1", "verified")
    await as_role(api, connection, "verifier")

    response = await api.get("/api/exports/verified.csv")

    assert response.status_code == 403
    assert await audit_rows(connection) == []


async def test_an_anonymous_caller_gets_401_and_nothing_is_audited(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    response = await api.get("/api/exports/verified.csv")

    assert response.status_code == 401
    assert await audit_rows(connection) == []
