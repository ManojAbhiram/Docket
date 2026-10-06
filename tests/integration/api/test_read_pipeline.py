"""An uploaded document is read once, typed, split into fields and logged (US-00-003).

Needs `make db` and `make migrate`. The page goes in through the upload route and comes out through
the real queue, the real call ledger and the gateway. The engine is the recorded one, loaded with
answers saved for the stored page, so the test makes no model call and needs no network.
"""

import asyncio
import hashlib
import json
import socket
from pathlib import Path
from uuid import UUID

import cv2
import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repositories.documents import SqlDocumentStore
from app.db.repositories.gateway_calls import SqlCallLedger
from app.gateway.reader import GatewayReader, build_reader
from app.jobs.worker import process_next
from tests.integration.api.test_documents import new_application, send
from tests.integration.helpers import seed_user, sign_in

pytestmark = pytest.mark.integration

CUTOFF = 0.95


def page(shade: int) -> bytes:
    ok, encoded = cv2.imencode(".png", np.full((64, 64, 3), shade, dtype=np.uint8))
    assert ok
    return bytes(encoded.tobytes())


def word(text_: str, y: float, confidence: float = 0.99, x: float = 10.0) -> dict[str, object]:
    return {"text": text_, "confidence": confidence, "box": [x, y, 10.0 * len(text_), 22.0]}


ID_CARD = [
    word("Identity Card", 0),
    word("Name", 60),
    word("Latha Sharma", 60, x=220.0),
    word("Date of birth", 100),
    word("10/12/2006", 100, confidence=0.5, x=220.0),
    word("ID number", 140),
    word("SYNID12345678", 140, x=220.0),
]
NO_TITLE = [word("Electricity bill", 0)]


async def upload_and_record(
    api: AsyncClient,
    connection: AsyncConnection,
    application_id: UUID,
    shade: int,
    words: list[dict[str, object]],
    recordings: dict[str, object],
) -> UUID:
    response = await send(api, application_id, page(shade), content_type="image/png")
    document_id = UUID(response.json()["id"])
    stored = (
        await connection.execute(
            text("SELECT content FROM document_blobs WHERE document_id = :id"), {"id": document_id}
        )
    ).scalar_one()
    recordings[hashlib.sha256(bytes(stored)).hexdigest()] = {"words": words}
    return document_id


def reader_for(
    settings: Settings,
    recordings: dict[str, object],
    tmp_path: Path,
    factory: async_sessionmaker[AsyncSession],
    *,
    cap: int = 1000,
) -> GatewayReader:
    recording = tmp_path / "recording.json"
    recording.write_text(json.dumps(recordings), encoding="utf-8")
    configured = settings.model_copy(
        update={
            "gateway_engine": "recorded",
            "gateway_recording": recording,
            "gateway_call_cap": cap,
        }
    )
    ledger = SqlCallLedger(
        factory, asyncio.get_running_loop(), engine_version="recorded-1", preprocess=False
    )
    return build_reader(configured, ledger)


async def test_one_document_is_read_with_one_gateway_call_typed_and_split_into_fields(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")
    application_id = await new_application(connection)
    recordings: dict[str, object] = {}
    document_id = await upload_and_record(api, connection, application_id, 90, ID_CARD, recordings)
    reader = reader_for(api_settings, recordings, tmp_path, factory)
    store = SqlDocumentStore(factory)

    def refuse(*_args: object, **_kwargs: object) -> None:
        pytest.fail("reading opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    first = await process_next(store, reader, confidence_cutoff=CUTOFF)
    second = await process_next(store, reader, confidence_cutoff=CUTOFF)

    assert (first, second) == ("read", "idle")
    document = (
        await connection.execute(
            text("SELECT status::text, detected_type::text FROM documents WHERE id = :id"),
            {"id": document_id},
        )
    ).one()
    assert tuple(document) == ("read", "id_proof")
    calls = (
        await connection.execute(
            text("SELECT engine, engine_version, outcome::text, cost FROM gateway_calls")
        )
    ).all()
    assert [tuple(c) for c in calls] == [("recorded", "recorded-1", "ok", 0)]
    fields = (
        await connection.execute(
            text(
                "SELECT field_name::text, value, confidence, needs_review, review_reason "
                "FROM extracted_fields WHERE document_id = :id ORDER BY field_name"
            ),
            {"id": document_id},
        )
    ).all()
    by_name = {f[0]: f for f in fields}
    assert set(by_name) == {"dob", "document_number", "name"}
    assert by_name["name"][1] == "Latha Sharma"
    assert by_name["name"][2] == pytest.approx(0.99, abs=1e-6)
    assert by_name["name"][3] is False
    assert by_name["dob"][3] is True
    assert by_name["dob"][4] == "low_confidence"


async def test_a_page_with_no_known_title_is_recorded_as_unknown_and_not_dropped(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")
    application_id = await new_application(connection)
    recordings: dict[str, object] = {}
    document_id = await upload_and_record(
        api, connection, application_id, 120, NO_TITLE, recordings
    )
    reader = reader_for(api_settings, recordings, tmp_path, factory)

    outcome = await process_next(SqlDocumentStore(factory), reader, confidence_cutoff=CUTOFF)

    assert outcome == "read"
    detected = (
        await connection.execute(
            text("SELECT detected_type::text FROM documents WHERE id = :id"), {"id": document_id}
        )
    ).scalar_one()
    assert detected == "unknown"


async def test_a_document_past_the_call_cap_fails_with_a_reason_and_the_refusal_is_logged(
    api: AsyncClient,
    connection: AsyncConnection,
    factory: async_sessionmaker[AsyncSession],
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(api, "staff.demo")
    application_id = await new_application(connection)
    recordings: dict[str, object] = {}
    await upload_and_record(api, connection, application_id, 60, ID_CARD, recordings)
    second = await upload_and_record(api, connection, application_id, 200, ID_CARD, recordings)
    reader = reader_for(api_settings, recordings, tmp_path, factory, cap=1)
    store = SqlDocumentStore(factory)

    outcomes = [await process_next(store, reader, confidence_cutoff=CUTOFF) for _ in range(2)]

    assert outcomes == ["read", "failed"]
    reason = (
        await connection.execute(
            text("SELECT failure_reason FROM documents WHERE id = :id"), {"id": second}
        )
    ).scalar_one()
    assert reason == "cap_reached"
    logged = (
        (await connection.execute(text("SELECT outcome::text FROM gateway_calls ORDER BY id")))
        .scalars()
        .all()
    )
    assert logged == ["ok", "refused"]
