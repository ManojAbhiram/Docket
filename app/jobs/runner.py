"""Start the document worker with the API and stop it with the API (ADR-0011).

Two background tasks share one stop signal: one claims and reads documents, one fails documents
stuck in `processing`. Stopping gives a read a few seconds to finish, then closes the reader, which
kills a child that is still reading, and waits for both tasks to end.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Protocol
from uuid import UUID

from app.domain.processing import ProcessedDocument
from app.jobs.worker import DocumentStore, process_next, run_loop, sweep_loop

_GRACE_SECONDS = 5.0


class ClosableReader(Protocol):
    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument: ...

    def close(self) -> None: ...


@dataclass
class RunningWorker:
    """The two tasks, the signal that ends them and the reader they share."""

    reader: ClosableReader
    stop_signal: asyncio.Event
    tasks: list[asyncio.Task[None]] = field(default_factory=list)
    finished: bool = False

    async def stop(self) -> None:
        self.stop_signal.set()
        _, pending = await asyncio.wait(self.tasks, timeout=_GRACE_SECONDS)
        self.reader.close()
        if pending:
            await asyncio.wait(pending, timeout=_GRACE_SECONDS)
        self.finished = all(task.done() for task in self.tasks)


def start_worker(
    store: DocumentStore,
    reader: ClosableReader,
    *,
    confidence_cutoff: float,
    idle_seconds: float,
    sweep_interval_seconds: float,
    settle: Callable[[UUID], Awaitable[None]] | None = None,
) -> RunningWorker:
    """Create both tasks on the running loop."""
    stop = asyncio.Event()
    step = partial(process_next, store, reader, confidence_cutoff=confidence_cutoff, settle=settle)
    worker = RunningWorker(reader=reader, stop_signal=stop)
    worker.tasks = [
        asyncio.create_task(run_loop(step, idle_seconds=idle_seconds, stop=stop)),
        asyncio.create_task(sweep_loop(store, interval_seconds=sweep_interval_seconds, stop=stop)),
    ]
    return worker
