"""A verifier's decision and the log entry it leaves (US-00-007, REQ-023 to REQ-027)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

DecisionAction = Literal["approve", "correct", "reject"]


class DecisionRequest(BaseModel):
    """What a verifier sends. A reject needs a reason, a correct needs the field and the value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: DecisionAction
    reason: str | None = Field(default=None, max_length=1000)
    extracted_field_id: int | None = None
    new_value: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _action_has_what_it_needs(self) -> Self:
        if self.action == "reject" and not (self.reason and self.reason.strip()):
            msg = "a rejection needs a reason"
            raise ValueError(msg)
        if self.action == "correct" and (self.extracted_field_id is None or self.new_value is None):
            msg = "a correction needs the field and the new value"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class DecisionLogEntry:
    """One line of the decision log: who, when, what and why. Never changed after it is made."""

    decided_by: UUID
    decided_at: datetime
    action: DecisionAction
    reason: str | None
    extracted_field_id: int | None
    old_value: str | None
    new_value: str | None


def log_entry(
    request: DecisionRequest,
    *,
    decided_by: UUID,
    decided_at: datetime,
    old_value: str | None = None,
) -> DecisionLogEntry:
    """Build the log entry for a decision. The time must carry a timezone."""
    if decided_at.tzinfo is None:
        msg = "decided_at needs a timezone"
        raise ValueError(msg)
    return DecisionLogEntry(
        decided_by=decided_by,
        decided_at=decided_at,
        action=request.action,
        reason=request.reason,
        extracted_field_id=request.extracted_field_id,
        old_value=old_value,
        new_value=request.new_value,
    )
