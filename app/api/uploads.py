"""Read one file out of a multipart request without letting it grow past a cap (ADR-0008).

The routes that take a file declare no body parameter, so FastAPI parses nothing until the
session, role and CSRF checks have passed. The body is then counted while it streams in and refused
at the cap, and only a body inside the cap is handed to the multipart parser.
"""

from dataclasses import dataclass

from fastapi import Request
from starlette.datastructures import UploadFile
from starlette.types import Message

from app.core.errors import DomainError
from app.domain.uploads import read_capped

# Room for the multipart boundaries and part headers around the file itself.
_OVERHEAD = 8_192


class MissingFileError(DomainError):
    """The request had no part named `file`."""

    status_code = 422
    code = "validation_error"


@dataclass(frozen=True)
class UploadedFile:
    name: str
    content_type: str
    data: bytes


async def read_one_file(request: Request, *, cap: int) -> UploadedFile:
    """The part named `file`, at most `cap` bytes. Over the cap raises `UploadTooLargeError`."""
    body = await read_capped(request.stream(), cap=cap + _OVERHEAD)
    sent = False

    async def replay() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    form = await Request(request.scope, replay).form(max_files=1, max_fields=1)
    try:
        part = form.get("file")
        if not isinstance(part, UploadFile):
            msg = "send the file as a multipart part named file"
            raise MissingFileError(msg)
        return UploadedFile(
            name=part.filename or "", content_type=part.content_type or "", data=await part.read()
        )
    finally:
        await form.close()
