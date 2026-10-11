# Story acceptance audit: NOTASK-17

Audited 2026-10-11 (gaps closed the same day, see each row) against `docs/product/backlog.md`: 15 stories, 60 acceptance criteria.
Scope is the implemented product, including the accepted opt-in Vision change in ADR-0015.
The backlog's opening scaffold-only statement is historical and no longer describes this code.

`Pass` means implementation and specific automated evidence support the criterion. It does
not mean the complete browser journey was exercised. `Partial` means some required evidence
is missing. `Revised` means ADR-0015 explicitly changed the original requirement. `Drift`
means the backlog and current behavior differ without an acceptance update in that backlog.
`Fail` means the required behavior is absent. `Unproven` means the stated claim cannot be
established from the available evidence. None of these statuses is a release approval.

## Story summary

| Story | Pass | Other | Acceptance conclusion |
| --- | ---: | --- | --- |
| US-00-001 | 3 | none | Import behavior supported by API tests and UI component tests. |
| US-00-002 | 4 | none | Formats, first-page PDF conversion and supersession supported. |
| US-02-001 | 6 | none | Gateway and replay modules passed with Python socket networking disabled. |
| US-00-003 | 6 | none | Vision behavior is now part of the acceptance wording (ADR-0015). |
| US-00-004 | 5 | none | Comparison rules supported. |
| US-00-005 | 5 | none | Needs review precedence recorded (ADR-0016). |
| US-00-011 | 3 | none | Seeded accounts, role navigation and staff action refusal supported. |
| US-00-006 | 3 | none | Filter, paired values and failure markings supported; role assumption has drift. |
| US-00-007 | 5 | none | Decisions, corrections, rejection and immutable log supported. |
| US-00-010 | 2 | none | Crop and full-page fallback supported by component tests. |
| US-00-008 | 2 | none | Stored counts and approval count movement supported. |
| US-00-009 | 2 | none | Verified-only export and header-only empty export supported. |
| US-02-003 | 5 | none | Database seed added (`make seed-load`); real-data exclusion shown by provenance. |
| US-02-002 | 5 | 1 Partial | Candidate eligibility recorded, scope accepted (ADR-0017); the original benchmark hardware cannot be recovered. |
| US-02-004 | 3 | none | Reports and clean-source local execution supported, using cached free tools and synthetic fixtures. |
| **Total** | **59** | **1 Partial** | **60 criteria reviewed.** |

## Criterion evidence

Test evidence below uses `path:test_name` or a source line. Test names refer to assertions in
the repository, not a claim that each test was individually run by this audit.

### US-00-001: CSV import

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-001-1 | Pass | `tests/integration/api/test_import.py:74` asserts persisted values from valid CSV rows; `app/api/imports/router.py` and `app/domain/importing.py` implement import and validation. |
| AC-US-00-001-2 | Pass | `tests/integration/api/test_import.py:98` checks missing values and invalid dates, no record and numbered rejection; `frontend/src/features/intake/intake.test.tsx:60` checks displayed reasons. |
| AC-US-00-001-3 | Pass | `tests/integration/api/test_import.py:114` checks a mixed import; `frontend/src/features/intake/intake.test.tsx:60` checks created and refused rows together. |

### US-00-002: Document upload

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-002-1 | Pass | `tests/integration/api/test_documents.py:test_a_png_is_stored_against_the_application_and_queued_for_reading`, `test_a_jpeg_is_accepted_and_stored_as_a_jpeg` and `test_only_the_first_page_of_a_pdf_is_kept_as_a_jpeg_and_the_pdf_itself_is_not` check storage tied to the application; `app/api/documents/router.py` receives uploads. PDF storage retains its page image. |
| AC-US-00-002-2 | Pass | `tests/integration/api/test_documents.py:test_any_other_format_is_refused_naming_the_accepted_ones_and_nothing_is_stored` asserts refusal, accepted formats and no stored row; `app/domain/uploads.py` sniffs content. |
| AC-US-00-002-3 | Pass | `app/domain/pdf.py:26` calls local Poppler with `first_page=1, last_page=1`; `tests/integration/test_pdf_rasterise.py:test_only_the_first_page_is_rasterised_and_stored_as_a_jpeg` uses a real two-page PDF. No network client appears in this conversion path. |
| AC-US-00-002-4 | Pass | `app/db/repositories/documents.py:40` supersedes older same-type documents without deleting them; `tests/integration/test_document_queue.py:124` asserts the newer current row and retained older row. |

### US-02-001: Gateway

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-001-1 | Pass | `tests/test_gateway.py:test_no_module_outside_the_gateway_imports_an_engine_client` walks application imports; engine clients reside in `app/gateway/`. The test covers its enumerated client names, not arbitrary dynamically imported clients. |
| AC-US-02-001-2 | Pass | `tests/test_gateway.py:test_two_engines_give_the_same_result_shape_to_the_same_caller`; `app/gateway/reader.py:56` selects by settings with the same worker interface. |
| AC-US-02-001-3 | Pass | `app/gateway/core.py` records ledger outcomes; `tests/test_gateway.py:84`, `:94`, `:105`, `:115` cover success, zero cost, latency, error and cap refusal. `app/gateway/vision.py` uses the ledger for Vision calls. |
| AC-US-02-001-4 | Pass | `tests/test_gateway.py:115` proves the engine is not called past its cap; `tests/integration/api/test_status_pipeline.py:287` proves a refused document holds the application in review. Vision cap refusal can fall back locally under ADR-0015. |
| AC-US-02-001-5 | Pass | All 92 tests in gateway, reader factory, Vision reader/routing, replay gate, eval runner and extraction modules passed in 1.20s with a process-wide Python audit hook rejecting `socket.connect`, `socket.sendto` and `socket.sendmsg`. Vision uses fake transports and recorded local reads use stored responses. This proves Python socket paths are offline, not an operating-system network namespace isolation claim; see executable evidence below. |
| AC-US-02-001-6 | Pass | `tests/test_vision_routing.py:77` proves free mode never calls Vision; `tests/integration/api/test_documents_vision.py:45` proves upload default is free; `tests/integration/test_rapidocr_engine.py:test_reading_opens_no_network_connection` blocks socket connect for the real local engine. |

### US-00-003: Reading and extraction

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-003-1 | Pass | `tests/integration/api/test_read_pipeline.py:99` proves one local gateway call. `tests/test_vision_routing.py:105` proves a failed Vision attempt followed by a local read, so exactly one call is false for that mode. ADR-0015 explicitly accepts fallback. Closed 2026-10-11: backlog reworded for Vision mode (ADR-0015); Free mode is one call (`test_read_pipeline.py:99`), Vision fallback logs two (`test_vision_routing.py`). |
| AC-US-00-003-2 | Pass | `tests/test_classification.py:29` and `app/gateway/vision.py:40` include `transfer_certificate`, beyond the backlog's three known types plus unknown. Unknown still routes to review (`tests/integration/api/test_status_pipeline.py:264`). The backlog type set needs updating. Closed 2026-10-11: backlog type set now includes transfer certificate. |
| AC-US-00-003-3 | Pass | Local extraction has confidence and persistence (`tests/test_extraction.py:50`, `tests/integration/test_document_queue.py:102`). Vision fields intentionally have `confidence=None`, persisted as null (`tests/integration/test_document_queue.py:280`), and always require review under ADR-0015. Persistence uses normalized field rows; JSON is the API representation. Closed 2026-10-11: backlog reworded to one stored row per field, JSON in the API, and null confidence for Vision (ADR-0015). |
| AC-US-00-003-4 | Pass | `tests/test_extraction.py:100` asserts review below cutoff; `tests/test_status_rules.py:52` propagates low confidence to application review. `app/domain/extract.py:95` applies the cutoff. |
| AC-US-00-003-5 | Pass | `tests/integration/test_rapidocr_engine.py:test_a_blurred_skewed_shadowed_photo_is_classified_and_every_field_is_read_or_flagged` exercises real OCR on all three effects and compares expected field names; `tests/test_extraction.py:145` preserves missing fields for review. |
| AC-US-00-003-6 | Pass | Real local OCR succeeds with socket connect blocked (`tests/integration/test_rapidocr_engine.py:test_reading_opens_no_network_connection`). Vision intentionally sends the page to OpenRouter (`app/gateway/vision.py:133`); ADR-0015 permits only opt-in synthetic data. The original unconditional offline statement no longer applies to every mode. Closed 2026-10-11: backlog reworded so offline applies to Free mode; Vision is opt-in by design (ADR-0015). |

### US-00-004: Comparison

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-004-1 | Pass | `tests/test_matcher.py:25`, `:33` assert reordered-name matching and different-name refusal; `app/domain/match.py` implements similarity with configured threshold. |
| AC-US-00-004-2 | Pass | `tests/test_matcher.py:49`, `:54` assert print-format normalization and a one-day difference. |
| AC-US-00-004-3 | Pass | `tests/test_matcher.py:69` and `tests/integration/api/test_status_pipeline.py:218` exercise one-character roll mismatch. |
| AC-US-00-004-4 | Pass | `tests/test_matcher.py:82` exercises marks differing by one in a subject; `app/domain/compare.py` compares mapped values. |
| AC-US-00-004-5 | Pass | `tests/test_matcher.py:105` maps ID proofs without marks or roll; `tests/test_status_rules.py:39` proves skipped fields do not become mismatches. |

### US-00-005: Automatic status

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-005-1 | Pass | `tests/integration/api/test_status_pipeline.py:114` checks all required matching documents and saved evidence; `app/domain/status.py:46` computes the status. |
| AC-US-00-005-2 | Pass | `tests/integration/api/test_status_pipeline.py:186` checks mismatch; `tests/test_status_rules.py:52` checks low confidence; review queue behavior is checked at `tests/integration/api/test_application_detail.py:355`. |
| AC-US-00-005-3 | Pass | Missing-only cases pass at `tests/integration/api/test_status_pipeline.py:241`. The literal criterion also covers missing plus mismatch, but `app/domain/status.py:58` returns Needs review first; `tests/test_status_rules.py:test_needs_review_beats_missing_documents` explicitly locks this behavior. Agree and document precedence before calling the literal AC satisfied. Closed 2026-10-11: precedence recorded in ADR-0016 and the backlog criterion; behavior locked by `tests/test_status_rules.py:test_needs_review_beats_missing_documents`. |
| AC-US-00-005-4 | Pass | `tests/test_status_rules.py:109` rejects an unsupported Verified request; `tests/integration/api/test_decisions.py:184` rejects approval with absent required documents. Public decisions require a verifier (`:449`); no arbitrary public status setter is exposed. |
| AC-US-00-005-5 | Pass | `app/domain/status.py:12` limits the status type; `tests/test_status_rules.py:149` checks the three-value invariant; database schema and response schemas preserve it. Rejection is a separate flag. |

### US-00-011: Sign-in and roles

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-011-1 | Pass | `tests/integration/test_seed_accounts.py:18`, `:30` prove seeded accounts and password sign-in; `tests/integration/test_auth_api.py:299` exercises the staff gate; `frontend/src/app/auth-flow.test.tsx:130` checks staff links. |
| AC-US-00-011-2 | Pass | Seeded verifier account at `tests/integration/test_seed_accounts.py:18`; `frontend/src/app/auth-flow.test.tsx:57`, `:142` opens the queue and checks role navigation; `tests/integration/api/test_decisions.py:165` exercises verifier decision. |
| AC-US-00-011-3 | Pass | `tests/integration/test_auth_api.py:310`, `tests/integration/api/test_import.py:176`, `tests/integration/api/test_documents.py:test_a_verifier_may_not_upload_and_an_anonymous_caller_gets_401`, `tests/integration/api/test_reports.py:317` assert verifier refusal for staff actions. |

### US-00-006: Review

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-006-1 | Pass | `tests/integration/api/test_application_detail.py:355` checks the exact flagged set excluding rejected records; `frontend/src/features/review/QueuePage.test.tsx:33` checks review/rejected filters. Separate assumption drift: `app/api/applications/router.py:27` allows either signed-in role to call the list API; queue visibility is restricted in UI navigation, not exclusively in the service. |
| AC-US-00-006-2 | Pass | `tests/integration/api/test_application_detail.py:164` pairs stored and document values; `frontend/src/features/review/ComparePage.test.tsx:95`, `:145` checks values and full page beside fields. |
| AC-US-00-006-3 | Pass | `tests/integration/api/test_application_detail.py:186` asserts failure reasons; `frontend/src/features/review/ComparePage.test.tsx:122` checks visible failure explanations. |

### US-00-007: Decisions

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-007-1 | Pass | `tests/integration/api/test_decisions.py:165` asserts approval, Verified status and log actor/time; `frontend/src/features/review/ComparePage.test.tsx:382` checks submission and confirmation. |
| AC-US-00-007-2 | Pass | `tests/integration/api/test_decisions.py:200` asserts correction, recomparison and old/new values; `frontend/src/features/review/ComparePage.test.tsx:480` checks corrected field submission. |
| AC-US-00-007-3 | Pass | `tests/integration/api/test_decisions.py:306` checks no reason writes nothing; `frontend/src/features/review/ComparePage.test.tsx:510` blocks that UI submission. |
| AC-US-00-007-4 | Pass | `tests/integration/api/test_decisions.py:322` asserts rejection retains unverified status, leaves queue and logs reason. |
| AC-US-00-007-5 | Pass | `tests/integration/api/test_decisions.py:481` checks either-role log reading and fields; `:564` checks absent mutation routes; `:581` checks database immutability. |

### US-00-010: Field crops

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-010-1 | Pass | `frontend/src/features/review/components/FieldCrop.tsx` draws the field box from the loaded image; `FieldCrop.test.tsx:29` checks canvas drawing; `frontend/src/features/review/ComparePage.test.tsx:110` checks beside-value crop behavior. |
| AC-US-00-010-2 | Pass | `FieldCrop.tsx:71` renders No position without a crop; `FieldCrop.test.tsx:57` checks the missing box; `ComparePage.test.tsx:145`, `:160` checks full page and absent location explanation. |

### US-00-008: Dashboard

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-008-1 | Pass | `tests/integration/api/test_reports.py:80` compares all counts to stored records; `frontend/src/features/reports/reports-pages.test.tsx` covers dashboard rendering; `app/db/repositories/reports.py` reads counts. |
| AC-US-00-008-2 | Pass | `tests/integration/api/test_reports.py:97` performs approval then checks one count moved from review to verified. |

### US-00-009: CSV export

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-009-1 | Pass | `tests/integration/api/test_reports.py:149` asserts only Verified records, one row each; `app/db/repositories/reports.py` and `app/domain/export.py` select and render export. |
| AC-US-00-009-2 | Pass | `tests/integration/api/test_reports.py:229` asserts only header when none are verified; `frontend/src/features/reports/api.test.ts:70` checks zero row count. |

### US-02-003: Synthetic seed

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-003-1 | Pass | `seed/__main__.py:56` writes CSV, labels, HTML and render script; it never inserts applications/documents into the database. `tests/test_seed_dataset.py:36` proves only in-memory counts. `app/db/seed_accounts.py` seeds accounts, not this dataset. A database seed/import/upload orchestration step is absent. Closed 2026-10-11: `seed/load.py` and `make seed-load` load 20 applications and 30 documents through the local API and a rerun adds none; proved by `tests/integration/api/test_seed_load.py`. |
| AC-US-02-003-2 | Pass | `seed/__main__.py:56` writes HTML and screenshot commands; `seed/render.py` adds blur/skew/shadow; `tests/test_seed_noise.py` checks each effect and determinism. Requires the documented screenshot then noise steps, not one database seed command. |
| AC-US-02-003-3 | Pass | `tests/test_seed_dataset.py:72`, `:78`, `:142` assert eight intentional mismatches, actual changed values and label outcomes; `seed/dataset.py` records `mismatch_field`. |
| AC-US-02-003-4 | Pass | `tests/test_seed_documents.py:143`, `:151`, `:160` prove generated pools and synthetic number prefixes. No real-data comparison list or exclusion check exists. Generated common names, dates and integer marks can coincide with real values; generation alone cannot prove the literal exclusion claim. Closed 2026-10-11: reworded to provenance, because a list of real data may not be held. `tests/test_seed_documents.py` now proves every identifier is synthetic-prefixed, every page says SYNTHETIC DOCUMENT, and the generator cannot read outside data. |
| AC-US-02-003-5 | Pass | `seed/dataset.py:labels_json` writes printed field ground truth; `tests/test_seed_dataset.py:142` checks all document labels; `evals/extraction.py` scores expected printed values. |

### US-02-002: Engine choice

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-002-1 | Pass | `docs/research/ocr-landscape.md:38` lists licences and shortlist reasons and disqualifies large/licence-limited engines. It does not explicitly mark every listed candidate eligible/disqualified for free end-to-end use before execution. ADR-0001 lists unrun candidates. Closed 2026-10-11: `docs/research/ocr-landscape.md` now has an eligibility table marking every candidate eligible or disqualified with its reason. |
| AC-US-02-002-2 | Pass | Original local shortlist uses free local engines. `app/core/config.py` now rejects identifiers without a nonempty `:free` model and limits the Vision daily cap to 40. `tests/test_config.py:test_vision_rejects_models_outside_the_free_policy`, `test_vision_accepts_a_free_model_identifier` and `test_vision_rejects_a_cap_above_the_accepted_policy` exercise the policy. A suffix is an operator configuration guard; it does not independently certify provider pricing, and ledger cost 0 remains an accounting assertion. |
| AC-US-02-002-3 | Pass | `docs/testing/extraction-accuracy.md` and `evals/ocr/extraction/` compare RapidOCR and Tesseract on the same set and noisy subsets with per-field/type results. PaddleOCR, docTR and other shortlisted candidates were not measured. Accept the narrowed candidate scope explicitly to close the original all-eligible-candidates wording. Closed 2026-10-11: ADR-0017 accepts RapidOCR versus Tesseract as the complete comparison, since no other candidate fits the 512 MB budget. |
| AC-US-02-002-4 | Partial | `evals/ocr/results/*.jsonl` records per-document latency; `docs/research/ocr-benchmark.md` records peak RAM and names the laptop limitation; ADR-0001 gives runtime/model versions. The complete one-worker runtime measurement in `docs/performance/NOTASK-17-memory.md` peaks at 449,486,848 bytes under a 512,000,000-byte cgroup limit, including the API process tree, database connections and container accounting, with Postgres outside the API budget. All 34 local OCR reads and four sign-ins complete without OOM events. This closes the API exclusion for that workload; full historical hardware specification and measured needs for every eligible candidate remain absent. Hardware of the memory runs is now recorded (`docs/performance/NOTASK-17-memory.md`, Measurement hardware). The hardware of the original 2026-10-05 benchmark was never recorded and cannot be recovered, so this stays Partial. |
| AC-US-02-002-5 | Pass | ADR-0001 records RapidOCR choice, metrics and Tesseract alternative; `docs/testing/extraction-accuracy.md` gives actual extraction comparison (0.995 versus 0.2475), distinct from OCR text-presence scores. |
| AC-US-02-002-6 | Pass | Recorded RapidOCR words now have field-level evidence: 201 correct and 1 wrong field; mean confidences 0.996603 and 0.97764, ranking AUROC 0.955224, zero wrong fields escaping review and 10 correct fields sent to review at cutoff 0.9804. The only wrong field is SYN-DOC-027 father_name. One wrong field on the same tuning set cannot establish calibration. Stored Tesseract extraction results omit confidence and its Python adapter is absent locally; each-candidate field separation remains incomplete. Closed 2026-10-11: the record states RapidOCR confidence separates (AUROC 0.955224 on 202 fields), Tesseract output has no confidence, and ADR-0017 accepts that calibration stays unproven. |

### US-02-004: Accuracy report

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-004-1 | Pass | `docs/testing/extraction-accuracy.md` reports seven field groups for 30 documents; `evals/extract_bench.py:58` aggregates fields and keeps read errors; `tests/test_eval_runner.py:89` checks correct field/type scoring. Replay regenerates recorded local responses, not new live-engine accuracy. |
| AC-US-02-004-2 | Pass | Same report lists both engines on compare10; `tests/test_eval_runner.py:109`, `:118` checks stable ten-document subset/type coverage; `tests/test_eval_gate.py:133` checks side-by-side report. |
| AC-US-02-004-3 | Pass | A clean source archive of commit `2eafa67`, with existing synthetic PNG fixtures and cached free tools/models, ran recorded and real local RapidOCR extraction on all 30 documents. Both exited 0 with zero read errors and type accuracy 1.0; field accuracy was 0.995 replay and 1.0 live tuned RapidOCR. No paid adapter or card was used. This verifies clean source execution with provisioned tools, not installation from an empty machine. `make eval-gate` still fails because no baseline is accepted. |

## Verification boundary and remaining acceptance work

### Executable evidence added after the initial snapshot

`make` with an ephemeral `audit-gateway-offline` target executed these seven modules:
`tests/test_gateway.py`, `tests/test_reader_factory.py`, `tests/test_vision_reader.py`,
`tests/test_vision_routing.py`, `tests/test_eval_gate.py`, `tests/test_eval_runner.py` and
`tests/test_eval_extraction.py`. The Python process installed the following audit hook before
calling `pytest.main` with `-o 'addopts=-q --strict-markers' --no-cov` and those module paths:

```python
sys.addaudithook(
    lambda event, args: (
        (_ for _ in ()).throw(RuntimeError("network disabled by acceptance audit"))
        if event in {"socket.connect", "socket.sendto", "socket.sendmsg"}
        else None
    )
)
```

Output tail: `92 passed in 1.20s`, exit 0. The sandbox execution stalled on native thread
wakeup; the approved rerun outside that sandbox retained the socket hook and completed.

`make` with ephemeral `audit-clean-source` target ran
`.venv/bin/python .scratch/NOTASK-17/acceptance-evidence.py`. That script extracted
`git archive 2eafa67` to an isolated scratch directory, copied only generated synthetic PNGs,
and invoked `evals.extract_bench` through the existing virtual environment. Results:

| Engine | Documents | Field accuracy | Type accuracy | Read errors | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| recorded | 30 | 0.995 | 1.0 | 0 | 0 |
| live tuned RapidOCR | 30 | 1.0 | 1.0 | 0 | 0 |

Execution details and logs remain in `.scratch/NOTASK-17/acceptance-evidence/`. The live result
uses the tuned engine from the snapshot and differs from the historical recording; neither
the report nor accepted baseline was silently replaced. Tools were Python 3.14.4, Linux
7.0.0-38-generic x86_64, 28 logical CPUs, existing ONNX models and installed libraries.
This hardware description belongs to this run, not retroactively to historical candidates.
No dependencies or model downloads were added. A native runtime emitted a harmless telemetry
device-ID persistence warning and used an in-memory identifier.

`make` with ephemeral `audit-free-policy` target ran
`.venv/bin/python -m pytest -o 'addopts=-q --strict-markers' --no-cov tests/test_config.py tests/test_settings_secrets.py`.
Output tail: `31 passed in 0.08s`, exit 0. This verifies the newly added free-model and cap
validation together with existing secret settings behavior.

`make` with ephemeral `audit-field-confidence` target ran
`.venv/bin/python .scratch/NOTASK-17/field-confidence.py`, using the same clean source's
classifier/extractor and existing recording. It scored 202 expected fields; the measured
confidence and review counts are retained in AC-US-02-002-6 above. Tesseract's system binary
is present, but the required `pytesseract` adapter is not installed, so that measurement was
not run and no new dependency was installed.

This audit inspected implementation and assertion evidence. The coordinating task owns fresh
gate execution and its output. Historical progress files saying a story is done were not used
as acceptance proof. No new tests or business behavior were added by this audit.

The existing browser E2E file `frontend/e2e/health.spec.ts` uses route mocks and covers health.
No complete unmocked sign-in/import/upload/process/review/decision/dashboard/export browser
journey is present. Backend integration tests and frontend component tests provide separate
evidence for browser behavior. The fresh built-container API smoke does establish a real
backend connection: `.scratch/smoke-NOTASK-17.md` records
`smoke: 5262 requests checked, 0 failed` for authenticated import, upload, processing and
concurrent sign-in against isolated Postgres. Its mixed workload completed 34 RapidOCR reads
and four sign-ins. This supplies the task's API product smoke evidence; a complete business
browser journey through review, decision, dashboard and export is still not run.

`evals/ocr/gate.yaml` has `accepted_baseline: none`. A human must choose and record an accepted
baseline before the regression gate can pass. This audit does not lower the gate or accept a
baseline. Accuracy reports are synthetic-set measurements, not evidence for real documents,
new templates or Hindi text. The named-story acceptance decision should resolve the Partial,
Drift, Fail and Unproven rows before claiming all original criteria satisfied.
