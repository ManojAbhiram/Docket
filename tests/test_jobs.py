"""The bulk OCR queue: claim one document, read it, record the result (US-00-003, ADR-0011).

Every test here fails until `app/jobs/worker.py` exists. The store and the reader are small fakes
of the two interfaces the worker owns; the claim query itself is covered by the integration tests.
"""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.domain.extract import ExtractedField
from app.gateway import CallCapReachedError, EngineError, OcrResult, OcrWord
from app.gateway.process import EngineTimeoutError
from app.jobs.worker import (
    ClaimedDocument,
    ProcessedDocument,
    ReadTimeoutError,
    process_next,
    run_loop,
    sweep_loop,
    sweep_stale_documents,
)

CUTOFF = 0.95


def word(text: str, x: float, y: float) -> OcrWord:
    return OcrWord(text=text, confidence=0.99, box=(x, y, 10.0 * len(text), 22.0))


ID_CARD = OcrResult(
    words=(
        word("Identity Card", 10, 0),
        word("Name", 10, 60),
        word("Latha Sharma", 220, 60),
        word("Date of birth", 10, 100),
        word("10/12/2006", 220, 100),
        word("ID number", 10, 140),
        word("SYNID12345678", 220, 140),
    )
)
NO_TITLE = OcrResult(words=(word("Electricity bill", 10, 0),))


@dataclass
class MemoryStore:
    queue: list[ClaimedDocument] = field(default_factory=list)
    completed: dict[UUID, ProcessedDocument] = field(default_factory=dict)
    failed: dict[UUID, str] = field(default_factory=dict)
    still_processing: bool = True
    swept_with: list[int] = field(default_factory=list)

    async def claim_next(self) -> ClaimedDocument | None:
        return self.queue.pop(0) if self.queue else None

    async def complete(self, document_id: UUID, result: ProcessedDocument) -> bool:
        if not self.still_processing:
            return False
        self.completed[document_id] = result
        return True

    async def fail(self, document_id: UUID, reason: str) -> bool:
        if not self.still_processing:
            return False
        self.failed[document_id] = reason
        return True

    async def sweep_stale(self, older_than_seconds: int) -> int:
        self.swept_with.append(older_than_seconds)
        return 2


class FakeReader:
    def __init__(self, result: OcrResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.images: list[bytes] = []

    def read(self, image: bytes) -> OcrResult:
        self.images.append(image)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def one_document(store: MemoryStore) -> UUID:
    document_id = uuid4()
    store.queue.append(ClaimedDocument(id=document_id, image=b"page"))
    return document_id


async def test_an_empty_queue_is_idle_and_reads_nothing() -> None:
    reader = FakeReader()

    assert await process_next(MemoryStore(), reader, confidence_cutoff=CUTOFF) == "idle"
    assert reader.images == []


async def test_a_claimed_document_is_read_classified_and_its_fields_recorded() -> None:
    store = MemoryStore()
    document_id = one_document(store)

    outcome = await process_next(store, FakeReader(result=ID_CARD), confidence_cutoff=CUTOFF)

    done = store.completed[document_id]
    assert outcome == "read"
    assert done.doc_type == "id_proof"
    assert {f.field_name for f in done.fields} == {"name", "dob", "document_number"}
    assert all(isinstance(f, ExtractedField) for f in done.fields)


async def test_a_page_with_no_known_title_is_recorded_as_unknown_not_dropped() -> None:
    store = MemoryStore()
    document_id = one_document(store)

    await process_next(store, FakeReader(result=NO_TITLE), confidence_cutoff=CUTOFF)

    assert store.completed[document_id].doc_type == "unknown"


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (CallCapReachedError("cap"), "cap_reached"),
        (ReadTimeoutError("slow"), "timeout"),
        (EngineError("engine"), "engine_error"),
    ],
)
async def test_a_read_that_does_not_finish_marks_the_document_failed_with_a_reason_code(
    error: Exception, reason: str
) -> None:
    store = MemoryStore()
    document_id = one_document(store)

    outcome = await process_next(store, FakeReader(error=error), confidence_cutoff=CUTOFF)

    assert outcome == "failed"
    assert store.failed == {document_id: reason}
    assert store.completed == {}


async def test_a_result_that_arrives_after_the_sweeper_gave_up_changes_nothing() -> None:
    store = MemoryStore(still_processing=False)
    one_document(store)

    outcome = await process_next(store, FakeReader(result=ID_CARD), confidence_cutoff=CUTOFF)

    assert outcome == "stale"
    assert store.completed == {}


async def test_the_sweeper_fails_documents_stuck_in_processing_for_five_minutes() -> None:
    store = MemoryStore()

    assert await sweep_stale_documents(store) == 2
    assert store.swept_with == [300]


async def test_the_loop_keeps_working_until_asked_to_stop() -> None:
    outcomes = ["read", "read", "idle", "idle"]
    stop = asyncio.Event()
    calls: list[str] = []

    async def step() -> str:
        outcome = outcomes[len(calls)]
        calls.append(outcome)
        if len(calls) == len(outcomes):
            stop.set()
        return outcome

    await asyncio.wait_for(run_loop(step, idle_seconds=0.01, stop=stop), timeout=2)

    assert calls == outcomes


async def test_a_step_that_raises_is_logged_and_the_loop_carries_on() -> None:
    stop = asyncio.Event()
    calls = 0

    async def step() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            msg = "boom"
            raise ValueError(msg)
        stop.set()
        return "idle"

    await asyncio.wait_for(run_loop(step, idle_seconds=0.01, stop=stop), timeout=2)

    assert calls == 2


async def test_an_engine_error_caused_by_a_timeout_is_recorded_as_a_timeout() -> None:
    store = MemoryStore()
    document_id = one_document(store)
    error = EngineError("the engine could not read the image")
    error.__cause__ = EngineTimeoutError("the read ran past its limit")

    outcome = await process_next(store, FakeReader(error=error), confidence_cutoff=CUTOFF)

    assert outcome == "failed"
    assert store.failed == {document_id: "timeout"}


async def test_the_sweep_loop_sweeps_again_and_again_until_asked_to_stop() -> None:
    stop = asyncio.Event()

    class StoppingStore(MemoryStore):
        async def sweep_stale(self, older_than_seconds: int) -> int:
            swept = await super().sweep_stale(older_than_seconds)
            if len(self.swept_with) == 3:
                stop.set()
            return swept

    store = StoppingStore()

    await asyncio.wait_for(sweep_loop(store, interval_seconds=0.01, stop=stop), timeout=3)

    assert store.swept_with == [300, 300, 300]
