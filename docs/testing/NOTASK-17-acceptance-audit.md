# Story acceptance audit: NOTASK-17

Audited 2026-10-11 against `docs/product/backlog.md`: 15 stories, 60 acceptance criteria.
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
| US-02-001 | 5 | 1 Partial | Whole-suite network-disabled replay run not evidenced. |
| US-00-003 | 2 | 3 Revised, 1 Drift | Vision changes call count, confidence and outbound behavior; type set expanded. |
| US-00-004 | 5 | none | Comparison rules supported. |
| US-00-005 | 4 | 1 Drift | Needs review takes precedence over a missing required type. |
| US-00-011 | 3 | none | Seeded accounts, role navigation and staff action refusal supported. |
| US-00-006 | 3 | none | Filter, paired values and failure markings supported; role assumption has drift. |
| US-00-007 | 5 | none | Decisions, corrections, rejection and immutable log supported. |
| US-00-010 | 2 | none | Crop and full-page fallback supported by component tests. |
| US-00-008 | 2 | none | Stored counts and approval count movement supported. |
| US-00-009 | 2 | none | Verified-only export and header-only empty export supported. |
| US-02-003 | 3 | 1 Fail, 1 Unproven | Seed writes a dataset to files, not the database; real-data exclusion unproven. |
| US-02-002 | 1 | 5 Partial | Two engines measured; complete candidate eligibility, free Vision enforcement and field confidence proof missing. |
| US-02-004 | 2 | 1 Partial | Reports exist; clean-checkout free-tool execution not established. |
| **Total** | **46** | **7 Partial, 3 Revised, 2 Drift, 1 Fail, 1 Unproven** | **60 criteria reviewed.** |

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
| AC-US-02-001-5 | Partial | `tests/test_gateway.py:test_a_recorded_engine_makes_no_network_connection` blocks socket connect for replay; `tests/test_eval_gate.py:73` checks recordings. No run of every gateway test with network globally disabled is recorded here. Vision tests use fake transports; a passing suite alone is not that stronger proof. |
| AC-US-02-001-6 | Pass | `tests/test_vision_routing.py:77` proves free mode never calls Vision; `tests/integration/api/test_documents_vision.py:45` proves upload default is free; `tests/integration/test_rapidocr_engine.py:test_reading_opens_no_network_connection` blocks socket connect for the real local engine. |

### US-00-003: Reading and extraction

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-00-003-1 | Revised | `tests/integration/api/test_read_pipeline.py:99` proves one local gateway call. `tests/test_vision_routing.py:105` proves a failed Vision attempt followed by a local read, so exactly one call is false for that mode. ADR-0015 explicitly accepts fallback. |
| AC-US-00-003-2 | Drift | `tests/test_classification.py:29` and `app/gateway/vision.py:40` include `transfer_certificate`, beyond the backlog's three known types plus unknown. Unknown still routes to review (`tests/integration/api/test_status_pipeline.py:264`). The backlog type set needs updating. |
| AC-US-00-003-3 | Revised | Local extraction has confidence and persistence (`tests/test_extraction.py:50`, `tests/integration/test_document_queue.py:102`). Vision fields intentionally have `confidence=None`, persisted as null (`tests/integration/test_document_queue.py:280`), and always require review under ADR-0015. Persistence uses normalized field rows; JSON is the API representation. |
| AC-US-00-003-4 | Pass | `tests/test_extraction.py:100` asserts review below cutoff; `tests/test_status_rules.py:52` propagates low confidence to application review. `app/domain/extract.py:95` applies the cutoff. |
| AC-US-00-003-5 | Pass | `tests/integration/test_rapidocr_engine.py:test_a_blurred_skewed_shadowed_photo_is_classified_and_every_field_is_read_or_flagged` exercises real OCR on all three effects and compares expected field names; `tests/test_extraction.py:145` preserves missing fields for review. |
| AC-US-00-003-6 | Revised | Real local OCR succeeds with socket connect blocked (`tests/integration/test_rapidocr_engine.py:test_reading_opens_no_network_connection`). Vision intentionally sends the page to OpenRouter (`app/gateway/vision.py:133`); ADR-0015 permits only opt-in synthetic data. The original unconditional offline statement no longer applies to every mode. |

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
| AC-US-00-005-3 | Drift | Missing-only cases pass at `tests/integration/api/test_status_pipeline.py:241`. The literal criterion also covers missing plus mismatch, but `app/domain/status.py:58` returns Needs review first; `tests/test_status_rules.py:test_needs_review_beats_missing_documents` explicitly locks this behavior. Agree and document precedence before calling the literal AC satisfied. |
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
| AC-US-02-003-1 | Fail | `seed/__main__.py:56` writes CSV, labels, HTML and render script; it never inserts applications/documents into the database. `tests/test_seed_dataset.py:36` proves only in-memory counts. `app/db/seed_accounts.py` seeds accounts, not this dataset. A database seed/import/upload orchestration step is absent. |
| AC-US-02-003-2 | Pass | `seed/__main__.py:56` writes HTML and screenshot commands; `seed/render.py` adds blur/skew/shadow; `tests/test_seed_noise.py` checks each effect and determinism. Requires the documented screenshot then noise steps, not one database seed command. |
| AC-US-02-003-3 | Pass | `tests/test_seed_dataset.py:72`, `:78`, `:142` assert eight intentional mismatches, actual changed values and label outcomes; `seed/dataset.py` records `mismatch_field`. |
| AC-US-02-003-4 | Unproven | `tests/test_seed_documents.py:143`, `:151`, `:160` prove generated pools and synthetic number prefixes. No real-data comparison list or exclusion check exists. Generated common names, dates and integer marks can coincide with real values; generation alone cannot prove the literal exclusion claim. |
| AC-US-02-003-5 | Pass | `seed/dataset.py:labels_json` writes printed field ground truth; `tests/test_seed_dataset.py:142` checks all document labels; `evals/extraction.py` scores expected printed values. |

### US-02-002: Engine choice

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-002-1 | Partial | `docs/research/ocr-landscape.md:38` lists licences and shortlist reasons and disqualifies large/licence-limited engines. It does not explicitly mark every listed candidate eligible/disqualified for free end-to-end use before execution. ADR-0001 lists unrun candidates. |
| AC-US-02-002-2 | Partial | Original local shortlist excludes licence-limited candidates and uses free local engines. ADR-0015 requires a free Vision model, but `app/core/config.py:42` accepts an arbitrary model string and `app/gateway/vision.py:134` forwards it without enforcing free eligibility. Ledger cost 0 is an accounting assertion, not provider price enforcement. A paid model can be configured, so the current product does not establish unconditional free-only exclusion. |
| AC-US-02-002-3 | Partial | `docs/testing/extraction-accuracy.md` and `evals/ocr/extraction/` compare RapidOCR and Tesseract on the same set and noisy subsets with per-field/type results. PaddleOCR, docTR and other shortlisted candidates were not measured. Accept the narrowed candidate scope explicitly to close the original all-eligible-candidates wording. |
| AC-US-02-002-4 | Partial | `evals/ocr/results/*.jsonl` records per-document latency; `docs/research/ocr-benchmark.md` records peak RAM and names the laptop limitation; ADR-0001 gives runtime/model versions. Full hardware specification and measured hardware needs for each eligible candidate are absent; the 512 MB figures originally excluded the API. NOTASK-17 memory evidence is a separate API/process-tree measurement. |
| AC-US-02-002-5 | Pass | ADR-0001 records RapidOCR choice, metrics and Tesseract alternative; `docs/testing/extraction-accuracy.md` gives actual extraction comparison (0.995 versus 0.2475), distinct from OCR text-presence scores. |
| AC-US-02-002-6 | Partial | `docs/research/ocr-benchmark.md` groups mean confidence by documents fully read versus those with a miss (`evals/ocr_bench.py:206`). This is document-level separation, not a per-field correct/wrong ranking. RapidOCR preprocessed pages have no miss group in that table. Field calibration/separation remains unproven. |

### US-02-004: Accuracy report

| Criterion | Status | Evidence and gap |
| --- | --- | --- |
| AC-US-02-004-1 | Pass | `docs/testing/extraction-accuracy.md` reports seven field groups for 30 documents; `evals/extract_bench.py:58` aggregates fields and keeps read errors; `tests/test_eval_runner.py:89` checks correct field/type scoring. Replay regenerates recorded local responses, not new live-engine accuracy. |
| AC-US-02-004-2 | Pass | Same report lists both engines on compare10; `tests/test_eval_runner.py:109`, `:118` checks stable ten-document subset/type coverage; `tests/test_eval_gate.py:133` checks side-by-side report. |
| AC-US-02-004-3 | Partial | Local RapidOCR/Tesseract and replay need no paid provider; source adapters and historical summaries support this. A clean checkout with complete system tools, models and rendered seed images was not exercised for this audit. `make eval-gate` replays 30 documents but fails because no baseline is accepted; that is not a clean-checkout pass. |

## Verification boundary and remaining acceptance work

This audit inspected implementation and assertion evidence. The coordinating task owns fresh
gate execution and its output. Historical progress files saying a story is done were not used
as acceptance proof. No new tests or business behavior were added by this audit.

The existing browser E2E file `frontend/e2e/health.spec.ts` uses route mocks and covers health.
No complete unmocked sign-in/import/upload/process/review/decision/dashboard/export browser
journey is present. Backend integration tests and frontend component tests provide separate
evidence, not proof of their complete connection in a running product. A fresh product smoke
run remains necessary for Definition of Done acceptance.

`evals/ocr/gate.yaml` has `accepted_baseline: none`. A human must choose and record an accepted
baseline before the regression gate can pass. This audit does not lower the gate or accept a
baseline. Accuracy reports are synthetic-set measurements, not evidence for real documents,
new templates or Hindi text. The named-story acceptance decision should resolve the Partial,
Drift, Fail and Unproven rows before claiming all original criteria satisfied.
