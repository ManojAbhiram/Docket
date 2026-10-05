"""The document queue and the decision log against a real Postgres (ADR-0011, US-00-007).

Needs `make db` and `make migrate` (migration 0002, the copy of docs/design/schema.sql). Each test
runs in a transaction that is rolled back.
"""

from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.db.repositories.documents import SqlDocumentStore
from app.domain.extract import ExtractedField
from app.jobs.worker import ProcessedDocument

pytestmark = pytest.mark.integration

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 40
SHA = "a" * 64


async def seed_user(connection: AsyncConnection) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO users (username, display_name, role, password_hash) "
            "VALUES ('verifier.one', 'Verifier One', 'verifier', 'hash') RETURNING id"
        )
    )
    return UUID(str(row.scalar_one()))


async def seed_application(connection: AsyncConnection, ref: str = "SYN-APP-001") -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category) VALUES (:ref, 'Latha Sharma', 'Salim Sharma', "
            "'2006-12-10', 'CBSE', 'SYN0945957', '{\"English\": 59}', 'General') RETURNING id"
        ),
        {"ref": ref},
    )
    return UUID(str(row.scalar_one()))


async def seed_document(
    connection: AsyncConnection, user: UUID, application: UUID, created_at: str = "2026-10-05"
) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO documents (application_id, uploaded_by, source_content_type, sha256, "
            "size_bytes, created_at) VALUES (:app, :user, 'image/png', :sha, 48, :created) "
            "RETURNING id"
        ),
        {"app": application, "user": user, "sha": SHA, "created": created_at},
    )
    document = UUID(str(row.scalar_one()))
    await connection.execute(
        text(
            "INSERT INTO document_blobs (document_id, content_type, content) "
            "VALUES (:id, 'image/png', :content)"
        ),
        {"id": document, "content": PNG},
    )
    return document


def processed(doc_type: str = "id_proof") -> ProcessedDocument:
    field = ExtractedField("name", None, "Latha Sharma", 0.99, (1.0, 2.0, 3.0, 4.0), False, None)
    return ProcessedDocument(doc_type=doc_type, fields=(field,))


async def status_of(connection: AsyncConnection, document: UUID) -> str:
    row = await connection.execute(
        text("SELECT status::text FROM documents WHERE id = :id"), {"id": document}
    )
    return str(row.scalar_one())


async def test_a_claim_takes_the_oldest_uploaded_document_and_its_image(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)
    older = await seed_document(connection, user, application, "2026-10-04")
    await seed_document(connection, user, application, "2026-10-05")

    claimed = await SqlDocumentStore(factory).claim_next()

    assert claimed is not None
    assert (claimed.id, claimed.image) == (older, PNG)
    assert await status_of(connection, older) == "processing"


async def test_an_empty_queue_claims_nothing(factory: async_sessionmaker[AsyncSession]) -> None:
    assert await SqlDocumentStore(factory).claim_next() is None


async def test_a_completed_read_sets_the_type_and_stores_the_fields(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)
    document = await seed_document(connection, user, application)
    store = SqlDocumentStore(factory)
    await store.claim_next()

    assert await store.complete(document, processed()) is True

    row = await connection.execute(
        text("SELECT status::text, detected_type::text, is_current FROM documents WHERE id = :id"),
        {"id": document},
    )
    assert row.one() == ("read", "id_proof", True)
    fields = await connection.execute(
        text("SELECT field_name::text, value FROM extracted_fields WHERE document_id = :id"),
        {"id": document},
    )
    assert [tuple(r) for r in fields.all()] == [("name", "Latha Sharma")]


async def test_a_newer_upload_of_the_same_type_becomes_current_and_the_older_is_kept(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)
    first = await seed_document(connection, user, application, "2026-10-04")
    second = await seed_document(connection, user, application, "2026-10-05")
    store = SqlDocumentStore(factory)
    await store.claim_next()
    await store.complete(first, processed())
    await store.claim_next()
    await store.complete(second, processed())

    rows = await connection.execute(
        text(
            "SELECT id, is_current FROM documents WHERE application_id = :app ORDER BY created_at"
        ),
        {"app": application},
    )
    assert [tuple(r) for r in rows.all()] == [(first, False), (second, True)]


async def test_a_late_result_after_the_sweeper_gave_up_changes_nothing(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)
    document = await seed_document(connection, user, application)
    store = SqlDocumentStore(factory)
    await store.claim_next()
    await connection.execute(
        text("UPDATE documents SET updated_at = now() - interval '10 minutes' WHERE id = :id"),
        {"id": document},
    )

    assert await store.sweep_stale(300) == 1
    assert await store.complete(document, processed()) is False

    assert await status_of(connection, document) == "failed"


async def test_a_failed_read_records_its_reason_code(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)
    document = await seed_document(connection, user, application)
    store = SqlDocumentStore(factory)
    await store.claim_next()

    assert await store.fail(document, "timeout") is True

    row = await connection.execute(
        text("SELECT failure_reason FROM documents WHERE id = :id"), {"id": document}
    )
    assert row.scalar_one() == "timeout"


# The decision log is append-only in the database, not only in the application.


async def seed_decision(connection: AsyncConnection) -> UUID:
    user, application = await seed_user(connection), await seed_application(connection)
    row = await connection.execute(
        text(
            "INSERT INTO decisions (application_id, decided_by, action, reason) "
            "VALUES (:app, :user, 'reject', 'Name does not match.') RETURNING id"
        ),
        {"app": application, "user": user},
    )
    return UUID(str(row.scalar_one()))


async def test_a_decision_cannot_be_deleted(connection: AsyncConnection) -> None:
    decision = await seed_decision(connection)

    with pytest.raises(DBAPIError, match="cannot be deleted"):
        await connection.execute(text("DELETE FROM decisions WHERE id = :id"), {"id": decision})


async def test_a_decision_cannot_be_rewritten(connection: AsyncConnection) -> None:
    decision = await seed_decision(connection)

    with pytest.raises(DBAPIError, match="erased marker"):
        await connection.execute(
            text("UPDATE decisions SET reason = 'Changed my mind.' WHERE id = :id"),
            {"id": decision},
        )


async def test_a_decision_cannot_be_truncated(connection: AsyncConnection) -> None:
    await seed_decision(connection)

    with pytest.raises(DBAPIError, match="cannot be truncated"):
        await connection.execute(text("TRUNCATE decisions"))


async def test_a_decision_text_may_be_replaced_only_by_the_erased_marker(
    connection: AsyncConnection,
) -> None:
    decision = await seed_decision(connection)

    await connection.execute(
        text("UPDATE decisions SET reason = '[erased]' WHERE id = :id"), {"id": decision}
    )

    row = await connection.execute(
        text("SELECT reason FROM decisions WHERE id = :id"), {"id": decision}
    )
    assert row.scalar_one() == "[erased]"


async def test_a_rejection_without_a_reason_is_refused_by_the_database(
    connection: AsyncConnection,
) -> None:
    user, application = await seed_user(connection), await seed_application(connection)

    with pytest.raises(DBAPIError, match="chk_decisions_reject_needs_reason"):
        await connection.execute(
            text(
                "INSERT INTO decisions (application_id, decided_by, action) "
                "VALUES (:app, :user, 'reject')"
            ),
            {"app": application, "user": user},
        )
