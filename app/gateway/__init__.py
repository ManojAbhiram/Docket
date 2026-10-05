"""The OCR gateway: the only package allowed to import an engine client (US-02-001)."""

from app.gateway.core import read_document
from app.gateway.types import (
    CallCapReachedError,
    CallLedger,
    CallRecord,
    Engine,
    EngineError,
    OcrResult,
    OcrWord,
    Outcome,
    RecordingMissingError,
)

__all__ = [
    "CallCapReachedError",
    "CallLedger",
    "CallRecord",
    "Engine",
    "EngineError",
    "OcrResult",
    "OcrWord",
    "Outcome",
    "RecordingMissingError",
    "read_document",
]
