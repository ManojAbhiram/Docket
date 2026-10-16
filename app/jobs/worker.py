"""The bulk OCR queue: claim one document, read it, record the result (US-00-003, ADR-0011).

One document at a time bounds memory. The store owns the SQL (a claim with `FOR UPDATE SKIP LOCKED`
and writes conditional on `status = 'processing'`); this module owns the order of events and what
each failure is called. A failure is a reason code, never the engine's message. The read itself is
CPU work, so it runs in a thread and the event loop stays free.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial
from typing import Literal, Protocol
from uuid import UUID

import structlog

from app.core.compute import compute_slot
from app.core.errors import DomainError
from app.domain.processing import ProcessedDocument
from app.gateway import CallCapReachedError, EngineError
from app.gateway.process import EngineTimeoutError
from app.gateway.vision import VisionError

log = structlog.get_logger()

Outcome = Literal["idle", "read", "failed", "stale"]
STALE_AFTER_SECONDS = 300
VISION_GRACE_SECONDS = 2.0


@dataclass(frozen=True)
class ClaimedDocument:
    """A document the worker now owns: its id and the stored image to read."""

    id: UUID
    image: bytes
    # What the uploader asked for: "free" (local OCR) or "vision" (OpenRouter, ADR-0015).
    mode: str = "free"
    # `updated_at` as the claim set it. A result is stored only while it is still this value, so a
    # read that outlives its claim (swept, reprocessed, claimed again) cannot overwrite the newer
    # attempt. None skips the check.
    claimed_at: datetime | None = None


class ReadTimeoutError(DomainError):
    """A read ran past the timeout and was stopped."""

    status_code = 504
    code = "read_timeout"


class DocumentStore(Protocol):
    """The queue in the database. `complete` and `fail` return False if the document is no longer
    `processing` under the same claim, which is how a late result is kept from overwriting the
    sweeper or a reprocessed attempt."""

    async def claim_next(self) -> ClaimedDocument | None: ...

    async def complete(
        self, document_id: UUID, result: ProcessedDocument, claimed_at: datetime | None = None
    ) -> bool: ...

    async def fail(
        self, document_id: UUID, reason: str, claimed_at: datetime | None = None
    ) -> bool: ...

    async def sweep_stale(self, older_than_seconds: int) -> int: ...


class Reader(Protocol):
    """The gateway call for one image, with the engine, ledger and cap already chosen."""

    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument: ...


async def process_next(
    store: DocumentStore,
    reader: Reader,
    *,
    confidence_cutoff: float,
    settle: Callable[[UUID], Awaitable[None]] | None = None,
    vision_reader: Reader | None = None,
    vision_grace_seconds: float = VISION_GRACE_SECONDS,
    compute_slots: asyncio.Semaphore | None = None,
) -> Outcome:
    """Handle the oldest waiting document, if there is one.

    `settle` runs once a document is read or failed: it compares the fields and sets the status. If
    it raises, the error is logged and the document keeps its outcome, because a read must not be
    lost to a failure further on.
    """
    document = await store.claim_next()
    if document is None:
        return "idle"
    try:
        result = await _read(
            document, reader, vision_reader, confidence_cutoff, compute_slots, vision_grace_seconds
        )
    except CallCapReachedError:
        return await _failed(store, document, "cap_reached", settle)
    except ReadTimeoutError:
        return await _failed(store, document, "timeout", settle)
    except EngineError as exc:
        reason = "timeout" if isinstance(exc.__cause__, EngineTimeoutError) else "engine_error"
        return await _failed(store, document, reason, settle)
    if not await store.complete(document.id, result, claimed_at=document.claimed_at):
        log.warning("worker.result_discarded", document_id=str(document.id))
        return "stale"
    log.info("document.read", document_id=str(document.id), doc_type=result.doc_type)
    await _settle(settle, document.id)
    return "read"


async def _read(
    document: ClaimedDocument,
    reader: Reader,
    vision_reader: Reader | None,
    confidence_cutoff: float,
    compute_slots: asyncio.Semaphore | None,
    vision_grace_seconds: float,
) -> ProcessedDocument:
    """Read with the engine asked for. Vision is a first try: any failure falls back to the
    local reader and keeps a safe reason, so an upload is never lost to the provider."""
    if document.mode != "vision":
        return await _local_read(reader, document.image, confidence_cutoff, compute_slots)
    reason = "vision_unavailable"
    if vision_reader is not None:
        try:
            return await _vision_read(
                vision_reader, document.image, confidence_cutoff, vision_grace_seconds
            )
        except CallCapReachedError:
            reason = "vision_cap_reached"
        except EngineError as exc:
            reason = _vision_reason(exc)
        except TimeoutError:
            reason = "vision_timeout"
        log.warning("document.vision_fallback", document_id=str(document.id), reason_code=reason)
    local = await _local_read(reader, document.image, confidence_cutoff, compute_slots)
    return replace(local, fallback_reason=reason)


async def _vision_read(
    reader: Reader, image: bytes, cutoff: float, grace_seconds: float
) -> ProcessedDocument:
    """Wait for Vision no longer than its own deadline plus a grace.

    The reader checks its deadline as bytes arrive, so a read blocked mid-piece could outlive it.
    The thread cannot be killed, but it is bounded by the client's own timeouts, and the page no
    longer waits for it.
    """
    work = asyncio.to_thread(reader.read, image, confidence_cutoff=cutoff)
    deadline: float | None = getattr(reader, "deadline_seconds", None)
    if deadline is None:
        return await work
    return await asyncio.wait_for(work, timeout=deadline + grace_seconds)


async def _local_read(
    reader: Reader, image: bytes, cutoff: float, slots: asyncio.Semaphore | None
) -> ProcessedDocument:
    work = partial(reader.read, image, confidence_cutoff=cutoff)
    if slots is None:
        return await asyncio.to_thread(work)
    async with compute_slot(slots) as lease:
        return await lease.run(work)


_VISION_REASONS = {
    "VisionTimeoutError": "vision_timeout",
    "VisionRateLimitedError": "vision_rate_limited",
    "VisionUpstreamError": "vision_upstream_error",
    "VisionBadAnswerError": "vision_bad_answer",
}


def _vision_reason(failure: EngineError) -> str:
    """The safe reason code for why Vision could not answer; unknown causes are `vision_error`."""
    cause = failure.__cause__
    if isinstance(cause, VisionError):
        return _VISION_REASONS.get(type(cause).__name__, "vision_error")
    return "vision_error"


async def sweep_stale_documents(store: DocumentStore) -> int:
    """Fail documents stuck in `processing` past the sweeper age, so nothing waits forever."""
    return await store.sweep_stale(STALE_AFTER_SECONDS)


async def run_loop(
    step: Callable[[], Awaitable[str]], *, idle_seconds: float, stop: asyncio.Event
) -> None:
    """Run `step` until `stop` is set. Wait when idle, and survive a step that raises."""
    while not stop.is_set():
        try:
            outcome = await step()
        except Exception as exc:
            log.error("worker.step_failed", error_type=type(exc).__name__)
            outcome = "idle"
        if outcome == "idle":
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=idle_seconds)


async def sweep_loop(store: DocumentStore, *, interval_seconds: float, stop: asyncio.Event) -> None:
    """Sweep every `interval_seconds` until `stop` is set, and survive a sweep that raises."""
    while not stop.is_set():
        try:
            swept = await sweep_stale_documents(store)
            if swept:
                log.warning("worker.swept", documents=swept)
        except Exception as exc:
            log.error("worker.sweep_failed", error_type=type(exc).__name__)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)


async def _failed(
    store: DocumentStore,
    document: ClaimedDocument,
    reason: str,
    settle: Callable[[UUID], Awaitable[None]] | None,
) -> Outcome:
    if not await store.fail(document.id, reason, claimed_at=document.claimed_at):
        return "stale"
    log.warning("document.failed", document_id=str(document.id), reason_code=reason)
    await _settle(settle, document.id)
    return "failed"


async def _settle(settle: Callable[[UUID], Awaitable[None]] | None, document_id: UUID) -> None:
    if settle is None:
        return
    try:
        await settle(document_id)
    except Exception as exc:
        log.error(
            "worker.settle_failed", document_id=str(document_id), error_type=type(exc).__name__
        )
