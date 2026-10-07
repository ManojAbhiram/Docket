"""Review a flagged application side by side (US-00-006, REQ-021, REQ-022).

Needs `make db` and `make migrate`. Rows are written straight to the tables, as the pipeline would
leave them, so these tests read what a verifier would see without running the engine. Synthetic
data only.
"""

import json
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.helpers import seed_user, sign_in

pytestmark = pytest.mark.integration

MISSING = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(range(40))
JPEG_BYTES = b"\xff\xd8\xff\xe0" + bytes(range(60))


async def make_application(
    connection: AsyncConnection,
    ref: str = "SYN-APP-001",
    *,
    status: str = "needs_review",
    minutes: int = 0,
    erased: bool = False,
    rejected: bool = False,
) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category, status, rejected_at, erased_at, updated_at) "
            "VALUES (:ref, 'Latha Sharma', 'Salim Sharma', '2006-12-10', 'CBSE', 'SYN0945957', "
            "CAST(:marks AS jsonb), 'General', CAST(:status AS application_status), "
            "CASE WHEN :rejected THEN now() END, CASE WHEN :erased THEN now() END, "
            "'2026-10-05T09:00:00Z'::timestamptz + make_interval(mins => :minutes)) RETURNING id"
        ),
        {
            "ref": ref,
            "marks": json.dumps({"English": 59, "Mathematics": 87}),
            "status": status,
            "minutes": minutes,
            "erased": erased,
            "rejected": rejected,
        },
    )
    application_id: UUID = row.scalar_one()
    return application_id


async def make_document(
    connection: AsyncConnection,
    application_id: UUID,
    *,
    doc_type: str = "10th_marksheet",
    is_current: bool = True,
    blob: bytes = PNG_BYTES,
    blob_type: str = "image/png",
    sha: str = "a",
    minute: int = 0,
) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO documents (application_id, uploaded_by, source_content_type, "
            "detected_type, status, is_current, sha256, size_bytes, created_at) "
            "SELECT :app, id, 'image/png', CAST(:dt AS document_type), 'read', :cur, :sha, 10, "
            "'2026-10-05T09:05:00Z'::timestamptz + make_interval(mins => :minute) "
            "FROM users LIMIT 1 RETURNING id"
        ),
        {
            "app": application_id,
            "dt": doc_type,
            "cur": is_current,
            "sha": sha * 64,
            "minute": minute,
        },
    )
    document_id: UUID = row.scalar_one()
    await connection.execute(
        text(
            "INSERT INTO document_blobs (document_id, content_type, content) "
            "VALUES (:id, :ct, :content)"
        ),
        {"id": document_id, "ct": blob_type, "content": blob},
    )
    return document_id


async def make_field(
    connection: AsyncConnection,
    document_id: UUID,
    name: str,
    value: str,
    *,
    subject: str | None = None,
    confidence: float | None = 0.99,
    match: str | None = "match",
    reason: str | None = None,
) -> None:
    await connection.execute(
        text(
            "INSERT INTO extracted_fields (document_id, field_name, subject, value, confidence, "
            "box, match_result, needs_review, review_reason) VALUES (:doc, "
            "CAST(:name AS field_name), :subject, :value, :confidence, "
            "CAST('[220, 60, 120, 22]' AS jsonb), CAST(:match AS match_result), "
            ":review, :reason)"
        ),
        {
            "doc": document_id,
            "name": name,
            "subject": subject,
            "value": value,
            "confidence": confidence,
            "match": match,
            "review": reason is not None,
            "reason": reason,
        },
    )


async def flagged_application(connection: AsyncConnection) -> UUID:
    """One application with a mismatching name, a low-confidence board and a matching mark."""
    application_id = await make_application(connection)
    document_id = await make_document(connection, application_id)
    await make_field(
        connection, document_id, "name", "Meera Nair", match="mismatch", reason="mismatch"
    )
    await make_field(
        connection,
        document_id,
        "board",
        "CBSE",
        confidence=0.9,
        reason="low_confidence",
    )
    await make_field(connection, document_id, "dob", "10/12/2006")
    await make_field(connection, document_id, "marks", "59", subject="english")
    await make_field(
        connection,
        document_id,
        "marks",
        "99",
        subject="Mathematics",
        match="mismatch",
        reason="mismatch",
    )
    await make_field(
        connection, document_id, "document_number", "SYN-ID-1", match="skipped", confidence=0.97
    )
    return application_id


async def as_verifier(api: AsyncClient, connection: AsyncConnection) -> None:
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")


async def test_the_detail_shows_each_document_value_beside_the_application_value(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await flagged_application(connection)

    response = await api.get(f"/api/applications/{application_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Latha Sharma"
    assert body["status"] == "needs_review"
    fields = {(f["field_name"], f["subject"]): f for f in body["documents"][0]["fields"]}
    name = fields[("name", None)]
    assert (name["value"], name["application_value"]) == ("Meera Nair", "Latha Sharma")
    assert fields[("dob", None)]["application_value"] == "2006-12-10"
    assert fields[("board", None)]["application_value"] == "CBSE"
    assert fields[("marks", "english")]["application_value"] == "59"
    assert fields[("marks", "Mathematics")]["application_value"] == "87"
    assert fields[("document_number", None)]["application_value"] is None


async def test_the_fields_that_failed_are_marked_with_the_reason(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await flagged_application(connection)

    body = (await api.get(f"/api/applications/{application_id}")).json()

    fields = {(f["field_name"], f["subject"]): f for f in body["documents"][0]["fields"]}
    assert (fields[("name", None)]["needs_review"], fields[("name", None)]["review_reason"]) == (
        True,
        "mismatch",
    )
    assert fields[("name", None)]["match_result"] == "mismatch"
    assert fields[("board", None)]["review_reason"] == "low_confidence"
    assert fields[("board", None)]["confidence"] == pytest.approx(0.9)
    assert fields[("dob", None)]["needs_review"] is False
    assert fields[("dob", None)]["match_result"] == "match"
    assert fields[("name", None)]["box"] == [220, 60, 120, 22]


async def test_current_documents_come_first_and_the_superseded_one_is_kept_and_marked(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection)
    older = await make_document(connection, application_id, is_current=False, sha="b", minute=1)
    newer = await make_document(connection, application_id, sha="c", minute=5)
    other = await make_document(connection, application_id, doc_type="id_proof", sha="d", minute=3)

    docs = (await api.get(f"/api/applications/{application_id}")).json()["documents"]

    assert [d["id"] for d in docs] == [str(newer), str(other), str(older)]
    assert [d["is_current"] for d in docs] == [True, True, False]
    assert all(d["application_id"] == str(application_id) for d in docs)


async def test_an_application_with_no_documents_has_an_empty_list(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection, status="missing_documents")

    body = (await api.get(f"/api/applications/{application_id}")).json()

    assert body["documents"] == []
    assert body["status"] == "missing_documents"


async def test_a_rejected_application_says_so(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection, rejected=True)

    assert (await api.get(f"/api/applications/{application_id}")).json()["rejected"] is True


async def test_staff_may_read_the_detail_too(api: AsyncClient, connection: AsyncConnection) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")
    application_id = await make_application(connection)

    assert (await api.get(f"/api/applications/{application_id}")).status_code == 200


async def test_an_anonymous_caller_gets_401_from_the_detail_and_the_image(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    application_id = await make_application(connection)

    detail = await api.get(f"/api/applications/{application_id}")
    image = await api.get(f"/api/documents/{MISSING}/image")

    assert (detail.status_code, image.status_code) == (401, 401)


async def test_an_unknown_erased_or_malformed_application_is_404_or_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    erased = await make_application(connection, "SYN-APP-009", erased=True)

    unknown = await api.get(f"/api/applications/{MISSING}")
    gone = await api.get(f"/api/applications/{erased}")
    malformed = await api.get("/api/applications/not-a-uuid")

    assert (unknown.status_code, gone.status_code, malformed.status_code) == (404, 404, 422)


async def test_the_etag_is_the_updated_at_and_changes_when_the_application_changes(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection)

    first = await api.get(f"/api/applications/{application_id}")
    await connection.execute(
        text("UPDATE applications SET updated_at = :at WHERE id = :id"),
        {"id": application_id, "at": datetime(2026, 10, 5, 9, 30, tzinfo=UTC)},
    )
    second = await api.get(f"/api/applications/{application_id}")

    assert first.headers["etag"] == '"2026-10-05T09:00:00+00:00"'
    assert second.headers["etag"] == '"2026-10-05T09:30:00+00:00"'
    assert first.json()["updated_at"].startswith("2026-10-05T09:00:00")


@pytest.mark.parametrize(
    ("blob", "blob_type", "suffix"),
    [(PNG_BYTES, "image/png", "png"), (JPEG_BYTES, "image/jpeg", "jpg")],
)
async def test_the_image_comes_back_byte_for_byte_with_the_fixed_safe_headers(
    api: AsyncClient, connection: AsyncConnection, blob: bytes, blob_type: str, suffix: str
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection)
    document_id = await make_document(connection, application_id, blob=blob, blob_type=blob_type)

    response = await api.get(f"/api/documents/{document_id}/image")

    assert response.status_code == 200
    assert response.content == blob
    assert response.headers["content-type"] == blob_type
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"] == (
        f'inline; filename="document-{document_id}.{suffix}"'
    )


async def test_the_image_never_carries_a_name_the_client_chose(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection)
    document_id = await make_document(connection, application_id)

    response = await api.get(f"/api/documents/{document_id}/image")

    assert "scan" not in response.headers["content-disposition"].replace("document-", "")
    assert str(document_id) in response.headers["content-disposition"]


async def test_staff_may_read_the_image_and_an_unknown_document_is_404(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")
    application_id = await make_application(connection)
    document_id = await make_document(connection, application_id)

    found = await api.get(f"/api/documents/{document_id}/image")
    unknown = await api.get(f"/api/documents/{MISSING}/image")
    malformed = await api.get("/api/documents/not-a-uuid/image")

    assert (found.status_code, unknown.status_code, malformed.status_code) == (200, 404, 422)


async def test_the_image_of_an_erased_application_is_gone(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection, erased=True)
    document_id = await make_document(connection, application_id)

    assert (await api.get(f"/api/documents/{document_id}/image")).status_code == 404


async def test_the_queue_is_exactly_the_flagged_applications_newest_change_first(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    await make_application(connection, "SYN-APP-001", status="verified", minutes=1)
    await make_application(connection, "SYN-APP-002", status="needs_review", minutes=2)
    await make_application(connection, "SYN-APP-003", status="missing_documents", minutes=3)
    await make_application(connection, "SYN-APP-004", status="needs_review", minutes=4)
    await make_application(
        connection, "SYN-APP-005", status="needs_review", minutes=5, rejected=True
    )
    await make_application(connection, "SYN-APP-006", status="needs_review", minutes=6, erased=True)

    queue = (
        await api.get(
            "/api/applications",
            params={"filter[status]": "needs_review", "filter[rejected]": "false"},
        )
    ).json()["data"]

    assert [a["application_ref"] for a in queue] == ["SYN-APP-004", "SYN-APP-002"]


# ISSUE-004 [NOTASK-2]: the queue row used to carry no reason, so the verifier saw an empty cell.
async def test_a_queue_row_says_why_it_is_flagged(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    await flagged_application(connection)

    queue = (
        await api.get(
            "/api/applications",
            params={"filter[status]": "needs_review", "filter[rejected]": "false"},
        )
    ).json()["data"]

    assert queue[0]["flag_reason"] == "Name does not match, and 2 more"


async def test_a_failed_document_is_the_reason_when_it_could_not_be_read(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    application_id = await make_application(connection)
    document_id = await make_document(connection, application_id)
    await connection.execute(
        text("UPDATE documents SET status = 'failed' WHERE id = :id"), {"id": document_id}
    )

    queue = (await api.get("/api/applications", params={"filter[status]": "needs_review"})).json()

    assert queue["data"][0]["flag_reason"] == "A document could not be read"


async def test_an_application_that_is_not_flagged_has_no_reason(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await as_verifier(api, connection)
    await make_application(connection, status="verified")

    data = (await api.get("/api/applications")).json()["data"]

    assert data[0]["flag_reason"] is None
