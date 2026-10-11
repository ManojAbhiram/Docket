"""Upload memory admission across body buffering, normalization and persistence."""

import asyncio
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncConnection

from app.api.documents import router as document_routes
from app.api.uploads import UploadedFile, read_one_file
from app.db.repositories.uploads import DocumentRecord, SqlUploadStore
from app.domain.uploads import StoredImage
from tests.integration.api.test_documents import new_application, picture, send, staff, stored_rows

pytestmark = pytest.mark.integration


async def test_an_upload_waits_for_compute_capacity_before_reading_the_body(
    api: AsyncClient,
    api_app: FastAPI,
    connection: AsyncConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    checked = asyncio.Event()
    read = asyncio.Event()
    exists = SqlUploadStore.application_exists
    read_file = read_one_file

    async def observed_exists(store: SqlUploadStore, application_id: UUID) -> bool:
        found = await exists(store, application_id)
        checked.set()
        return found

    async def observed_read(request: Request, *, cap: int, max_fields: int = 1) -> UploadedFile:
        read.set()
        return await read_file(request, cap=cap, max_fields=max_fields)

    monkeypatch.setattr(SqlUploadStore, "application_exists", observed_exists)
    monkeypatch.setattr(document_routes, "read_one_file", observed_read)
    slots: asyncio.Semaphore = api_app.state.hash_slots

    async with slots:
        pending = asyncio.create_task(
            send(api, application_id, picture("png"), content_type="image/png")
        )
        await asyncio.wait_for(checked.wait(), timeout=3)
        buffered_while_busy = read.is_set()

    response = await asyncio.wait_for(pending, timeout=3)
    assert buffered_while_busy is False
    assert response.status_code == 202
    assert read.is_set()


async def test_busy_upload_capacity_times_out_without_reading_the_body(
    api: AsyncClient,
    api_app: FastAPI,
    connection: AsyncConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    api_app.state.settings = api_app.state.settings.model_copy(
        update={"read_timeout_seconds": 0.02}
    )

    async def refused_read(request: Request, *, cap: int, max_fields: int = 1) -> UploadedFile:
        pytest.fail("busy upload buffered its body")

    monkeypatch.setattr(document_routes, "read_one_file", refused_read)
    async with api_app.state.hash_slots:
        response = await send(api, application_id, picture("png"), content_type="image/png")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert await stored_rows(connection) == []


async def test_upload_admission_covers_waiting_for_persistence(
    api: AsyncClient,
    api_app: FastAPI,
    connection: AsyncConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    persisting = asyncio.Event()
    release = asyncio.Event()
    second_checked = asyncio.Event()
    reads = 0
    checks = 0
    original_add = SqlUploadStore.add_document
    original_read = read_one_file
    original_exists = SqlUploadStore.application_exists

    async def observed_exists(store: SqlUploadStore, application_id: UUID) -> bool:
        nonlocal checks
        found = await original_exists(store, application_id)
        checks += 1
        if checks == 2:
            second_checked.set()
        return found

    async def observed_read(request: Request, *, cap: int, max_fields: int = 1) -> UploadedFile:
        nonlocal reads
        reads += 1
        return await original_read(request, cap=cap, max_fields=max_fields)

    async def blocked_add(
        store: SqlUploadStore,
        application_id: UUID,
        uploaded_by: UUID,
        *,
        source_content_type: str,
        sha256: str,
        size_bytes: int,
        stored: StoredImage,
        mode: str = "free",
    ) -> tuple[DocumentRecord, bool]:
        persisting.set()
        await release.wait()
        return await original_add(
            store,
            application_id,
            uploaded_by,
            source_content_type=source_content_type,
            sha256=sha256,
            size_bytes=size_bytes,
            stored=stored,
            mode=mode,
        )

    monkeypatch.setattr(SqlUploadStore, "application_exists", observed_exists)
    monkeypatch.setattr(SqlUploadStore, "add_document", blocked_add)
    monkeypatch.setattr(document_routes, "read_one_file", observed_read)
    first = asyncio.create_task(send(api, application_id, picture("png"), content_type="image/png"))
    second: asyncio.Task[Response] | None = None
    try:
        await asyncio.wait_for(persisting.wait(), timeout=3)
        second = asyncio.create_task(
            send(api, application_id, picture("png", shade=120), content_type="image/png")
        )
        await asyncio.wait_for(second_checked.wait(), timeout=3)
        buffered_while_persisting = reads
    finally:
        release.set()
        first_response = await asyncio.wait_for(first, timeout=3)
        if second is not None:
            second_response = await asyncio.wait_for(second, timeout=3)
    assert buffered_while_persisting == 1
    assert first_response.status_code == second_response.status_code == 202
