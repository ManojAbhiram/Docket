"""The shared extraction result passed from the gateway to document persistence."""

from dataclasses import dataclass

from app.domain.extract import ExtractedField


@dataclass(frozen=True)
class ProcessedDocument:
    """A classified document and the source fields extracted by either reader."""

    doc_type: str
    fields: tuple[ExtractedField, ...]
    # Which engine read it, and why a requested engine was not used (a safe reason code).
    engine: str | None = None
    fallback_reason: str | None = None
