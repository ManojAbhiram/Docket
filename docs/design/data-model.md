# Data model: Docket

**Store:** PostgreSQL · **Tables:** 12 · **Columns:** 106 · **Indexes:** 20 · **Personal-data columns:** 14

The database holds the staff and verifier accounts, the applications imported from a CSV, the uploaded documents with their image bytes, what the OCR engine read from each, how each field compared with the application, the status of each application, and an append-only log of verifier decisions and engine calls. The API reads and writes it; the OCR gateway writes `gateway_calls` and `extracted_fields`; the dashboard and export only read. One PostgreSQL 16 database is enough for every acceptance criterion (all of them are relational and consistency-critical), and it is already in `docker-compose.yml` and `app/db/session.py`.

- Task: US-02-002
- Serves: US-00-001, US-00-002, US-00-003, US-00-004, US-00-005, US-00-006, US-00-007, US-00-008, US-00-009, US-00-011, US-02-001, REQ-001 to REQ-034
- ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006 (sessions), ADR-0007 (image bytes in Postgres). The store itself is settled by the code (`docker-compose.yml`, `app/core/config.py`), not by an ADR.
- Stores: postgres
- Companion files: `docs/design/schema.sql`, `docs/design/data-dictionary.csv`, `docs/design/erd.md`
- Author: draft, unreviewed. 2026-10-05. Status: Draft. Version v1.

## 1. Why these stores

### PostgreSQL

**Holds:** every entity below.

Each acceptance criterion needs a foreign key or a constraint: a document belongs to one application, a status is exactly one of three (AC-US-00-005-5), a rejection needs a reason (AC-US-00-007-3), a decision survives its application (AC-US-00-007-5). Volumes are small: 5,000 applications, about 15,000 documents and about 120,000 extracted field rows for a July intake (estimates from `docs/product/PRD.md` B1 and three documents per application).

| Considered | Why not |
| --- | --- |
| MongoDB | The shapes are fixed and cross-referenced and the stories need foreign keys and constraints, not documents read whole. |
| ClickHouse | The dashboard counts five thousand rows by status, an ordinary index scan. Applications change status, which is an edit, not an append-only event. Analytics is out of scope (decisions log). |
| Object storage for the images | Right at 15,000 real photos (see the volume note under `document_blobs`) but needs another service; ADR-0007 keeps bytes in Postgres behind a storage interface and sets the trigger for moving. |

No second store is chosen here. A hosted deployment would move the images, not the rest. The index count in the headline is the 17 named secondary indexes in `schema.sql`; the ten primary-key indexes are not counted.

## 2. Entities: ownership and lifecycle

Single office, so there is no `tenant_id` anywhere (deviation recorded in section 10).

| Entity | Owner | Created by | Changed by | Ended by | Stories | PII | Retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| user | auth module | seed script | deactivation, sign-in time | never deleted | US-00-011 | yes | UNDEFINED |
| session | auth module | sign-in | each request (last seen), sign-out | expiry sweeper, user deletion | US-00-011 | no | absolute 8 h, idle 30 min (assumed, ADR-0006) |
| export audit entry | export route | each export of the verified list | never | never deleted by the app | US-00-009 | no | UNDEFINED |
| idempotency key | every creating route | first creating request with a key | the same request when it finishes (status, resource) | sweeper after 24 h, user deletion | US-00-001, US-00-002, US-00-007 | no | 24 h (stated in `api/openapi.yaml`) |
| import | import module | CSV upload | never | UNDEFINED | US-00-001 | no | UNDEFINED |
| import row error | import module | CSV upload | never | with its import | US-00-001 | no | with its import |
| application | applications module | CSV import | comparison and decision services (status), erase job | erased in place, row kept | US-00-001, US-00-004, US-00-005, US-00-006, US-00-008, US-00-009 | yes | UNDEFINED |
| document | documents module | upload | processing worker (status, type), re-upload (is_current) | with its application | US-00-002, US-00-003, US-00-005 | yes | UNDEFINED |
| document blob | documents module | upload | never | with its document | US-00-002, US-00-006 | yes | UNDEFINED |
| extracted field | extraction module | OCR gateway result | comparison service, verifier correction | with its document | US-00-003, US-00-004, US-00-005, US-00-006, US-00-007 | yes | UNDEFINED |
| gateway call | OCR gateway | each engine call | never | never deleted by the app | US-02-001 | no | UNDEFINED |
| decision | review module | verifier action | only the erase job, replacing free text | never deleted | US-00-007 | yes | UNDEFINED |

Not modelled: the dashboard counts, the export and the review queue, because they are queries (`status` plus the partial index), not stored data. A status history table, because no story reads past statuses. The required-documents list (Q-004) and the review thresholds (ADR-0005), because they are configuration. A login audit table, because no story reads it.

**Every writer, every column** (checked against the stories):

| Table | Writers | NOT NULL columns and where each path gets the value |
| --- | --- | --- |
| applications | CSV import; comparison service (status); decision service (status, `rejected_at`); erase job | All eight CSV columns are required and a row missing one is refused (AC-US-00-001-2), so `NOT NULL` holds on the only path that inserts. |
| documents | upload route; processing worker | `source_content_type`, `sha256`, `size_bytes` come from the upload itself. The type is not known at upload, so `detected_type` is nullable until the worker sets it (rules below). |
| extracted_fields | processing worker; verifier correction | Inserted only by the worker with `value`. A correction updates `value` and logs the old value in `decisions`, with `extracted_field_id` naming the row. |
| decisions | decision service | `reason` is required for reject by `chk_decisions_reject_needs_reason`, and `old_value`, `new_value`, `field_name` for correct; `extracted_field_id` names the changed field. |
| gateway_calls | OCR gateway | A `pending` row is committed before the engine runs, then updated to `ok` or `error`; a refused call writes `refused` with the same columns. |

**Processing rules.** The sequences the schema relies on. Each is a service rule, because the database cannot see across steps.

1. **Claiming and typing a document.** The worker claims a document with the single statement given under `documents` below (oldest `uploaded` row, `FOR UPDATE SKIP LOCKED`, `RETURNING id`); no row returned means nothing is waiting. When the engine returns, one transaction takes `SELECT ... FOR UPDATE` on the application row, sets `detected_type` and decides `is_current`: the new document becomes current and clears the previously current document of the same type only if its `created_at` is later, otherwise it is written with `is_current = false`. A retried older upload therefore cannot displace a newer one (AC-US-00-002-4), and `uq_documents_current_type` cannot fail inside the worker. The completion write is guarded like the claim: `UPDATE documents SET status = 'read' ... WHERE id = $1 AND status = 'processing'`, so a read that finishes after the sweeper marked the document `failed` changes nothing (review finding, HLD section 16).
2. **Logging a call.** Under `pg_advisory_xact_lock` the gateway checks the cap and inserts a `pending` row in `gateway_calls`, then commits. It then runs the engine and updates the row to `ok` or `error`. A crash leaves a `pending` row, which counts toward the cap so the count is never understated, and a sweeper later marks it `error`. The cap count is the number of rows whose outcome is not `refused`, read under the same lock so two workers cannot both pass it. A retry after `error` inserts a new row. Whether REQ-008's "exactly one call per document" allows a retry is an open question for the owner.
3. **Status precedence.** Needs review wins: a document that is `failed`, has type `unknown`, or has a field with `needs_review` makes the application Needs review (AC-US-00-005-2, AC-US-02-001-4). Otherwise a required document type with no document at all makes it Missing documents (AC-US-00-005-3, Q-004). Otherwise, with every field matching, it is Verified. A document that exists but could not be read is a person's job, not a missing upload. A verifier decision is an input: an `approve` logged after the latest read or failed document of the application makes the status Verified whatever the field flags say (AC-US-00-007-1), and a later upload or correction that changes a document or field makes the decision stale, so the rules above apply again. A `failed` or untyped document that a later `read` document of the same type has superseded is ignored. The decision service takes `SELECT ... FOR UPDATE` on the application row and refuses with 409 unless the status is Needs review and `rejected_at` is null, so two verifiers or a stale screen cannot both decide.
4. **A rejection clears on new evidence.** A new upload or a correction after a rejection clears `rejected_at` in the same update, because `chk_applications_rejected_in_review` forbids a rejected row that is no longer in review. The application returns to the queue.
5. **Import is one transaction with a savepoint per row.** The `imports` row is inserted with zero counts and updated at the end, so `chk_imports_counts_consistent` holds at both moments. A database refusal on a row (a duplicate reference raced by another import, a date outside the range, a wrong column count) is caught at its savepoint and recorded as `duplicate_application_ref`, `out_of_range` or `malformed_row`, so one bad row cannot abort the file.
6. **Erased applications leave every list.** The review queue index, the dashboard counts and the verified export all repeat `erased_at IS NULL`, so an erased application is not counted, listed or exported.

## 3. Relationships

| From | To | Cardinality | FK column | On delete | Why |
| --- | --- | --- | --- | --- | --- |
| users | sessions | one-to-many | sessions.user_id | CASCADE | A session means nothing without its user; users are deactivated, not deleted. |
| users | export_audit | one-to-many | export_audit.exported_by | RESTRICT | Audit: who exported applicant data (threat T-23). |
| users | idempotency_keys | one-to-many | idempotency_keys.user_id | CASCADE | A key means nothing without its user, and keys live 24 hours. |
| users | imports | one-to-many | imports.uploaded_by | RESTRICT | Audit: who imported. |
| users | documents | one-to-many | documents.uploaded_by | RESTRICT | Audit: who uploaded. |
| users | decisions | one-to-many | decisions.decided_by | RESTRICT | AC-US-00-007-5: the log keeps its author. |
| imports | import_row_errors | one-to-many | import_row_errors.import_id | CASCADE | Errors are read with their import (AC-US-00-001-3). |
| imports | applications | one-to-many | applications.import_id | SET NULL | Purging the import log must not delete applicants. |
| applications | documents | one-to-many | documents.application_id | CASCADE | Documents are the applicant's personal data and go with the record. |
| applications | decisions | one-to-many | decisions.application_id | RESTRICT | The log must outlive routine changes; erasure anonymises in place (section 8). |
| documents | document_blobs | one-to-one | document_blobs.document_id | CASCADE | The bytes go with the document. |
| documents | extracted_fields | one-to-many | extracted_fields.document_id | CASCADE | Derived from the document. |
| documents | gateway_calls | one-to-many | gateway_calls.document_id | SET NULL | The call count must survive a deleted document (AC-US-02-001-4). |
| extracted_fields | decisions | one-to-many | decisions.extracted_field_id | SET NULL | A correction names the exact field of the exact document it changed (AC-US-00-007-2); erasing a document must not break the log. |

The diagram and a sentence per relationship are in `docs/design/erd.md`.

## 4. PostgreSQL tables

Every column, its type, key, default, personal-data flag and Why is in `docs/design/data-dictionary.csv`, one row per column, so the two cannot drift. Below: the reason for each table and for the indexes and constraints that carry a rule.

### `users`: Staff and verifiers (hot: no)

Serves US-00-011. Volume: tens of rows (10^1), seeded. `uq_users_username` on `lower(username)` serves sign-in by name ignoring case. `chk_users_username_not_blank`, `chk_users_session_version_positive` and `chk_users_text_lengths` refuse a blank name, a zero version and an oversized value.

### `sessions`: Signed-in browsers (hot: no)

Serves US-00-011. Volume: 10^1 to 10^2 live rows, a sweeper deletes expired ones. `uq_sessions_token_hash` is the lookup on every request; `idx_sessions_user_id` serves logout everywhere and the foreign-key rule. `chk_sessions_expiry_after_creation` refuses a session that has already ended. Expiry is checked in the reading query (`expires_at > now()`), not in an index, so no predicate calls `now()`.

### `export_audit`: Exports of applicant data (hot: no)

Serves US-00-009 and threat T-23. Volume: a few rows a day (10^2 a year). The export route inserts one row in the same transaction that reads the Verified rows, so an export that returns data always has its entry. `chk_export_audit_row_count_not_negative` refuses a negative count. `idx_export_audit_exported_by` is the foreign-key index. The application role gets INSERT and SELECT only (migration 0003), so the log cannot be edited, and the table is never deleted by the application. Retention is UNDEFINED.

### `idempotency_keys`: Remembered creating requests (hot: no)

Serves US-00-001, US-00-002, US-00-007 (the three creating routes). Volume: 10^2 to 10^4 rows at any time, because a sweeper deletes keys older than 24 hours. The primary key `(user_id, key)` is the lookup and also the guard: the first request inserts the row before it does any work, so two concurrent retries cannot both proceed (the second sees the existing row and either waits for `response_status` or replays). `request_hash` separates a retry (same body, replay the first result) from a different request under the same key (409). Only the status and the id of the created resource are kept, so a replay re-reads the resource and no response body or personal data is stored. `idx_idempotency_keys_created_at` serves the sweeper. An upload also keeps its own `sha256` check in `documents`, but this table is what makes two identical concurrent uploads produce one document.

### `imports` and `import_row_errors`: CSV import runs (hot: no)

Serves US-00-001. Volume: tens of imports, up to 10^3 error rows. `chk_imports_counts_consistent` refuses an import whose created plus rejected rows do not equal the rows read. `import_row_errors.reason_code` is a closed set (`chk_import_row_errors_reason_code`) and no value is stored, so a minor's data never enters the error table. `idx_import_row_errors_import_id` lists one import's errors in row order.

### `applications`: Applicants and their status (hot: no)

Serves US-00-001, US-00-004, US-00-005, US-00-006, US-00-008, US-00-009. Volume 10^3 to 10^4 (5,000 for July). `uq_applications_application_ref` refuses a duplicate CSV application id at import. `idx_applications_review_queue` is a partial index on `(updated_at, id)` where `status = 'needs_review' AND rejected_at IS NULL AND erased_at IS NULL`: it serves the verifier queue (AC-US-00-006-1), and the query must repeat all three conditions literally. Dashboard counts and the verified export have no index: 5,000 rows scan in milliseconds, the count is a `GROUP BY status`, and both repeat `erased_at IS NULL` (processing rule 6). `marks` is `jsonb` because the subject set varies by board and no query filters on a subject; it is validated at the boundary and `chk_applications_marks_is_object` refuses a non-object. `chk_applications_rejected_in_review` refuses a rejected application that is not in review. `chk_applications_dob_range` refuses a date outside 1950 to 2020 (a typo or the wrong century).

### `documents`: Uploaded scans (hot: no)

Serves US-00-002, US-00-003, US-00-005. Volume 10^4. `uq_documents_current_type` is a partial unique index on `(application_id, detected_type)` where the document is current and typed: a re-upload of the same type replaces the older one for matching and the older one is kept (AC-US-00-002-4, Q-010). The type is only known after reading, so the worker sets it and the flag together under a row lock on the application, newest upload winning (processing rule 1). The original file name is not stored: no criterion reads it and it can contain a name. `idx_documents_application_id` orders an application's documents newest first for the review screen. `idx_documents_uploaded_created_at` is a partial index on `created_at` where `status = 'uploaded'`: the processing loop claims the oldest uploaded document with one statement, `UPDATE documents SET status = 'processing' WHERE id = (SELECT id FROM documents WHERE status = 'uploaded' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id`, and the query must repeat the predicate. `chk_documents_size_range` caps a file at 8 MiB, `chk_documents_content_type` closes the accepted formats (AC-US-00-002-2).

### `document_blobs`: Image bytes (hot: no, but large)

Serves US-00-002, US-00-006. Volume: 10^4 rows, but about 3 MB each for real phone photos is on the order of 4.5 x 10^10 bytes at 15,000 documents (estimate). The 30-document demo is about 5 MB. Neon's free tier holds 1 GB, so the demo is the supported size; moving to object storage is the trigger in ADR-0007 (more than 500 documents or 1 GB). The bytes sit in their own table so `documents` stays narrow and a later move drops one table. A PDF is stored as its first page rasterised to JPEG at no more than 200 dpi, which keeps it well under the cap; the original PDF is not kept, which is an assumption about AC-US-00-002-1 ("the file is stored") for the product owner. `chk_document_blobs_size_range` repeats the 8 MiB cap at the database.

### `extracted_fields`: What the engine read (hot: yes during processing)

Serves US-00-003, US-00-004, US-00-005, US-00-006, US-00-007. Volume 10^5 (up to eleven rows per marksheet: six fields plus five subjects, fewer on an ID proof or transfer certificate, so about 10^5 for 15,000 documents). It is hot only while a batch is processed. `uq_extracted_fields_document_field` allows one row per field per document, and per subject for marks, and serves reading a document's fields. `chk_extracted_fields_subject_only_for_marks` ties `subject` to the marks field. `chk_extracted_fields_review_flag_matches_reason` makes `needs_review` true exactly when a `review_reason` exists, and `chk_extracted_fields_review_reason_known` closes the reasons to the ones ADR-0005 defines. `confidence` is per field because `CONSTRAINTS.md` section 3.1 asks for it.

### `gateway_calls`: Engine call log (hot: no)

Serves US-02-001. Volume 10^4 to 10^5 (calls plus retries). The running call count against the cap is a `count(*)` over this table, taken under an advisory lock together with the insert of a `pending` row (processing rule 2), so it survives a restart (Q-009 assumption) and two workers cannot both pass the cap; at 10^5 rows it is a few milliseconds, so no index serves it. `uq_gateway_calls_document_ok` allows exactly one successful call per document (AC-US-00-003-1) while letting a failed call be retried. `chk_gateway_calls_cost_zero` makes the zero cost a fact in the table, and `error_class` holds a class name, never a message that could carry document text.

### `decisions`: The decision log (hot: no)

Serves US-00-007. Volume 10^3 (about 600 flagged applications for July). Append-only: `trg_decisions_append_only` refuses a delete and any update except replacing `reason`, `old_value` or `new_value` with `[erased]` and nulling `extracted_field_id`; `trg_decisions_no_truncate` refuses `TRUNCATE`, which a row trigger does not see. A trigger cannot stop a superuser from disabling it, so the real boundary is the roles (migration 0003): the owner role runs migrations and the erase function, the API role has `INSERT` and `SELECT` only on this table and never connects as the owner. `chk_decisions_reject_needs_reason` and `chk_decisions_correct_needs_values` carry AC-US-00-007-3 and AC-US-00-007-2, and `extracted_field_id` says which field of which document a correction changed. That `decided_by` is a verifier is a service rule: a CHECK cannot read another table. `idx_decisions_application_id` returns one application's history in time order; `idx_decisions_extracted_field_id` serves the foreign key.

## 5. MongoDB

Not used.

## 6. ClickHouse

Not used.

## 7. Enumerations

| Name | Values | Why |
| --- | --- | --- |
| `user_role` | `staff`, `verifier` | The two roles of the product (spec 4); a third is an ADR and a migration. |
| `application_status` | `verified`, `needs_review`, `missing_documents` | AC-US-00-005-5: exactly these three; rejected is a flag, not a status (Q-006). |
| `document_type` | `10th_marksheet`, `12th_marksheet`, `id_proof`, `transfer_certificate`, `unknown` | AC-US-00-003-2 plus the stretch type (Q-007); `unknown` sends the application to Needs review. |
| `document_status` | `uploaded`, `processing`, `read`, `failed` | The lifecycle the worker moves through. |
| `field_name` | `name`, `father_name`, `dob`, `board`, `roll_number`, `marks`, `document_number` | The fields the matching rules know (REQ-012 to REQ-016); `document_number` is read but never compared. |
| `match_result` | `match`, `mismatch`, `skipped` | AC-US-00-004-5: a field the document type does not carry is skipped, not a mismatch. |
| `call_outcome` | `pending`, `ok`, `error`, `refused` | AC-US-02-001-3 and 4: every call is logged before it runs, and a call refused at the cap is recorded. |
| `decision_action` | `approve`, `correct`, `reject` | AC-US-00-007-1 to 4. |

## 8. Retention and personal data

Rules marked **UNDEFINED** are decisions owed by a person before real data is used; this document does not make them. Nothing in the repository states a lifetime for applicant data, and the product handles minors' data (see `docs/privacy/DATA_MAP.md`).

| Table | Rule | Mechanism | Source |
| --- | --- | --- | --- |
| `applications` | UNDEFINED (asked: how long after the admission cycle ends? owner: product owner and legal) | none until decided | not stated |
| `documents`, `document_blobs`, `extracted_fields` | UNDEFINED (go with their application; asked: do images outlive the decision?) | cascade from the application | not stated |
| `decisions` | UNDEFINED (asked: how long must the audit log be kept? owner: product owner) | never deleted; erasure replaces free text with `[erased]` | not stated |
| `imports`, `import_row_errors` | UNDEFINED (asked: are import logs kept after the intake?) | none | not stated |
| `gateway_calls` | UNDEFINED (asked: how long is the call log kept?) | none | not stated |
| `users` | UNDEFINED (asked: when is a leaver's account removed?) | deactivate only | not stated |
| `sessions` | absolute 8 hours, idle 30 minutes | a daily sweeper deletes expired rows | assumption, ADR-0006, unconfirmed |

**Erasure of one applicant** (the mechanism, not a schedule): one `SECURITY DEFINER` function, `erase_application(id)`, owned by the owner role and created in migration 0003. The API role gets `EXECUTE` on it and no `UPDATE` on `decisions`. In one transaction it deletes the application's documents (cascading to blobs and fields, and nulling `gateway_calls.document_id` and `decisions.extracted_field_id`), replaces the personal columns of `applications` with placeholders (`'[erased]'` for the names, roll number and category, the application's own uuid as text for `application_ref`, which is 36 characters and fits the 40 cap and stays unique, `{}` for `marks`, `1950-01-01` for `date_of_birth`) and sets `erased_at`, and replaces `reason`, `old_value` and `new_value` in that application's decisions with `[erased]`. The application row and its decisions stay, because the decision log must not lose its parent, and every list repeats `erased_at IS NULL`. It runs only on a request, never on a schedule, because no period is decided. No story owns it yet (open concern).

Personal-data columns (14): `users.username`, `users.display_name`, `applications.application_ref`, `applications.full_name`, `applications.father_name`, `applications.date_of_birth`, `applications.roll_number`, `applications.marks`, `applications.category`, `document_blobs.content`, `extracted_fields.value`, `decisions.reason`, `decisions.old_value`, `decisions.new_value`. Two columns were removed after review because no criterion read them: `documents.original_name` (a file name can hold a name) and `extracted_fields.engine_value` (the old value is already in `decisions.old_value`). `imports.source_name` is the office's file name, not an applicant's, and is not flagged.

## 9. Migration plan

The repository uses Alembic with sequential four-digit revisions; `0001_init` creates `schema_probe`.

| # | db-migration name | Phase (expand, migrate or contract) | Hot table | Lock risk and batch note |
| --- | --- | --- | --- | --- |
| 0002 | core_schema (from schema.sql, also drops `schema_probe`) | expand | no | empty database apart from the probe, no lock risk. `schema.sql` is pasted as one `op.execute` per statement without `BEGIN` and `COMMIT`, with a Down that drops everything in reverse, run by `make migrate-verify`. Dropping `schema_probe` is the contract step for the probe. |
| 0003 | roles_and_erase_function | expand | no | creates the owner role (migrations and the erase function) and a separate API login role with `SELECT, INSERT, UPDATE, DELETE` on named tables, but only `INSERT` and `SELECT` on `decisions` and no DDL; creates `erase_application(id)` as `SECURITY DEFINER` with `search_path` set empty and `EXECUTE` for the API role only; runs `REVOKE ALL ON SCHEMA public FROM PUBLIC`. Needs a second database URL: `app/core/config.py`, `alembic/env.py` and `.env.example` gain a `MIGRATION_DATABASE_URL`, because today both use one `postgres` superuser URL (`docker-compose.yml:6`, `.env.example:6`). No lock risk on empty tables. |

No table is hot (all under 10^6 rows), so no batching or concurrent index builds are needed.

## 10. Rules and deviations

Rules checked: 24 against `database/references/postgres.md`. Deviations: 7.

- deviation: multi-tenant rules (`tenant_id` first, row-level security, tenant-safe references), because the product is one admissions office. Revisit when a second institution is added, which adds `tenant_id` to every table and a `UNIQUE (tenant_id, id)` parent key.
- deviation: derived state stored (`applications.status`, `extracted_fields.match_result`), because the dashboard, the export and the review queue index read it and a decision sets it. The comparison service updates field results and status in one transaction. Revisit if drift is found.
- deviation: `gen_random_uuid()` (v4) ids, allowed by the reference only on tables that stay small. Every table stays under 10^5 rows except `extracted_fields` and `gateway_calls`, which use `bigint` identity.
- deviation: image bytes in a `bytea` column (not a reference rule), because free hosts have ephemeral disks. ADR-0007 sets the trigger for moving to object storage.
- deviation: `decisions` has no `updated_at`, because it is append-only; the trigger allows only the erase marker.
- deviation: the invariant "Verified only when all fields match or a verifier decided" (REQ-019, AC-US-00-005-4) is enforced in the service, not the database, because it spans three tables. Revisit with a deferred constraint trigger if a path is found that skips the service.
- deviation: that `decisions.decided_by` is a verifier, and that a `created_at` is not backdated, are service rules, because a CHECK cannot read another table and the table has no insert trigger. The API role cannot set `created_at` beyond its default if the service never passes it. Revisit with an insert trigger if a path writes the column.

## 11. What the review found

Reviewed by: critic, 2026-10-05. Findings: BLOCKER 0, MAJOR 5, MINOR 4, NIT 1 (open 1, a build item).

### MAJOR: the document type is unknown at upload, so "newest current document" had no defined sequence (`documents`)

`uq_documents_current_type` keys on `detected_type`, which is null until the worker sets it, and a retried older upload could overwrite a newer one. Missing documents and Needs review also collided for documents that could not be read. **Fix:** processing rules 1 and 3 (a row lock on the application, newest upload wins, Needs review takes precedence). Status: fixed in this version.

### MAJOR: the call-uniqueness index guarded the log, not the call (`gateway_calls`)

A crash between a successful call and its row, or a retry after one, left the call unlogged or the cap understated, and the cap check raced across the two workers. **Fix:** a `pending` row is committed before the call, the cap is checked under an advisory lock, and a sweeper marks stale `pending` rows `error` (processing rule 2, new `pending` outcome). Status: fixed in this version. Whether a retry is allowed under REQ-008 is an open question for the owner.

### MAJOR: append-only on `decisions` was not yet a mechanism (`decisions`)

Today the app and alembic share one `postgres` superuser URL, and a superuser can truncate the table or disable its trigger. **Fix:** a `BEFORE TRUNCATE` trigger, a separate owner role and API role in migration 0003, and erasure through a `SECURITY DEFINER` function so the API never holds `UPDATE`. Status: fixed in the design; the `MIGRATION_DATABASE_URL` setting in `config.py`, `alembic/env.py` and `.env.example` is still to be built (open).

### MAJOR: erased applications stayed live in the queue, dashboard and export (`applications`)

**Fix:** the queue index and every list repeat `erased_at IS NULL` (processing rule 6); the erased `application_ref` is the application's uuid text, which fits the 40 cap. Status: fixed in this version.

### MAJOR: a correction could not say which document it changed (`decisions`)

An application can have a name on several documents. **Fix:** `decisions.extracted_field_id`, with the guard allowing only the nulling erasure causes. Status: fixed in this version.

### MINOR: cited ADRs were missing and a PDF page could exceed the size cap

**Fix:** ADR-0006 (sessions) and ADR-0007 (image bytes) are written, with the session times and the move trigger marked as assumptions. A PDF is rasterised to JPEG at no more than 200 dpi and the original is not kept (an assumption for the owner). Status: fixed in this version.

### MINOR: import constraints could abort a whole import, and a rejection could strand a row

**Fix:** processing rules 4 and 5 and two more reason codes. Status: fixed in this version.

### MINOR: `schema.sql` could not be pasted into a migration

**Fix:** section 9 and the file header say how it becomes migration 0002. Status: fixed in this version.

### MINOR: personal data nobody reads

`documents.original_name` and `extracted_fields.engine_value` are removed; `category` is flagged as sensitive and queued as a question in the DPIA. Status: fixed in this version.

### NIT: counts and wording

The headline now says the 17 indexes exclude primary keys; "about eight rows per document" is corrected; the migration table header is fixed. Status: fixed in this version.

## 12. Open concerns

- **[gap]** No story owns `erase_application(id)` or the sweeper for stale `pending` calls and expired sessions. Owner: product owner and engineering lead, by 2026-10-31. Blocks development: no, blocks real data.
- **[ambiguity]** REQ-008 says "exactly one call per document"; the model allows a retry after an `error`. Which reading is meant? Owner: product owner, by 2026-10-31. Blocks development: no.
- **[risk]** `MIGRATION_DATABASE_URL` does not exist yet: until it does, the app connects as a superuser and the append-only guarantee on `decisions` is only as strong as the trigger. Owner: engineering lead, by the first migration. Blocks development: yes, for migration 0003.
- **[conflict]** Erasure versus the append-only log: `decisions` references `applications` with RESTRICT and its trigger refuses any update except the erase marker and the field-link null, so erasure anonymises in place instead of deleting. This keeps the audit trail but leaves a pseudonymous application row for every erased child. Owner: product owner and legal, by 2026-10-31. Blocks development: no, blocks real data.
- **[gap]** No retention period is stated for any applicant data (section 8). Owner: product owner, by 2026-10-31. Blocks development: no, blocks real data.
- **[gap]** The 8 MiB file cap and the 8 hour and 30 minute session times are assumptions. Owner: product owner, by 2026-10-31. Blocks development: no.
- **[risk]** `document_blobs` in Postgres does not scale to real photos (4.5 x 10^10 bytes estimated at 15,000 documents against Neon's 1 GB). Owner: engineering lead, trigger in ADR-0007. Blocks development: no.
- **[ambiguity]** "Retried up to N times" does not appear in the stories, but a failed gateway call can be retried: the model allows any number of `error` rows and one `ok` row per document. Owner: engineering lead, by 2026-10-31. Blocks development: no.
- **[scope]** No `application_status_history` table: if product wants a status audit beyond decisions, it is a new table and migration. Owner: product owner. Blocks development: no.

## 13. Applying this

`schema.sql` runs top to bottom in one transaction against an empty database: enum types first, then tables in foreign-key order. It becomes migration 0002; every change after the first release is its own migration, never an edit to this file.

- Gate: not run (no shell in this session); run `python3 "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/data-model/scripts/model_check.py" --dir docs/design`
- Applied to an empty Postgres: not run; run `bash "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/data-model/scripts/apply_check.sh" docs/design/schema.sql`
