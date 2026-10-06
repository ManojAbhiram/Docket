"""Opaque cursors for lists ordered by `(updated_at, id)` descending (api/openapi.yaml: Cursor)."""

import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from app.core.errors import DomainError


class InvalidCursorError(DomainError):
    """The cursor was not made by this API, or was changed on the way."""

    status_code = 422
    code = "validation_error"


def encode_cursor(updated_at: datetime, row_id: UUID) -> str:
    raw = json.dumps({"u": updated_at.isoformat(), "i": str(row_id)}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(token: str) -> tuple[datetime, UUID]:
    try:
        padded = token + "=" * (-len(token) % 4)
        parsed = json.loads(base64.urlsafe_b64decode(padded.encode()))
        return datetime.fromisoformat(parsed["u"]), UUID(parsed["i"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        msg = "the cursor is not valid"
        raise InvalidCursorError(msg) from exc
