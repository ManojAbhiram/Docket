# Architecture decisions: Docket

One row per decision, and every contradiction settled once so it is not settled again, differently, in each file that runs into it.

Titles, status and reversibility of ADR-0001 to ADR-0005 come from `docs/decisions.md` and the benchmark records, not from re-reading each ADR file in this run; check them against the files.

## Decisions

| Id | Title | Area | Status | Reversibility |
| --- | --- | --- | --- | --- |
| ADR-0001 | Use RapidOCR with OpenCV preprocessing and a 640 px cap as the engine | vision approach | Accepted | awkward: the gateway is swappable, but a new engine must be measured again on the same set |
| ADR-0002 | Extract fields with rules over OCR boxes and format validators | vision approach | Accepted | cheap: rules live in one module |
| ADR-0003 | No LLM fallback in v1, gateway left swappable | llm provider and models | Accepted | cheap: add a second engine behind the gateway |
| ADR-0004 | Run a local docker compose demo now and host later at or below about 400 MB | compute | Accepted | cheap: no hosted state exists yet |
| ADR-0005 | Route reviews by validators plus a configured confidence cutoff, initially 0.9804 | review routing | Accepted | cheap: the cutoff is a setting |
| ADR-0006 | Use server-side cookie sessions | auth | Accepted | awkward: every client call and the session table would change |
| ADR-0007 | Store document images in Postgres behind a storage interface | database | Accepted | awkward: bytes must be copied and one read path switched |
| ADR-0008 | Receive uploads through the API with streaming size caps and a fixed set of types | object storage | Proposed | cheap: one route and one limit |
| ADR-0009 | No malware scan in v1, mitigate with limits and fixed serving headers | object storage | Proposed | cheap: a scan step is added later |
| ADR-0010 | Re-encode uploaded images to strip metadata and cap size | object storage | Proposed | irreversible for stored documents: originals are not kept |
| ADR-0011 | Run document processing inside one API process | compute | Proposed | cheap: the loop moves to its own container |

## Conflicts that were settled

### Whether the API runs one worker or two

**Between:** `Dockerfile:18` (`WEB_CONCURRENCY=2`), ADR-0001 (engine peaks near 509 MB), ADR-0004 (one instance, at or below about 400 MB to host), `docs/design/uploads-pattern.md` (the loop runs inside the API process).

**Decision.** One worker, with the processing loop inside it, the engine loaded lazily on the first claimed document.

**Why.** Two workers would load the engine twice, about 1,018 MB for the engines alone (2 x 509), against a 512 MB budget.

**Settled by:** Proposed (ADR-0011, awaiting the engineer).

**What now has to change to match:**
- `Dockerfile:18`: `WEB_CONCURRENCY=1`.
- ADR-0011 moves from Proposed to Accepted when the engineer agrees.

### Whether the uploaded file is stored as given

**Between:** AC-US-00-002-1 ("the file is stored against that application"), ADR-0007 (a PDF is stored as its first page, the original is not kept), ADR-0010 (images are re-encoded).

**Decision.** Store the re-encoded first-page image only, and ask Product to amend AC-US-00-002-1 to say "the page image is stored".

**Why.** The original carries metadata about minors and several megabytes the free database cannot hold.

**Settled by:** open (product owner).

**What now has to change to match:**
- `docs/product/backlog.md` AC-US-00-002-1 wording, by Product.

### Whether a retry breaks "exactly one gateway call per document"

**Between:** REQ-008 and AC-US-00-003-1, `docs/design/data-model.md` processing rule 2 (a retry after `error` inserts a new `gateway_calls` row), `docs/design/uploads-pattern.md` (an interrupted document is re-uploaded, which creates a new document).

**Decision.** One call per processing attempt; a failed read is not retried automatically, so a document has one call, and a re-upload is a new document with its own call.

**Why.** It keeps REQ-008 true as written and the cap count honest.

**Settled by:** open (product owner), because it reads a requirement.

**What now has to change to match:**
- Data model processing rule 2: remove the retry sentence if the decision stands.

### Which roles may read the dashboard

**Between:** US-00-008 (persona: admissions staff), `docs/security/AUTH.md` (both roles read counts).

**Decision.** Both roles read the dashboard, because it returns counts only and no personal data.

**Why.** Verifiers use the Needs review count to size their work (US-00-008 narrative).

**Settled by:** Proposed.

**What now has to change to match:**
- `docs/product/backlog.md` US-00-008 persona, by Product.

### Whether sign-in is a Should

**Between:** US-00-011 (Priority Should), US-00-006 and US-00-007 (Must, both depend on US-00-011), `docs/product/estimate.md` (Must 54, Should 5).

**Decision.** Raise US-00-011 to Must.

**Why.** A Must cannot depend on a Should, and the decision log needs a known user (REQ-027).

**Settled by:** Proposed.

**What now has to change to match:**
- `docs/product/backlog.md` priority of US-00-011, by Product.
- `docs/product/estimate.md` totals: Must 59, Should 0.

### Whether the engine runs on the API's Python version

**Between:** `pyproject.toml:6` (Python 3.14 only), ADR-0001 and `docs/research/ocr-benchmark.md` (509 MB and 1.42 s per page measured on Python 3.12, `scripts/run-ocr-benchmark.sh:8`), ADR-0011 (the engine runs inside the API process), DEBT-006 (cp314 wheels not checked).

**Decision.** Check first: install `rapidocr`, `onnxruntime` and `opencv-python-headless` for Python 3.14 and re-measure inside the API. If they do not install, a separate 3.12 worker image supersedes ADR-0011.

**Why.** The in-process layout is only buildable if the wheels exist, and every number in the HLD is for 3.12 until then.

**Settled by:** open (engineer, after running the check).

**What now has to change to match:**
- ADR-0011 is superseded if the wheels are missing.
- HLD sections 3 and 8 cite the 3.14 measurement when it exists.

### Where idempotency keys are stored

**Between:** `api/openapi.yaml` (`Idempotency-Key` required on three POSTs, replay for 24 hours), `docs/design/schema.sql` (no table held the key).

**Decision.** A table `idempotency_keys` with primary key `(user_id, key)`, the body hash, the first status and the id of the created resource, swept after 24 hours.

**Why.** The primary key makes the first request win and a retry replay, which no per-request check can guarantee.

**Settled by:** Proposed.

**What now has to change to match:**
- `docs/design/schema.sql`, `data-dictionary.csv`, `erd.md` and `data-model.md` (done in this run).
- Migration 0002 and the sweeper (build items).

### Whether the compose demo includes the API and frontend

**Between:** ADR-0004 (a local `docker compose` demo), `docker-compose.yml` (only `postgres`), `frontend/nginx.conf` (the `/api/` proxy is commented out), `docs/security/AUTH.md` (same-origin cookie).

**Decision.** Add the API and frontend services and enable the proxy so the browser reaches the API on one origin (story PS-11).

**Why.** ADR-0006 depends on a same-origin cookie, and a demo that cannot run end to end is not a demo.

**Settled by:** Proposed.

**What now has to change to match:**
- `docker-compose.yml`: add `api` and `web` services.
- `frontend/nginx.conf`: enable the `/api/` location.
