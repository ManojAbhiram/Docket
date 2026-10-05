"""The real PDF rasteriser: poppler through pdf2image, first page only, with a time limit.

Needs the `poppler-utils` system package. It is covered by the integration test, which runs where
poppler is installed; the unit tests use a fake `Rasteriser`.
"""

import io

_DPI = 200
_TIMEOUT_SECONDS = 30


class PopplerRasteriser:
    """Rasterises page 1 of a PDF at 200 dpi. Nothing is read from or written to disk by name."""

    def first_page(self, pdf: bytes) -> bytes:
        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(
            pdf, dpi=_DPI, first_page=1, last_page=1, fmt="png", timeout=_TIMEOUT_SECONDS
        )
        buffer = io.BytesIO()
        pages[0].save(buffer, format="PNG")
        return buffer.getvalue()
