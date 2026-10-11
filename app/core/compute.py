"""Keep shared memory admission until native work actually finishes."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager


class ComputeLease:
    """A slot whose lifetime includes uncancellable native thread work."""

    def __init__(self, slots: asyncio.Semaphore) -> None:
        self._slots = slots
        self._pending: asyncio.Task[object] | None = None

    async def run[T](self, work: Callable[[], T]) -> T:
        task = asyncio.create_task(asyncio.to_thread(work))
        self._pending = task
        return await asyncio.shield(task)

    def release(self) -> None:
        pending = self._pending
        if pending is not None and not pending.done():
            pending.add_done_callback(self._finished)
        else:
            self._slots.release()

    def _finished(self, task: asyncio.Task[object]) -> None:
        if not task.cancelled():
            task.exception()
        self._slots.release()


@asynccontextmanager
async def compute_slot(slots: asyncio.Semaphore) -> AsyncIterator[ComputeLease]:
    """Acquire before buffering inputs; cancelled callers retain running native work's slot."""
    await slots.acquire()
    lease = ComputeLease(slots)
    try:
        yield lease
    finally:
        lease.release()
