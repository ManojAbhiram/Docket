"""Reading one file out of a multipart body under a byte cap (US-00-001, US-00-002, ADR-0008)."""

import pytest
from starlette.requests import Request
from starlette.types import Message

from app.api.uploads import MissingFileError, read_one_file
from app.domain.uploads import UploadTooLargeError

BOUNDARY = "docketboundary"


def multipart(*parts: tuple[str, str, str, bytes]) -> bytes:
    body = b""
    for field, filename, content_type, data in parts:
        body += (
            (
                f"--{BOUNDARY}\r\n"
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
            + data
            + b"\r\n"
        )
    return body + f"--{BOUNDARY}--\r\n".encode()


def request_with(body: bytes, *, chunk: int = 1024) -> Request:
    chunks = [body[i : i + chunk] for i in range(0, len(body), chunk)] or [b""]
    queue: list[Message] = [
        {"type": "http.request", "body": c, "more_body": index < len(chunks) - 1}
        for index, c in enumerate(chunks)
    ]

    async def receive() -> Message:
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode())],
    }
    return Request(scope, receive)


async def test_the_file_part_comes_back_with_its_name_type_and_bytes() -> None:
    body = multipart(("file", "scan.csv", "text/csv", b"a,b\n1,2\n"))

    upload = await read_one_file(request_with(body), cap=1_000)

    assert (upload.name, upload.content_type, upload.data) == (
        "scan.csv",
        "text/csv",
        b"a,b\n1,2\n",
    )


async def test_a_body_over_the_cap_is_refused_before_it_is_parsed() -> None:
    body = multipart(("file", "big.bin", "application/octet-stream", b"x" * 50_000))

    with pytest.raises(UploadTooLargeError):
        await read_one_file(request_with(body), cap=1_000)


async def test_a_request_without_a_part_named_file_is_refused() -> None:
    body = multipart(("other", "x.csv", "text/csv", b"data"))

    with pytest.raises(MissingFileError):
        await read_one_file(request_with(body), cap=1_000)
