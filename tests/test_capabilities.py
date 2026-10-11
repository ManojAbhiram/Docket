"""What this server can do for the signed-in person (ADR-0015).

The upload screen asks before it offers Vision, so it never offers a choice the server refuses.
"""

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.auth.deps import current_user
from app.domain.auth import SessionUser


@pytest.fixture
def signed_in(app: FastAPI) -> FastAPI:
    async def staff() -> SessionUser:
        return SessionUser(id=UUID(int=1), display_name="Demo Staff", role="staff")

    app.dependency_overrides[current_user] = staff
    return app


async def test_vision_is_off_until_a_key_and_a_model_are_set(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    response = await client.get("/api/capabilities")

    assert response.status_code == 200
    assert response.json() == {"vision": False}


async def test_vision_is_on_once_a_key_and_a_model_are_set(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    signed_in.state.settings = signed_in.state.settings.model_copy(
        update={"openrouter_api_key": "sk-or-v1-test", "openrouter_model": "vendor/model:free"}
    )

    assert (await client.get("/api/capabilities")).json() == {"vision": True}


async def test_the_answer_never_carries_the_key_or_the_model(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    signed_in.state.settings = signed_in.state.settings.model_copy(
        update={"openrouter_api_key": "sk-or-v1-test", "openrouter_model": "vendor/model:free"}
    )

    body = (await client.get("/api/capabilities")).text

    assert "sk-or" not in body
    assert "vendor" not in body


async def test_a_caller_who_is_not_signed_in_gets_401(client: AsyncClient) -> None:
    assert (await client.get("/api/capabilities")).status_code == 401
