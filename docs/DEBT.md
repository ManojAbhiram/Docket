# Technical debt register

Review cadence: monthly, first working week   Owner: Docket team (rotation unconfirmed)
Last seed: not run (Bash unavailable; marker, suppression and skipped-test scan was not done). Rows below were added by hand from docs/research/ocr-landscape.md.
Last review: none   Total interest: est. 4.5 h/week

> Update 2026-10-16 (NOTASK-29): The seed scan was run; results are in the section "Seed scan 2026-10-16" below. DEBT-001 and DEBT-004 were found settled by code and moved to Paid; DEBT-002, DEBT-003, DEBT-005 and DEBT-006 carry a dated note and stay open. Total interest is now est. 3.0 h/week (0.5 + 1.5 + 0.5 + 0.5), the same estimates minus the two paid rows. No review meeting happened, so "Last review" stays none. The text of every row is kept as written.

Interest is what the item costs per week (hours, `est.` when estimated).
Principal is the effort to pay it off (hours). Trigger is when it must be
paid. Ids are never reused; paid rows move to the Paid table with a date.
These are research risks, not code yet: the interest is the rework each one
would cause if left unresolved while the engine is built, and every number is
an estimate.

## Open

| Id | Description (file:line) | Class | Interest h/wk | Principal h | Trigger | Owner | Added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEBT-002 | Hindi relies on PP-OCRv5 Devanagari models; PP-OCRv6 dropped Devanagari, so the engine pins to an older model line (docs/research/ocr-landscape.md, Risks) Update 2026-10-16 (NOTASK-29), still open, subject changed: the Devanagari pin exists only in the benchmark harness (`evals/ocr_bench.py:84`, `Rec.lang_type=DEVANAGARI`, `OCRVersion.PPOCRV5`). The production engine builds `RapidOCR` with no language or version parameter (`app/gateway/rapidocr_engine.py:36-46`), so it runs the models bundled in the rapidocr 3.9.2 wheel (PP-OCRv6 small detector and recogniser in `rapidocr/models/`), and no Hindi model is wired into the service. Hindi support is therefore unbuilt, not pinned. | other | est. 0.5 | est. 3 | when RapidOCR or Paddle drop v5 models, or at each engine upgrade | Docket team | 2026-10-05 |
| DEBT-003 | OCR scores are uncalibrated while REQ-011 routes on them (docs/product/PRD.md REQ-011, Q-016) Update 2026-10-16 (NOTASK-29), still open: the trigger has passed (routing on scores is built, cutoff `review_confidence_cutoff = 0.9804` at `app/core/config.py:52`) and the limit was accepted in ADR-0017 (cutoff provisional, 201 of 202 recorded fields right, the one wrong field sent to review). The scores are still uncalibrated beyond that synthetic set; revisit when real photographed documents exist, as ADR-0017 says. Q-016 is still `open` in `docs/product/questions.md:52`. | other | est. 1.5 | est. 6 | before US-00-003 is built | Docket team | 2026-10-05 |
| DEBT-005 | Hindi accuracy evidence is general text, not document photos; no benchmark on Indian marksheets or IDs found (docs/research/ocr-landscape.md, Evidence on Hindi) Update 2026-10-16 (NOTASK-29), still open: the trigger is met (the synthetic set exists, US-02-003 done) but it has no Devanagari text: `evals/report.py:29` says "English only ... the Hindi question is still open" and `evals/extraction_report.py:21` says the same. No Hindi accuracy figure exists on documents or on photos. | other | est. 0.5 | est. 4 | when the synthetic set exists (US-02-003) | Docket team | 2026-10-05 |
| DEBT-006 | Python 3.14 wheels for PaddlePaddle, PyTorch and the other benchmark OCR packages not checked (ONNX Runtime and RapidOCR are confirmed on 3.14, 2026-10-06) Update 2026-10-16 (NOTASK-29), narrowed, still open: the runtime stack is confirmed on Python 3.14 (`Dockerfile:1` is `python:3.14-slim-bookworm`; `make check` runs on it). What stays unchecked is the PaddlePaddle, PyTorch, docTR and EasyOCR wheels, which are benchmark candidates that were not chosen and are not runtime dependencies; ADR-0017 accepts the two-engine comparison on that basis. Candidate to close at the first review. | other | est. 0.5 | est. 1 | before the first engine install | Docket team | 2026-10-05 |

## Seed scan 2026-10-16

Run by NOTASK-29 on `origin/main` at 4375863 with `git grep` over tracked files. Vendored third-party skill folders (`.claude/skills/`, `.github/skills/`) and lock files were left out. Results are the output, not a summary of intent.

| Scan | Pattern | Paths | Result |
| --- | --- | --- | --- |
| Markers | `TODO`, `FIXME`, `HACK`, `XXX` | everything except `docs/`, lock files | 0 in Docket's own code. The only hits are third-party: `live-browser.js:8565` in two vendored impeccable skill copies, and the words `XXXXXX` in `.githooks/pre-push:14` (a `mktemp` template). `.claude/rules/code.md:33` mentions the TODO rule. |
| Python suppressions | `# noqa`, `# type: ignore`, `# pyright: ignore`, `nosec`, `# pragma: no cover` | `*.py` | 2: `alembic/env.py:12` (`# noqa: F401`, import registers tables on the metadata, intended) and `tests/test_decisions.py:89` (`# type: ignore[misc]`, a test that assigns to a frozen entry on purpose, intended) |
| Formatter suppression | `# fmt: skip` | `*.py` | 1: `evals/tesseract_engine.py:46`, keeps a wide `zip` readable (intended) |
| TypeScript suppressions | `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `@ts-nocheck`, `as any`, `: any` | `frontend/src`, `frontend/e2e` | 1: `frontend/src/components/ErrorBoundary.test.tsx:62` (`eslint-disable-next-line ... only-throw-error`, with a reason, intended) |
| Config-level relaxations | ruff `ignore` and `per-file-ignores`, mypy overrides, ESLint `off` | `pyproject.toml`, `frontend/eslint.config.js` | ruff: `S104` ignored (container bind, commented), `S101` and `S106` in `tests/**`, `E402` in `alembic/**`, `PLC0415` in `app/core/telemetry.py` (all commented). mypy: `ignore_missing_imports` for four libraries (`pyproject.toml:109-111`), recorded as DEBT-007. ESLint: `no-non-null-assertion` and `react-refresh/only-export-components` off for tests, e2e and config files (`frontend/eslint.config.js:72-73`), two import rules off for config files (`:81-82`). |
| Skipped or expected-fail tests | `pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip(`, `importorskip`, `.skip(`, `xit`, `test.fixme`, `describe.skip` | `tests`, `frontend/src`, `frontend/e2e`, `evals`, `scripts` | 0. The one word match, `tests/test_eval_gate.py:96`, is a test name that says a recording must stop instead of skipping a document. |
| Lowered thresholds | coverage `fail_under`, vitest `thresholds` | `pyproject.toml:128`, `frontend/vitest.config.ts:31` | both 80; no lowering found (history was not walked) |
| Gate skips | `.skipped` file in `Makefile:6` | `make check` | `make check` fails when a gate is skipped unless `BEARING_ALLOW_SKIP=1` is set locally; CI never sets it (`Makefile:119`). Not a debt item. |

Not scanned: `docs/` (markers there are prose), generated files, and git history.

## Needs an estimate

| Id | Description | Missing |
| --- | --- | --- |
| none | Every row carries an estimate, all marked est. | Confirm interest figures with the owner at the first review |
| DEBT-007 | Update 2026-10-16 (NOTASK-29), from the seed scan: `pyproject.toml:109-111` (the override block) sets `ignore_missing_imports = true` for `asyncpg.*`, `opentelemetry.instrumentation.*`, `opentelemetry.exporter.*` and `pdf2image.*`, so calls into those four libraries are untyped under mypy strict. Class: lint suppression | Interest and principal, and whether stubs exist for these libraries (not checked) |

## Paid

| Id | Description | Paid on | Task | Interest saved h/wk |
| --- | --- | --- | --- | --- |
| DEBT-001 | No engine has a published CPU RAM figure under 512 MB (docs/research/ocr-landscape.md, Candidates). Measured 2026-10-05 on a laptop: RapidOCR 500.8 to 538.1 MB across repeats of the same settings (508.9 MB with images capped at 640 px), Tesseract 63 to 74 MB. Single runs cannot settle a 512 MB limit; needs repeats, an idle baseline and a smaller configuration (docs/research/ocr-benchmark.md) Settled (found 2026-10-16, NOTASK-29): `docs/performance/NOTASK-17-memory.md` records three repeats of the 30-page workload at a median of 379,469,824 bytes (362 MiB) peak RSS, and a container run limited to 512,000,000 bytes that peaked at 449,486,848 bytes with no OOM, including four concurrent 25 megapixel uploads. Two limits remain, both stated there: arbitrary traffic and more than one worker are not bounded, and the runtime misses ADR-0004's 400 MB hosting target (the owner now hosts on 1 GB, ADR-0018). Regression tests: `tests/test_process_engine.py:119` `test_default_recycling_releases_the_child_after_each_page`. | 2026-10-11 | NOTASK-17 | est. 1 |
| DEBT-004 | RapidOCR downloads models on first use; CI and offline runs need pre-downloaded, pinned models (docs/research/ocr-landscape.md, Risks). The CI eval gate (NOTASK-8) does not need the models: it replays evals/recordings/rapidocr.json. Only the live recording step (make eval-record) still does Settled (found 2026-10-16, NOTASK-29): the models ship inside the rapidocr wheel (`app/gateway/rapidocr_engine.py:6`, `rapidocr/models/*.onnx`), the wheel is locked with a hash in `uv.lock` and installed with `uv sync --locked` (`Dockerfile:8`), and `tests/integration/test_rapidocr_engine.py:78` `test_reading_opens_no_network_connection` fails if the engine opens a socket. Nothing is downloaded on first use any more, so CI and offline runs need no pre-downloaded models and `make eval-record` is no exception. | 2026-10-11 | NOTASK-17 | est. 0.5 |

## Review log

| Date | Open | Paid this month | Interest h/wk | Top item | Decision |
| --- | --- | --- | --- | --- | --- |
