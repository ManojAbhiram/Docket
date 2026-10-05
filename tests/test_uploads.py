"""Safe uploads (US-00-002, REQ-004 to REQ-006, ADR-0008, ADR-0010, threats T-10 to T-14).

Every test here fails until `app/domain/uploads.py` exists. Nothing is stored here: these are the
checks and the transformation applied to the bytes before they reach the database.
"""

import hashlib
from collections.abc import AsyncIterator

import cv2
import numpy as np
import pytest

from app.domain.uploads import (
    ImageTooLargeError,
    ImageUnreadableError,
    UnsupportedUploadError,
    UploadTooLargeError,
    check_declared_type,
    first_page_image,
    image_dimensions,
    normalise_image,
    read_capped,
    sha256_hex,
    sniff_type,
)

MIB = 1024 * 1024


def png(width: int, height: int) -> bytes:
    ok, encoded = cv2.imencode(".png", np.zeros((height, width, 3), dtype=np.uint8))
    assert ok
    return bytes(encoded.tobytes())


def jpeg(width: int, height: int) -> bytes:
    ok, encoded = cv2.imencode(".jpg", np.full((height, width, 3), 200, dtype=np.uint8))
    assert ok
    return bytes(encoded.tobytes())


def with_gps_exif(data: bytes) -> bytes:
    """Splice an EXIF segment with a GPS tag in behind the JPEG start marker."""
    body = b"Exif\x00\x00GPSLatitude 12.9716 N GPSLongitude 77.5946 E"
    segment = b"\xff\xe1" + (len(body) + 2).to_bytes(2, "big") + body
    return data[:2] + segment + data[2:]


async def chunks(count: int, size: int, seen: list[int]) -> AsyncIterator[bytes]:
    for index in range(count):
        seen.append(index)
        yield b"x" * size


# The size cap is enforced while the body streams, never after it is all in memory.


async def test_a_body_under_the_cap_is_read_whole() -> None:
    seen: list[int] = []

    data = await read_capped(chunks(3, MIB, seen), cap=8 * MIB)

    assert len(data) == 3 * MIB


async def test_a_body_over_the_cap_is_refused_and_the_rest_is_never_read() -> None:
    seen: list[int] = []

    with pytest.raises(UploadTooLargeError):
        await read_capped(chunks(20, MIB, seen), cap=3 * MIB)

    assert len(seen) == 4


# The type is read from the first bytes and must agree with the declared type (AC-US-00-002-2).


def test_the_type_is_sniffed_from_the_first_bytes() -> None:
    assert sniff_type(jpeg(10, 10)) == "image/jpeg"
    assert sniff_type(png(10, 10)) == "image/png"
    assert sniff_type(b"%PDF-1.7 rest of the file") == "application/pdf"
    assert sniff_type(b"hello, this is text") is None


def test_a_declared_type_that_matches_the_bytes_is_accepted() -> None:
    assert check_declared_type("image/jpeg", jpeg(10, 10)) == "image/jpeg"
    assert check_declared_type("application/pdf", b"%PDF-1.7 x") == "application/pdf"


@pytest.mark.parametrize(
    ("declared", "data"),
    [
        ("image/png", b"hello, this is text"),
        ("image/png", b"\xff\xd8\xff\xe0 pretending"),
        ("text/plain", b"\x89PNG\r\n\x1a\n rest"),
        ("application/zip", b"PK\x03\x04 rest"),
    ],
)
def test_a_declared_type_that_disagrees_with_the_bytes_or_is_not_allowed_is_refused(
    declared: str, data: bytes
) -> None:
    with pytest.raises(UnsupportedUploadError):
        check_declared_type(declared, data)


# Dimensions come from the header, so a huge image is refused before it is decoded.


def test_dimensions_are_read_from_the_header_of_a_png_and_a_jpeg() -> None:
    assert image_dimensions(png(300, 200)) == (300, 200)
    assert image_dimensions(jpeg(120, 80)) == (120, 80)


def test_bytes_that_are_not_an_image_have_no_dimensions() -> None:
    assert image_dimensions(b"not an image") is None


def test_an_image_over_the_pixel_cap_is_refused_before_decoding() -> None:
    header = b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR"
    header += (10_000).to_bytes(4, "big") + (10_000).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"

    with pytest.raises(ImageTooLargeError):
        normalise_image(header, "image/png", max_pixels=25_000_000)


# Normalising: one fixed form, no metadata, a bounded size (ADR-0010).


def test_the_longest_side_is_brought_down_to_the_cap_keeping_the_shape() -> None:
    stored = normalise_image(png(3000, 1500), "image/png", max_side=2000)

    assert (stored.width, stored.height) == (2000, 1000)


def test_a_small_image_is_not_enlarged() -> None:
    stored = normalise_image(png(400, 300), "image/png", max_side=2000)

    assert (stored.width, stored.height) == (400, 300)


def test_gps_and_other_exif_data_do_not_survive() -> None:
    original = with_gps_exif(jpeg(200, 100))
    assert b"GPSLatitude" in original

    stored = normalise_image(original, "image/jpeg")

    assert b"Exif" not in stored.data
    assert b"GPS" not in stored.data


def test_a_jpeg_stays_a_jpeg_and_a_png_stays_a_png() -> None:
    assert sniff_type(normalise_image(jpeg(50, 50), "image/jpeg").data) == "image/jpeg"
    assert sniff_type(normalise_image(png(50, 50), "image/png").data) == "image/png"


def test_bytes_that_look_like_a_jpeg_but_cannot_be_decoded_are_refused() -> None:
    broken = b"\xff\xd8\xff\xc0\x00\x0b\x08\x00\x10\x00\x10\x01\x01\x11\x00" + b"garbage" * 5

    with pytest.raises(ImageUnreadableError):
        normalise_image(broken, "image/jpeg")


def test_the_hash_is_of_the_bytes_that_were_uploaded() -> None:
    assert sha256_hex(b"abc") == hashlib.sha256(b"abc").hexdigest()


# A PDF becomes its first page, as an image. The original PDF is never stored or served (ADR-0007).


class FakeRasteriser:
    def __init__(self, page: bytes | None = None, fail: bool = False) -> None:
        self.page = page if page is not None else png(1654, 2339)
        self.fail = fail
        self.received: list[bytes] = []

    def first_page(self, pdf: bytes) -> bytes:
        self.received.append(pdf)
        if self.fail:
            msg = "poppler exploded with /private/path/name.pdf"
            raise RuntimeError(msg)
        return self.page


def test_a_pdf_is_rasterised_once_and_stored_as_a_jpeg_within_the_size_cap() -> None:
    rasteriser = FakeRasteriser(page=png(3000, 4000))

    stored = first_page_image(b"%PDF-1.7 many pages", rasteriser, max_side=2000)

    assert rasteriser.received == [b"%PDF-1.7 many pages"]
    assert sniff_type(stored.data) == "image/jpeg"
    assert stored.content_type == "image/jpeg"
    assert max(stored.width, stored.height) == 2000


def test_a_pdf_that_cannot_be_rasterised_is_refused_without_the_tool_message() -> None:
    with pytest.raises(ImageUnreadableError) as raised:
        first_page_image(b"%PDF-1.7 broken", FakeRasteriser(fail=True))

    assert "private" not in str(raised.value)
