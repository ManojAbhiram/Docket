"""structlog configuration. Stdlib loggers (uvicorn, sqlalchemy) share the formatter."""

import logging
import sys
from typing import TextIO

import structlog
from structlog.typing import EventDict, Processor

from app.core.config import LogFormat, LogLevel

REDACTED = "[redacted]"
# Personal data of applicants (minors) and credentials. A field with one of these names is never
# written, whatever the caller meant: log the id of the record instead.
_REDACTED_KEYS = frozenset(
    {
        "name",
        "full_name",
        "father_name",
        "date_of_birth",
        "dob",
        "roll_number",
        "application_ref",
        "marks",
        "category",
        "value",
        "old_value",
        "new_value",
        "reason",
        "file_name",
        "filename",
        "email",
        "phone",
        "password",
        "token",
        "authorization",
        "cookie",
        "secret",
    }
)


def redact_personal_data(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
    """Replace the value of every personal or secret field, at any depth, with a marker."""
    return {key: _redact(key, value) for key, value in event_dict.items()}


def _redact(key: str, value: object) -> object:
    if key.casefold() in _REDACTED_KEYS:
        return REDACTED
    if isinstance(value, dict):
        return {inner_key: _redact(str(inner_key), inner) for inner_key, inner in value.items()}
    if isinstance(value, list):
        return [_redact("", item) for item in value]
    return value


class _CurrentStdoutHandler(logging.StreamHandler[TextIO]):
    """Write to whatever `sys.stdout` is at emit time.

    A handler bound to the stream that existed at configuration time writes to a
    closed file once a test runner or a supervisor swaps stdout.
    """

    @property
    def stream(self) -> TextIO:
        return sys.stdout

    @stream.setter
    def stream(self, value: TextIO) -> None:
        """Ignore the stream the base class constructor offers."""


def configure_logging(level: LogLevel, fmt: LogFormat) -> None:
    """Route every log line through structlog with the request context merged in."""
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        redact_personal_data,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
        foreign_pre_chain=shared,
    )
    handler = _CurrentStdoutHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    # The request-id middleware logs every request; uvicorn's access log would duplicate it.
    logging.getLogger("uvicorn.access").disabled = True
    # An HTTP client logs the full URL of every call at INFO, query string included, which can
    # carry a name or an email. Keep it to warnings and above (threat T-13).
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
