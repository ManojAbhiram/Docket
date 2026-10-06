"""Starting and stopping the document worker with the API (US-00-003, ADR-0011).

The worker is two background tasks: one claims and reads documents, one fails documents stuck in
`processing`. Stopping must end both and close the engine, even if a read is under way.
"""

import asyncio
from uuid import UUID

from app.gateway import OcrResult
from app.jobs.runner import start_worker
from app.jobs.worker import ClaimedDocument, ProcessedDocument


class IdleStore:
    def __init__(self) -> None:
        self.claims = 0
        self.sweeps = 0
        self.busy_twice = asyncio.Event()

    def _note(self) -> None:
        if self.claims >= 2 and self.sweeps >= 2:
            self.busy_twice.set()

    async def claim_next(self) -> ClaimedDocument | None:
        self.claims += 1
        self._note()
        return None

    async def complete(self, document_id: UUID, result: ProcessedDocument) -> bool:
        return True

    async def fail(self, document_id: UUID, reason: str) -> bool:
        return True

    async def sweep_stale(self, older_than_seconds: int) -> int:
        self.sweeps += 1
        self._note()
        return 0


class ClosableReader:
    def __init__(self) -> None:
        self.closed = False

    def read(self, image: bytes) -> OcrResult:
        return OcrResult(words=())

    def close(self) -> None:
        self.closed = True


async def test_a_started_worker_runs_until_stopped_and_then_closes_the_reader() -> None:
    store, reader = IdleStore(), ClosableReader()
    worker = start_worker(
        store,
        reader,
        confidence_cutoff=0.95,
        idle_seconds=0.01,
        sweep_interval_seconds=0.01,
    )
    await asyncio.wait_for(store.busy_twice.wait(), timeout=3)

    await asyncio.wait_for(worker.stop(), timeout=3)

    assert reader.closed is True
    assert worker.finished is True


async def test_stopping_twice_is_harmless() -> None:
    reader = ClosableReader()
    worker = start_worker(
        IdleStore(), reader, confidence_cutoff=0.95, idle_seconds=0.01, sweep_interval_seconds=0.01
    )

    await worker.stop()
    await worker.stop()

    assert reader.closed is True
