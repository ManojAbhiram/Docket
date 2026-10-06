"""The one function every OCR call goes through."""

import threading
import time

from app.gateway.types import (
    CallCapReachedError,
    CallLedger,
    CallRecord,
    Engine,
    EngineError,
    OcrResult,
)

# Calls that hold a slot but have not been logged yet, per ledger. Without them a check and a write
# that sit apart let every concurrent caller see the same free slot.
_slots_lock = threading.Lock()
_in_flight: dict[int, int] = {}


def read_document(image: bytes, *, engine: Engine, ledger: CallLedger, cap: int) -> OcrResult:
    """Read one image: refuse past the cap, otherwise run the engine and log the call."""
    if not _reserve_slot(ledger, cap):
        ledger.record(CallRecord(engine=engine.name, outcome="refused", duration_ms=0, units=0))
        msg = "the call cap is reached"
        raise CallCapReachedError(msg)
    started = time.perf_counter()
    try:
        try:
            result = engine.read(image)
        except Exception as exc:
            ledger.record(
                CallRecord(
                    engine=engine.name, outcome="error", duration_ms=_since(started), units=0
                )
            )
            msg = "the engine could not read the image"
            raise EngineError(msg) from exc
        ledger.record(
            CallRecord(
                engine=engine.name,
                outcome="ok",
                duration_ms=_since(started),
                units=len(result.words),
            )
        )
        return result
    finally:
        _release_slot(ledger)


def _reserve_slot(ledger: CallLedger, cap: int) -> bool:
    """Take a slot if the logged calls plus the calls in flight leave room, in one locked step."""
    with _slots_lock:
        if ledger.calls_made() + _in_flight.get(id(ledger), 0) >= cap:
            return False
        _in_flight[id(ledger)] = _in_flight.get(id(ledger), 0) + 1
        return True


def _release_slot(ledger: CallLedger) -> None:
    """Give the slot back once the call is logged, so a failed call never holds one."""
    with _slots_lock:
        remaining = _in_flight[id(ledger)] - 1
        if remaining:
            _in_flight[id(ledger)] = remaining
        else:
            del _in_flight[id(ledger)]


def _since(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
