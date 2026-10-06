"""The demo accounts: generated one-time passwords, printed once, never stored in clear (PS-03)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.db.repositories.auth import SqlAuthStore
from app.db.seed_accounts import ACCOUNTS, seed_accounts
from app.domain.auth import Passwords

pytestmark = pytest.mark.integration


def passwords() -> Passwords:
    return Passwords(memory_kib=8, time_cost=1, parallelism=1)


async def test_the_two_demo_accounts_are_created_with_different_generated_passwords(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    issued = await seed_accounts(SqlAuthStore(factory), passwords())

    assert set(issued) == {"staff.demo", "verifier.demo"}
    assert issued["staff.demo"] != issued["verifier.demo"]
    assert all(len(phrase) >= 16 for phrase in issued.values())
    roles = (await connection.execute(text("SELECT username, role::text FROM users"))).all()
    assert {(r[0], r[1]) for r in roles} == {(a.username, a.role) for a in ACCOUNTS}


async def test_a_generated_password_signs_the_account_in_and_is_not_stored_in_clear(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    store = SqlAuthStore(factory)
    issued = await seed_accounts(store, passwords())

    user = await store.find_user("staff.demo")

    assert user is not None
    assert passwords().verify(user.password_hash, issued["staff.demo"]) is True
    assert issued["staff.demo"] not in user.password_hash


async def test_running_the_seed_again_keeps_the_accounts_and_issues_nothing_new(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    store = SqlAuthStore(factory)
    await seed_accounts(store, passwords())
    before = await store.find_user("staff.demo")

    again = await seed_accounts(store, passwords())

    assert again == {}
    after = await store.find_user("staff.demo")
    assert before is not None
    assert after is not None
    assert before.password_hash == after.password_hash
