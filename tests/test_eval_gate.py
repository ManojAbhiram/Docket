"""The gate compares a replayed score with the accepted baseline."""

import hashlib
from pathlib import Path

import pytest

from app.gateway.engines import RecordedEngine
from app.gateway.types import OcrResult, OcrWord
from evals.extraction_report import render
from evals.gate_check import check, parse_gate
from evals.recordings import record
from seed.dataset import build_dataset

GATE = "delta: 0.02\nsubset: all\naccepted_baseline: 0.97\n"


class _Fixed:
    name = "fixed"

    def read(self, image: bytes) -> OcrResult:
        return OcrResult(words=(OcrWord("Name", 0.97, (1.0, 2.0, 3.0, 4.0)),))


def test_gate_parses_flat_key_value_lines_and_ignores_comments() -> None:
    text = "# note\nmetric: mean (x)\ndelta: 0.02  # absolute\naccepted_baseline: none\n"

    gate = parse_gate(text)

    assert gate["delta"] == "0.02"
    assert gate["accepted_baseline"] == "none"


def test_a_score_within_delta_of_the_baseline_passes() -> None:
    ok, _ = check({"mean_field_accuracy": 0.955, "documents": 30}, parse_gate(GATE))

    assert ok


def test_a_score_more_than_delta_below_fails_with_the_numbers_in_the_message() -> None:
    ok, message = check({"mean_field_accuracy": 0.90, "documents": 30}, parse_gate(GATE))

    assert not ok
    assert "0.9" in message
    assert "0.97" in message


def test_no_accepted_baseline_is_reported_not_passed() -> None:
    gate = parse_gate("delta: 0.02\naccepted_baseline: none\n")

    ok, message = check({"mean_field_accuracy": 1.0, "documents": 30}, gate)

    assert not ok
    assert "no accepted baseline" in message


def test_fewer_documents_than_the_subset_fails() -> None:
    ok, message = check({"mean_field_accuracy": 1.0, "documents": 12}, parse_gate(GATE))

    assert not ok
    assert "30" in message


def test_a_replay_with_read_errors_fails_even_when_the_score_holds() -> None:
    summary = {"mean_field_accuracy": 0.99, "documents": 30, "read_errors": 1}

    ok, message = check(summary, parse_gate(GATE))

    assert not ok
    assert "read error" in message


def test_a_recording_replays_the_words_it_was_made_from(tmp_path: Path) -> None:
    docs = list(build_dataset().documents[:2])
    for doc in docs:
        (tmp_path / doc.file_name).write_bytes(doc.document_id.encode())
    out = tmp_path / "rec.json"

    written = record(_Fixed(), docs, tmp_path, out)

    replay = RecordedEngine(out).read(docs[0].document_id.encode())
    assert written == 2
    assert replay.words == (OcrWord("Name", 0.97, (1.0, 2.0, 3.0, 4.0)),)


def test_a_recording_is_keyed_by_the_sha256_of_the_image(tmp_path: Path) -> None:
    doc = build_dataset().documents[0]
    (tmp_path / doc.file_name).write_bytes(b"pixels")
    out = tmp_path / "rec.json"

    record(_Fixed(), [doc], tmp_path, out)

    assert hashlib.sha256(b"pixels").hexdigest() in out.read_text(encoding="utf-8")


def test_recording_a_document_that_cannot_be_read_stops_instead_of_skipping_it(
    tmp_path: Path,
) -> None:
    doc = build_dataset().documents[0]

    with pytest.raises(FileNotFoundError):
        record(_Fixed(), [doc], tmp_path, tmp_path / "rec.json")


def _summary(engine: str, subset: str, mean: float, documents: int = 30) -> dict[str, object]:
    return {
        "engine": engine,
        "subset": subset,
        "documents": documents,
        "read_errors": 2,
        "type_accuracy": 0.9333,
        "field_accuracy": {"name": 0.8123, "marks": mean},
        "by_doc_type": {"id_proof": {"name": 0.7777}},
        "mean_field_accuracy": mean,
        "failed_documents": ["SYN-DOC-001"],
    }


def test_the_report_says_so_when_there_are_no_summaries() -> None:
    assert "no summaries; run make eval-extract" in render([])


def test_the_report_carries_the_numbers_it_was_given() -> None:
    text = render([_summary("rapidocr", "all", 0.9123)])

    assert "0.9123" in text
    assert "0.8123" in text
    assert "0.7777" in text
    assert "0.9333" in text
    assert "Read errors" in text


def test_the_report_puts_two_engines_side_by_side_on_the_comparison_subset() -> None:
    summaries = [
        _summary("rapidocr", "compare10", 0.9511, documents=10),
        _summary("tesseract", "compare10", 0.2022, documents=10),
    ]

    text = render(summaries)

    assert "0.9511" in text
    assert "0.2022" in text
    assert "Comparison on 10 documents" in text


def test_a_perfect_score_brings_the_clean_page_caveat() -> None:
    assert "cannot separate" in render([_summary("rapidocr", "all", 1.0)])


def test_a_score_below_perfect_does_not_claim_the_set_cannot_separate_engines() -> None:
    assert "cannot separate" not in render([_summary("rapidocr", "all", 0.95)])
