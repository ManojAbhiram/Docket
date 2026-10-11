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


async def insert_call(connection: AsyncConnection, engine: str, age_hours: float) -> None:
    await connection.execute(
        text(
            "INSERT INTO gateway_calls (engine, engine_version, preprocess, duration_ms, outcome, "
            "units, created_at) VALUES (:engine, 'v', false, 1, 'ok', 1, "
            "now() - make_interval(secs => :seconds))"
        ),
        {"engine": engine, "seconds": age_hours * 3600},
    )


async def test_a_ledger_scoped_to_one_engine_counts_only_its_own_recent_calls(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    await insert_call(connection, "openrouter", age_hours=1)
    await insert_call(connection, "openrouter", age_hours=23)
    await insert_call(connection, "openrouter", age_hours=25)
    await insert_call(connection, "rapidocr", age_hours=1)
    vision = SqlCallLedger(
        factory,
        asyncio.get_running_loop(),
        engine_version="vendor/model:free",
        preprocess=False,
        counts_engine="openrouter",
        window_hours=24,
    )

    assert await asyncio.to_thread(vision.calls_made) == 2


async def test_an_unscoped_ledger_still_counts_every_call_ever_made(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    await insert_call(connection, "openrouter", age_hours=100)
    await insert_call(connection, "rapidocr", age_hours=1)

    assert await asyncio.to_thread(ledger_for(factory).calls_made) == 2


# Regression: ISSUE-001 [NOTASK-16], found by /qa on 2026-10-11. `error_class` existed in the schema
# but was never written, so a failed call said nothing about why.
async def test_a_failed_call_keeps_the_class_of_its_failure_and_an_ok_call_has_none(
    factory: async_sessionmaker[AsyncSession], connection: AsyncConnection
) -> None:
    ledger = ledger_for(factory)

    await asyncio.to_thread(
        ledger.record,
        CallRecord(
            engine="openrouter",
            outcome="error",
            duration_ms=5,
            units=0,
            error_class="VisionRateLimitedError",
        ),
    )
    await asyncio.to_thread(
        ledger.record, CallRecord(engine="openrouter", outcome="ok", duration_ms=5, units=3)
    )

    result = await connection.execute(text("SELECT error_class FROM gateway_calls ORDER BY id"))
    assert [row[0] for row in result.all()] == ["VisionRateLimitedError", None]
