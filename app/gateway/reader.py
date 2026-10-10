"""The reader the document worker calls: the gateway with its engine, ledger and cap chosen.

The engine is picked by configured name, so nothing that reads a document changes when the engine
does (REQ-031). `rapidocr` runs in a child process the loop can kill (ADR-0011); `recorded` replays
saved answers and is what the tests use.
"""

from app.core.config import Settings
from app.domain.classify import classify
from app.domain.extract import extract_fields
from app.domain.processing import ProcessedDocument
from app.gateway.core import read_document
from app.gateway.engines import build_engine
from app.gateway.process import ProcessEngine
from app.gateway.rapidocr_engine import ENGINE_NAME, make_engine, release
from app.gateway.types import CallLedger, Engine

_RECORDED_VERSION = "recorded-1"


class GatewayReader:
    """One call to `read_document` per image, with the cap and the ledger fixed up front."""

    def __init__(self, engine: Engine, ledger: CallLedger, cap: int) -> None:
        self.engine = engine
        self._ledger = ledger
        self._cap = cap

    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument:
        """Normalize OCR into the shared document result at the gateway boundary."""
        result = read_document(image, engine=self.engine, ledger=self._ledger, cap=self._cap)
        doc_type = classify(result.words)
        fields = extract_fields(result.words, doc_type, confidence_cutoff=confidence_cutoff)
        return ProcessedDocument(doc_type=doc_type, fields=fields)

    def close(self) -> None:
        if isinstance(self.engine, ProcessEngine):
            self.engine.close()


def engine_version(settings: Settings) -> str:
    """What `gateway_calls.engine_version` records for the configured engine."""
    return release() if settings.gateway_engine == ENGINE_NAME else _RECORDED_VERSION


def build_reader(settings: Settings, ledger: CallLedger) -> GatewayReader:
    """The reader for the configured engine. An unknown name or a missing file stops start-up."""
    engine: Engine
    if settings.gateway_engine == ENGINE_NAME:
        engine = ProcessEngine(
            make_engine,
            name=ENGINE_NAME,
            read_timeout=settings.read_timeout_seconds,
            recycle_after=settings.engine_recycle_after,
        )
    elif settings.gateway_engine == "recorded":
        if settings.gateway_recording is None:
            msg = "GATEWAY_RECORDING must name the recording file for the recorded engine"
            raise ValueError(msg)
        engine = build_engine("recorded", recording=settings.gateway_recording)
    else:
        msg = f"unknown engine {settings.gateway_engine}"
        raise ValueError(msg)
    return GatewayReader(engine, ledger, settings.gateway_call_cap)
