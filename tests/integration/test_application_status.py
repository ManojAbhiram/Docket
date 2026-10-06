"""An application's status is set from its documents and their compared fields (US-00-005).

Needs `make db` and `make migrate`. Each test runs in a transaction that is rolled back, except the
lock test, which needs two real connections and removes what it wrote. The comparison step is not
involved: tests seed `match_result` and `needs_review` directly, which is the contract the
comparison writes (`docs/design/schema.sql`, extracted_fields). Data is synthetic.
"""

import asyncio
import os
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.repositories.statuses import recompute_status, request_status
from app.domain.status import StatusNotAllowedError, VerificationNotAllowedError

pytestmark = pytest.mark.integration

REQUIRED = ("10th_marksheet", "12th_marksheet", "id_proof")
FIELDS = {
    "10th_marksheet": ("name", "dob", "roll_number"),
    "12th_marksheet": ("name", "dob", "roll_number"),
    "id_proof": ("name", "dob", "document_number"),
}


async def new_user(connection: AsyncConnection) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO users (username, display_name, role, password_hash) "
            "VALUES ('staff.status', 'Demo Staff', 'staff', 'x') RETURNING id"
        )
    )
    user_id: UUID = row.scalar_one()
    return user_id


async def new_application(connection: AsyncConnection, ref: str = "SYN-STATUS-001") -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category) VALUES (:ref, 'A B', 'C D', '2006-01-01', "
            "'CBSE', :roll, '{}', 'General') RETURNING id"
        ),
        {"ref": ref, "roll": f"R-{ref}"},
    )
    application_id: UUID = row.scalar_one()
    return application_id


async def add_document(
    connection: AsyncConnection,
    application_id: UUID,
    user_id: UUID,
    doc_type: str | None,
    *,
    state: str = "read",
    current: bool = True,
    match: str | None = "match",
    weak: bool = False,
    sha: str = "a",
) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO documents (application_id, uploaded_by, source_content_type, "
            "detected_type, status, failure_reason, is_current, sha256, size_bytes) "
            "VALUES (:app, :user, 'image/png', CAST(:type AS document_type), "
            "CAST(:state AS document_status), CASE WHEN :state = 'failed' THEN 'engine_error' END, "
            ":current, :sha, 10) RETURNING id"
        ),
        {
            "app": application_id,
            "user": user_id,
            "type": doc_type,
            "state": state,
            "current": current,
            "sha": sha * 64,
        },
    )
    document_id: UUID = row.scalar_one()
    if state != "read" or doc_type is None:
        return document_id
    for name in FIELDS.get(doc_type, ("name",)):
        flagged = weak and name == "name"
        await connection.execute(
            text(
                "INSERT INTO extracted_fields (document_id, field_name, value, confidence, "
                "match_result, needs_review, review_reason) VALUES (:doc, "
                "CAST(:name AS field_name), 'synthetic', 0.99, CAST(:match AS match_result), "
                ":flag, CASE WHEN :flag THEN 'low_confidence' END)"
            ),
            {"doc": document_id, "name": name, "match": match, "flag": flagged},
        )
    return document_id


async def complete_application(
    connection: AsyncConnection, ref: str = "SYN-STATUS-001"
) -> tuple[UUID, UUID]:
    user_id = await new_user(connection)
    application_id = await new_application(connection, ref)
    for number, doc_type in enumerate(REQUIRED):
        await add_document(connection, application_id, user_id, doc_type, sha=str(number))
    return application_id, user_id


async def stored_status(connection: AsyncConnection, application_id: UUID) -> str:
    row = await connection.execute(
        text("SELECT status::text FROM applications WHERE id = :id"), {"id": application_id}
    )
    status: str = row.scalar_one()
    return status


async def test_all_required_documents_read_and_every_field_matching_is_verified_and_kept(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)

    result = await recompute_status(factory, application_id)

    assert result == "verified"
    assert await stored_status(connection, application_id) == "verified"
    kept = (await connection.execute(text("SELECT count(*) FROM extracted_fields"))).scalar_one()
    assert kept == 9


async def test_a_mismatching_field_gives_needs_review(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET match_result = 'mismatch', needs_review = true, "
            "review_reason = 'mismatch' WHERE id = (SELECT min(id) FROM extracted_fields)"
        )
    )

    assert await recompute_status(factory, application_id) == "needs_review"


async def test_a_low_confidence_field_gives_needs_review_even_when_it_matched(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user_id = await new_user(connection)
    application_id = await new_application(connection)
    await add_document(connection, application_id, user_id, "10th_marksheet", weak=True, sha="1")
    await add_document(connection, application_id, user_id, "12th_marksheet", sha="2")
    await add_document(connection, application_id, user_id, "id_proof", sha="3")

    assert await recompute_status(factory, application_id) == "needs_review"


async def test_a_missing_required_type_gives_missing_documents(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user_id = await new_user(connection)
    application_id = await new_application(connection)
    await add_document(connection, application_id, user_id, "10th_marksheet", sha="1")
    await add_document(connection, application_id, user_id, "id_proof", sha="3")

    assert await recompute_status(factory, application_id) == "missing_documents"


async def test_an_application_with_no_documents_is_missing_documents(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await new_application(connection)

    assert await recompute_status(factory, application_id) == "missing_documents"


async def test_a_direct_request_for_verified_is_refused_without_a_match_or_an_approval(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET match_result = 'mismatch', needs_review = true, "
            "review_reason = 'mismatch' WHERE id = (SELECT min(id) FROM extracted_fields)"
        )
    )

    with pytest.raises(VerificationNotAllowedError):
        await request_status(factory, application_id, "verified", approved=False)

    assert await stored_status(connection, application_id) == "missing_documents"


async def test_a_direct_request_for_verified_is_allowed_with_an_approval(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET match_result = 'mismatch', needs_review = true, "
            "review_reason = 'mismatch' WHERE id = (SELECT min(id) FROM extracted_fields)"
        )
    )

    result = await request_status(factory, application_id, "verified", approved=True)

    assert result == "verified"
    assert await stored_status(connection, application_id) == "verified"


async def test_an_approval_cannot_verify_an_application_that_lacks_a_required_document(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    user_id = await new_user(connection)
    application_id = await new_application(connection)
    await add_document(connection, application_id, user_id, "10th_marksheet", sha="1")

    with pytest.raises(VerificationNotAllowedError):
        await request_status(factory, application_id, "verified", approved=True)


async def test_a_request_for_any_other_status_must_equal_what_the_evidence_gives(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)

    with pytest.raises(StatusNotAllowedError):
        await request_status(factory, application_id, "needs_review", approved=False)
    with pytest.raises(StatusNotAllowedError):
        await request_status(factory, application_id, "pending", approved=False)

    assert await request_status(factory, application_id, "verified", approved=False) == "verified"


@pytest.mark.parametrize("state", ["failed", "uploaded", "processing"])
async def test_a_document_that_failed_or_is_still_waiting_never_lets_the_application_verify(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession], state: str
) -> None:
    application_id, user_id = await complete_application(connection)
    await add_document(connection, application_id, user_id, None, state=state, sha="9")

    result = await recompute_status(factory, application_id)

    assert result == ("needs_review" if state == "failed" else "missing_documents")


async def test_a_document_of_unknown_type_sends_the_application_to_needs_review(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, user_id = await complete_application(connection)
    await add_document(connection, application_id, user_id, "unknown", match="skipped", sha="8")

    assert await recompute_status(factory, application_id) == "needs_review"


async def test_a_field_not_yet_compared_blocks_verified(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET match_result = NULL "
            "WHERE id = (SELECT min(id) FROM extracted_fields)"
        )
    )

    assert await recompute_status(factory, application_id) == "needs_review"


async def test_a_skipped_field_does_not_block_verified(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text(
            "UPDATE extracted_fields SET match_result = 'skipped' "
            "WHERE field_name = 'document_number'"
        )
    )

    assert await recompute_status(factory, application_id) == "verified"


async def test_an_older_superseded_document_with_a_mismatch_does_not_block_the_newer_match(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, user_id = await complete_application(connection)
    await add_document(
        connection,
        application_id,
        user_id,
        "10th_marksheet",
        current=False,
        match="mismatch",
        sha="7",
    )

    assert await recompute_status(factory, application_id) == "verified"


async def test_a_rejected_application_keeps_needs_review_whatever_the_evidence_says(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text("UPDATE applications SET status = 'needs_review', rejected_at = now() WHERE id = :id"),
        {"id": application_id},
    )

    assert await recompute_status(factory, application_id) == "needs_review"
    assert await stored_status(connection, application_id) == "needs_review"


async def test_recomputing_is_idempotent_and_leaves_updated_at_alone_when_nothing_changed(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await recompute_status(factory, application_id)
    await connection.execute(
        text("UPDATE applications SET updated_at = '2026-01-01T00:00:00Z' WHERE id = :id"),
        {"id": application_id},
    )

    again = await recompute_status(factory, application_id)

    assert again == "verified"
    stamp = (
        await connection.execute(
            text("SELECT updated_at FROM applications WHERE id = :id"), {"id": application_id}
        )
    ).scalar_one()
    assert stamp.year == 2026
    assert stamp.month == 1


async def test_a_change_of_status_moves_updated_at_forward(
    connection: AsyncConnection, factory: async_sessionmaker[AsyncSession]
) -> None:
    application_id, _ = await complete_application(connection)
    await connection.execute(
        text("UPDATE applications SET updated_at = '2026-01-01T00:00:00Z' WHERE id = :id"),
        {"id": application_id},
    )

    await recompute_status(factory, application_id)

    stamp = (
        await connection.execute(
            text("SELECT updated_at FROM applications WHERE id = :id"), {"id": application_id}
        )
    ).scalar_one()
    assert stamp.year >= 2026
    assert (stamp.year, stamp.month) != (2026, 1)


async def test_an_unknown_application_is_not_found(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await recompute_status(factory, UUID("0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b"))


async def test_a_recompute_waits_for_the_application_row_and_then_sees_what_was_committed() -> None:
    """The lock settles the two orders: a comparison that commits while a recompute waits is seen.

    One connection holds the application row and has a field still uncompared. A recompute starts
    and must wait. The holder then records the match and commits. Only then may the recompute run,
    and it must read the committed match, so it answers verified, never a stale needs_review.
    Uses two real connections and deletes what it wrote.
    """
    engine = create_async_engine(os.environ["DATABASE_URL"])
    live = async_sessionmaker(engine, expire_on_commit=False)
    application_id: UUID | None = None
    try:
        async with engine.begin() as setup:
            application_id, _ = await complete_application(setup, "SYN-LOCK-001")
            await setup.execute(
                text(
                    "UPDATE extracted_fields SET match_result = NULL "
                    "WHERE id = (SELECT min(id) FROM extracted_fields WHERE document_id IN "
                    "(SELECT id FROM documents WHERE application_id = :id))"
                ),
                {"id": application_id},
            )
        async with engine.connect() as holder:
            transaction = await holder.begin()
            await holder.execute(
                text("SELECT id FROM applications WHERE id = :id FOR UPDATE"),
                {"id": application_id},
            )
            waiting = asyncio.create_task(recompute_status(live, application_id))
            await asyncio.sleep(0.5)
            assert not waiting.done()
            await holder.execute(
                text(
                    "UPDATE extracted_fields SET match_result = 'match' WHERE match_result IS NULL "
                    "AND document_id IN (SELECT id FROM documents WHERE application_id = :id)"
                ),
                {"id": application_id},
            )
            await transaction.commit()
            assert await asyncio.wait_for(waiting, timeout=5) == "verified"
    finally:
        async with engine.begin() as cleanup:
            await cleanup.execute(
                text("DELETE FROM applications WHERE application_ref = 'SYN-LOCK-001'")
            )
            await cleanup.execute(text("DELETE FROM users WHERE username = 'staff.status'"))
        await engine.dispose()
