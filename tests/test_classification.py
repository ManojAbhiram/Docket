"""Name the type of a document from what was read at the top of it (US-00-003, REQ-009).

Every test here fails until `app/domain/classify.py` exists. The titles are the ones the synthetic
pages print (`seed/pages.py`).
"""

import pytest

from app.domain.classify import classify
from app.gateway import OcrWord


def words(*lines: str) -> list[OcrWord]:
    return [
        OcrWord(text=line, confidence=0.99, box=(10.0, 10.0 + 30.0 * index, 400.0, 22.0))
        for index, line in enumerate(lines)
    ]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Secondary School Examination, Class X: Statement of Marks", "10th_marksheet"),
        ("Senior School Certificate Examination, Class XII: Statement of Marks", "12th_marksheet"),
        ("Identity Card", "id_proof"),
        ("School Transfer Certificate", "transfer_certificate"),
    ],
)
def test_each_document_type_is_named_from_its_title(title: str, expected: str) -> None:
    assert classify(words(title, "Name", "Latha Sharma")) == expected


def test_class_xii_is_not_mistaken_for_class_x() -> None:
    assert classify(words("Class XII: Statement of Marks")) == "12th_marksheet"


def test_case_and_spacing_do_not_matter() -> None:
    assert classify(words("  IDENTITY   CARD ")) == "id_proof"


def test_a_title_split_across_several_words_is_still_read() -> None:
    split = words("Secondary School", "Examination, Class X:", "Statement of Marks")

    assert classify(split) == "10th_marksheet"


def test_a_page_with_no_known_title_is_unknown_and_goes_to_review() -> None:
    assert classify(words("Electricity bill", "Total due")) == "unknown"


def test_a_page_with_no_text_is_unknown() -> None:
    assert classify([]) == "unknown"
