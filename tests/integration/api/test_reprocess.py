"""Reprocess a failed document against a real Postgres (PS-12, NOTASK-30).

Needs `make db` and `make migrate`. A failed document goes back to `uploaded` in one transaction,
with the failure and the old read cleared, and the worker then reads it again like any other.
"""

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repositories.documents import SqlDocumentStore
from app.jobs.worker import process_next
from tests.integration.api.test_documents import new_application, picture, send, staff
from tests.integration.api.test_read_pipeline import ID_CARD, reader_for
from tests.integration.helpers import SAME_ORIGIN, csrf_header, seed_user, sign_in

pytestmark = pytest.mark.integration

UNKNOWN_ID = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b"


async def failed_document(
    connection: AsyncConnection,
    application_id: UUID,
    *,
    sha: str = "b" * 64,
    mode: str = "free",
) -> UUID:
    """A failed document with a stale engine and fallback, plus a stale extracted field."""
    row = await connection.execute(
        text(
            "INSERT INTO documents (application_id, uploaded_by, source_content_type, sha256, "
            "size_bytes, status, failure_reason, requested_mode, read_engine, fallback_reason) "
            "SELECT :app, id, 'image/png', :sha, 48, 'failed', 'timeout', :mode, 'rapidocr', "
            "'vision_timeout' FROM users LIMIT 1 RETURNING id"
        ),
        {"app": application_id, "sha": sha, "mode": mode},
    )
    document_id: UUID = row.scalar_one()
    await connection.execute(
        text(
            "INSERT INTO document_blobs (document_id, content_type, content) "
            "VALUES (:id, 'image/png', :content)"
        ),
        {"id": document_id, "content": picture("png")},
    )
    await connection.execute(
        text(
            "INSERT INTO extracted_fields (document_id, field_name, value, confidence, "
            "needs_review) VALUES (:id, 'name', 'Old Value', 0.99, false)"
        ),
        {"id": document_id},
    )
    return document_id


async def reprocess(
    client: AsyncClient, document_id: UUID | str, *, headers: dict[str, str] | None = None
) -> Response:
    return await client.post(
        f"/api/documents/{document_id}/reprocess",
        headers=headers if headers is not None else csrf_header(client),
    )


async def row_of(connection: AsyncConnection, document_id: UUID) -> tuple[object, ...]:
    result = await connection.execute(
        text(
            "SELECT status::text, failure_reason, read_engine, fallback_reason, "
            "detected_type::text, requested_mode, "
            "(SELECT count(*) FROM extracted_fields WHERE document_id = documents.id) "
            "FROM documents WHERE id = :id"
        ),
        {"id": document_id},
    )
    return tuple(result.one())


async def application_status(connection: AsyncConnection, application_id: UUID) -> str:
    result = await connection.execute(
        text("SELECT status::text FROM applications WHERE id = :id"), {"id": application_id}
    )
    return str(result.scalar_one())


async def test_a_failed_document_goes_back_to_uploaded_with_the_old_outcome_cleared(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id, mode="vision")
    created_before = (
        await connection.execute(
            text("SELECT created_at FROM documents WHERE id = :id"), {"id": document_id}
        )
    ).scalar_one()

    response = await reprocess(api, document_id)

    assert response.status_code == 202
    body = response.json()
    assert (body["id"], body["status"], body["failure_reason"]) == (
        str(document_id),
        "uploaded",
        None,
    )
    assert (body["read_engine"], body["fallback_reason"], body["detected_type"]) == (
        None,
        None,
        None,
    )
    assert await row_of(connection, document_id) == (
        "uploaded",
        None,
        None,
        None,
        None,
        "vision",
        0,
    )
    created_after = (
        await connection.execute(
            text("SELECT created_at FROM documents WHERE id = :id"), {"id": document_id}
        )
    ).scalar_one()
    assert created_after == created_before


async def test_the_application_status_is_recomputed_in_the_same_request(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    await connection.execute(
        text("UPDATE applications SET status = 'needs_review' WHERE id = :id"),
        {"id": application_id},
    )

    response = await reprocess(api, document_id)

    assert response.status_code == 202
    assert await application_status(connection, application_id) == "missing_documents"


async def test_a_rejected_application_stays_needs_review_after_a_reprocess(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    await connection.execute(
        text("UPDATE applications SET status = 'needs_review', rejected_at = now() WHERE id = :id"),
        {"id": application_id},
    )

    response = await reprocess(api, document_id)

    assert response.status_code == 202
    assert await application_status(connection, application_id) == "needs_review"


@pytest.mark.parametrize("state", ["uploaded", "processing", "read"])
async def test_a_document_that_is_not_failed_is_refused_with_409_and_left_alone(
    api: AsyncClient, connection: AsyncConnection, state: str
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    await connection.execute(
        text(
            "UPDATE documents SET status = CAST(:s AS document_status), failure_reason = NULL "
            "WHERE id = :id"
        ),
        {"s": state, "id": document_id},
    )
    before = await row_of(connection, document_id)

    response = await reprocess(api, document_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_failed"
    assert await row_of(connection, document_id) == before


async def test_a_second_call_after_the_first_gets_409_and_queues_nothing_more(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    # The row lock makes truly simultaneous calls end the same way; the shared test connection
    # cannot run two requests at once, so this pins the outcome the lock produces.
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)

    first = await reprocess(api, document_id)
    second = await reprocess(api, document_id)

    assert (first.status_code, second.status_code) == (202, 409)
    assert second.json()["error"]["code"] == "document_not_failed"


async def test_a_reprocessed_document_is_read_again_with_a_new_gateway_call(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    stored = (
        await connection.execute(
            text("SELECT content FROM document_blobs WHERE document_id = :id"), {"id": document_id}
        )
    ).scalar_one()
    recordings: dict[str, object] = {hashlib.sha256(bytes(stored)).hexdigest(): {"words": ID_CARD}}
    reader = reader_for(api_settings, recordings, tmp_path, factory)
    await reprocess(api, document_id)

    outcome = await process_next(SqlDocumentStore(factory), reader, confidence_cutoff=0.95)

    assert outcome == "read"
    assert (await row_of(connection, document_id))[0] == "read"
    calls = (await connection.execute(text("SELECT count(*) FROM gateway_calls"))).scalar_one()
    assert calls == 1


async def test_a_document_that_failed_on_the_call_cap_reads_after_the_cap_is_raised(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    await connection.execute(
        text("UPDATE documents SET failure_reason = 'cap_reached' WHERE id = :id"),
        {"id": document_id},
    )
    stored = (
        await connection.execute(
            text("SELECT content FROM document_blobs WHERE document_id = :id"), {"id": document_id}
        )
    ).scalar_one()
    recordings: dict[str, object] = {hashlib.sha256(bytes(stored)).hexdigest(): {"words": ID_CARD}}
    store = SqlDocumentStore(factory)
    await reprocess(api, document_id)
    capped = reader_for(api_settings, recordings, tmp_path, factory, cap=0)
    first = await process_next(store, capped, confidence_cutoff=0.95)
    await reprocess(api, document_id)
    raised = reader_for(api_settings, recordings, tmp_path, factory, cap=1000)

    second = await process_next(store, raised, confidence_cutoff=0.95)

    assert (first, second) == ("failed", "read")


async def test_a_verifier_gets_403_and_an_anonymous_caller_gets_401(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    application_id = await new_application(connection)
    await seed_user(connection, "staff.demo", "staff")
    document_id = await failed_document(connection, application_id)
    anonymous = await reprocess(api, document_id, headers=SAME_ORIGIN)
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")

    refused = await reprocess(api, document_id)

    assert (anonymous.status_code, refused.status_code) == (401, 403)
    assert (await row_of(connection, document_id))[0] == "failed"


async def test_a_call_without_the_csrf_token_or_from_a_foreign_origin_is_refused(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    token = csrf_header(api)["X-CSRF-Token"]

    no_token = await reprocess(api, document_id, headers=SAME_ORIGIN)
    foreign = await reprocess(
        api, document_id, headers={"X-CSRF-Token": token, "Origin": "https://evil.example"}
    )

    assert (no_token.status_code, foreign.status_code) == (403, 403)
    assert (await row_of(connection, document_id))[0] == "failed"


async def test_an_unknown_document_or_an_erased_application_is_404_and_a_bad_id_is_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    document_id = await failed_document(connection, application_id)
    await connection.execute(
        text("UPDATE applications SET erased_at = now() WHERE id = :id"), {"id": application_id}
    )

    unknown = await reprocess(api, UNKNOWN_ID)
    erased = await reprocess(api, document_id)
    malformed = await reprocess(api, "not-a-uuid")

    assert (unknown.status_code, erased.status_code, malformed.status_code) == (404, 404, 422)
    assert (await row_of(connection, document_id))[0] == "failed"


async def test_the_same_bytes_uploaded_again_still_return_the_failed_document(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    png = picture("png")
    first = await send(api, application_id, png, content_type="image/png")
    await connection.execute(
        text("UPDATE documents SET status = 'failed', failure_reason = 'timeout' WHERE id = :id"),
        {"id": first.json()["id"]},
    )

    again = await send(api, application_id, png, content_type="image/png")

    assert again.status_code == 200
    assert (again.json()["id"], again.json()["status"]) == (first.json()["id"], "failed")
