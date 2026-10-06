"""The bulk OCR queue: claim one document, read it, record the result (US-00-003, ADR-0011).

One document at a time bounds memory. The store owns the SQL (a claim with `FOR UPDATE SKIP LOCKED`
and writes conditional on `status = 'processing'`); this module owns the order of events and what
each failure is called. A failure is a reason code, never the engine's message. The read itself is
CPU work, so it runs in a thread and the event loop stays free.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

import structlog

from app.core.errors import DomainError
from app.domain.classify import classify
from app.domain.extract import ExtractedField, extract_fields
from app.gateway import CallCapReachedError, EngineError, OcrResult
from app.gateway.process import EngineTimeoutError

log = structlog.get_logger()

Outcome = Literal["idle", "read", "failed", "stale"]
STALE_AFTER_SECONDS = 300


@dataclass(frozen=True)
class ClaimedDocument:
    """A document the worker now owns: its id and the stored image to read."""

    id: UUID
    image: bytes


@dataclass(frozen=True)
class ProcessedDocument:
    """What reading a document produced: its type and every field it carries."""

    doc_type: str
    fields: tuple[ExtractedField, ...]


class ReadTimeoutError(DomainError):
    """A read ran past the timeout and was stopped."""

    status_code = 504
    code = "read_timeout"


class DocumentStore(Protocol):
    """The queue in the database. `complete` and `fail` return False if the document is no longer
    `processing`, which is how a late result is kept from overwriting the sweeper."""

    async def claim_next(self) -> ClaimedDocument | None: ...

    async def complete(self, document_id: UUID, result: ProcessedDocument) -> bool: ...

    async def fail(self, document_id: UUID, reason: str) -> bool: ...

    async def sweep_stale(self, older_than_seconds: int) -> int: ...


class Reader(Protocol):
    """The gateway call for one image, with the engine, ledger and cap already chosen."""

    def read(self, image: bytes) -> OcrResult: ...


async def process_next(
    store: DocumentStore, reader: Reader, *, confidence_cutoff: float
) -> Outcome:
    """Handle the oldest waiting document, if there is one."""
    document = await store.claim_next()
    if document is None:
        return "idle"
    try:
        result = await asyncio.to_thread(reader.read, document.image)
    except CallCapReachedError:
        return await _failed(store, document.id, "cap_reached")
    except ReadTimeoutError:
        return await _failed(store, document.id, "timeout")
    except EngineError as exc:
        reason = "timeout" if isinstance(exc.__cause__, EngineTimeoutError) else "engine_error"
        return await _failed(store, document.id, reason)
    doc_type = classify(result.words)
    fields = extract_fields(result.words, doc_type, confidence_cutoff=confidence_cutoff)
    if not await store.complete(document.id, ProcessedDocument(doc_type=doc_type, fields=fields)):
        log.warning("worker.result_discarded", document_id=str(document.id))
        return "stale"
    log.info("document.read", document_id=str(document.id), doc_type=doc_type)
    return "read"


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


async def _failed(store: DocumentStore, document_id: UUID, reason: str) -> Outcome:
    if not await store.fail(document_id, reason):
        return "stale"
    log.warning("document.failed", document_id=str(document_id), reason_code=reason)
    return "failed"
