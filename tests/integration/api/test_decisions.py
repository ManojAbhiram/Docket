"""A verifier approves, corrects or rejects a flagged application, and the log keeps it (US-00-007).

Needs `make db` and `make migrate`. Each test runs in a transaction that is rolled back, except the
lock test, which holds a row from a real second connection and leaves nothing behind. Applications
are seeded straight into the tables in the state the pipeline leaves them: documents read, fields
compared. Data is synthetic. Decisions (Q-005 a, Q-006 c): a correction edits the extracted value
and re-runs the comparison; an approval makes the application Verified; a rejection keeps
Needs review, sets the rejected flag and takes the application out of the queue.
"""

import asyncio
import os
from datetime import datetime
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.decisions.deps import get_decision_store
from app.api.decisions.etag import etag_for
from app.core.errors import ConflictError
from app.db.repositories.decisions import SqlDecisionStore
from app.db.repositories.statuses import recompute_status
from app.domain.decisions import DecisionRequest
from tests.integration.helpers import SAME_ORIGIN, csrf_header, seed_user, sign_in

pytestmark = pytest.mark.integration

THRESHOLD = 0.85
REQUIRED = ("10th_marksheet", "12th_marksheet", "id_proof")


@pytest.fixture
async def decisions(api_app: FastAPI, factory: async_sessionmaker[AsyncSession]) -> None:
    api_app.dependency_overrides[get_decision_store] = lambda: SqlDecisionStore(
        factory, name_threshold=THRESHOLD
    )


async def new_application(
    connection: AsyncConnection,
    user_id: UUID,
    ref: str = "SYN-DECIDE-001",
    *,
    types: tuple[str, ...] = REQUIRED,
) -> tuple[UUID, dict[str, int]]:
    """A needs_review application whose 12th marksheet carries a wrong name.

    Returns the application and the id of the name field of each document. The evidence is dated a
    minute back so a decision made now is newer than it, as it would be in a live database.
    """
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category, status, updated_at) VALUES (:ref, "
            "'Latha Sharma', 'Salim Sharma', '2006-12-10', 'CBSE', 'SYN0945957', '{}', "
            "'General', 'needs_review', now() - interval '1 minute') RETURNING id"
        ),
        {"ref": ref},
    )
    application_id: UUID = row.scalar_one()
    name_fields: dict[str, int] = {}
    for number, doc_type in enumerate(types):
        document = await connection.execute(
            text(
                "INSERT INTO documents (application_id, uploaded_by, source_content_type, "
                "detected_type, status, sha256, size_bytes, created_at, updated_at) VALUES (:app, "
                ":user, 'image/png', CAST(:type AS document_type), 'read', :sha, 10, "
                "now() - interval '1 minute', now() - interval '1 minute') RETURNING id"
            ),
            {"app": application_id, "user": user_id, "type": doc_type, "sha": str(number) * 64},
        )
        document_id: UUID = document.scalar_one()
        wrong = doc_type == "12th_marksheet"
        for field, value in (
            ("name", "Meera Nair" if wrong else "Latha Sharma"),
            ("dob", "10/12/2006"),
        ):
            flagged = wrong and field == "name"
            inserted = await connection.execute(
                text(
                    "INSERT INTO extracted_fields (document_id, field_name, value, confidence, "
                    "match_result, needs_review, review_reason, created_at, updated_at) VALUES "
                    "(:doc, CAST(:name AS field_name), :value, 0.99, "
                    "CAST(:result AS match_result), :flag, CASE WHEN :flag THEN 'mismatch' END, "
                    "now() - interval '1 minute', now() - interval '1 minute') RETURNING id"
                ),
                {
                    "doc": document_id,
                    "name": field,
                    "value": value,
                    "result": "mismatch" if flagged else "match",
                    "flag": flagged,
                },
            )
            if field == "name":
                name_fields[doc_type] = inserted.scalar_one()
    return application_id, name_fields


async def etag(connection: AsyncConnection, application_id: UUID) -> str:
    stamp = (
        await connection.execute(
            text("SELECT updated_at FROM applications WHERE id = :id"), {"id": application_id}
        )
    ).scalar_one()
    return etag_for(stamp)


async def decide(
    api: AsyncClient,
    connection: AsyncConnection,
    application_id: UUID,
    body: dict[str, object],
    *,
    if_match: str | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    sent = headers if headers is not None else csrf_header(api)
    match = if_match if if_match is not None else await etag(connection, application_id)
    return await api.post(
        f"/api/applications/{application_id}/decisions",
        json=body,
        headers={**sent, "If-Match": match},
    )


async def verifier(api: AsyncClient, connection: AsyncConnection) -> UUID:
    user_id = await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")
    return user_id


async def status_of(connection: AsyncConnection, application_id: UUID) -> tuple[str, bool]:
    row = (
        await connection.execute(
            text("SELECT status::text, rejected_at IS NOT NULL FROM applications WHERE id = :id"),
            {"id": application_id},
        )
    ).one()
    return row[0], row[1]


async def logged(
    connection: AsyncConnection,
) -> list[tuple[str, str | None, str | None, str | None]]:
    rows = await connection.execute(
        text(
            "SELECT action::text, reason, old_value, new_value FROM decisions "
            "ORDER BY created_at, id"
        )
    )
    return [(r[0], r[1], r[2], r[3]) for r in rows.all()]


async def test_approving_a_flagged_application_makes_it_verified_and_logs_who_and_when(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)

    response = await decide(api, connection, application_id, {"action": "approve"})

    assert response.status_code == 201
    body = response.json()
    assert (body["action"], body["application_status"]) == ("approve", "verified")
    assert body["decided_by"] == "Demo verifier"
    assert await status_of(connection, application_id) == ("verified", False)
    row = (await connection.execute(text("SELECT decided_by, created_at FROM decisions"))).one()
    assert row[0] == user_id
    assert isinstance(row[1], datetime)
    assert row[1].tzinfo is not None


async def test_an_approval_cannot_stand_in_for_a_document_that_was_never_uploaded(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(
        connection, user_id, types=("10th_marksheet", "12th_marksheet")
    )

    response = await decide(api, connection, application_id, {"action": "approve"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "verification_not_allowed"
    assert await status_of(connection, application_id) == ("needs_review", False)
    assert await logged(connection) == []


async def test_correcting_a_value_reruns_the_comparison_and_logs_the_old_and_new_value(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    field_id = names["12th_marksheet"]

    response = await decide(
        api,
        connection,
        application_id,
        {"action": "correct", "extracted_field_id": field_id, "new_value": "Latha Sharma"},
    )

    assert response.status_code == 201
    assert response.json()["extracted_field_id"] == field_id
    field = (
        await connection.execute(
            text(
                "SELECT value, match_result::text, needs_review, review_reason "
                "FROM extracted_fields WHERE id = :id"
            ),
            {"id": field_id},
        )
    ).one()
    assert tuple(field) == ("Latha Sharma", "match", False, None)
    assert await logged(connection) == [("correct", None, "Meera Nair", "Latha Sharma")]
    named = (
        await connection.execute(text("SELECT field_name::text, extracted_field_id FROM decisions"))
    ).one()
    assert tuple(named) == ("name", field_id)
    assert response.json()["application_status"] == "verified"
    assert await status_of(connection, application_id) == ("verified", False)


async def test_a_correction_that_still_does_not_match_leaves_the_application_in_review(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)

    response = await decide(
        api,
        connection,
        application_id,
        {
            "action": "correct",
            "extracted_field_id": names["12th_marksheet"],
            "new_value": "Someone Else",
        },
    )

    assert response.status_code == 201
    assert response.json()["application_status"] == "needs_review"
    result = (
        await connection.execute(
            text("SELECT match_result::text, review_reason FROM extracted_fields WHERE id = :id"),
            {"id": names["12th_marksheet"]},
        )
    ).one()
    assert tuple(result) == ("mismatch", "mismatch")


async def test_a_correction_names_a_field_of_this_application_or_it_is_refused(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    _, other_names = await new_application(connection, user_id, "SYN-DECIDE-002")
    body: dict[str, object] = {"action": "correct", "new_value": "Latha Sharma"}

    elsewhere = await decide(
        api,
        connection,
        application_id,
        {**body, "extracted_field_id": other_names["12th_marksheet"]},
    )
    missing = await decide(
        api, connection, application_id, {**body, "extracted_field_id": 987_654_321}
    )

    assert (elsewhere.status_code, missing.status_code) == (404, 404)
    assert await logged(connection) == []


async def test_a_correction_without_the_field_or_a_value_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)

    no_field = await decide(
        api, connection, application_id, {"action": "correct", "new_value": "x"}
    )
    blank = await decide(
        api,
        connection,
        application_id,
        {"action": "correct", "extracted_field_id": names["12th_marksheet"], "new_value": "  "},
    )

    assert (no_field.status_code, blank.status_code) == (422, 422)
    assert await logged(connection) == []


@pytest.mark.parametrize("reason", [None, "", "   "])
async def test_a_rejection_with_no_reason_is_refused_and_writes_nothing(
    api: AsyncClient, connection: AsyncConnection, decisions: None, reason: str | None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    body: dict[str, object] = {"action": "reject"}
    if reason is not None:
        body["reason"] = reason

    response = await decide(api, connection, application_id, body)

    assert response.status_code == 422
    assert await logged(connection) == []
    assert await status_of(connection, application_id) == ("needs_review", False)


async def test_a_rejection_with_a_reason_leaves_the_queue_stays_unverified_and_is_logged(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    queue = {"filter[status]": "needs_review", "filter[rejected]": "false"}
    before = (await api.get("/api/applications", params=queue)).json()["data"]

    response = await decide(
        api,
        connection,
        application_id,
        {"action": "reject", "reason": "Name on the marksheet does not match."},
    )

    assert response.status_code == 201
    assert response.json()["application_status"] == "needs_review"
    assert await status_of(connection, application_id) == ("needs_review", True)
    after = (await api.get("/api/applications", params=queue)).json()["data"]
    rejected = (
        await api.get("/api/applications", params={**queue, "filter[rejected]": "true"})
    ).json()["data"]
    assert [a["application_ref"] for a in before] == ["SYN-DECIDE-001"]
    assert after == []
    assert [a["application_ref"] for a in rejected] == ["SYN-DECIDE-001"]
    assert await logged(connection) == [
        ("reject", "Name on the marksheet does not match.", None, None)
    ]


async def test_a_rejected_application_cannot_be_decided_again(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    await decide(api, connection, application_id, {"action": "reject", "reason": "Wrong person."})

    again = await decide(api, connection, application_id, {"action": "approve"})

    assert again.status_code == 409
    assert await status_of(connection, application_id) == ("needs_review", True)


@pytest.mark.parametrize("state", ["verified", "missing_documents"])
async def test_an_application_that_is_not_in_review_cannot_be_decided(
    api: AsyncClient, connection: AsyncConnection, decisions: None, state: str
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    await connection.execute(
        text("UPDATE applications SET status = CAST(:s AS application_status) WHERE id = :id"),
        {"s": state, "id": application_id},
    )

    response = await decide(api, connection, application_id, {"action": "approve"})

    assert response.status_code == 409
    assert await logged(connection) == []


async def test_a_decision_made_on_a_version_that_has_since_changed_is_refused_and_not_logged(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    seen = await etag(connection, application_id)
    first = await decide(
        api,
        connection,
        application_id,
        {
            "action": "correct",
            "extracted_field_id": names["12th_marksheet"],
            "new_value": "Someone Else",
        },
    )

    stale = await decide(api, connection, application_id, {"action": "approve"}, if_match=seen)

    assert first.status_code == 201
    assert stale.status_code == 409
    assert len(await logged(connection)) == 1
    assert await status_of(connection, application_id) == ("needs_review", False)


@pytest.mark.parametrize("header", ["not-a-version", '"2026-13-45"'])
async def test_an_unreadable_if_match_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection, decisions: None, header: str
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)

    response = await decide(api, connection, application_id, {"action": "approve"}, if_match=header)

    assert response.status_code == 422
    assert await logged(connection) == []


async def test_a_request_without_if_match_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)

    response = await api.post(
        f"/api/applications/{application_id}/decisions",
        json={"action": "approve"},
        headers=csrf_header(api),
    )

    assert response.status_code == 422


async def test_an_unknown_application_is_404(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    await verifier(api, connection)

    response = await api.post(
        "/api/applications/0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b/decisions",
        json={"action": "approve"},
        headers={**csrf_header(api), "If-Match": '"2026-10-06T09:00:00+00:00"'},
    )

    assert response.status_code == 404


async def test_staff_may_not_decide_and_an_anonymous_caller_gets_401(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    staff_id = await seed_user(connection, "staff.demo", "staff")
    application_id, _ = await new_application(connection, staff_id)
    match = await etag(connection, application_id)
    url = f"/api/applications/{application_id}/decisions"
    anonymous = await api.post(
        url, json={"action": "approve"}, headers={**SAME_ORIGIN, "If-Match": match}
    )
    await sign_in(api, "staff.demo")

    refused = await decide(api, connection, application_id, {"action": "approve"})

    assert (anonymous.status_code, refused.status_code) == (401, 403)
    assert await logged(connection) == []


async def test_a_decision_without_the_csrf_token_is_refused(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)

    response = await decide(
        api, connection, application_id, {"action": "approve"}, headers=SAME_ORIGIN
    )

    assert response.status_code == 403
    assert await logged(connection) == []


async def test_either_role_reads_the_log_newest_first_with_who_what_when_and_why(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    await decide(
        api,
        connection,
        application_id,
        {
            "action": "correct",
            "extracted_field_id": names["12th_marksheet"],
            "new_value": "Someone Else",
        },
    )
    await decide(
        api, connection, application_id, {"action": "reject", "reason": "Name does not match."}
    )
    await api.post("/api/auth/logout", headers=csrf_header(api))
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")

    response = await api.get(f"/api/applications/{application_id}/decisions")

    assert response.status_code == 200
    entries = response.json()["data"]
    assert [e["action"] for e in entries] == ["reject", "correct"]
    newest = entries[0]
    assert newest["decided_by"] == "Demo verifier"
    assert newest["reason"] == "Name does not match."
    assert newest["created_at"]
    assert newest["application_id"] == str(application_id)
    assert "old_value" not in newest
    assert "new_value" not in newest


async def test_the_log_pages_newest_first_without_gaps(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    for value in ("One Name", "Two Name", "Three Name"):
        await decide(
            api,
            connection,
            application_id,
            {
                "action": "correct",
                "extracted_field_id": names["12th_marksheet"],
                "new_value": value,
            },
        )

    first = (
        await api.get(f"/api/applications/{application_id}/decisions", params={"limit": 2})
    ).json()
    second = (
        await api.get(
            f"/api/applications/{application_id}/decisions",
            params={"limit": 2, "cursor": first["page"]["next_cursor"]},
        )
    ).json()

    assert [len(first["data"]), len(second["data"])] == [2, 1]
    ids = [d["id"] for d in first["data"] + second["data"]]
    assert len(set(ids)) == 3
    assert first["page"]["has_more"] is True
    assert second["page"]["has_more"] is False


async def test_the_log_of_an_unknown_application_is_404_and_needs_a_session(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    url = "/api/applications/0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b/decisions"
    anonymous = await api.get(url)
    await verifier(api, connection)

    unknown = await api.get(url)

    assert (anonymous.status_code, unknown.status_code) == (401, 404)


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
async def test_the_log_has_no_way_to_edit_or_remove_an_entry(
    api: AsyncClient, connection: AsyncConnection, decisions: None, method: str
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    created = await decide(api, connection, application_id, {"action": "reject", "reason": "No."})
    url = f"/api/applications/{application_id}/decisions/{created.json()['id']}"

    response = await api.request(method, url, headers=csrf_header(api))
    collection = await api.request(
        method, f"/api/applications/{application_id}/decisions", headers=csrf_header(api)
    )

    assert response.status_code in (404, 405)
    assert collection.status_code == 405


async def test_the_database_refuses_to_change_or_delete_a_logged_decision(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, _ = await new_application(connection, user_id)
    await decide(api, connection, application_id, {"action": "reject", "reason": "No."})

    async def refused(statement: str) -> bool:
        nested = await connection.begin_nested()
        try:
            await connection.execute(text(statement))
        except DBAPIError:
            await nested.rollback()
            return True
        await nested.rollback()
        return False

    assert await refused("UPDATE decisions SET action = 'approve'")
    assert await refused("DELETE FROM decisions")


async def test_an_approval_holds_until_new_evidence_arrives_and_then_it_is_stale(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    decisions: None,
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    await decide(api, connection, application_id, {"action": "approve"})

    unchanged = await recompute_status(factory, application_id)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET value = 'Changed Name', match_result = 'mismatch', "
            "needs_review = true, review_reason = 'mismatch', "
            "updated_at = clock_timestamp() + interval '1 second' "
            "WHERE id = :id"
        ),
        {"id": names["10th_marksheet"]},
    )
    after_new_evidence = await recompute_status(factory, application_id)

    assert unchanged == "verified"
    assert after_new_evidence == "needs_review"


async def test_two_decisions_on_one_application_cannot_both_win(
    api: AsyncClient, connection: AsyncConnection, decisions: None
) -> None:
    user_id = await verifier(api, connection)
    application_id, names = await new_application(connection, user_id)
    seen = await etag(connection, application_id)
    correct = {
        "action": "correct",
        "extracted_field_id": names["12th_marksheet"],
        "new_value": "Someone Else",
    }
    first = await decide(api, connection, application_id, correct, if_match=seen)

    second = await decide(api, connection, application_id, {"action": "approve"}, if_match=seen)

    assert (first.status_code, second.status_code) == (201, 409)
    assert [entry[0] for entry in await logged(connection)] == ["correct"]


async def test_a_decision_waits_for_the_row_and_then_sees_the_change_made_while_it_waited() -> None:
    """The lock settles the order: a decision on a version that changes while it waits is stale.

    One real connection changes the application (as another decision would) and keeps its
    transaction open, holding the row. A second decision, made on the version seen before, starts
    and must wait. Once the first commits, the second must read the new version and be refused as
    stale, not go on to a later check. It must be the stale refusal itself: a decision that read the
    old row without the lock would pass the version check and fail further on for another reason.
    Uses real connections and removes what it seeded.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    live = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as setup:
            user_id = await seed_user(setup, "verifier.lock", "verifier")
            application_id, _ = await new_application(
                setup, user_id, "SYN-DECIDE-LOCK", types=("10th_marksheet", "12th_marksheet")
            )
            stamp = (
                await setup.execute(
                    text("SELECT updated_at FROM applications WHERE id = :id"),
                    {"id": application_id},
                )
            ).scalar_one()
        async with live() as holder:
            await holder.execute(
                text("UPDATE applications SET updated_at = clock_timestamp() WHERE id = :id"),
                {"id": application_id},
            )
            waiting = asyncio.create_task(
                SqlDecisionStore(live, name_threshold=THRESHOLD).decide(
                    application_id, user_id, DecisionRequest(action="approve"), etag=stamp
                )
            )
            await asyncio.sleep(0.5)
            assert not waiting.done()
            await holder.commit()
            with pytest.raises(ConflictError) as raised:
                await asyncio.wait_for(waiting, timeout=5)
        assert type(raised.value) is ConflictError
        assert "changed" in raised.value.message
        async with engine.connect() as check:
            count = (await check.execute(text("SELECT count(*) FROM decisions"))).scalar_one()
        assert count == 0
    finally:
        async with engine.begin() as cleanup:
            await cleanup.execute(
                text("DELETE FROM applications WHERE application_ref = 'SYN-DECIDE-LOCK'")
            )
            await cleanup.execute(text("DELETE FROM users WHERE username = 'verifier.lock'"))
        await engine.dispose()
