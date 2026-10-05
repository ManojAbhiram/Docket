"""Readiness answers within a bound and leaks nothing (`bearing:health-checks`).

A dependency that hangs must not hang the probe. Tests that need the timeout setting fail until
`readiness_timeout_seconds` exists and `/readyz` enforces it.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Coroutine

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health.router import get_readiness_check
from app.core.config import Settings
from app.main import create_app


async def serve(
    settings: Settings, check: Callable[[], Coroutine[None, None, None]]
) -> AsyncIterator[AsyncClient]:
    application: FastAPI = create_app(settings)
    application.dependency_overrides[get_readiness_check] = lambda: check
    async with LifespanManager(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_a_readiness_check_that_hangs_answers_503_within_the_timeout(
    settings: Settings,
) -> None:
    async def hang() -> None:
        await asyncio.sleep(3600)

    quick = settings.model_copy(update={"readiness_timeout_seconds": 0.05})
    started = time.perf_counter()

    async for client in serve(quick, hang):
        response = await client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert time.perf_counter() - started < 2.0


async def test_a_failing_check_does_not_leak_the_driver_message(
    settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    async def refuse() -> None:
        msg = "password=hunter2 host=db.internal"
        raise OSError(msg)

    async for client in serve(settings, refuse):
        response = await client.get("/readyz")

    assert response.status_code == 503
    assert "hunter2" not in response.text
    assert "hunter2" not in capsys.readouterr().out


async def test_liveness_does_not_depend_on_any_dependency(settings: Settings) -> None:
    async def refuse() -> None:
        raise OSError

    async for client in serve(settings, refuse):
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
