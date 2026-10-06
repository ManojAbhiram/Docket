"""The real PDF rasteriser: poppler through pdf2image, first page only, with a time limit.

Needs the `poppler-utils` system package. It is covered by the integration test, which runs where
poppler is installed; the unit tests use a fake `Rasteriser`.
"""

import io
import re

from app.domain.uploads import MAX_PIXELS, ImageTooLargeError, ImageUnreadableError

_DPI = 200
_TIMEOUT_SECONDS = 30
_POINTS_PER_INCH = 72
_PAGE_SIZE = re.compile(r"([\d.]+) x ([\d.]+) pts")


class PopplerRasteriser:
    """Rasterises page 1 of a PDF at 200 dpi. Nothing is read from or written to disk by name."""

    def first_page(self, pdf: bytes) -> bytes:
        from pdf2image import convert_from_bytes

        _refuse_a_page_that_is_too_big(pdf)
        pages = convert_from_bytes(
            pdf, dpi=_DPI, first_page=1, last_page=1, fmt="png", timeout=_TIMEOUT_SECONDS
        )
        buffer = io.BytesIO()
        pages[0].save(buffer, format="PNG")
        return buffer.getvalue()


def _refuse_a_page_that_is_too_big(pdf: bytes) -> None:
    """Read the first page's size from the PDF and refuse before poppler allocates the pixels."""
    from pdf2image import pdfinfo_from_bytes

    info = pdfinfo_from_bytes(pdf, timeout=_TIMEOUT_SECONDS)
    match = _PAGE_SIZE.search(str(info.get("Page size", "")))
    if match is None:
        msg = "the PDF page has no readable size"
        raise ImageUnreadableError(msg)
    scale = _DPI / _POINTS_PER_INCH
    if float(match.group(1)) * scale * float(match.group(2)) * scale > MAX_PIXELS:
        msg = "the PDF page is too large to rasterise"
        raise ImageTooLargeError(msg)
