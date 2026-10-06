"""Upload, read, compare, status: the whole path against a real Postgres (US-00-004, US-00-005).

The engine is the recorded one, loaded with the words each stored page should give, so nothing
here runs a model. The application holds Latha Sharma's values; a document either repeats them or
changes one.
"""

from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repositories.documents import SqlDocumentStore
from app.jobs.settle import make_settle
from app.jobs.worker import process_next
from tests.integration.api.test_documents import picture, send
from tests.integration.api.test_read_pipeline import NO_TITLE, reader_for, upload_and_record
from tests.integration.helpers import seed_user, sign_in

pytestmark = pytest.mark.integration

CUTOFF = 0.95
THRESHOLD = 0.85


def word(text_: str, x: float, y: float) -> dict[str, object]:
    return {"text": text_, "confidence": 0.99, "box": [x, y, 10.0 * len(text_), 22.0]}


def labelled(label: str, value: str, y: float) -> list[dict[str, object]]:
    return [word(label, 10, y), word(value, 220, y)]


def marksheet(title: str, **overrides: str) -> list[dict[str, object]]:
    values = {"name": "Latha Sharma", "dob": "10/12/2006", "roll": "SYN0945957"} | overrides
    return [
        word(title, 10, 0),
        *labelled("Name", values["name"], 60),
        *labelled("Father's name", "Salim Sharma", 100),
        *labelled("Date of birth", values["dob"], 140),
        *labelled("Board", "CBSE", 180),
        *labelled("Roll number", values["roll"], 220),
        word("Subject", 10, 270),
        word("Marks", 220, 270),
        *labelled("English", "59", 310),
        *labelled("Mathematics", "87", 350),
    ]


TENTH = "Secondary School Examination, Class X: Statement of Marks"
TWELFTH = "Senior School Certificate Examination, Class XII: Statement of Marks"


def id_card() -> list[dict[str, object]]:
    return [
        word("Identity Card", 10, 0),
        *labelled("Name", "Latha Sharma", 60),
        *labelled("Date of birth", "10/12/2006", 100),
        *labelled("ID number", "SYNID12345678", 140),
    ]


async def application(connection: AsyncConnection) -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category) VALUES ('SYN-APP-001', 'Latha Sharma', "
            "'Salim Sharma', '2006-12-10', 'CBSE', 'SYN0945957', "
            "CAST('{\"English\": 59, \"Mathematics\": 87}' AS jsonb), 'General') RETURNING id"
        )
    )
    application_id: UUID = row.scalar_one()
    return application_id


async def status_of(connection: AsyncConnection, application_id: UUID) -> str:
    found = await connection.execute(
        text("SELECT status::text FROM applications WHERE id = :id"), {"id": application_id}
    )
    value: str = found.scalar_one()
    return value


async def read_all(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    tmp_path: Path,
    words_by_document: list[list[dict[str, object]]],
    application_id: UUID,
    *,
    cap: int = 1000,
) -> None:
    recordings: dict[str, object] = {}
    for shade, words in enumerate(words_by_document, start=1):
        await upload_and_record(api, connection, application_id, shade * 20, words, recordings)
    reader = reader_for(settings, recordings, tmp_path, factory, cap=cap)
    store = SqlDocumentStore(factory)
    settle = make_settle(factory, name_threshold=THRESHOLD)
    for _ in words_by_document:
        await process_next(store, reader, confidence_cutoff=CUTOFF, settle=settle)


async def staff(api: AsyncClient, connection: AsyncConnection) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")


async def test_three_required_documents_that_all_match_make_the_application_verified(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH), marksheet(TWELFTH), id_card()],
        application_id,
    )

    assert await status_of(connection, application_id) == "verified"
    results = (
        (
            await connection.execute(
                text("SELECT DISTINCT match_result::text FROM extracted_fields ORDER BY 1")
            )
        )
        .scalars()
        .all()
    )
    assert results == ["match", "skipped"]


async def test_a_name_that_differs_on_one_document_sends_the_application_to_review(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH), marksheet(TWELFTH, name="Meera Nair"), id_card()],
        application_id,
    )

    assert await status_of(connection, application_id) == "needs_review"
    flagged = (
        await connection.execute(
            text(
                "SELECT field_name::text, review_reason FROM extracted_fields "
                "WHERE match_result = 'mismatch'"
            )
        )
    ).all()
    assert [tuple(f) for f in flagged] == [("name", "mismatch")]


async def test_a_roll_number_off_by_one_digit_is_a_mismatch(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH, roll="SYN0945958"), marksheet(TWELFTH), id_card()],
        application_id,
    )

    assert await status_of(connection, application_id) == "needs_review"


async def test_with_a_required_document_missing_the_status_is_missing_documents(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH), id_card()],
        application_id,
    )

    assert await status_of(connection, application_id) == "missing_documents"


async def test_a_document_of_unknown_type_sends_the_application_to_review(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH), marksheet(TWELFTH), id_card(), NO_TITLE],
        application_id,
    )

    assert await status_of(connection, application_id) == "needs_review"


async def test_a_document_the_gateway_refused_holds_the_application_in_review(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await staff(api, connection)
    application_id = await application(connection)

    await read_all(
        api,
        connection,
        factory,
        api_settings,
        tmp_path,
        [marksheet(TENTH), marksheet(TWELFTH), id_card()],
        application_id,
        cap=2,
    )

    assert await status_of(connection, application_id) == "needs_review"


async def test_an_upload_recomputes_the_status_so_a_stale_verified_cannot_stand(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await application(connection)
    await connection.execute(
        text("UPDATE applications SET status = 'verified' WHERE id = :id"), {"id": application_id}
    )

    response = await send(api, application_id, picture("png"), content_type="image/png")

    assert response.status_code == 202
    assert await status_of(connection, application_id) == "missing_documents"
