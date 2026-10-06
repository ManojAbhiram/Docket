"""The version of an application a verifier saw (api/openapi.yaml: ETag and If-Match).

The version is the application's `updated_at`. Every decision moves it, so a decision made on a
page that has since been decided on, corrected or recomputed is refused instead of landing on top.
"""

from datetime import datetime

from app.core.errors import DomainError


class InvalidEtagError(DomainError):
    """The `If-Match` value is not a version this API made."""

    status_code = 422
    code = "validation_error"


def etag_for(updated_at: datetime) -> str:
    """The header value for an application last changed at `updated_at`."""
    return f'"{updated_at.isoformat()}"'


def parse_etag(header: str) -> datetime:
    """The instant an `If-Match` value names. Anything else, or a time with no zone, is refused."""
    try:
        parsed = datetime.fromisoformat(header.strip().strip('"'))
    except ValueError as exc:
        msg = "If-Match is not a version this API gave out"
        raise InvalidEtagError(msg) from exc
    if parsed.tzinfo is None:
        msg = "If-Match is not a version this API gave out"
        raise InvalidEtagError(msg)
    return parsed
