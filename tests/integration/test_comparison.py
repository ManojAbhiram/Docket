"""Comparing a read document with its application against a real Postgres (US-00-004).

Needs `make db` and `make migrate`. Each test runs in a transaction that is rolled back. The
contract with the status step: this writes `match_result`, and flags a mismatch with the review
reason `mismatch` unless the field already carries another reason.
"""

from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.db.repositories.comparison import compare_document

pytestmark = pytest.mark.integration

THRESHOLD = 0.85


async def new_application(connection: AsyncConnection, ref: str = "SYN-APP-001") -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category) VALUES (:ref, 'Latha Sharma', 'Salim Sharma', "
            "'2006-12-10', 'Karnataka State Board', 'SYN0945957', "
            "CAST('{\"English\": 59, \"Hindi\": 77}' AS jsonb), 'General') RETURNING id"
        ),
        {"ref": ref},
    )
    application_id: UUID = row.scalar_one()
    return application_id


async def new_document(
    connection: AsyncConnection,
    application_id: UUID,
    *,
    doc_type: str = "10th_marksheet",
    status: str = "read",
    sha: str = "a" * 64,
) -> UUID:
    await connection.execute(
        text(
            "INSERT INTO users (username, display_name, role, password_hash) "
            "VALUES (:u, 'Demo', 'staff', 'x') ON CONFLICT DO NOTHING"
        ),
        {"u": f"staff-{sha[:6]}"},
    )
    row = await connection.execute(
        text(
            "INSERT INTO documents (application_id, uploaded_by, source_content_type, "
            "detected_type, status, sha256, size_bytes) SELECT :app, id, 'image/png', "
            "CAST(:doc_type AS document_type), CAST(:status AS document_status), :sha, 10 "
            "FROM users ORDER BY created_at LIMIT 1 RETURNING id"
        ),
        {"app": application_id, "doc_type": doc_type, "status": status, "sha": sha},
    )
    document_id: UUID = row.scalar_one()
    return document_id


async def add_field(
    connection: AsyncConnection,
    document_id: UUID,
    name: str,
    value: str,
    *,
    subject: str | None = None,
    reason: str | None = None,
) -> None:
    await connection.execute(
        text(
            "INSERT INTO extracted_fields (document_id, field_name, subject, value, confidence, "
            "needs_review, review_reason) VALUES (:d, CAST(:n AS field_name), :s, :v, 0.99, "
            ":flag, :reason)"
        ),
        {
            "d": document_id,
            "n": name,
            "s": subject,
            "v": value,
            "flag": reason is not None,
            "reason": reason,
        },
    )


async def results(
    connection: AsyncConnection, document_id: UUID
) -> dict[str, tuple[str | None, bool, str | None]]:
    rows = await connection.execute(
        text(
            "SELECT field_name::text || coalesce(':' || subject, ''), match_result::text, "
            "needs_review, review_reason FROM extracted_fields WHERE document_id = :d"
        ),
        {"d": document_id},
    )
    return {r[0]: (r[1], r[2], r[3]) for r in rows.all()}


async def test_each_field_gets_match_mismatch_or_skipped_and_a_mismatch_is_flagged(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id)
    await add_field(connection, document_id, "name", "Sharma Latha")
    await add_field(connection, document_id, "dob", "11/12/2006")
    await add_field(connection, document_id, "marks", "59", subject="English")
    await add_field(connection, document_id, "marks", "78", subject="Hindi")

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert await results(connection, document_id) == {
        "name": ("match", False, None),
        "dob": ("mismatch", True, "mismatch"),
        "marks:English": ("match", False, None),
        "marks:Hindi": ("mismatch", True, "mismatch"),
    }


async def test_a_field_the_type_does_not_carry_is_skipped_and_not_flagged(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id, doc_type="id_proof")
    await add_field(connection, document_id, "name", "Latha Sharma")
    await add_field(connection, document_id, "document_number", "SYNID12345678")
    await add_field(connection, document_id, "roll_number", "WRONG")

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert await results(connection, document_id) == {
        "name": ("match", False, None),
        "document_number": ("skipped", False, None),
        "roll_number": ("skipped", False, None),
    }


async def test_a_mismatch_keeps_the_review_reason_the_field_already_had(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id)
    await add_field(connection, document_id, "dob", "11/12/2006", reason="low_confidence")

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert await results(connection, document_id) == {"dob": ("mismatch", True, "low_confidence")}


async def test_comparing_twice_gives_the_same_rows(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id)
    await add_field(connection, document_id, "name", "Ravi Menon")
    await compare_document(factory, document_id, name_threshold=THRESHOLD)
    first = await results(connection, document_id)

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert (
        await results(connection, document_id) == first == {"name": ("mismatch", True, "mismatch")}
    )


async def test_a_corrected_value_clears_a_mismatch_flag_it_set_before(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id)
    await add_field(connection, document_id, "name", "Ravi Menon")
    await compare_document(factory, document_id, name_threshold=THRESHOLD)
    await connection.execute(
        text("UPDATE extracted_fields SET value = 'Latha Sharma' WHERE document_id = :d"),
        {"d": document_id},
    )

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert await results(connection, document_id) == {"name": ("match", False, None)}


async def test_a_document_that_is_not_read_is_left_alone(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    document_id = await new_document(connection, application_id, status="processing")
    await add_field(connection, document_id, "name", "Ravi Menon")

    await compare_document(factory, document_id, name_threshold=THRESHOLD)

    assert await results(connection, document_id) == {"name": (None, False, None)}


async def test_another_documents_rows_are_never_touched(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)
    first = await new_document(connection, application_id, sha="a" * 64)
    other = await new_document(connection, application_id, doc_type="12th_marksheet", sha="b" * 64)
    await add_field(connection, first, "name", "Ravi Menon")
    await add_field(connection, other, "name", "Ravi Menon")

    await compare_document(factory, first, name_threshold=THRESHOLD)

    assert await results(connection, other) == {"name": (None, False, None)}


async def test_an_unknown_document_id_changes_nothing_and_does_not_raise(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    await compare_document(
        factory, UUID("0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b"), name_threshold=THRESHOLD
    )
