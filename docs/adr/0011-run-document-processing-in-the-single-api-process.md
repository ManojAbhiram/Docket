# ADR-0011: Run document processing inside one API process

- Status: Proposed (awaiting the engineer; found by the high-level design reconciliation, not yet decided by a person)
- Date: 2026-10-05
- Task: US-02-002
- Deciders: none yet
- Area: compute
- Reversibility: cheap: the loop is one module; moving it to its own container later changes the compose file and the claim query stays.

## Context

The engine peaks near 509 MB resident (ADR-0001, five repeats 508.5 to 509.5). `Dockerfile:18` sets `WEB_CONCURRENCY=2`, which starts two gunicorn workers, and the uploads plan runs the processing loop inside the API process (`docs/design/uploads-pattern.md`). With two workers each could load the engine, which is about 1,018 MB for the engines alone (2 x 509, arithmetic from the measurement, not a new measurement). ADR-0004 allows one instance and a host only at or below about 400 MB.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| One worker, loop in the API process (proposed) | OCR and API share one process and one memory budget | the demo, one office |
| Two workers, loop in one of them | gunicorn cannot choose which worker runs the loop, so it needs a cross-process lock, and every worker still carries the API's own memory | more request concurrency |
| A separate worker container | a second image and service, and a second copy of the API code in memory | a hosted deployment with room |

## Decision

We will run one gunicorn worker (`WEB_CONCURRENCY=1`) and host the claiming loop in it, and run the engine in one long-lived child process that the loop starts on the first claimed document, so a read that hangs can be killed. The read timeout is 120 seconds, below the 5 minute sweeper age, so the loop kills and restarts the child, marks the document `failed` with reason `timeout`, and the sweeper never races a live read. The child is recycled after 500 documents (an assumption until memory growth is measured, HLD section 16). Every completion write is conditional on `status = 'processing'`. This keeps one copy of the engine in memory: the API process holds none.

## Consequences

- Easier: one engine in memory, the claim query (`FOR UPDATE SKIP LOCKED`) is still safe if a second consumer is added later.
- Harder: API latency during a read is shared with the engine's CPU use. `Dockerfile:18` must change from 2 to 1. The API plus engine total is unmeasured (the 509 MB figure is for the benchmark process).
- Buildable on paper, not yet proven: the API is pinned to Python 3.14 (`pyproject.toml:6`) and the engine was measured on 3.12 only (DEBT-006). A PyPI check on 2026-10-05 found 3.14 Linux x86_64 wheels for onnxruntime 1.30.0, pyclipper 1.4.0, Shapely 2.1.2 and a stable-ABI opencv-python-headless, and rapidocr 3.9.2 is pure Python (HLD section 16). A dry-run install on 3.14 by the engineer resolved 22 packages (rapidocr 3.9.2, onnxruntime 1.30.0, opencv-python 5.0.0.93), but nothing was built, imported or measured. If the install fails on 3.14, or the benchmark repeated under 3.14 breaks the memory budget, this ADR is superseded by a separate 3.12 worker image. rapidocr depends on the non-headless `opencv_python`, which needs a system `libGL` in the slim image (assumption). The 120 second timeout, the 500 document recycle and the child process are proposals, not measured, and the child adds the API's own memory beside the engine (unmeasured).
- Revisit when the API plus engine is measured together, or at the first hosted deployment.

## Commits us to

No new technology. A change to `Dockerfile:18` and a compose service for the API.
