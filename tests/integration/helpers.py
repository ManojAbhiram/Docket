"""Shared by the API integration tests: a fake clock, seeded users and a signed-in client."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.domain.auth import Passwords

START = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
LOGIN_PHRASE = "synthetic-one-time-phrase"
SAME_ORIGIN = {"Origin": "http://localhost:5173"}


class FakeClock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: int) -> None:
        self.now += timedelta(**delta)


async def seed_user(
    connection: AsyncConnection, username: str, role: str, *, active: bool = True
) -> UUID:
    stored = Passwords(memory_kib=8, time_cost=1, parallelism=1).hash(LOGIN_PHRASE)
    row = await connection.execute(
        text(
            "INSERT INTO users (username, display_name, role, password_hash, is_active) "
            "VALUES (:u, :d, CAST(:r AS user_role), :h, :a) RETURNING id"
        ),
        {"u": username, "d": f"Demo {role}", "r": role, "h": stored, "a": active},
    )
    user_id: UUID = row.scalar_one()
    return user_id


async def sign_in(client: AsyncClient, username: str, password: str = LOGIN_PHRASE) -> Response:
    return await client.post("/api/auth/login", json={"username": username, "password": password})


def csrf_header(client: AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies["docket_csrf"], **SAME_ORIGIN}
