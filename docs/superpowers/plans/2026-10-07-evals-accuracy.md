# Evals: real extraction accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report field-level extraction accuracy on the 30 labelled synthetic documents, compare the chosen engine with the runner-up on 10 of them, and gate CI on a replayed run that makes no live engine call.

**Architecture:** A pure scorer compares the app's real extraction (`classify` then `extract_fields`) with the `printed_*` labels of each `DocumentRecord`. A runner feeds it OCR words from any `Engine` (`RapidOcrEngine` live, a new `TesseractEngine` for the comparison, `RecordedEngine` for CI). A recorder saves each live engine's words keyed by the image SHA-256, in the format `RecordedEngine` already reads, so CI replays them. A small gate script compares a replayed score with `evals/ocr/gate.yaml`.

**Tech Stack:** Python 3.14, uv, pytest, pytesseract (already an eval-only dependency in `evals/requirements-ocr.txt`), the app's own `app.gateway`, `app.domain.extract`, `app.domain.classify`, `seed.dataset`.

**Spec:** `docs/superpowers/specs/2026-10-07-docket-completion-design.md` (Piece 2: evals)

## Global Constraints

- Zero cost, no paid API, no card (`CONSTRAINTS.md` section 1). CI makes no live engine call (`CONSTRAINTS.md` section 3.1).
- Synthetic data only. The 30 documents are `data/seed/png/*.png`, labelled by `seed.dataset.build_dataset().documents`.
- No new dependency in `pyproject.toml` (AGENTS.md rule 7). `gate.yaml` is flat `key: value` lines: parse it by hand, do not import yaml.
- Accepting a baseline in `evals/ocr/gate.yaml` is a deliberate human edit (the file says so). This plan prepares the numbers and the exact edit and never sets `accepted_baseline` itself.
- Gate: `delta: 0.02` absolute drop, `subset: all` (from `gate.yaml`).
- The extraction confidence cutoff is `Settings.review_confidence_cutoff` (default 0.9804, `app/core/config.py:45`). The eval uses the same default, not a copy of the number: read it from `Settings(_env_file=None).review_confidence_cutoff`.
- Python 3.14, `except A, B:` without parentheses is valid. Conventional commits ending `[NOTASK-8]`, no AI attribution, no em dashes, never push.
- Gate: `make check`. New eval modules live under `evals/` and are covered by `make test` (check `pyproject.toml` coverage settings before assuming; if `evals/` is excluded from coverage, tests still run).

## Review Focus

- A document the runner skips or fails to read must be counted as all fields wrong and listed, never silently dropped (the denominator stays 30). Pinned in Task 2.
- Label names and extractor names differ (`printed_name` vs field `name`, `printed_id_number` vs `document_number`, marks per subject). A mismatch would score 0 or 100 for the wrong reason. Pinned in Task 1.
- The runner-up must be scored on the same bytes as the chosen engine, with the same cutoff. Pinned in Task 3.
- A replay with a missing recording must fail the gate, not pass with a smaller sample (`RecordingMissingError`). Pinned in Task 4.
- Near-perfect scores on clean pages can hide weakness; the noisy subset must be chosen by the stored noise values, not by hand. Pinned in Task 3.
- The ID proof and the transfer certificate both exist in the data; the transfer certificate is a stretch type. Report it separately and do not count it in the headline if the app does not treat it as supported. Pinned in Task 2.

## File Structure

| File | Responsibility |
| --- | --- |
| `evals/extraction.py` (create) | Pure scoring: expected values from a `DocumentRecord`, comparison with `ExtractedField`s |
| `evals/extract_bench.py` (create) | Run an `Engine` over documents, write a summary JSON, CLI |
| `evals/tesseract_engine.py` (create) | `Engine` adapter over pytesseract for the comparison |
| `evals/recordings.py` (create) | Save and load recordings in `RecordedEngine` format |
| `evals/gate_check.py` (create) | Compare a summary with `gate.yaml` |
| `evals/extraction_report.py` (create) | Write `docs/testing/extraction-accuracy.md` from the summaries |
| `tests/test_eval_extraction.py`, `tests/test_eval_runner.py`, `tests/test_eval_gate.py` (create) | No live engine |
| `Makefile`, `.github/workflows/ci.yml` (modify) | `eval-extract`, `eval-gate`; CI job |

---

### Task 1: The extraction scorer

**Files:**
- Create: `evals/extraction.py`
- Test: `tests/test_eval_extraction.py`

**Interfaces:**
- Consumes: `seed.dataset.DocumentRecord`, `app.domain.extract.ExtractedField`.
- Produces: `expected_values(doc: DocumentRecord) -> dict[tuple[str, str | None], str]` (key is `(field_name, subject)`), `score_document(doc: DocumentRecord, doc_type: str, fields: Sequence[ExtractedField]) -> DocumentScore`, `DocumentScore(document_id: str, doc_type: str, predicted_type: str, type_ok: bool, correct: dict[tuple[str, str | None], bool])`.

- [ ] **Step 1: Read first.** Read `seed/dataset.py:128-160` and `app/domain/extract.py:37-62, 75-115`. Confirm that for a marksheet the extractor emits one field per subject with `field_name == "marks"` and `subject` set, that dates are returned as printed text, and which `field_name`s each type carries (`app/domain/match.py:10-20`). If any of this differs from the code below, follow the code you read and say so in your report.

- [ ] **Step 2: Write the failing tests**

```python
"""The extraction scorer compares what the app extracts with what a document prints."""

from app.domain.extract import ExtractedField
from evals.extraction import expected_values, score_document
from seed.dataset import build_dataset


def _field(name: str, value: str, subject: str | None = None) -> ExtractedField:
    return ExtractedField(
        field_name=name, subject=subject, value=value, confidence=0.99,
        box=None, needs_review=False, review_reason=None,
    )


def _doc(doc_type: str):
    return next(d for d in build_dataset().documents if d.doc_type == doc_type)


def test_a_marksheet_expects_every_printed_value_per_field_and_subject() -> None:
    doc = _doc("10th_marksheet")
    expected = expected_values(doc)
    assert expected[("name", None)] == doc.printed_name
    assert expected[("roll_number", None)] == doc.printed_roll_number
    for subject, mark in (doc.printed_marks or {}).items():
        assert expected[("marks", subject)] == str(mark)


def test_an_id_proof_expects_its_document_number_and_no_marks() -> None:
    doc = _doc("id_proof")
    expected = expected_values(doc)
    assert expected[("document_number", None)] == doc.printed_id_number
    assert not any(name == "marks" for name, _ in expected)


def test_a_perfect_extraction_scores_every_field_correct() -> None:
    doc = _doc("10th_marksheet")
    fields = [_field(n, v, s) for (n, s), v in expected_values(doc).items()]
    score = score_document(doc, "10th_marksheet", fields)
    assert score.type_ok and all(score.correct.values())


def test_names_are_compared_ignoring_case_and_word_order() -> None:
    doc = _doc("10th_marksheet")
    fields = [_field(n, v, s) for (n, s), v in expected_values(doc).items()]
    swapped = [
        _field("name", " ".join(reversed(doc.printed_name.upper().split())))
        if f.field_name == "name" else f
        for f in fields
    ]
    assert score_document(doc, "10th_marksheet", swapped).correct[("name", None)]


def test_a_missing_field_and_a_wrong_value_are_both_incorrect() -> None:
    doc = _doc("10th_marksheet")
    fields = [_field(n, v, s) for (n, s), v in expected_values(doc).items()]
    fields = [f for f in fields if f.field_name != "board"]
    fields = [_field("roll_number", "WRONG") if f.field_name == "roll_number" else f for f in fields]
    score = score_document(doc, "10th_marksheet", fields)
    assert score.correct[("board", None)] is False
    assert score.correct[("roll_number", None)] is False


def test_a_wrong_document_type_is_recorded_and_still_scores_fields() -> None:
    doc = _doc("10th_marksheet")
    score = score_document(doc, "unknown", [])
    assert score.type_ok is False and score.predicted_type == "unknown"
    assert not any(score.correct.values())
```

- [ ] **Step 3: Run to see it fail.** `uv run pytest tests/test_eval_extraction.py -q 2>&1 | tail -8` (expect `ModuleNotFoundError: evals.extraction`).

- [ ] **Step 4: Implement**

```python
"""Score the app's real extraction against what a synthetic document prints.

Unlike evals/scoring.py, which only checks that a printed value appears somewhere in the OCR
text, this compares the value the extractor assigned to each field. Names ignore case and word
order, dates and roll numbers ignore case and spacing, marks compare as integers.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.extract import ExtractedField
from seed.dataset import DocumentRecord

type Key = tuple[str, str | None]


@dataclass(frozen=True)
class DocumentScore:
    document_id: str
    doc_type: str
    predicted_type: str
    type_ok: bool
    correct: dict[Key, bool]


def expected_values(doc: DocumentRecord) -> dict[Key, str]:
    """What the document prints, keyed the way the extractor names its fields."""
    expected: dict[Key, str] = {("name", None): doc.printed_name, ("dob", None): doc.printed_dob}
    optional = {
        "father_name": doc.printed_father_name,
        "board": doc.printed_board,
        "roll_number": doc.printed_roll_number,
        "document_number": doc.printed_id_number,
    }
    for name, value in optional.items():
        if value is not None:
            expected[(name, None)] = value
    for subject, mark in (doc.printed_marks or {}).items():
        expected[("marks", subject)] = str(mark)
    return expected


def score_document(
    doc: DocumentRecord, predicted_type: str, fields: Sequence[ExtractedField]
) -> DocumentScore:
    """One boolean per expected field. A field the extractor did not return is incorrect."""
    found = {(f.field_name, f.subject): f.value for f in fields}
    correct = {
        key: key in found and _same(key[0], found[key], value)
        for key, value in expected_values(doc).items()
    }
    return DocumentScore(
        document_id=doc.document_id,
        doc_type=doc.doc_type,
        predicted_type=predicted_type,
        type_ok=predicted_type == doc.doc_type,
        correct=correct,
    )


def _same(name: str, got: str, want: str) -> bool:
    if name in {"name", "father_name"}:
        return sorted(got.casefold().split()) == sorted(want.casefold().split())
    if name == "marks":
        return got.strip().isdigit() and int(got) == int(want)
    return _squash(got) == _squash(want)


def _squash(text: str) -> str:
    return re.sub(r"[\s/.\-]", "", text).casefold()
```

If Step 1 shows the extractor names a field differently (for example `dob` returned in another format), fix `expected_values` or `_same` to match and keep the tests.

- [ ] **Step 5: Run to see it pass, then `make check 2>&1 | tail -4`.**

- [ ] **Step 6: Commit**

```bash
git add evals/extraction.py tests/test_eval_extraction.py
git commit -m "feat(evals): score the app's extraction against the printed labels [NOTASK-8]"
```

---

### Task 2: The runner and the summary

**Files:**
- Create: `evals/extract_bench.py`
- Modify: `Makefile` (add target)
- Test: `tests/test_eval_runner.py`

**Interfaces:**
- Consumes: Task 1; `app.gateway.types.Engine`, `OcrResult`, `OcrWord`; `app.domain.classify.classify`; `app.domain.extract.extract_fields`.
- Produces: `run_documents(engine: Engine, docs: Sequence[DocumentRecord], png_dir: Path, cutoff: float) -> list[DocumentScore]` (a document that cannot be read becomes a score with every field incorrect and `predicted_type="read_error"`), `summarise(scores: Sequence[DocumentScore], engine_name: str, subset: str) -> dict[str, object]` with keys `engine`, `subset`, `documents`, `read_errors`, `type_accuracy`, `field_accuracy` (by field name), `by_doc_type` (field accuracy per type), `mean_field_accuracy`, and `main()` for `python -m evals.extract_bench`.

- [ ] **Step 1: Write the failing tests** (no live engine: a fake `Engine` returns words laid out like a marksheet; build them with the same helper words other tests use, see `tests/process_fakes.py` and `tests/test_extraction.py` and copy their word-building helper).

```python
"""The runner scores every document and never drops one."""

from pathlib import Path

from app.gateway.types import OcrResult
from evals.extract_bench import run_documents, summarise
from seed.dataset import build_dataset


class _Empty:
    name = "empty"

    def read(self, image: bytes) -> OcrResult:
        return OcrResult(words=())


class _Broken:
    name = "broken"

    def read(self, image: bytes) -> OcrResult:
        raise RuntimeError("engine fell over")


def test_an_engine_that_reads_nothing_scores_zero_but_keeps_all_documents(tmp_path: Path) -> None:
    docs = build_dataset().documents[:3]
    for doc in docs:
        (tmp_path / doc.file_name).write_bytes(b"png")
    scores = run_documents(_Empty(), docs, tmp_path, cutoff=0.98)
    assert len(scores) == 3
    summary = summarise(scores, "empty", "all")
    assert summary["documents"] == 3 and summary["mean_field_accuracy"] == 0.0


def test_a_document_that_cannot_be_read_is_counted_as_a_read_error(tmp_path: Path) -> None:
    docs = build_dataset().documents[:2]
    for doc in docs:
        (tmp_path / doc.file_name).write_bytes(b"png")
    scores = run_documents(_Broken(), docs, tmp_path, cutoff=0.98)
    summary = summarise(scores, "broken", "all")
    assert summary["read_errors"] == 2 and summary["documents"] == 2


def test_a_missing_image_file_is_a_read_error_not_a_crash(tmp_path: Path) -> None:
    docs = build_dataset().documents[:1]
    scores = run_documents(_Empty(), docs, tmp_path, cutoff=0.98)
    assert scores[0].predicted_type == "read_error"
```

- [ ] **Step 2: Run to see it fail.** `uv run pytest tests/test_eval_runner.py -q 2>&1 | tail -8`

- [ ] **Step 3: Implement** `evals/extract_bench.py`:

```python
"""Run an engine over the labelled documents and write a summary of real extraction accuracy.

    uv run python -m evals.extract_bench rapidocr --out evals/ocr/extraction
    uv run python -m evals.extract_bench recorded --recording evals/recordings/rapidocr.json

Every document is scored. A document that cannot be read counts as all fields wrong and is
reported as a read error, so the denominator never shrinks.
"""

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from app.core.config import Settings
from app.domain.classify import classify
from app.domain.extract import extract_fields
from app.gateway.types import Engine
from evals.extraction import DocumentScore, expected_values, score_document
from seed.dataset import DocumentRecord, build_dataset

READ_ERROR = "read_error"


def run_documents(
    engine: Engine, docs: Sequence[DocumentRecord], png_dir: Path, cutoff: float
) -> list[DocumentScore]:
    scores: list[DocumentScore] = []
    for doc in docs:
        try:
            image = (png_dir / doc.file_name).read_bytes()
            words = engine.read(image).words
        except Exception:  # an engine may fail in many ways; the eval must still count the document
            scores.append(_failed(doc))
            continue
        predicted = classify(words)
        fields = extract_fields(words, predicted, confidence_cutoff=cutoff)
        scores.append(score_document(doc, predicted, fields))
    return scores


def _failed(doc: DocumentRecord) -> DocumentScore:
    return DocumentScore(
        document_id=doc.document_id,
        doc_type=doc.doc_type,
        predicted_type=READ_ERROR,
        type_ok=False,
        correct=dict.fromkeys(expected_values(doc), False),
    )


def summarise(scores: Sequence[DocumentScore], engine_name: str, subset: str) -> dict[str, object]:
    by_field: dict[str, list[bool]] = defaultdict(list)
    by_type: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for score in scores:
        for (name, _subject), ok in score.correct.items():
            by_field[name].append(ok)
            by_type[score.doc_type][name].append(ok)
    every = [ok for oks in by_field.values() for ok in oks]
    return {
        "engine": engine_name,
        "subset": subset,
        "documents": len(scores),
        "read_errors": sum(1 for s in scores if s.predicted_type == READ_ERROR),
        "type_accuracy": _mean([s.type_ok for s in scores]),
        "field_accuracy": {name: _mean(oks) for name, oks in sorted(by_field.items())},
        "by_doc_type": {
            doc_type: {name: _mean(oks) for name, oks in sorted(fields.items())}
            for doc_type, fields in sorted(by_type.items())
        },
        "mean_field_accuracy": _mean(every),
        "failed_documents": [s.document_id for s in scores if not all(s.correct.values())],
    }


def _mean(values: Sequence[bool]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0
```

Then add `main()`: arguments `engine` (`rapidocr`, `tesseract`, `recorded`), `--png-dir` (default `data/seed/png`), `--out` (default `evals/ocr/extraction`), `--recording` (path, required for `recorded`), `--subset` (`all`, `compare10`, `noisy`; subsets come from Task 3), builds the engine (`RapidOcrEngine()` from `app.gateway.rapidocr_engine`, `TesseractEngine()` from Task 3, `RecordedEngine(path)` from `app.gateway.engines`), runs, writes `<out>/<engine>-<subset>.summary.json` and a `.jsonl` of per-document scores, prints the mean, returns 0. The bare `except Exception` is the one place a broad catch is correct (an engine failure must not stop the eval); if ruff flags it, narrow to `(EngineError, ValueError, OSError, RuntimeError)` from `app.gateway.types`, never add a suppression.

Add to the `Makefile` (copy the style of neighbouring targets, with a `## ` help comment): `eval-extract: ## Real extraction accuracy on the 30 labelled documents (RapidOCR, local, free)` running `uv run python -m evals.extract_bench rapidocr`.

- [ ] **Step 4: Run to see it pass, then `make check 2>&1 | tail -4`.**

- [ ] **Step 5: Commit**

```bash
git add evals/extract_bench.py tests/test_eval_runner.py Makefile
git commit -m "feat(evals): run an engine over the labelled documents and summarise [NOTASK-8]"
```

---

### Task 3: Runner-up engine, the 10-document comparison and the noisy subset

**Files:**
- Create: `evals/tesseract_engine.py`, `evals/subsets.py`
- Modify: `evals/extract_bench.py` (subset flag)
- Test: `tests/test_eval_runner.py` (append)

**Interfaces:**
- Consumes: Task 2; `pytesseract` (eval-only, may be absent: import inside `__init__`).
- Produces: `TesseractEngine(lang="eng", psm=6)` implementing `Engine` (`name = "tesseract"`, `read(image: bytes) -> OcrResult` with `OcrWord.box == (left, top, width, height)` in pixels and `confidence` in 0..1, matching `app/gateway/rapidocr_engine.py:56-70`); `compare_ten(docs) -> list[DocumentRecord]`; `noisiest(docs, count=10) -> list[DocumentRecord]`.

- [ ] **Step 1: Write the failing tests**

```python
from evals.subsets import compare_ten, noisiest
from seed.dataset import build_dataset


def test_the_comparison_set_is_ten_documents_and_stable() -> None:
    docs = build_dataset().documents
    first, second = compare_ten(docs), compare_ten(docs)
    assert len(first) == 10 and [d.document_id for d in first] == [d.document_id for d in second]


def test_the_comparison_set_covers_every_document_type_present() -> None:
    docs = build_dataset().documents
    assert {d.doc_type for d in compare_ten(docs)} == {d.doc_type for d in docs}


def test_the_noisy_subset_takes_the_highest_combined_noise() -> None:
    docs = build_dataset().documents
    picked = noisiest(docs, 10)
    others = [d for d in docs if d not in picked]

    def level(d) -> float:  # same formula as the module documents
        return d.noise.blur_radius + abs(d.noise.skew_degrees) / 5 + d.noise.shadow_strength

    assert min(level(d) for d in picked) >= max(level(d) for d in others)
```

Read `seed/dataset.py` for the exact `NoiseSpec` attribute names (labels.json shows `blur_radius`, `low_light`, `shadow_strength`, `skew_degrees`) and use them.

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: Implement.** `evals/subsets.py`: `compare_ten` sorts documents by `document_id` then takes round-robin one per `doc_type` until ten are chosen (deterministic, covers all types); `noisiest` sorts by `blur_radius + abs(skew_degrees) / 5 + shadow_strength` descending, ties by `document_id`, takes `count`. `evals/tesseract_engine.py`: lazy `import pytesseract`, decode bytes with `cv2.imdecode`, `pytesseract.image_to_data(rgb, lang=lang, config=f"--psm {psm}", output_type=Output.DICT)` as in `evals/ocr_bench.py:52-68`, one `OcrWord` per non-blank token with box `(left, top, width, height)` from `data["left"|"top"|"width"|"height"]` and confidence `max(conf, 0) / 100`. Wire `--subset` in `main()`: `all` uses all documents, `compare10` uses `compare_ten`, `noisy` uses `noisiest`.

- [ ] **Step 4: Run tests and `make check`. Then, if `tesseract` is installed (`tesseract --version`), run `uv run python -m evals.extract_bench tesseract --subset compare10 2>&1 | tail -5` and the same for `rapidocr`; if the binary or the models are missing, write "not run" in the report. Do not fabricate numbers.**

- [ ] **Step 5: Commit**

```bash
git add evals tests/test_eval_runner.py
git commit -m "feat(evals): add the runner-up engine and the comparison and noisy subsets [NOTASK-8]"
```

---

### Task 4: Recordings, the gate and the CI job

**Files:**
- Create: `evals/recordings.py`, `evals/gate_check.py`, `evals/recordings/` (output), `tests/test_eval_gate.py`
- Modify: `Makefile`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Task 2 runner; `app.gateway.engines.RecordedEngine` format (dict of SHA-256 hex to `{"words": [{"text", "confidence", "box"}]}`).
- Produces: `record(engine: Engine, docs, png_dir: Path, out: Path) -> int` (documents written), `parse_gate(text: str) -> dict[str, str]`, `check(summary: dict, gate: dict[str, str]) -> tuple[bool, str]`, CLI `python -m evals.gate_check <summary.json>` (exit 0 pass, 1 fail, 2 no accepted baseline).

- [ ] **Step 1: Write the failing tests**

```python
"""The gate compares a replayed score with the accepted baseline."""

from evals.gate_check import check, parse_gate

GATE = "delta: 0.02\nsubset: all\naccepted_baseline: 0.97\n"


def test_gate_parses_flat_key_value_lines_and_ignores_comments() -> None:
    gate = parse_gate("# note\nmetric: mean field accuracy (x)\ndelta: 0.02\naccepted_baseline: none\n")
    assert gate["delta"] == "0.02" and gate["accepted_baseline"] == "none"


def test_a_score_within_delta_of_the_baseline_passes() -> None:
    ok, _ = check({"mean_field_accuracy": 0.955, "documents": 30}, parse_gate(GATE))
    assert ok


def test_a_score_more_than_delta_below_fails_with_the_numbers_in_the_message() -> None:
    ok, message = check({"mean_field_accuracy": 0.90, "documents": 30}, parse_gate(GATE))
    assert not ok and "0.9" in message and "0.97" in message


def test_no_accepted_baseline_is_reported_not_passed() -> None:
    ok, message = check({"mean_field_accuracy": 1.0, "documents": 30}, parse_gate("delta: 0.02\naccepted_baseline: none\n"))
    assert not ok and "no accepted baseline" in message


def test_fewer_documents_than_the_subset_fails() -> None:
    ok, message = check({"mean_field_accuracy": 1.0, "documents": 12}, parse_gate(GATE))
    assert not ok and "30" in message
```

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: Implement.** `parse_gate`: for each non-blank line not starting with `#`, split on the first `:`, strip, drop any trailing ` # comment`. `check`: baseline `none` gives `(False, "no accepted baseline in gate.yaml; a person must accept one")`; `subset: all` requires `documents == 30` (message names 30); else passes when `mean_field_accuracy >= float(baseline) - float(delta)`; the message always carries the score, the baseline and delta. CLI maps the three outcomes to exit codes 0, 1, 2. `evals/recordings.py` `record()` runs the engine over each PNG and writes the JSON in `RecordedEngine` format (`json.dumps` with sorted keys, `indent=1`), keyed by `hashlib.sha256(image).hexdigest()`; add `python -m evals.recordings rapidocr` as a CLI that writes `evals/recordings/rapidocr.json`. Add Makefile targets `eval-record` (live, local, human-run) and `eval-gate` (`uv run python -m evals.extract_bench recorded --recording evals/recordings/rapidocr.json --out evals/ocr/extraction && uv run python -m evals.gate_check evals/ocr/extraction/recorded-all.summary.json`).

CI: add a job `eval-gate` to `.github/workflows/ci.yml` beside `unit`, with the same checkout/uv setup steps, `needs: unit`, running `make eval-gate`. It uses only the recording, so it makes no live engine call and needs no model download. Because `accepted_baseline` is `none` until a person edits it, the job exits 2 and must not fail the pipeline yet: write the step as `run: make eval-gate || [ $? -eq 2 ]` with a comment that exit 2 means "no baseline accepted yet", and say in the report that this must be changed to a hard failure when the engineer accepts a baseline. (This is not a lowered threshold: nothing is gated until a baseline exists.)

- [ ] **Step 4: Run tests and `make check`. The recording itself needs the live engine: run `make eval-record` only if RapidOCR models are present locally (report "not run" otherwise). If the recording is produced, commit `evals/recordings/rapidocr.json` (synthetic words only; check its size and tell the engineer if it is over 2 MB).**

- [ ] **Step 5: Commit**

```bash
git add evals tests/test_eval_gate.py Makefile .github/workflows/ci.yml
git commit -m "feat(evals): record engine output and gate CI on a replayed score [NOTASK-8]"
```

---

### Task 5: The accuracy report and the baseline proposal

**Files:**
- Create: `evals/extraction_report.py`, `docs/testing/extraction-accuracy.md` (generated), `docs/progress/NOTASK-8.md`
- Modify: `docs/DEBT.md` (DEBT-004 note), `Makefile` (`eval-report`)

**Interfaces:**
- Consumes: the summaries in `evals/ocr/extraction/*.summary.json`.

- [ ] **Step 1: Test** (`tests/test_eval_gate.py`, append): `render(summaries: list[dict]) -> str` includes each engine's mean accuracy, the per-field table, the by-document-type table, the read-error count and, when two engines are given, a side-by-side on the `compare10` subset; with no summaries it says "no summaries; run make eval-extract" (copy the behaviour of `evals/report.py`). Assert numbers in the output equal the numbers in the input, and that the caveat sentence about clean synthetic pages is present when an engine scores 1.0.

- [ ] **Step 2: Implement** `evals/extraction_report.py` (`python -m evals.extraction_report` writes `docs/testing/extraction-accuracy.md`; every number is read from the summaries, none typed by hand; caveats: 30 documents is a seed set, one template per type, English only, a perfect clean score cannot separate engines so the noisy subset is reported separately).

- [ ] **Step 3: Run what can run.** `make eval-extract`, the `compare10` and `noisy` runs for both engines, `make eval-report`. Anything that cannot run here (no models, no tesseract) is reported as "not run" and the report file is not written with invented numbers.

- [ ] **Step 4: Baseline proposal.** In `docs/progress/NOTASK-8.md` put the proposed `accepted_baseline` value (the replayed mean from the recording) and the exact edit for `evals/ocr/gate.yaml` (`accepted_baseline: <value>`, plus who and when), and the CI edit that turns exit 2 into a hard failure. Do not edit `gate.yaml`. Add one line to DEBT-004 stating whether the CI gate needs the models (it does not: it replays the recording) and that the live recording step still does.

- [ ] **Step 5: `make check`, then commit**

```bash
git add evals docs Makefile tests
git commit -m "docs(evals): add the extraction accuracy report and the baseline proposal [NOTASK-8]"
```

Report in the AGENTS.md shape (Changed, Verified, Not done, Noticed). Print the push command for the engineer: `git push -u origin feature/NOTASK-8-Evals`.

---

## Self-review

- Spec coverage: real extraction accuracy (Tasks 1, 2); 10-document engine comparison (Task 3); noisier subset (Task 3); baseline in `gate.yaml` by a person and a CI replay job with no live call (Tasks 4, 5); report from data (Task 5).
- Names are consistent across tasks: `expected_values`, `score_document`, `DocumentScore`, `run_documents`, `summarise`, `compare_ten`, `noisiest`, `TesseractEngine`, `record`, `parse_gate`, `check`, `render`.
- Known unknowns the implementer must resolve by reading, not guessing: the exact value format the extractor returns for dates, and the `NoiseSpec` attribute names (both read from code in Tasks 1 and 3).
- The plan was written without running anything. Whether RapidOCR models and the tesseract binary are present on the build machine is unknown, so Tasks 3 to 5 may end with some runs reported "not run".
