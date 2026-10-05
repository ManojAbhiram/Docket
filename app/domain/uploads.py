"""Safe uploads: size, type, pixels, metadata and the first page of a PDF (US-00-002).

Nothing here stores anything. It checks the bytes and returns the form that is stored: one fixed
image, no metadata, a bounded size (ADR-0010). The client's file name is never an input.
"""

import hashlib
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Literal, Protocol

import cv2
import numpy as np

from app.core.errors import DomainError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 25_000_000
MAX_SIDE = 2000
JPEG_QUALITY = 85

ContentType = Literal["image/jpeg", "image/png", "application/pdf"]
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_HEADER_LENGTH = 24
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PDF_SIGNATURE = b"%PDF-"
_SOF_MARKERS = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


class UploadTooLargeError(DomainError):
    """The body is over the size cap."""

    status_code = 413
    code = "payload_too_large"


class UnsupportedUploadError(DomainError):
    """The type is not allowed, or the first bytes do not match the declared type."""

    status_code = 415
    code = "unsupported_media_type"


class ImageTooLargeError(DomainError):
    """The image has more pixels than the cap, so it is not decoded."""

    status_code = 422
    code = "validation_error"


class ImageUnreadableError(DomainError):
    """The bytes could not be read as an image, or the PDF could not be rasterised."""

    status_code = 422
    code = "validation_error"


@dataclass(frozen=True)
class StoredImage:
    """The image as it is stored: re-encoded, no metadata, at most `MAX_SIDE` on its long side."""

    content_type: Literal["image/jpeg", "image/png"]
    data: bytes
    width: int
    height: int


class Rasteriser(Protocol):
    """Turns the first page of a PDF into image bytes. The real one runs poppler."""

    def first_page(self, pdf: bytes) -> bytes: ...


async def read_capped(chunks: AsyncIterable[bytes], *, cap: int = MAX_BYTES) -> bytes:
    """Read a body while counting, and stop at the cap without reading the rest."""
    received = bytearray()
    async for chunk in chunks:
        received += chunk
        if len(received) > cap:
            msg = "the file is over the size cap"
            raise UploadTooLargeError(msg)
    return bytes(received)


def sniff_type(data: bytes) -> ContentType | None:
    """The type the first bytes say, or None for anything else."""
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_PDF_SIGNATURE):
        return "application/pdf"
    return None


def check_declared_type(declared: str, data: bytes) -> ContentType:
    """The declared type and the first bytes must name the same allowed type."""
    sniffed = sniff_type(data)
    if sniffed is None or sniffed != declared:
        msg = "the file must be a JPG, PNG or PDF, and its content must match its type"
        raise UnsupportedUploadError(msg)
    return sniffed


def sha256_hex(data: bytes) -> str:
    """Hash of the uploaded bytes, to spot the same file sent twice."""
    return hashlib.sha256(data).hexdigest()


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Width and height from the header of a PNG or JPEG, without decoding the pixels."""
    if data.startswith(_PNG_SIGNATURE) and len(data) >= _PNG_HEADER_LENGTH:
        return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
    if data.startswith(_JPEG_SIGNATURE):
        return _jpeg_dimensions(data)
    return None


def normalise_image(
    data: bytes,
    content_type: Literal["image/jpeg", "image/png"],
    *,
    max_side: int = MAX_SIDE,
    max_pixels: int = MAX_PIXELS,
) -> StoredImage:
    """Decode, bring the long side down to `max_side`, and re-encode without any metadata."""
    dimensions = image_dimensions(data)
    if dimensions is None:
        msg = "the file is not a readable image"
        raise ImageUnreadableError(msg)
    if dimensions[0] * dimensions[1] > max_pixels:
        msg = "the image has too many pixels"
        raise ImageTooLargeError(msg)
    decoded: object = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if not isinstance(decoded, np.ndarray):
        msg = "the file is not a readable image"
        raise ImageUnreadableError(msg)
    pixels = np.asarray(decoded)
    height, width = pixels.shape[:2]
    longest = max(height, width)
    if longest > max_side:
        scale = max_side / longest
        pixels = np.asarray(
            cv2.resize(
                pixels,
                (round(width * scale), round(height * scale)),
                interpolation=cv2.INTER_AREA,
            )
        )
        height, width = pixels.shape[:2]
    if content_type == "image/png":
        ok, encoded = cv2.imencode(".png", pixels)
    else:
        ok, encoded = cv2.imencode(".jpg", pixels, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        msg = "the image could not be re-encoded"
        raise ImageUnreadableError(msg)
    return StoredImage(content_type, bytes(encoded.tobytes()), width, height)


def first_page_image(
    pdf: bytes, rasteriser: Rasteriser, *, max_side: int = MAX_SIDE
) -> StoredImage:
    """The first page of a PDF as a JPEG. The PDF itself is not kept (ADR-0007)."""
    try:
        page = rasteriser.first_page(pdf)
    except Exception as exc:
        msg = "the PDF could not be read"
        raise ImageUnreadableError(msg) from exc
    return normalise_image(page, "image/jpeg", max_side=max_side)


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    position = 2
    while position + 4 <= len(data):
        if data[position] != 0xFF:
            return None
        marker = data[position + 1]
        if marker == 0xFF:
            position += 1
            continue
        if marker in _SOF_MARKERS:
            if position + 9 > len(data):
                return None
            height = int.from_bytes(data[position + 5 : position + 7], "big")
            width = int.from_bytes(data[position + 7 : position + 9], "big")
            return (width, height)
        position += 2 + int.from_bytes(data[position + 2 : position + 4], "big")
    return None
