"""The real poppler rasteriser on a real PDF (US-00-002, AC-US-00-002-3).

Needs the `poppler-utils` system package (`sudo apt install poppler-utils`) and `pdf2image`.
Run with `make test-integration`. The unit tests use a fake rasteriser.
"""

import pytest

from app.domain.pdf import PopplerRasteriser
from app.domain.uploads import ImageTooLargeError, first_page_image, sniff_type

pytestmark = pytest.mark.integration

TWO_PAGE_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] >> endobj
4 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] >> endobj
trailer << /Root 1 0 R /Size 5 >>
%%EOF
"""


def test_only_the_first_page_is_rasterised_and_stored_as_a_jpeg() -> None:
    stored = first_page_image(TWO_PAGE_PDF, PopplerRasteriser())

    assert sniff_type(stored.data) == "image/jpeg"
    assert stored.width > stored.height


def test_a_pdf_whose_first_page_would_be_too_many_pixels_is_refused_before_it_is_rasterised() -> (
    None
):
    huge_page = TWO_PAGE_PDF.replace(b"300 200", b"20000 20000")

    with pytest.raises(ImageTooLargeError):
        PopplerRasteriser().first_page(huge_page)


def test_a_pdf_of_ordinary_page_size_is_still_rasterised() -> None:
    assert sniff_type(PopplerRasteriser().first_page(TWO_PAGE_PDF)) == "image/png"
