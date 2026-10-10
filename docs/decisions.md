# Decision log

One row per technology decision. The ADR holds the full reasoning; this
table is the index. `tech-decision` maintains it.

| Date | Key | Choice | Recommended | Why it was chosen | ADR | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-10 | document extraction contract | Shared structured result normalized at gateway | Shared result | both engines feed one worker/store without invented OCR evidence; user selected D3/3A | ADR-0014 | Accepted |
| 2026-10-05 | vision approach (OCR engine) | RapidOCR + OpenCV preprocessing, 640 px cap | RapidOCR + preprocessing | only measured option that reads the synthetic pages (100% value presence, CER 0.0003) against Tesseract's best 36%; memory unmeasured past 30 pages | ADR-0001 | Accepted |
| 2026-10-05 | vision approach (field extraction) | Rules over OCR boxes + format validators | Rules + validators | deterministic, free, no extra RAM; validators decide Needs review | ADR-0002 | Accepted |
| 2026-10-05 | llm provider and models (fallback) | None in v1, gateway left swappable | None in v1 | nothing fails that a fallback would fix; every option costs RAM or sends images to a third party | ADR-0003 | Accepted |
| 2026-10-05 | compute (hosting) | Local docker compose now, hosted later at or below about 400 MB | Local now, hosted later | 509 MB is 99.4% of 512 MB before the API's overhead; Render free RAM unverified | ADR-0004 | Accepted |
| 2026-10-05 | review routing | Validators + configured confidence cutoff, initially 0.9804 (provisional) | Validators + cutoff | score alone separates right from wrong too weakly; 12% of applications is about 4.2% of documents | ADR-0005 | Accepted |
| 2026-10-05 | auth (session or token) | Server-side cookie session | Server-side cookie session | one browser app on one origin; a session must be revocable at once | ADR-0006 | Accepted |
| 2026-10-05 | database (file storage) | document_blobs table in Postgres behind a storage interface | document_blobs in Postgres | works locally and on an ephemeral-disk host with nothing new to run; supports only the demo size | ADR-0007 | Accepted |
| 2026-10-05 | object storage (upload route) | Through the API, streamed, 8 MiB cap, JPEG/PNG/PDF by type and magic bytes | Through the API | no object store exists to presign for; the API transforms the file | ADR-0008 | Proposed |
| 2026-10-05 | object storage (malware scan) | None in v1, limits and fixed serving headers instead | No scan in v1 | scanner does not fit 512 MB; data is synthetic; accepted risk | ADR-0009 | Proposed |
| 2026-10-05 | object storage (image handling) | Re-encode on upload, drop metadata, cap 2,000 px | Re-encode on upload | removes GPS and device data from minors' photos | ADR-0010 | Proposed |
| 2026-10-05 | compute (process model) | One gunicorn worker with the processing loop inside it | One worker, loop in process | two workers would load the engine twice (about 1,018 MB from 2 x 509) | ADR-0011 | Proposed |
