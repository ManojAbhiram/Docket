# Technical debt register

Review cadence: monthly, first working week   Owner: Docket team (rotation unconfirmed)
Last seed: not run (Bash unavailable; marker, suppression and skipped-test scan was not done). Rows below were added by hand from docs/research/ocr-landscape.md.
Last review: none   Total interest: est. 4.5 h/week

Interest is what the item costs per week (hours, `est.` when estimated).
Principal is the effort to pay it off (hours). Trigger is when it must be
paid. Ids are never reused; paid rows move to the Paid table with a date.
These are research risks, not code yet: the interest is the rework each one
would cause if left unresolved while the engine is built, and every number is
an estimate.

## Open

| Id | Description (file:line) | Class | Interest h/wk | Principal h | Trigger | Owner | Added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEBT-001 | No engine has a published CPU RAM figure under 512 MB (docs/research/ocr-landscape.md, Candidates). Measured 2026-10-05 on a laptop: RapidOCR 500.8 to 538.1 MB across repeats of the same settings (508.9 MB with images capped at 640 px), Tesseract 63 to 74 MB. Single runs cannot settle a 512 MB limit; needs repeats, an idle baseline and a smaller configuration (docs/research/ocr-benchmark.md) | other | est. 1 | est. 4 | before US-02-002 picks an engine | Docket team | 2026-10-05 |
| DEBT-002 | Hindi relies on PP-OCRv5 Devanagari models; PP-OCRv6 dropped Devanagari, so the engine pins to an older model line (docs/research/ocr-landscape.md, Risks) | other | est. 0.5 | est. 3 | when RapidOCR or Paddle drop v5 models, or at each engine upgrade | Docket team | 2026-10-05 |
| DEBT-003 | OCR scores are uncalibrated while REQ-011 routes on them (docs/product/PRD.md REQ-011, Q-016) | other | est. 1.5 | est. 6 | before US-00-003 is built | Docket team | 2026-10-05 |
| DEBT-004 | RapidOCR downloads models on first use; CI and offline runs need pre-downloaded, pinned models (docs/research/ocr-landscape.md, Risks) | other | est. 0.5 | est. 2 | before the gateway tests replay recorded responses in CI (US-02-001) | Docket team | 2026-10-05 |
| DEBT-005 | Hindi accuracy evidence is general text, not document photos; no benchmark on Indian marksheets or IDs found (docs/research/ocr-landscape.md, Evidence on Hindi) | other | est. 0.5 | est. 4 | when the synthetic set exists (US-02-003) | Docket team | 2026-10-05 |
| DEBT-006 | Python 3.14 wheels for ONNX Runtime, PaddlePaddle, PyTorch and the OCR packages not checked (pyproject.toml requires 3.14) | other | est. 0.5 | est. 1 | before the first engine install | Docket team | 2026-10-05 |

## Needs an estimate

| Id | Description | Missing |
| --- | --- | --- |
| none | Every row carries an estimate, all marked est. | Confirm interest figures with the owner at the first review |

## Paid

| Id | Description | Paid on | Task | Interest saved h/wk |
| --- | --- | --- | --- | --- |

## Review log

| Date | Open | Paid this month | Interest h/wk | Top item | Decision |
| --- | --- | --- | --- | --- | --- |
