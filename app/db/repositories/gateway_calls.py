"""The gateway's call log in Postgres. Its row count is the count the cap is checked against.

The gateway is synchronous and runs in a worker thread, while the session is async. The ledger hands
each statement to the event loop and waits for it, so no second database driver is needed.
"""

import asyncio
from collections.abc import Coroutine

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway import CallRecord

_COUNT = text("SELECT count(*) FROM gateway_calls WHERE outcome <> 'refused'")
_INSERT = text(
    "INSERT INTO gateway_calls (engine, engine_version, preprocess, duration_ms, outcome, units, "
    "cost) VALUES (:engine, :engine_version, :preprocess, :duration_ms, "
    "CAST(:outcome AS call_outcome), :units, :cost)"
)


class SqlCallLedger:
    """`CallLedger` over `gateway_calls`. Call it from a worker thread, never from the loop."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        loop: asyncio.AbstractEventLoop,
        *,
        engine_version: str,
        preprocess: bool,
    ) -> None:
        self._factory = factory
        self._loop = loop
        self._engine_version = engine_version
        self._preprocess = preprocess

    def calls_made(self) -> int:
        """Calls that ran, refused ones excluded."""
        return self._run(self._count())

    def record(self, record: CallRecord) -> None:
        self._run(self._insert(record))

    def _run[T](self, work: Coroutine[None, None, T]) -> T:
        try:
            on_loop_thread = asyncio.get_running_loop() is self._loop
        except RuntimeError:
            on_loop_thread = False
        if on_loop_thread:
            work.close()
            msg = "the ledger must be called from a worker thread, not the event loop thread"
            raise RuntimeError(msg)
        return asyncio.run_coroutine_threadsafe(work, self._loop).result()

    async def _count(self) -> int:
        async with self._factory() as session:
            return int((await session.execute(_COUNT)).scalar_one())

    async def _insert(self, record: CallRecord) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                _INSERT,
                {
                    "engine": record.engine,
                    "engine_version": self._engine_version,
                    "preprocess": self._preprocess,
                    "duration_ms": record.duration_ms,
                    "outcome": record.outcome,
                    "units": record.units,
                    "cost": record.cost,
                },
            )
