"""The runner scores every document and never drops one."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from app.gateway.types import OcrResult, OcrWord
from evals.extract_bench import run_documents, summarise
from evals.subsets import compare_ten, noisiest
from evals.tesseract_engine import words_from_data
from seed.dataset import DocumentRecord, build_dataset


class _Empty:
    name = "empty"

    def read(self, image: bytes) -> OcrResult:
        return OcrResult(words=())


class _Broken:
    name = "broken"

    def read(self, image: bytes) -> OcrResult:
        msg = "engine fell over"
        raise RuntimeError(msg)


class _Echo:
    """Prints back the id proof the dataset describes, laid out label then value on a row."""

    name = "echo"

    def __init__(self, rows: list[tuple[str, str]], title: str) -> None:
        self._rows = rows
        self._title = title

    def read(self, image: bytes) -> OcrResult:
        words = [OcrWord(self._title, 0.99, (10.0, 0.0, 300.0, 22.0))]
        for index, (label, value) in enumerate(self._rows):
            top = 60.0 + 40.0 * index
            words.append(OcrWord(label, 0.99, (10.0, top, 100.0, 22.0)))
            words.append(OcrWord(value, 0.99, (220.0, top, 100.0, 22.0)))
        return OcrResult(words=tuple(words))


def _level(doc: DocumentRecord) -> float:
    noise = doc.noise
    return noise.blur_radius + abs(noise.skew_degrees) / 5 + noise.shadow_strength


def _write_images(directory: Path, count: int) -> list[DocumentRecord]:
    docs = list(build_dataset().documents[:count])
    for doc in docs:
        (directory / doc.file_name).write_bytes(b"png")
    return docs


def test_an_engine_that_reads_nothing_scores_zero_but_keeps_all_documents(tmp_path: Path) -> None:
    docs = _write_images(tmp_path, 3)

    scores = run_documents(_Empty(), docs, tmp_path, cutoff=0.98)

    summary = summarise(scores, "empty", "all")
    assert len(scores) == 3
    assert summary["documents"] == 3
    assert summary["mean_field_accuracy"] == 0.0


def test_a_document_that_cannot_be_read_is_counted_as_a_read_error(tmp_path: Path) -> None:
    docs = _write_images(tmp_path, 2)

    scores = run_documents(_Broken(), docs, tmp_path, cutoff=0.98)

    summary = summarise(scores, "broken", "all")
    assert summary["read_errors"] == 2
    assert summary["documents"] == 2


def test_a_missing_image_file_is_a_read_error_not_a_crash(tmp_path: Path) -> None:
    docs = list(build_dataset().documents[:1])

    scores = run_documents(_Empty(), docs, tmp_path, cutoff=0.98)

    assert scores[0].predicted_type == "read_error"


def test_a_correct_read_scores_the_extracted_fields_and_the_type(tmp_path: Path) -> None:
    doc = next(d for d in build_dataset().documents if d.doc_type == "id_proof")
    (tmp_path / doc.file_name).write_bytes(b"png")
    engine = _Echo(
        [
            ("Name", doc.printed_name),
            ("Date of birth", doc.printed_dob),
            ("ID number", doc.printed_id_number or ""),
        ],
        "Identity card",
    )

    scores = run_documents(engine, [doc], tmp_path, cutoff=0.5)

    summary = summarise(scores, "echo", "all")
    assert summary["type_accuracy"] == 1.0
    assert summary["mean_field_accuracy"] == 1.0
    assert summary["failed_documents"] == []


def test_the_comparison_set_is_ten_documents_and_stable() -> None:
    docs = build_dataset().documents

    first, second = compare_ten(docs), compare_ten(docs)

    assert len(first) == 10
    assert [d.document_id for d in first] == [d.document_id for d in second]


def test_the_comparison_set_covers_every_document_type_present() -> None:
    docs = build_dataset().documents

    assert {d.doc_type for d in compare_ten(docs)} == {d.doc_type for d in docs}


def test_the_noisy_subset_takes_the_highest_combined_noise() -> None:
    docs = build_dataset().documents

    picked = noisiest(docs, 10)

    others = [d for d in docs if d not in picked]
    assert len(picked) == 10
    assert min(_level(d) for d in picked) >= max(_level(d) for d in others)


def test_tesseract_tokens_join_into_phrases_with_pixel_boxes_and_unit_confidence() -> None:
    data: dict[str, Sequence[object]] = {
        "text": ["Date", "of", " ", "birth", "10/12/2006"],
        "conf": [96.0, 94.0, -1.0, 90.0, 88.0],
        "left": [10, 50, 0, 80, 300],
        "top": [20, 20, 0, 20, 20],
        "width": [35, 20, 0, 50, 120],
        "height": [18, 18, 0, 18, 18],
        "block_num": [1, 1, 1, 1, 1],
        "par_num": [1, 1, 1, 1, 1],
        "line_num": [1, 1, 1, 1, 1],
    }

    words = words_from_data(data)

    assert [w.text for w in words] == ["Date of birth", "10/12/2006"]
    assert words[0].box == (10.0, 20.0, 120.0, 18.0)
    assert words[0].confidence == pytest.approx(0.933333)
    assert words[1].confidence == 0.88


def test_tesseract_tokens_on_different_lines_never_join() -> None:
    data: dict[str, Sequence[object]] = {
        "text": ["Name", "Latha"],
        "conf": [96.0, 96.0],
        "left": [10, 12],
        "top": [20, 50],
        "width": [40, 50],
        "height": [18, 18],
        "block_num": [1, 1],
        "par_num": [1, 1],
        "line_num": [1, 2],
    }

    words = words_from_data(data)

    assert [w.text for w in words] == ["Name", "Latha"]
