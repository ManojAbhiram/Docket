"""The call log in Postgres: the count behind the cap survives a restart (US-02-001, Q-009).

Needs `make db` and `make migrate`. Each test runs in a transaction that is rolled back. The gateway
runs in a worker thread, as the document worker does, while the ledger reaches the async session on
the event loop.
"""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.db.repositories.gateway_calls import SqlCallLedger
from app.gateway import CallCapReachedError, CallRecord, OcrResult, OcrWord, read_document

pytestmark = pytest.mark.integration

WORDS = (OcrWord(text="Latha Sharma", confidence=0.99, box=(1.0, 2.0, 3.0, 4.0)),)


class StaticEngine:
    name = "rapidocr"

    def read(self, image: bytes) -> OcrResult:
        return OcrResult(words=WORDS)


def ledger_for(factory: async_sessionmaker[AsyncSession]) -> SqlCallLedger:
    return SqlCallLedger(
        factory, asyncio.get_running_loop(), engine_version="rapidocr-3.0", preprocess=True
    )


async def rows(connection: AsyncConnection) -> list[tuple[str, int, str, bool, str]]:
    result = await connection.execute(
        text(
            "SELECT engine, units, engine_version, preprocess, outcome::text "
            "FROM gateway_calls ORDER BY id"
        )
    )
    return [(r[0], r[1], r[2], r[3], r[4]) for r in result.all()]


async def test_a_call_writes_one_row_with_engine_version_units_and_zero_cost(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    ledger = ledger_for(factory)

    await asyncio.to_thread(read_document, b"page", engine=StaticEngine(), ledger=ledger, cap=5)

    assert await rows(connection) == [("rapidocr", 1, "rapidocr-3.0", True, "ok")]
    cost = (await connection.execute(text("SELECT cost FROM gateway_calls"))).scalar_one()
    assert cost == 0


async def test_a_new_ledger_sees_the_calls_an_earlier_one_made(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    first = ledger_for(factory)
    for _ in range(3):
        await asyncio.to_thread(read_document, b"page", engine=StaticEngine(), ledger=first, cap=5)

    restarted = ledger_for(factory)

    assert await asyncio.to_thread(restarted.calls_made) == 3


async def test_the_cap_still_refuses_after_a_restart_and_the_refusal_is_logged_not_counted(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    first = ledger_for(factory)
    for _ in range(2):
        await asyncio.to_thread(read_document, b"page", engine=StaticEngine(), ledger=first, cap=2)
    restarted = ledger_for(factory)

    with pytest.raises(CallCapReachedError):
        await asyncio.to_thread(
            read_document, b"page", engine=StaticEngine(), ledger=restarted, cap=2
        )

    assert [row[4] for row in await rows(connection)] == ["ok", "ok", "refused"]
    assert await asyncio.to_thread(restarted.calls_made) == 2


async def test_an_engine_failure_is_logged_as_an_error_and_still_counts(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    ledger = ledger_for(factory)

    await asyncio.to_thread(
        ledger.record,
        CallRecord(engine="rapidocr", outcome="error", duration_ms=4, units=0),
    )

    assert [row[4] for row in await rows(connection)] == ["error"]
    assert await asyncio.to_thread(ledger.calls_made) == 1


async def test_calling_the_ledger_from_the_event_loop_thread_is_refused_not_deadlocked(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = ledger_for(factory)

    with pytest.raises(RuntimeError, match="worker thread"):
        ledger.calls_made()
