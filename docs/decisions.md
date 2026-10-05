# Decision log

One row per technology decision. The ADR holds the full reasoning; this
table is the index. `tech-decision` maintains it.

| Date | Key | Choice | Recommended | Why it was chosen | ADR | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-05 | vision approach (OCR engine) | RapidOCR + OpenCV preprocessing, 640 px cap | RapidOCR + preprocessing | only measured option that reads the synthetic pages (100% value presence, CER 0.0003) against Tesseract's best 36%; memory unmeasured past 30 pages | ADR-0001 | Accepted |
| 2026-10-05 | vision approach (field extraction) | Rules over OCR boxes + format validators | Rules + validators | deterministic, free, no extra RAM; validators decide Needs review | ADR-0002 | Accepted |
| 2026-10-05 | llm provider and models (fallback) | None in v1, gateway left swappable | None in v1 | nothing fails that a fallback would fix; every option costs RAM or sends images to a third party | ADR-0003 | Accepted |
| 2026-10-05 | compute (hosting) | Local docker compose now, hosted later at or below about 400 MB | Local now, hosted later | 509 MB is 99.4% of 512 MB before the API's overhead; Render free RAM unverified | ADR-0004 | Accepted |
| 2026-10-05 | review routing | Validators + configured confidence cutoff, initially 0.9804 (provisional) | Validators + cutoff | score alone separates right from wrong too weakly; 12% of applications is about 4.2% of documents | ADR-0005 | Accepted |
