"""Every failure comes back in the one envelope."""

from typing import Annotated

from fastapi import FastAPI, Query
from httpx import AsyncClient
from structlog.testing import capture_logs

from app.core.errors import NotFoundError


async def test_domain_error_is_mapped(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise NotFoundError("invoice 7", details={"id": 7})

    response = await client.get("/boom")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "invoice 7",
        "details": {"id": 7},
        "request_id": response.headers["x-request-id"],
    }


async def test_validation_error_is_422_in_envelope(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/items")
    async def items(limit: Annotated[int, Query(le=100)]) -> dict[str, int]:
        return {"limit": limit}

    response = await client.get("/items", params={"limit": "500"})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"]["errors"][0]["loc"] == ["query", "limit"]


async def test_unknown_route_uses_envelope(client: AsyncClient) -> None:
    response = await client.get("/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


async def test_unhandled_error_is_500_without_detail(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/crash")
    async def crash() -> dict[str, str]:
        raise RuntimeError("secret internals")

    response = await client.get("/crash")

    assert response.status_code == 500
    assert "secret internals" not in response.text
    assert response.json()["error"] == {
        "code": "internal",
        "message": "internal error",
        "details": {},
        "request_id": response.headers["x-request-id"],
    }


async def test_unhandled_error_log_keeps_the_class_but_not_the_message(
    app: FastAPI, client: AsyncClient
) -> None:
    """A database error message can carry a key value; applicants are minors."""

    @app.get("/leak")
    async def leak() -> dict[str, str]:
        raise ValueError("Key (application_ref)=(APP-7) already exists")

    with capture_logs() as logs:
        await client.get("/leak")

    entries = [entry for entry in logs if entry["event"] == "unhandled error"]
    assert len(entries) == 1
    assert entries[0]["error_type"] == "ValueError"
    assert "APP-7" not in str(logs)
