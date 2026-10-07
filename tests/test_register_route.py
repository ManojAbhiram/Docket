"""Register: the paths that are decided before the database is touched."""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.domain.auth import RegistrationLimiter

GOOD = {
    "username": "asha.k",
    "display_name": "Asha Kumar",
    "password": "a-long-phrase-1",
    "role": "staff",
}


@pytest.mark.parametrize(
    "change",
    [
        {"username": "ab"},
        {"password": "short"},
        {"password": "ASHA.K"},
        {"display_name": "   "},
        {"role": "admin"},
        {"is_active": True},
    ],
)
async def test_a_bad_body_is_refused_with_422(
    client: AsyncClient, change: dict[str, object]
) -> None:
    response = await client.post("/api/auth/register", json={**GOOD, **change})
    assert response.status_code == 422


async def test_a_422_never_echoes_the_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={**GOOD, "password": "tooshort", "username": "x"}
    )
    assert response.status_code == 422
    assert "tooshort" not in response.text


async def test_a_source_over_its_limit_gets_429(app: FastAPI, client: AsyncClient) -> None:
    app.state.register_limiter = RegistrationLimiter(
        max_per_source=0, window=timedelta(hours=1), clock=app.state.clock
    )
    response = await client.post("/api/auth/register", json=GOOD)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert response.json()["error"]["code"] == "too_many_attempts"
