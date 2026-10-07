"""Sign-in, sessions, CSRF and the role gate against a real Postgres (US-00-011, ADR-0006).

Needs `make db` and `make migrate`. Each test runs in a transaction that is rolled back, and the
app reads its time from `app.state.clock`, so expiry is tested without waiting. The role gate is
exercised through a test-only router, because the import, upload, decision and export routes do not
exist yet; each gate test carries the matrix id it covers (docs/security/permission-matrix.md).
"""

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.api.auth.deps import get_auth_store, require_role, verify_csrf
from app.core.config import Settings
from app.db.repositories.auth import SqlAuthStore
from app.main import create_app
from tests.integration.helpers import (
    SAME_ORIGIN,
    START,
    FakeClock,
    csrf_header,
    seed_user,
    sign_in,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def app(
    clock: FakeClock, factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    settings = Settings(
        _env_file=None,
        env="test",
        log_format="console",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5433/docket",
        session_cookie_secure=False,
        argon2_memory_kib=8,
        argon2_time_cost=1,
    )
    application = create_app(settings)
    gate = APIRouter(prefix="/_gate")

    @gate.get("/staff", dependencies=[Depends(require_role("staff"))])
    async def staff_only() -> dict[str, str]:
        return {"ok": "staff"}

    @gate.get("/verifier", dependencies=[Depends(require_role("verifier"))])
    async def verifier_only() -> dict[str, str]:
        return {"ok": "verifier"}

    @gate.get("/any", dependencies=[Depends(require_role("staff", "verifier"))])
    async def either() -> dict[str, str]:
        return {"ok": "either"}

    @gate.post("/change", dependencies=[Depends(require_role("staff")), Depends(verify_csrf)])
    async def change() -> dict[str, str]:
        return {"ok": "changed"}

    application.include_router(gate)
    application.dependency_overrides[get_auth_store] = lambda: SqlAuthStore(factory)
    async with LifespanManager(application):
        application.state.clock = clock
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_a_login_returns_the_user_and_sets_a_session_cookie_that_script_cannot_read(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")

    response = await sign_in(client, "staff.demo")

    assert response.status_code == 200
    assert set(response.json()) == {"id", "display_name", "role"}
    assert response.json()["role"] == "staff"
    cookies = response.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("docket_session="))
    assert "HttpOnly" in session
    assert "samesite=lax" in session.lower()
    assert "Path=/" in session
    csrf = next(c for c in cookies if c.startswith("docket_csrf="))
    assert "HttpOnly" not in csrf


async def test_the_response_never_carries_a_password_hash(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")

    response = await sign_in(client, "staff.demo")

    assert "argon2" not in response.text
    assert "password" not in response.text.lower()


async def test_an_unknown_user_and_a_wrong_password_get_the_same_answer(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")

    unknown = await sign_in(client, "nobody.here")
    wrong = await sign_in(client, "staff.demo", "not the password")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["error"]["code"] == wrong.json()["error"]["code"] == "unauthorized"
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]


async def test_a_deactivated_user_cannot_sign_in(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "gone.demo", "staff", active=False)

    assert (await sign_in(client, "gone.demo")).status_code == 401


async def test_a_login_with_a_missing_or_oversized_field_is_refused_before_any_hashing(
    client: AsyncClient,
) -> None:
    missing = await client.post("/api/auth/login", json={"username": "staff.demo"})
    huge = await sign_in(client, "staff.demo", "x" * 300)

    assert missing.status_code == huge.status_code == 422


async def test_me_returns_the_signed_in_user_and_refuses_an_anonymous_caller(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "verifier.demo", "verifier")
    assert (await client.get("/api/auth/me")).status_code == 401

    await sign_in(client, "verifier.demo")
    me = await client.get("/api/auth/me")

    assert me.status_code == 200
    assert me.json()["role"] == "verifier"


async def test_the_database_keeps_only_a_hash_of_the_session_token(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")
    token = client.cookies["docket_session"]

    stored = (await connection.execute(text("SELECT token_hash FROM sessions"))).scalar_one()

    assert bytes(stored) != token.encode()
    assert len(bytes(stored)) == 32


async def test_a_login_records_the_time_of_the_last_sign_in(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")

    await sign_in(client, "staff.demo")

    stamp = (await connection.execute(text("SELECT last_login_at FROM users"))).scalar_one()
    assert stamp == START


async def test_the_fifth_wrong_password_locks_the_account_even_for_the_right_password(
    client: AsyncClient, connection: AsyncConnection, clock: FakeClock
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    for _ in range(5):
        await sign_in(client, "staff.demo", "wrong")

    locked = await sign_in(client, "staff.demo")

    assert locked.status_code == 429
    assert locked.headers["retry-after"] == "900"
    clock.advance(minutes=16)
    assert (await sign_in(client, "staff.demo")).status_code == 200


async def test_logout_without_the_csrf_token_is_refused_and_the_session_survives(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    refused = await client.post("/api/auth/logout", headers=SAME_ORIGIN)

    assert refused.status_code == 403
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_logout_from_another_origin_is_refused_even_with_the_token(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")
    headers = {"X-CSRF-Token": client.cookies["docket_csrf"], "Origin": "https://evil.example"}

    assert (await client.post("/api/auth/logout", headers=headers)).status_code == 403


async def test_logout_ends_the_session_on_the_server_and_clears_both_cookies(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")
    stolen = client.cookies["docket_session"]

    response = await client.post("/api/auth/logout", headers=csrf_header(client))

    assert response.status_code == 204
    assert "docket_session" not in client.cookies
    client.cookies.set("docket_session", stolen)
    assert (await client.get("/api/auth/me")).status_code == 401
    revoked = (await connection.execute(text("SELECT revoked_at FROM sessions"))).scalar_one()
    assert revoked == START


async def test_a_session_idle_for_thirty_minutes_ends(
    client: AsyncClient, connection: AsyncConnection, clock: FakeClock
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    clock.advance(minutes=31)

    assert (await client.get("/api/auth/me")).status_code == 401


async def test_activity_keeps_a_session_alive_until_the_eight_hour_limit(
    client: AsyncClient, connection: AsyncConnection, clock: FakeClock
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    clock.advance(minutes=25)
    assert (await client.get("/api/auth/me")).status_code == 200
    statuses = []
    for _ in range(20):
        clock.advance(minutes=25)
        statuses.append((await client.get("/api/auth/me")).status_code)

    assert statuses[0] == 200
    assert statuses[-1] == 401


async def test_ending_every_session_of_a_user_makes_an_open_one_stale(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    await connection.execute(
        text("UPDATE users SET session_version = session_version + 1 WHERE id = :id"),
        {"id": user_id},
    )

    assert (await client.get("/api/auth/me")).status_code == 401


async def test_deactivating_a_user_ends_the_session_at_the_next_request(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    await connection.execute(
        text("UPDATE users SET is_active = false WHERE id = :id"), {"id": user_id}
    )

    assert (await client.get("/api/auth/me")).status_code == 401


# Matrix cells: TC-AUTH-anonymous-*, staff-*, verifier-* for the role gate (docs/security).


async def test_anonymous_callers_get_401_from_every_gated_route(client: AsyncClient) -> None:
    codes = [(await client.get(path)).status_code for path in ("/_gate/staff", "/_gate/verifier")]

    assert codes == [401, 401]


async def test_staff_passes_the_staff_gate_and_gets_403_from_the_verifier_gate(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    assert (await client.get("/_gate/staff")).status_code == 200
    assert (await client.get("/_gate/verifier")).status_code == 403
    assert (await client.get("/_gate/any")).status_code == 200


async def test_a_verifier_gets_403_from_a_staff_only_action(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(client, "verifier.demo")

    refused = await client.get("/_gate/staff")

    assert refused.status_code == 403
    assert (await client.get("/_gate/verifier")).status_code == 200
    assert refused.json()["error"]["code"] == "forbidden"


async def test_a_state_changing_gated_route_needs_the_csrf_token(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")

    without = await client.post("/_gate/change", headers=SAME_ORIGIN)
    forged = await client.post("/_gate/change", headers={"X-CSRF-Token": "0" * 64, **SAME_ORIGIN})
    allowed = await client.post("/_gate/change", headers=csrf_header(client))

    assert (without.status_code, forged.status_code, allowed.status_code) == (403, 403, 200)


REGISTER = {
    "username": "  Asha.K  ",
    "display_name": "Asha Kumar",
    "password": "a-long-phrase-1",
    "role": "verifier",
}


async def test_registering_signs_the_person_in_with_the_chosen_role(client: AsyncClient) -> None:
    response = await client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 200
    assert response.json()["role"] == "verifier"
    assert "docket_session" in client.cookies
    assert "docket_csrf" in client.cookies
    me = await client.get("/api/auth/me")
    assert me.json()["display_name"] == "Asha Kumar"


async def test_the_name_is_stored_trimmed_and_lower_case_and_signs_in_later(
    client: AsyncClient,
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    client.cookies.clear()
    again = await sign_in(client, "asha.k", "a-long-phrase-1")
    assert again.status_code == 200


async def test_a_taken_name_in_another_case_is_a_409_and_creates_nothing(
    client: AsyncClient,
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    client.cookies.clear()
    second = await client.post(
        "/api/auth/register", json={**REGISTER, "username": "ASHA.K", "role": "staff"}
    )
    assert second.status_code == 409
    assert "docket_session" not in client.cookies


async def test_the_stored_password_is_an_argon2_hash(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    row = await connection.execute(
        text("SELECT password_hash FROM users WHERE username = 'asha.k'")
    )
    stored = row.scalar_one()
    assert stored.startswith("$argon2id$")
    assert "a-long-phrase-1" not in stored
