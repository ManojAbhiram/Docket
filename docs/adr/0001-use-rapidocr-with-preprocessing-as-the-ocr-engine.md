# ADR-0001: Use RapidOCR with OpenCV preprocessing as the OCR engine

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: vision approach (OCR engine)
- Reversibility: cheap: the engine sits behind one gateway function (`CONSTRAINTS.md` section 3.1), so swapping it changes configuration and adapters, not callers.

## Context

`CONSTRAINTS.md` requires a free engine chosen by measurement and a 512 MB hosting budget (from the request). Measured on 30 synthetic documents (4 templates, English only) with `evals/ocr_bench.py`, one laptop (`docs/research/ocr-benchmark.md`, `evals/ocr/results/`):

- RapidOCR (PP-OCRv6 small, ONNX Runtime) with `evals/preprocess.py` and images capped at 640 px: every printed value present in the OCR text (100% on six field types), CER 0.0003, 30 of 30 documents fully read, 1.42 s/page median, peak RSS 508.9 MB (five repeats 508.5 to 509.5).
- Without preprocessing: mean 90% (marks 41 to 45%), 19 of 30 documents fully read.
- Tesseract with `hin+eng`: best case 36% mean, CER 0.28, 74 MB (page mode 11 plus preprocessing); worst 3% (mode 6, raw).
- RapidOCR memory after 1 page is about 365 MB and after 30 pages about 505 MB (raw, 640 px). Growth past 30 pages is not measured. The figure excludes FastAPI, SQLAlchemy and tracing.
- PaddleOCR, docTR and the PP-OCRv5 Devanagari model were not run. Speed was measured on a multi-core laptop, not one core.
- The 100% is "value present in the OCR text", not extraction: the father's surname always equals the student's in the seed, so name checks are partly free, and only the marks check depends on position.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| RapidOCR with preprocessing (chosen) | about 509 MB at 30 pages with unmeasured growth, so no margin under 512 MB; Devanagari model unmeasured; measured on synthetic pages only | the memory limit is not binding (local demo) or growth is bounded |
| Tesseract with preprocessing | 36% best case here, needs table-line removal and tuning first | RapidOCR cannot fit the host; the 74 MB footprint becomes the deciding fact |
| Run PaddleOCR and docTR before deciding | about a day of setup and 2 GB or more of downloads; PaddleOCR peaked at 2,220 MB on Paddle's own measurement | the shortlist must be fully measured before any commitment |
| Hosted vision API as the engine | sends page images to a third party; free-tier terms allow training and human review | the API host must stay tiny and the data is synthetic |

## Decision

We will use RapidOCR with the `evals/preprocess.py` steps (light flattening, deskew) and a 640 px image cap as the engine behind the gateway, because it is the only measured option that reads the synthetic pages, it is free and open source (Apache-2.0), and it costs about 0.11 s per page for preprocessing.

## Consequences

- Easier: one local engine, no data leaves the process, cost is zero.
- Harder: roughly 500 MB RAM, so only the local run is safe today (ADR-0004), and one worker per process (`Dockerfile:18` sets 2, which doubles model memory).
- Must be measured before relying on it: memory over 15,000 pages (loop the 30 images 20 times and log RSS per page; try the ONNX memory arena disabled), single-core time per page (`taskset -c 0`), and the v5 Devanagari model.
- Revisit if peak RSS exceeds 450 MB at 1,000 pages with the mitigations tried, if single-core time makes a 60 s request timeout likely, or if the extractor's accuracy on realistic layouts is below the bar the product owner sets.

## Commits us to

RapidOCR 3.9.x, ONNX Runtime 1.30, OpenCV 4.14 (headless), NumPy 2, PP-OCRv6 small models.
