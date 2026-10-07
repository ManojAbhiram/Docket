"""The runner scores every document and never drops one."""

from pathlib import Path

from app.gateway.types import OcrResult, OcrWord
from evals.extract_bench import run_documents, summarise
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
