# Progress: NOTASK-8 Evals

- Task: NOTASK-8
- Title: Evals (real extraction accuracy)
- Branch: feature/NOTASK-8-Evals
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-07
- Updated: 2026-10-07
- Plan: docs/superpowers/plans/2026-10-07-evals-accuracy.md

## Changed

- evals/extraction.py: scorer. Compares the value the app's extractor assigned to each field with the `printed_*` label (names ignore case and word order, dates and roll numbers ignore case and spacing, marks as integers).
- evals/extract_bench.py: runs an engine over the 30 documents (classify, then extract_fields, at the default review cutoff read from `Settings`), writes `<engine>-<subset>.summary.json` and a `.jsonl`. A document that cannot be read counts as every field wrong and stays in the 30.
- evals/subsets.py: `compare_ten` (one document per type in turn, by document id) and `noisiest` (blur radius + skew/5 + shadow strength, from the stored noise values).
- evals/tesseract_engine.py: Tesseract behind the `Engine` interface, for the runner-up.
- evals/recordings.py and evals/recordings/rapidocr.json: records RapidOCR words for the 30 images in the `RecordedEngine` format (68 KB, synthetic words only).
- evals/gate_check.py: compares a replayed summary with `evals/ocr/gate.yaml`. Exit 0 pass, 1 fail, 2 no accepted baseline.
- evals/extraction_report.py and docs/testing/extraction-accuracy.md: the report, every number read from the summaries.
- evals/ocr/extraction/: the summaries and per-document lines the report is built from.
- Makefile: `eval-extract`, `eval-record`, `eval-gate` (with `EVAL_ALLOW_NO_BASELINE=1` to pass while no baseline exists), `eval-report`.
- .github/workflows/ci.yml: job `eval-gate` after `unit`, replaying the recording (no live engine, no model download).
- docs/DEBT.md: DEBT-004 notes that the CI gate does not need the models and only `make eval-record` still does.
- docs/superpowers/plans/2026-10-07-evals-accuracy.md: whitespace only, from `ruff format` (it formats the python blocks in markdown and `make check` failed on the plan file otherwise).
- tests/test_eval_extraction.py, tests/test_eval_runner.py, tests/test_eval_gate.py: no live engine.

## Verified

- Each task's tests were seen failing first (`ModuleNotFoundError` on the missing module), then passing.
- `make test`: `476 passed, 197 deselected in 17.21s`.
- `make check`: `check: 5 gates run, 0 skipped` then `check: passed` (run before each commit).
- Live runs on this machine (RapidOCR models present, tesseract 5.5.0 present, pytesseract supplied with `uv run --with pytesseract`, not added to pyproject.toml):

| Engine | all 30 | compare10 | noisy 10 | type accuracy (all) |
| --- | --- | --- | --- | --- |
| rapidocr | 0.995 | 1.0 | 0.9863 | 1.0 |
| tesseract (psm 11) | 0.2475 | 0.2027 | 0.0274 | 1.0 |

- Replay: `make eval-gate` reads `evals/recordings/rapidocr.json` and gives mean 0.995, 30 documents, 0 read errors, the same as the live run. It then reports `no accepted baseline in gate.yaml; a person must accept one` and exits 2. With `EVAL_ALLOW_NO_BASELINE=1` it exits 0.
- The one wrong field in RapidOCR's 30: SYN-DOC-027 `father_name`, printed `Mahesh Iyer`, read `Mahesh lyer` (a capital I read as a lowercase L), a noisy page.

## Baseline proposal (a person edits; nothing was set)

Proposed value: the replayed mean field accuracy, `0.995`, 30 documents, from `evals/recordings/rapidocr.json`.

Edit to `evals/ocr/gate.yaml` (also record who accepted it and the date next to it):

```
accepted_baseline: 0.995   # accepted by <name> on <date>, replay of evals/recordings/rapidocr.json
```

Then in `.github/workflows/ci.yml`, job `eval-gate`, change the last step from `make eval-gate EVAL_ALLOW_NO_BASELINE=1` to `make eval-gate`, so a drop of more than `delta: 0.02` (below 0.975) fails the pipeline.

## Not done

- `evals/ocr/gate.yaml` is untouched, so the CI job gates nothing until a person accepts a baseline.
- No second recording was made for Tesseract: CI replays the chosen engine only.
- Nothing pushed. For the engineer: `git push -u origin feature/NOTASK-8-Evals`.

## Differences from the plan

- `TesseractEngine` joins tokens into phrases (gap up to 0.8 line heights on the same line). Without it the extractor, which reads a label and a value as segments, scored Tesseract at 0.0 for a reason unrelated to the engine. RapidOCR already returns segments.
- `TesseractEngine` runs the app's `preprocess` before Tesseract so both engines read the same pixels, and its default page segmentation mode is 11, not 6. On the 10-document comparison set the mean field accuracy was 0.0 at psm 6, 0.0811 at psm 4 and 0.2027 at psm 11 (psm 11 also matches the best setting in the earlier benchmark). The setting was chosen on the comparison set, which favours Tesseract, not RapidOCR.
- The review cutoff is read from `Settings.model_fields["review_confidence_cutoff"].default`: `Settings(_env_file=None)` needs a `database_url`, which an eval should not require. An environment override of the cutoff is not applied.
- The transfer certificate is counted in the headline: `classify` and `match.py` both support it. It is also listed on its own in the by-type table.
- The gate fails when the replay has any read error (stricter than the plan), so a missing recording cannot pass with a smaller sample.
- CI uses `make eval-gate EVAL_ALLOW_NO_BASELINE=1` instead of `make eval-gate || [ $? -eq 2 ]`: make exits 2 for any recipe failure, so the plan's form would also swallow a real gate failure (exit 1).
- `run_documents` catches `(EngineError, RecordingMissingError, ValueError, OSError, RuntimeError)` rather than `Exception`.
- `pytesseract` is loaded with `importlib.import_module`, so mypy needs no override for an eval-only package.

## Noticed

- Tesseract is far behind RapidOCR on these pages even with preprocessing (0.2475 against 0.995). The comparison is not close, so it does not need the noisy subset to separate them; the noisy subset still shows RapidOCR dropping to 0.9863.
- RapidOCR scores 1.0 on the 10-document comparison set, so that set alone cannot show weakness; the other 20 documents hold the only error.
- `ruff format` rewrites python blocks inside markdown files, so a plan with an unformatted code block fails `make format-check`.
- docs/superpowers/plans/2026-10-07-accounts-sign-up.md has an uncommitted modification from before this task; it was left alone.
