"""What the gateway accepts and returns, and the two interfaces it owns."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from app.core.errors import DomainError

Outcome = Literal["ok", "error", "refused"]


@dataclass(frozen=True)
class OcrWord:
    """One piece of recognised text with its confidence and where it sits on the image."""

    text: str
    confidence: float
    box: tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrResult:
    """Everything an engine read from one image."""

    words: tuple[OcrWord, ...]


@dataclass(frozen=True)
class CallRecord:
    """One row of the call log. The cost is always zero: only free engines are allowed."""

    engine: str
    outcome: Outcome
    duration_ms: int
    units: int
    cost: Decimal = Decimal(0)


class Engine(Protocol):
    """An OCR engine. It reads bytes and returns words, nothing else."""

    name: str

    def read(self, image: bytes) -> OcrResult: ...


class CallLedger(Protocol):
    """Where calls are counted and logged. The database version writes `gateway_calls`."""

    def calls_made(self) -> int:
        """Calls that ran, refused ones excluded."""
        ...

    def record(self, record: CallRecord) -> None: ...


class CallCapReachedError(DomainError):
    """The configured call cap is used up, so no further engine call is made."""

    status_code = 503
    code = "call_cap_reached"


class EngineError(DomainError):
    """The engine failed. The engine's own message is never carried: it can hold a value."""

    status_code = 502
    code = "engine_error"


class RecordingMissingError(DomainError):
    """A recorded engine was asked for an image it has no recording for."""

    status_code = 500
    code = "recording_missing"
