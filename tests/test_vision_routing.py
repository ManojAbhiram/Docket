"""The worker reads a document with the engine its uploader asked for (ADR-0015).

Vision is opt-in and only ever a first try: when it cannot answer, the document is read by the
local OCR and the safe reason is kept, so an upload is never lost to the provider.
"""

import threading
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.domain.extract import ExtractedField
from app.domain.processing import ProcessedDocument
from app.gateway import CallCapReachedError, EngineError
from app.gateway.vision import (
    VisionBadAnswerError,
    VisionRateLimitedError,
    VisionTimeoutError,
    VisionUpstreamError,
)
from app.jobs.worker import ClaimedDocument, process_next

CUTOFF = 0.95
VISION_DOC = ProcessedDocument(
    doc_type="id_proof",
    fields=(ExtractedField("name", None, "Latha Sharma", None, None, True, "low_confidence"),),
    engine="openrouter",
)
LOCAL_DOC = ProcessedDocument(
    doc_type="id_proof",
    fields=(ExtractedField("name", None, "Latha Sharma", 0.99, (1, 2, 3, 4), False, None),),
    engine="rapidocr",
)


@dataclass
class Store:
    queue: list[ClaimedDocument] = field(default_factory=list)
    completed: dict[UUID, ProcessedDocument] = field(default_factory=dict)
    failed: dict[UUID, str] = field(default_factory=dict)

    async def claim_next(self) -> ClaimedDocument | None:
        return self.queue.pop(0) if self.queue else None

    async def complete(self, document_id: UUID, result: ProcessedDocument) -> bool:
        self.completed[document_id] = result
        return True

    async def fail(self, document_id: UUID, reason: str) -> bool:
        self.failed[document_id] = reason
        return True

    async def sweep_stale(self, older_than_seconds: int) -> int:
        return 0


class Reader:
    def __init__(self, result: ProcessedDocument | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.reads = 0

    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument:
        self.reads += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def queued(store: Store, mode: str) -> UUID:
    document_id = uuid4()
    store.queue.append(ClaimedDocument(id=document_id, image=b"page", mode=mode))
    return document_id


async def test_a_free_document_never_reaches_vision() -> None:
    store, local, vision = Store(), Reader(LOCAL_DOC), Reader(VISION_DOC)
    document_id = queued(store, "free")

    await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=vision)

    assert store.completed[document_id] == LOCAL_DOC
    assert (local.reads, vision.reads) == (1, 0)


async def test_a_vision_document_is_read_by_vision_alone() -> None:
    store, local, vision = Store(), Reader(LOCAL_DOC), Reader(VISION_DOC)
    document_id = queued(store, "vision")

    outcome = await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=vision)

    assert outcome == "read"
    assert store.completed[document_id] == VISION_DOC
    assert (local.reads, vision.reads) == (0, 1)


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (CallCapReachedError("cap"), "vision_cap_reached"),
        (EngineError("engine"), "vision_error"),
    ],
)
async def test_a_vision_failure_falls_back_to_the_local_reader_and_says_why(
    error: Exception, reason: str
) -> None:
    store, local, vision = Store(), Reader(LOCAL_DOC), Reader(error=error)
    document_id = queued(store, "vision")

    outcome = await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=vision)

    assert outcome == "read"
    assert store.completed[document_id].engine == "rapidocr"
    assert store.completed[document_id].fallback_reason == reason
    assert store.failed == {}


async def test_a_vision_timeout_is_named_as_such() -> None:
    timeout = EngineError("engine")
    timeout.__cause__ = VisionTimeoutError()
    store, local = Store(), Reader(LOCAL_DOC)
    document_id = queued(store, "vision")

    await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=Reader(error=timeout))

    assert store.completed[document_id].fallback_reason == "vision_timeout"


async def test_a_vision_document_with_vision_switched_off_is_read_locally() -> None:
    store, local = Store(), Reader(LOCAL_DOC)
    document_id = queued(store, "vision")

    await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=None)

    assert store.completed[document_id].fallback_reason == "vision_unavailable"
    assert local.reads == 1


async def test_when_the_fallback_also_fails_the_document_fails_with_the_local_reason() -> None:
    store = Store()
    document_id = queued(store, "vision")

    outcome = await process_next(
        store,
        Reader(error=EngineError("local")),
        confidence_cutoff=CUTOFF,
        vision_reader=Reader(error=EngineError("vision")),
    )

    assert outcome == "failed"
    assert store.failed == {document_id: "engine_error"}


# Regression: ISSUE-001 [NOTASK-16], found by /qa on 2026-10-11. The fallback reason must say why.
@pytest.mark.parametrize(
    ("cause", "reason"),
    [
        (VisionRateLimitedError(), "vision_rate_limited"),
        (VisionUpstreamError(), "vision_upstream_error"),
        (VisionBadAnswerError(), "vision_bad_answer"),
        (VisionTimeoutError(), "vision_timeout"),
        (ValueError("anything else"), "vision_error"),
    ],
)
async def test_the_fallback_reason_names_why_vision_could_not_answer(
    cause: Exception, reason: str
) -> None:
    failure = EngineError("engine")
    failure.__cause__ = cause
    store, local = Store(), Reader(LOCAL_DOC)
    document_id = queued(store, "vision")

    await process_next(store, local, confidence_cutoff=CUTOFF, vision_reader=Reader(error=failure))

    assert store.completed[document_id].fallback_reason == reason


class Stuck:
    """A Vision reader whose read never returns until released, as a blocked network read does."""

    deadline_seconds = 0.05

    def __init__(self) -> None:
        self.release = threading.Event()

    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument:
        self.release.wait(timeout=5)
        return VISION_DOC


# NOTASK-17 security review: the Vision deadline was only checked as bytes arrived, so a read
# blocked mid-piece could outlive it. The worker now stops waiting at the deadline plus a grace.
async def test_a_vision_read_that_never_returns_is_cut_off_and_read_locally() -> None:
    store, local, stuck = Store(), Reader(LOCAL_DOC), Stuck()
    document_id = queued(store, "vision")

    try:
        outcome = await process_next(
            store, local, confidence_cutoff=CUTOFF, vision_reader=stuck, vision_grace_seconds=0.05
        )
    finally:
        stuck.release.set()

    assert outcome == "read"
    assert store.completed[document_id].fallback_reason == "vision_timeout"
    assert local.reads == 1
