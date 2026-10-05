"""The one function every OCR call goes through."""

import time

from app.gateway.types import (
    CallCapReachedError,
    CallLedger,
    CallRecord,
    Engine,
    EngineError,
    OcrResult,
)


def read_document(image: bytes, *, engine: Engine, ledger: CallLedger, cap: int) -> OcrResult:
    """Read one image: refuse past the cap, otherwise run the engine and log the call."""
    if ledger.calls_made() >= cap:
        ledger.record(CallRecord(engine=engine.name, outcome="refused", duration_ms=0, units=0))
        msg = "the call cap is reached"
        raise CallCapReachedError(msg)
    started = time.perf_counter()
    try:
        result = engine.read(image)
    except Exception as exc:
        ledger.record(
            CallRecord(engine=engine.name, outcome="error", duration_ms=_since(started), units=0)
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


def _since(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
