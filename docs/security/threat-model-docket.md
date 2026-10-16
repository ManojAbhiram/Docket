# Threat model: Docket (admissions document verification)

- Task: US-02-002
- Serves: US-00-001, US-00-002, US-00-003, US-00-004, US-00-005, US-00-006, US-00-007, US-00-008, US-00-009, US-00-011, US-02-001, REQ-001 to REQ-044, ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006, ADR-0007
- HLD: docs/design/docket-hld.md; diagram: docs/architecture/docket-c4.md
- Sensitive classes: auth, PII (minors, community category), external input (CSV, images, PDFs)
- Author: draft, unreviewed. 2026-10-05. Status: Draft (v1)
- Abuse-path pass: not run (design only, no application code yet to anchor evidence to)

Scope: the planned system as designed in `docs/design/data-model.md` and the backlog. Application code does not exist yet (`app/domain/` is empty), so every mitigation that depends on it is `planned` and points to a story. Routes are the planned set that `api/openapi.yaml` will carry.

> Update 2026-10-16 (NOTASK-23): Application code now exists. Mitigations marked `planned` below were not re-checked in this pass; see `docs/security/NOTASK-17-vision-upload.md` and `docs/security/AUTH.md` for what was built and reviewed. The text below is kept as written on its date. Current state of the code and its evidence: `docs/testing/NOTASK-17-acceptance-audit.md`.

> Update 2026-10-16 (NOTASK-29): Every `planned` and `mitigated` status was re-checked against the code and the tests. The result is section 4a, one row per threat whose status or evidence changed, each with a `path:line` or `path:test_name`. The table in section 4 is kept as written on its date; where the two disagree, section 4a is newer. The entry point count in section 3 and the counts in section 7 are corrected in notes under those sections.

## 1. Assets

| Asset | Where it lives | Owner | Why an attacker wants it |
| --- | --- | --- | --- |
| applicant personal data (names, dates of birth, roll numbers, marks, category) of minors | postgres `applications` | admissions office operations role | identity theft, selling or leaking records of children, tampering with an admission |
| document images (marksheets, ID proofs) | postgres `document_blobs` | admissions office operations role | the same data plus the document itself, usable for fraud |
| verified status and decision log (audit integrity) | postgres `applications.status`, `decisions` | verifier lead role | forcing a Verified outcome, erasing who approved what |
| staff and verifier credentials and sessions | postgres `users.password_hash`, `sessions.token_hash`, cookie | platform rotation | account takeover of a role that can read all applicants |
| exported verified list | `GET /api/exports/verified.csv` response | admissions office operations role | one request that dumps many applicants |
| OCR engine availability | api process (about 509 MB peak measured, growth unmeasured) | platform rotation | taking the verification queue down |
| model files and dependencies | RapidOCR models, python packages | platform rotation | code or result tampering through the supply chain |
| secrets (database URL, session secret) | environment, `.env` (ignored) | platform rotation | database access |

## 2. Trust boundaries

| # | From | To | Protocol | Auth on the edge | Source |
| --- | --- | --- | --- | --- | --- |
| B1 | browser | frontend static server | HTTP locally, TLS from the host when hosted | none (static files) | frontend/Dockerfile:16 |
| B2 | browser | api | HTTP locally, TLS from the host when hosted | session cookie (planned) | Dockerfile:25 |
| B3 | api | postgres | SQL over TCP, no TLS locally | database role and password from the environment | docker-compose.yml:1 |
| B4 | api | OCR engine and image decoders (OpenCV, ONNX Runtime, PDF rasteriser) | in-process library calls on untrusted bytes | none | assumption: no gateway code yet |
| B5 | api | model download host | HTTPS, on first use | none | assumption: RapidOCR downloads models on first use (docs/research/ocr-landscape.md) |
| B6 | staff role | verifier role | in-process authorisation checks | role on the session | assumption: no auth code yet |
| B7 | CI and developer machine | package registries | HTTPS | lockfile (uv.lock) | Makefile:73 |

Assumed boundaries: 4 of 7 (B4, B5, B6 and the TLS statements in B1 to B3).

## 3. Entry points

| # | Entry point | Kind | Auth required | Boundary |
| --- | --- | --- | --- | --- |
| E1 | POST /api/auth/login | route | none (credentials in body) | B2 |
| E2 | POST /api/auth/logout | route | session | B2 |
| E3 | POST /api/imports (CSV upload) | route, external input | session, staff role | B2 |
| E4 | GET /api/applications (queue and list) | route | session | B2 |
| E5 | GET /api/applications/{id} | route | session | B2 |
| E6 | POST /api/applications/{id}/documents (image or PDF upload) | route, external input | session, staff role | B2 |
| E7 | GET /api/documents/{id}/image | route | session | B2 |
| E8 | POST /api/applications/{id}/decisions | route | session, verifier role | B2 |
| E9 | GET /api/dashboard | route | session | B2 |
| E10 | GET /api/exports/verified.csv | route | session, staff role | B2 |
| E11 | GET /healthz and GET /readyz | route | none | B2 (app/api/health/router.py:34, :40) |
| E12 | GET /docs and /openapi.json | route | none, off in production | B2 (app/main.py:46) |
| E13 | document processing worker (reads uploaded bytes, calls the engine) | consumer | internal | B4 |
| E14 | seed and import scripts on the host | cron or CLI | host access | B3 |
| E15 | POST /api/auth/register | route | none (the caller chooses the role) | B2, B6 |

Entry points: 15. Admin screens: none beyond the verifier and staff screens behind E4 to E10.

> Update 2026-10-16 (NOTASK-29): the table has 15 entry points (E15 was added for ADR-0013), while section 7 below says 14. The routes now exist at the planned paths. Four session-gated reads are not listed separately: `GET /api/capabilities`, `GET /api/applications/{id}/documents`, `GET /api/applications/{id}/decisions` (same data as E4, E5 and E7) and `GET /api/auth/me`.

## 4. Threats (STRIDE)

| Id | Entry or boundary | Category | Threat | Likelihood | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-01 | E1 | Spoofing | credential stuffing or brute force against a staff or verifier account | M | H | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-02 | E1, B2 | Spoofing | a stolen session cookie is replayed | M | H | US-00-011 | planned |
| T-03 | E2, E3, E6, E8 | Tampering | cross-site request forgery makes a signed-in user import, upload or decide | M | H | new story: CSRF protection for cookie sessions | planned |
| T-04 | E1 | Repudiation | considered, none: sign-ins are recorded in `users.last_login_at` and every state change names its user (US-00-007) | | | | |
| T-05 | E1 | Information disclosure | the login response or its timing reveals which usernames exist | M | L | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-06 | E1 | Denial of service | many login attempts exhaust CPU through the password hash | M | M | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-07 | E1, E14 | Elevation of privilege | seeded accounts keep a default or shared password | M | H | new story: Seed accounts with generated one-time passwords | planned |
| T-08 | B6, E3, E8, E10 | Elevation of privilege | a verifier imports or exports, or a staff member decides, outside the role | M | H | US-00-011 | planned |
| T-09 | E7 | Information disclosure | a document image is fetched without a session, or by a role that has no need | M | H | US-00-011 | planned |
| T-10 | E6, B4 | Tampering | a crafted image or PDF exploits a decoder (OpenCV, ONNX Runtime, the PDF rasteriser) | M | H | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-11 | E6, E13 | Denial of service | a decompression bomb or huge pixel size exhausts the 512 MB budget (509 MB measured at 30 normal pages) | H | H | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-12 | E6 | Spoofing | a file whose content type does not match its bytes passes the format check | M | M | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-13 | E6, E13 | Information disclosure | a client file name that contains a name is written to logs or URLs | M | M | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-14 | E6 | Tampering | path traversal through the client file name | L | M | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-15 | E3, E10 | Tampering | a name starting with `=`, `+`, `-` or `@` runs as a formula when the export opens in a spreadsheet | M | M | new story: CSV hardening: size and row caps, formula-safe export | planned |
| T-16 | E3 | Denial of service | a very large CSV or millions of rows exhausts memory or time | M | M | new story: CSV hardening: size and row caps, formula-safe export | planned |
| T-17 | E3 | Tampering | malformed or duplicate rows overwrite or corrupt applicants | M | M | US-00-001 | planned |
| T-18 | E3 | Information disclosure | a rejected-row error message echoes the personal value that failed | L | M | US-00-001 | planned |
| T-19 | E8 | Tampering | a verifier edits or deletes a decision log entry | L | H | US-00-007 | planned |
| T-20 | E8 | Repudiation | a verifier denies having approved an application | M | M | US-00-007 | planned |
| T-21 | E8 | Elevation of privilege | an application is made Verified by a direct request without matching evidence or a decision (REQ-019) | M | H | US-00-005 | planned |
| T-22 | E8 | Information disclosure | the free-text reason, old value or new value of a decision carries personal data into logs | L | M | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-23 | E10 | Information disclosure | one request exports every verified applicant to any signed-in user, with no trace | M | H | new story: Audit entry for every export of applicant data | planned |
| T-24 | E9 | Information disclosure | considered, none: the dashboard returns counts by status only, no personal data (US-00-008) | | | | |
| T-25 | E4, E5 | Information disclosure | considered, none beyond T-08: every staff and verifier may read every applicant by design (single office), so there is no per-record owner to enforce | | | | |
| T-26 | B5 | Tampering | model files downloaded on first use are replaced in transit or at the source | L | H | new story: Pin and checksum the OCR models, bake them into the image | planned |
| T-27 | B4, E13 | Denial of service | one request pushes the engine past available memory (509 MB measured, growth beyond 30 pages unmeasured) | H | M | US-02-001 | planned |
| T-28 | B4, E13 | Information disclosure | recognised text or field values are written to the gateway log | M | H | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-29 | B4, E13 | Repudiation | considered, none: every engine call is a `gateway_calls` row with engine, version and outcome (US-02-001) | | | | |
| T-30 | B3 | Information disclosure | database traffic is unencrypted and the API role has more rights than it needs | L | H | new story: Database TLS and a least-privilege API role | planned |
| T-31 | B3 | Tampering | considered, none beyond T-30: parameterised queries only (`.claude/rules/database.md`), asyncpg through SQLAlchemy (app/db/session.py:19) | | | | |
| T-32 | E12 | Information disclosure | the API documentation and schema are exposed in production | L | L | app/main.py:46 | mitigated |
| T-33 | E11, B2 | Information disclosure | an error response leaks a stack trace or internal detail | L | M | app/main.py:57 | mitigated |
| T-34 | B2 | Elevation of privilege | the API container runs as root | L | H | Dockerfile:19 | mitigated |
| T-35 | B7 | Tampering | a vulnerable or malicious dependency enters through the lockfile | M | H | Makefile:73 | mitigated |
| T-36 | B1, B2 | Spoofing | considered, none for the local demo: traffic is plain HTTP on localhost; a hosted deployment gets TLS from the host (ADR-0004) | | | | |
| T-37 | E14 | Elevation of privilege | considered, none: scripts run with host access by the operator, outside the application's trust model | | | | |
| T-38 | E15, B6 | Elevation of privilege | an anonymous caller registers as a verifier and approves applications | H | H | accepted risk (ADR-0013, chosen by the engineer on 2026-10-07 against the recommendation of invite-only). Bears on escalation: every decision stores its actor by user id (US-00-007), but the log, dashboard and export show `users.display_name`, which is self-chosen by an anonymous caller and not unique, so the shown name is not proof of who acted and the id is the true actor; the per-source sign-up limit (`register_max_per_source`, `register_window_minutes`) only slows bulk registration; nothing stops a person choosing the verifier role. Resource use only, not escalation: the Argon2 hash slots (`login_hash_concurrency`) cap hashing CPU and memory. Residual: register and login have no Origin or CSRF check because no session exists yet, so a cross-site request can replace the victim's session cookie with the attacker's (login CSRF) and spend the victim's source quota; accepted for now, follow-up is to apply the `verify_csrf` Origin allow-list to both routes. Follow-up option: an access code required for the verifier role | accepted |

Categories: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.

## 4a. Status re-check, 2026-10-16 (NOTASK-29)

Rule used: `mitigated` only with the control and a test or the enforcing code; `partly:` names what is missing; `planned` is kept where nothing was built. Test names are in `tests/` and are read from the code, not re-run for this note (see `docs/progress/NOTASK-29.md` for what was run).

| Id | Was | Now | Control and evidence |
| --- | --- | --- | --- |
| T-01 | planned | mitigated | Per-account lock (5 failures, 15 minutes) and per-source lock (20 failures): `app/domain/auth.py:134` `LoginLimiter`, used at `app/api/auth/router.py:65` and `:76`. Tests: `tests/test_auth_domain.py` `test_the_fifth_failure_locks_the_account_for_fifteen_minutes` and `test_twenty_failures_from_one_source_lock_that_source_across_accounts`; `tests/integration/test_auth_api.py` `test_the_fifth_wrong_password_locks_the_account_even_for_the_right_password`. Limits: counts live in process memory and reset on restart (`docs/security/AUTH.md`), and an attacker can lock a named account for the lock time. |
| T-02 | planned | partly: a stolen cookie still works until it expires or is revoked | Cookie is `HttpOnly`, `Secure` (`session_cookie_secure`, required in production by `app/core/config.py:90`) and `SameSite=Lax` (`app/api/auth/router.py:163-174`); only the SHA-256 of the token is stored (`test_the_database_keeps_only_a_hash_of_the_session_token`); 30 minute idle and 8 hour absolute limits (`test_a_session_idle_for_thirty_minutes_ends`, `test_activity_keeps_a_session_alive_until_the_eight_hour_limit`); logout revokes (`test_logout_ends_the_session_on_the_server_and_clears_both_cookies`); ending every session of a user makes an open one stale (`test_ending_every_session_of_a_user_makes_an_open_one_stale`). Missing: no binding of a session to a client, no endpoint to end all sessions (only the store call), and the lifetimes are unconfirmed assumptions. |
| T-03 | planned | mitigated | `verify_csrf` checks the `Origin` allow-list and a session-derived `X-CSRF-Token`: `app/api/auth/deps.py:72`. It is a dependency of logout (`app/api/auth/router.py:124`), import (`app/api/imports/router.py:40`), upload (`app/api/documents/router.py:54`) and decide (`app/api/decisions/router.py:39`). Tests: `test_logout_without_the_csrf_token_is_refused_and_the_session_survives`, `test_logout_from_another_origin_is_refused_even_with_the_token`, `test_a_state_changing_gated_route_needs_the_csrf_token` (all `tests/integration/test_auth_api.py`); `test_an_upload_without_the_csrf_token_is_refused` (`tests/integration/api/test_documents.py`); `test_an_import_without_the_csrf_token_is_refused` (`test_import.py`); `test_a_decision_without_the_csrf_token_is_refused` (`test_decisions.py`). Not covered: login and register carry no check (T-38 residual). |
| T-05 | planned | mitigated for login | An unknown name, a deactivated account and a wrong password all answer the same 401 and each costs one hash against a dummy hash: `app/api/auth/router.py:69-77`. Test: `tests/integration/test_auth_api.py` `test_an_unknown_user_and_a_wrong_password_get_the_same_answer`. Timing is equal by construction, not measured. `POST /api/auth/register` answers 409 for a taken name by design (`docs/security/AUTH.md`, Registration). |
| T-06 | planned | partly: hashing is bounded, a flood can still queue logins | All hashing runs inside `login_hash_concurrency` slots, default 1 (`app/main.py:113`, `app/core/compute.py:34`, used at `app/api/auth/router.py:73` and `:109`); sign-in and sign-up are rate limited per source (T-01; `RegistrationLimiter` at `app/domain/auth.py:194`). Tests: `tests/test_compute.py` (a slot is held until native work ends), `tests/test_registration_domain.py`. Missing: no test floods the slot, and with one slot a burst of failed sign-ins from many sources delays real users. |
| T-07 | planned | partly: no forced change at first sign-in | `make seed-accounts` generates a random password per demo account, prints it once, stores only the hash and leaves existing accounts alone: `app/db/seed_accounts.py:36-45`. Tests (`tests/integration/test_seed_accounts.py`): `test_the_two_demo_accounts_are_created_with_different_generated_passwords`, `test_a_generated_password_signs_the_account_in_and_is_not_stored_in_clear`, `test_running_the_seed_again_keeps_the_accounts_and_issues_nothing_new`. Missing: the acceptance asked for a forced change on first sign-in; there is no change-password endpoint (`docs/security/AUTH.md`, Open items). |
| T-08 | planned | mitigated | `require_role` (`app/api/auth/deps.py:61`) on import (`app/api/imports/router.py:39`, staff), upload (`app/api/documents/router.py:53`, staff), export (`app/api/reports/router.py:50`, staff) and decide (`app/api/decisions/router.py:38`, verifier). Tests: `test_a_verifier_may_not_import_and_an_anonymous_caller_gets_401` (`tests/integration/api/test_import.py`), `test_a_verifier_may_not_upload_and_an_anonymous_caller_gets_401` (`test_documents.py`), `test_staff_may_not_decide_and_an_anonymous_caller_gets_401` (`test_decisions.py`), `test_a_verifier_is_refused_the_export_and_nothing_is_audited` (`test_reports.py`). Note: roles are self-chosen at sign-up (T-38), so this separates duties, not people. |
| T-09 | planned | mitigated | `GET /api/documents/{id}/image` depends on `current_user` (`app/api/documents/router.py:132-134`); both roles may read by design (T-25). Tests (`tests/integration/api/test_application_detail.py`): `test_an_anonymous_caller_gets_401_from_the_detail_and_the_image`, `test_staff_may_read_the_image_and_an_unknown_document_is_404`, `test_the_image_comes_back_byte_for_byte_with_the_fixed_safe_headers`. |
| T-10 | planned | partly: decoders still run on untrusted bytes in process | Reduced: the type must match the first bytes (`app/domain/uploads.py:96`), the pixel cap is checked from the header before decoding (`:130-133`), images are decoded and re-encoded without metadata, a PDF is rasterised one page by poppler with a 30 second limit and a page-size check (`app/domain/pdf.py:21-47`), the step runs under a timeout and a compute slot (`app/api/documents/router.py:64-66`), and the engine runs in a killable child (`app/gateway/process.py`). Tests: `tests/test_uploads.py`, `tests/integration/test_pdf_rasterise.py`, `tests/test_process_engine.py`. Missing: no sandbox and no fuzzing; OpenCV, poppler and ONNX Runtime still parse attacker bytes. ADR-0009 (no malware scan, mitigate by limits) is still Proposed. |
| T-11 | planned | mitigated | Body cap 8 MiB while streaming (`app/domain/uploads.py:74`, `app/api/uploads.py`), pixel cap 25 million from the header before decoding (`app/domain/uploads.py:18`, `:130-133`), PDF page-size check before rasterising (`app/domain/pdf.py:33-47`), one shared compute slot for upload normalisation, hashing and OCR (`app/core/compute.py:34`, `app/api/documents/router.py:65`). Tests: `tests/test_uploads.py` `test_an_image_over_the_pixel_cap_is_refused_before_decoding` and `test_a_body_over_the_cap_is_refused_and_the_rest_is_never_read`; `tests/integration/test_pdf_rasterise.py` `test_a_pdf_whose_first_page_would_be_too_many_pixels_is_refused_before_it_is_rasterised`; `tests/integration/api/test_upload_memory.py` (three tests). Measured: four concurrent 25 megapixel PNG uploads plus four sign-ins and 34 documents peaked at 449,486,848 bytes in a 512,000,000 byte container with no OOM (`docs/performance/NOTASK-17-memory.md`). Limit: one worker only. |
| T-12 | planned | mitigated | `check_declared_type` refuses a file whose first bytes and declared type differ (`app/domain/uploads.py:96-103`); the stored form is a re-encoded image. Tests: `tests/test_uploads.py` `test_a_declared_type_that_disagrees_with_the_bytes_or_is_not_allowed_is_refused`; `tests/integration/api/test_documents.py` `test_any_other_format_is_refused_naming_the_accepted_ones_and_nothing_is_stored`. |
| T-13 | planned | partly: no test captures the logs | The client file name is never stored for documents and never logged: the upload log carries ids and the content type only (`app/api/documents/router.py:97-104`), the import log carries counts (`app/api/imports/router.py:59-65`), `file_name` and `filename` are redacted keys (`app/core/logging.py:30-31`, processor at `:43`), and the name never reaches a URL (`test_the_image_never_carries_a_name_the_client_chose`). Tests for the processor: `tests/test_logging_redaction.py` `test_a_personal_field_is_replaced_before_it_is_written` and `test_a_query_string_never_reaches_the_request_log`. Missing: the acceptance test that runs an import, an upload and a decision with known values and asserts none is in the captured logs (only the export has a check of that kind: `tests/integration/api/test_reports.py` `test_the_audit_row_has_no_column_that_could_hold_applicant_data`). The import's file name is kept in `imports` (`app/api/imports/router.py:80` `_source_name`, 255 characters) as data, not in logs. |
| T-14 | planned | mitigated | There is no file-system path to traverse: image bytes go to `document_blobs` in Postgres, `documents` has no name column (`alembic/versions/0002_core_schema.sql`), and the served name is built from the document id (`app/api/documents/router.py:160`). Test: `tests/integration/api/test_application_detail.py` `test_the_image_never_carries_a_name_the_client_chose`. |
| T-15 | planned | mitigated | Every text cell that starts with `=`, `+`, `-`, `@`, tab or carriage return is prefixed with an apostrophe: `app/domain/export.py:46`, applied to the reference, name, board, roll number, category and the verifier's display name (`:55-65`). Tests: `tests/test_export_csv.py` `test_a_cell_that_starts_like_a_formula_is_prefixed_so_it_shows_as_text`, `test_a_verifier_name_that_looks_like_a_formula_is_neutralised`, `test_a_malicious_name_is_neutralised_in_the_file`; `tests/integration/api/test_reports.py` `test_a_name_that_looks_like_a_formula_is_exported_as_text`. |
| T-16 | planned | mitigated | Import is capped at `import_max_bytes` 5,000,000 (`app/core/config.py:54`, read while streaming at `app/api/imports/router.py:45`) and `import_max_rows` 20,000 (`app/core/config.py:55`, `app/domain/importing.py:100-129`). Tests: `tests/test_import_csv.py` `test_a_file_over_the_size_cap_is_refused_before_it_is_read` and `test_a_file_with_more_rows_than_the_cap_is_refused`; `tests/integration/api/test_import.py` `test_a_file_over_the_size_cap_is_refused_with_413_and_creates_nothing`. |
| T-17 | planned | mitigated | Rows are validated per column; a repeated reference in the file or in the database is refused, not overwritten (`app/domain/importing.py`). Tests: `tests/test_import_csv.py` `test_a_repeated_application_id_in_the_file_is_refused_not_overwritten`, `test_an_application_id_already_in_the_database_is_refused`, `test_valid_rows_are_created_and_malformed_rows_are_listed_with_reasons`; `tests/integration/api/test_import.py` `test_importing_the_same_file_again_refuses_every_row_as_a_duplicate`. |
| T-18 | planned | mitigated | A refused row carries a row number, a column and a reason, never the value. Tests: `tests/test_import_csv.py` `test_a_refused_row_never_carries_the_value_that_failed`; `tests/integration/api/test_import.py` `test_no_cell_value_comes_back_or_is_stored_with_a_refused_row`. |
| T-19 | planned | mitigated | The database refuses UPDATE and DELETE on `decisions` except the erase marker, and TRUNCATE: function `decisions_guard` and trigger `trg_decisions_append_only` (`alembic/versions/0002_core_schema.sql:397-417`), `trg_decisions_no_truncate` (`:419-425`). The app has no edit or delete route. Tests: `tests/integration/api/test_decisions.py` `test_the_database_refuses_to_change_or_delete_a_logged_decision` and `test_the_log_has_no_way_to_edit_or_remove_an_entry`; `tests/integration/test_schema.py` `test_the_decision_log_guard_triggers_exist`. Limit: a database superuser can still drop the trigger, and the app connects as one role (T-30). |
| T-20 | planned | mitigated | Each decision stores `decided_by` (the user id), the action, the time and the reason, and the log is append-only (T-19). Tests (`tests/integration/api/test_decisions.py`): `test_approving_a_flagged_application_makes_it_verified_and_logs_who_and_when`, `test_either_role_reads_the_log_newest_first_with_who_what_when_and_why`. Limit: the shown name is self-chosen (T-38); the id is the actor. |
| T-21 | planned | mitigated | No route sets a status. It is computed from evidence (`app/domain/status.py:57`), and `request_status` refuses `verified` unless every field matched or an approval stands (`app/db/repositories/statuses.py:89-115`, `app/domain/status.py:69`). An approval also needs every required document (`tests/integration/api/test_decisions.py` `test_an_approval_cannot_stand_in_for_a_document_that_was_never_uploaded`). Tests: `tests/test_status_rules.py` `test_a_direct_request_for_verified_is_refused_without_a_match_or_a_decision`; `tests/integration/test_application_status.py` `test_a_direct_request_for_verified_is_refused_without_a_match_or_an_approval`. |
| T-22 | planned | partly: no test captures the logs | The decision log line carries ids, the action and the status only (`app/api/decisions/router.py:45-51`); `reason`, `old_value` and `new_value` are redacted keys (`app/core/logging.py:27-29`). Missing: the same end-to-end log-capture test as T-13. `db_echo` (`app/core/config.py:34`, off by default) would print SQL parameters if switched on. |
| T-23 | planned | partly: the entry exists but is not tamper-proof | Staff only (`app/api/reports/router.py:50`); one `export_audit` row per export with who and how many rows, written with the read (`app/db/repositories/reports.py:36`; table `alembic/versions/0002_core_schema.sql:112-126`), including an empty export. Tests (`tests/integration/api/test_reports.py`): `test_every_export_writes_one_audit_row_with_who_and_how_many`, `test_an_empty_export_is_audited_too`, `test_a_verifier_is_refused_the_export_and_nothing_is_audited`. Missing: the acceptance said the entry cannot be edited, and `export_audit` has no append-only trigger (a comment says it is never updated), unlike `decisions`. |
| T-26 | planned | mitigated by a different control than planned | The models ship inside the rapidocr 3.9.2 wheel (`app/gateway/rapidocr_engine.py:6`), the wheel is hash-locked in `uv.lock` and installed with `uv sync --locked` (`Dockerfile:8`), and nothing downloads at run time. Test: `tests/integration/test_rapidocr_engine.py` `test_reading_opens_no_network_connection`. Not built: the planned per-file checksum of the model files; the wheel hash stands in for it. |
| T-27 | planned | partly: bounded and measured for one workload, not for arbitrary traffic | The engine runs in a child killed after `read_timeout_seconds` (`app/core/config.py:49`) and replaced after every page (`:51`), behind the shared compute slot (`app/gateway/process.py`). Tests: `tests/test_process_engine.py` `test_a_read_that_runs_past_the_timeout_kills_the_child_and_says_so` and `test_default_recycling_releases_the_child_after_each_page`. Measured: 30 pages at a median 379,469,824 bytes peak, and the container run under T-11 at 449,486,848 bytes (`docs/performance/NOTASK-17-memory.md`). Missing: the 15,000 page run was not tried, one worker only, and the 400 MB hosting target of ADR-0004 is missed (the owner hosts on 1 GB, ADR-0018). |
| T-28 | planned | partly: no test captures the logs | Gateway calls log engine, outcome, units and an error class, never text (`app/db/repositories/gateway_calls.py:20-25`); an engine error crosses the process pipe as a class name only (`tests/test_process_engine.py` `test_an_error_inside_the_engine_crosses_as_a_class_name_never_the_message`); the worker logs ids and reason codes (`app/jobs/worker.py:102`, `:131`, `:219`); `value` is a redacted key. Missing: the same end-to-end log-capture test as T-13. |
| T-30 | planned | planned (re-checked, nothing built) | `app/db/session.py:19-25` passes the URL through with no TLS option and `app/core/config.py` has no TLS setting; no migration or script creates a second role or a `GRANT` (searched `alembic/`, `deploy/`, the compose files). The app and the migrations share `DATABASE_URL` (`alembic/env.py:22-24`). The append-only guard on `decisions` is a trigger, so it holds for any role except a superuser. |
| T-32 | mitigated | mitigated (reference moved) | `docs_url` and `openapi_url` are `None` when `ENV=production`: `app/main.py:132-139` (was `:46`). `tests/test_deploy_files.py` `test_the_production_api_runs_in_production_mode_with_secure_cookies_and_a_ceiling` checks the production stack sets the mode; no test requests `/docs` in production. |
| T-33 | mitigated | mitigated (reference moved) | The outer middleware turns any unhandled error into a 500 envelope with no detail: `app/core/middleware.py:58-63`, `app/core/errors.py:149-157` (was `app/main.py:57`). Tests: `tests/test_errors.py` `test_unhandled_error_is_500_without_detail` and `test_unhandled_error_log_keeps_the_class_but_not_the_message`. |
| T-34 | mitigated | mitigated (reference moved) | `USER app` after creating a system user with uid 10001: `Dockerfile:18` and `:22` (was `:19`). No test asserts it. |
| T-35 | mitigated | mitigated (reference moved) | `make vuln` runs `pip-audit --strict` over the locked runtime set (`Makefile:79-84`, was `:73`), it is one of the gates in `make check` (`Makefile:9`), and CI runs it (`.github/workflows/ci.yml:157`). The image installs with `uv sync --locked` (`Dockerfile:8`). Frontend dependencies are not covered by this gate. |

Unchanged: T-04, T-24, T-25, T-29, T-31, T-36, T-37 ("considered, none"; their reasons were not re-checked, except that `tests/integration/test_auth_api.py` `test_a_login_records_the_time_of_the_last_sign_in` confirms the `last_login_at` claim in T-04) and T-38 (accepted, ADR-0013).

Re-checked tally (31 threats): mitigated 20 (T-01, T-03, T-05, T-08, T-09, T-11, T-12, T-14 to T-21, T-26, T-32 to T-35), partly 9 (T-02, T-06, T-07, T-10, T-13, T-22, T-23, T-27, T-28), planned 1 (T-30), accepted 1 (T-38).


Not threats here and why: dependence on a third-party model API (none, ADR-0003); payments (none); webhooks and callbacks (none); multi-tenant isolation (single office, `docs/design/data-model.md` section 10); minors' consent and retention are privacy matters handled in `docs/privacy/DATA_MAP.md`.

## 5. Residual risks

| Threat | Risk accepted or planned | Owner (role) | Revisit |
| --- | --- | --- | --- |
| T-01 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-02 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-03 | planned: new story CSRF protection | backend lead rotation | 2026-11-15 |
| T-05 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-06 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-07 | planned: new story Seed accounts | backend lead rotation | 2026-11-15 |
| T-08 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-09 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-10 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-11 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-12 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-13 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-14 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-15 | planned: new story CSV hardening | backend lead rotation | 2026-11-15 |
| T-16 | planned: new story CSV hardening | backend lead rotation | 2026-11-15 |
| T-17 | planned in US-00-001 | backend lead rotation | 2026-11-15 |
| T-18 | planned in US-00-001 | backend lead rotation | 2026-11-15 |
| T-19 | planned in US-00-007 | verifier lead role | 2026-11-15 |
| T-20 | planned in US-00-007 | verifier lead role | 2026-11-15 |
| T-21 | planned in US-00-005 | backend lead rotation | 2026-11-15 |
| T-22 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-23 | planned: new story Audit entry for every export | admissions office operations role | 2026-11-15 |
| T-38 | accepted: open sign up with a self-chosen role (ADR-0013); revisit before any real student data | backend lead rotation | before any real student data |
| T-26 | planned: new story Pin and checksum the OCR models | platform rotation | 2026-11-15 |
| T-27 | planned in US-02-001, memory growth still to measure (ADR-0001) | platform rotation | 2026-11-15 |
| T-28 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-30 | planned: new story Database TLS and least-privilege role | platform rotation | 2026-11-15 |

> Update 2026-10-16 (NOTASK-29): the table above is as written on 2026-10-05. Current status of each row is in section 4a: T-01, T-03, T-05, T-08, T-09, T-11, T-12, T-14 to T-21 and T-26 are no longer open, T-02, T-06, T-07, T-10, T-13, T-22, T-23, T-27 and T-28 are `partly` with the missing part named there, and only T-30 is still `planned`. The 2026-11-15 revisit dates were not changed.

## 6. New stories needed

- Login hardening: rate limit, lockout and uniform errors (mitigates T-01, T-05, T-06), acceptance: after five failed attempts in a minute from one source the sixth is refused with the same message as a wrong password, and an unknown user and a wrong password take comparable time.
- CSRF protection for cookie sessions (mitigates T-03), acceptance: a state-changing request without the anti-forgery token or a matching `Origin` gets 403 and changes nothing.
- Seed accounts with generated one-time passwords (mitigates T-07), acceptance: the seed script prints a random password once, no password appears in the repository, and the first sign-in forces a change.
- Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names (mitigates T-10, T-11, T-12, T-14), acceptance: a file whose bytes are not a PNG, JPEG or PDF is refused whatever its name, an image over the pixel cap or a PDF over the page cap is refused before decoding, a document that takes longer than the timeout is marked failed, and stored names never come from the client.
- No personal data in logs or URLs, enforced by tests (mitigates T-13, T-22, T-28), acceptance: a test runs an import, an upload and a decision with known values and asserts none appears in the captured logs or any URL.
- CSV hardening: size and row caps, formula-safe export (mitigates T-15, T-16), acceptance: a file over the size or row cap is refused, and an exported cell that starts with `=`, `+`, `-` or `@` is prefixed so a spreadsheet shows it as text.
- Audit entry for every export of applicant data (mitigates T-23), acceptance: every export writes who, when and how many rows, and the entry cannot be edited.
- Pin and checksum the OCR models, bake them into the image (mitigates T-26), acceptance: the image build fails if a model file's checksum differs and the running service never downloads a model.
- Database TLS and a least-privilege API role (mitigates T-30), acceptance: a hosted configuration refuses a database URL without TLS, and the API role cannot run DDL or update `decisions` beyond the erase marker.

## 7. Counts

Not run. `threats_check.py` could not run in this session (no shell). Run:

```
python3 "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/threat-model/scripts/threats_check.py" docs/security/threat-model-docket.md
```

and paste its "Threats by category:", "threat-model:" and "Gate:" lines here. By my own count, not the gate's: assets 8, boundaries 7, entry points 14, 37 rows of which 30 are threats (mitigated 4, planned 26) and 7 are "considered, none".

> Update 2026-10-16 (NOTASK-29): `threats_check.py` was run and printed, for the section 4 table as written: `threat-model: 1 files, 31 threats (mitigated 4, planned 26, unmitigated 0; retired 0), mitigations: code 2, story 10, new story 17; 3 sensitive classes, 2 problems`, `Threats by category: S 3, T 8, R 1, I 10, D 4, E 5` and `Gate: FAILED (2 problems)`. The two problems are T-34 (`Dockerfile:19`) and T-35 (`Makefile:73`): the script's path pattern needs a file extension, so it cannot parse the extensionless files `Dockerfile` and `Makefile`. The original cells were kept; the current lines are in section 4a (`Dockerfile:22`, `Makefile:79-84`, `.github/workflows/ci.yml:157`).
>
> The line "30 threats, 4 mitigated, 26 planned" was right for 37 rows on 2026-10-05. The table now has 38 rows: 31 threats and 7 "considered, none", because T-38 (accepted, ADR-0013) was added, and the entry point count is 15, not 14. In the table as written the 31 threats are 4 mitigated, 26 planned and 1 accepted. After the re-check in section 4a they are 20 mitigated, 9 partly, 1 planned and 1 accepted. The script reads the status column of section 4 only, so it still reports the old split.
