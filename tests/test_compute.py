"""Shared memory admission follows native work beyond request cancellation."""

import asyncio
import threading

import pytest

from app.core.compute import compute_slot


@pytest.mark.parametrize("fails", [False, True])
async def test_cancelled_native_work_holds_capacity_until_it_finishes(fails: bool) -> None:
    slots = asyncio.Semaphore(1)
    started = asyncio.Event()
    finish = threading.Event()
    loop = asyncio.get_running_loop()

    def native() -> int:
        loop.call_soon_threadsafe(started.set)
        assert finish.wait(timeout=5)
        if fails:
            raise ValueError("native failure after cancellation")
        return 7

    async def request() -> int:
        async with compute_slot(slots) as lease:
            return await lease.run(native)

    pending = asyncio.create_task(request())
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert slots.locked()
    finally:
        finish.set()
    await asyncio.wait_for(slots.acquire(), timeout=3)
    slots.release()


async def test_failed_native_work_returns_its_slot() -> None:
    slots = asyncio.Semaphore(1)

    def native() -> int:
        raise ValueError("expected failure")

    with pytest.raises(ValueError, match="expected failure"):
        async with compute_slot(slots) as lease:
            await lease.run(native)
    assert not slots.locked()


async def test_cancelling_a_waiting_caller_does_not_create_capacity() -> None:
    slots = asyncio.Semaphore(1)

    async def waiting() -> None:
        async with compute_slot(slots):
            pytest.fail("busy native capacity was admitted")

    async with slots:
        pending = asyncio.create_task(waiting())
        await asyncio.sleep(0)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert slots.locked()
    assert not slots.locked()
