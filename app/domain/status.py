"""The status of an application, computed from evidence (US-00-005, REQ-017 to REQ-020).

Needs review beats Missing documents beats Verified. A verifier's approval stands in for a field
that did not match, never for a document that was not uploaded.
"""

from dataclasses import dataclass
from typing import Literal

from app.core.errors import ConflictError

Status = Literal["verified", "needs_review", "missing_documents"]
DocumentState = Literal["uploaded", "processing", "read", "failed"]

REQUIRED_TYPES = frozenset({"10th_marksheet", "12th_marksheet", "id_proof"})


@dataclass(frozen=True)
class FieldFacts:
    """How one extracted field compared. `match` is None when the field was skipped."""

    match: bool | None = True
    needs_review: bool = False


@dataclass(frozen=True)
class DocumentFacts:
    """What the status needs to know about one document."""

    doc_type: str | None
    state: DocumentState
    fields: tuple[FieldFacts, ...] = ()


class StatusNotAllowedError(ConflictError):
    """A status was asked for that the evidence does not give."""

    code = "status_not_allowed"


class VerificationNotAllowedError(StatusNotAllowedError):
    """Verified was asked for without every field matching or a verifier's approval."""

    code = "verification_not_allowed"


def compute_status(documents: list[DocumentFacts], *, approved: bool = False) -> Status:
    """One of the three statuses. `approved` is a verifier approval newer than the evidence."""
    present = {
        d.doc_type for d in documents if d.state == "read" and d.doc_type not in (None, "unknown")
    }
    waiting = any(d.state in ("uploaded", "processing") for d in documents)
    # An upload nobody has read yet is evidence still to come, so it holds back Verified.
    missing = waiting or not present >= REQUIRED_TYPES
    if approved:
        return "missing_documents" if missing else "verified"
    if any(_needs_a_person(d) for d in documents):
        return "needs_review"
    return "missing_documents" if missing else "verified"


def assert_can_verify(documents: list[DocumentFacts], *, approved: bool) -> None:
    """Refuse a direct request for Verified that the evidence does not support (REQ-019)."""
    if compute_status(documents, approved=approved) != "verified":
        msg = "the application cannot be verified from this evidence"
        raise VerificationNotAllowedError(msg)


def _needs_a_person(document: DocumentFacts) -> bool:
    return (
        document.state == "failed"
        or document.doc_type == "unknown"
        or any(f.needs_review or f.match is False for f in document.fields)
    )
