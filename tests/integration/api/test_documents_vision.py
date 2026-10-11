"""Choosing how a page is read when it is uploaded (ADR-0015).

`free` is the default and reads on this machine. `vision` is opt-in, needs a configured key and
model, and is only a request: the worker decides what actually read it.
"""

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.api.test_documents import new_application, picture, staff
from tests.integration.helpers import csrf_header

pytestmark = pytest.mark.integration


async def send_with_mode(
    client: AsyncClient, application_id: UUID, data: bytes, mode: str | None
) -> Response:
    return await client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": ("scan", data, "image/png")},
        data={} if mode is None else {"mode": mode},
        headers=csrf_header(client),
    )


def switch_vision_on(api_app: FastAPI) -> None:
    api_app.state.settings = api_app.state.settings.model_copy(
        update={"openrouter_api_key": "sk-or-v1-test", "openrouter_model": "vendor/model:free"}
    )


async def requested_modes(connection: AsyncConnection) -> list[str]:
    rows = await connection.execute(
        text("SELECT requested_mode FROM documents ORDER BY created_at")
    )
    return [str(row[0]) for row in rows.all()]


async def test_an_upload_without_a_mode_is_free(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send_with_mode(api, application_id, picture("png"), None)

    assert response.status_code == 202
    assert response.json()["requested_mode"] == "free"
    assert await requested_modes(connection) == ["free"]


async def test_a_vision_upload_is_refused_while_vision_is_not_configured(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send_with_mode(api, application_id, picture("png"), "vision")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vision_unavailable"
    assert await requested_modes(connection) == []


async def test_a_vision_upload_is_queued_with_its_mode_once_vision_is_configured(
    api: AsyncClient, api_app: FastAPI, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    switch_vision_on(api_app)
    application_id = await new_application(connection)

    response = await send_with_mode(api, application_id, picture("png"), "vision")

    assert response.status_code == 202
    assert response.json()["requested_mode"] == "vision"
    assert response.json()["read_engine"] is None
    assert await requested_modes(connection) == ["vision"]


@pytest.mark.parametrize("mode", ["gpt", "", "FREE "])
async def test_an_unknown_mode_is_a_validation_error_and_stores_nothing(
    api: AsyncClient, connection: AsyncConnection, mode: str
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send_with_mode(api, application_id, picture("png"), mode)

    assert response.status_code == 422
    assert await requested_modes(connection) == []


async def test_the_same_bytes_sent_again_in_another_mode_keep_the_first_documents_mode(
    api: AsyncClient, api_app: FastAPI, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    switch_vision_on(api_app)
    application_id = await new_application(connection)
    png = picture("png")
    first = await send_with_mode(api, application_id, png, "free")

    again = await send_with_mode(api, application_id, png, "vision")

    assert (first.status_code, again.status_code) == (202, 200)
    assert again.json()["requested_mode"] == "free"
    assert await requested_modes(connection) == ["free"]
