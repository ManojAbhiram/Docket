"""The gateway's call log in Postgres. Its row count is the count the cap is checked against.

The gateway is synchronous and runs in a worker thread, while the session is async. The ledger hands
each statement to the event loop and waits for it, so no second database driver is needed.
"""

import asyncio
from collections.abc import Coroutine

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway import CallRecord

_COUNT = text(
    "SELECT count(*) FROM gateway_calls WHERE outcome <> 'refused' "
    "AND (CAST(:engine AS text) IS NULL OR engine = :engine) "
    "AND (CAST(:seconds AS double precision) IS NULL "
    "OR created_at > now() - make_interval(secs => CAST(:seconds AS double precision)))"
)
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
        counts_engine: str | None = None,
        window_hours: float | None = None,
    ) -> None:
        self._factory = factory
        self._loop = loop
        self._engine_version = engine_version
        self._preprocess = preprocess
        # The count behind the cap: one engine and a rolling window, or every call ever made.
        self._counts_engine = counts_engine
        self._window_seconds = None if window_hours is None else window_hours * 3600

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
            counted = await session.execute(
                _COUNT, {"engine": self._counts_engine, "seconds": self._window_seconds}
            )
            return int(counted.scalar_one())

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
