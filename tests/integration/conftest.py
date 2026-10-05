"""Integration fixtures: a real Postgres, the migrated schema, and a transaction per test.

Run `make db` and `make migrate` first, then `make test-integration`. Every test works inside one
transaction that is rolled back, so nothing is left behind and tests do not see each other.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def connection() -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def factory(connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Sessions that join the test's transaction, each commit becoming a savepoint."""
    return async_sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
async def session(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """One session inside the test's transaction, for tests that use the ORM."""
    async with factory() as active:
        yield active
