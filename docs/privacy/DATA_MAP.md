# Data map

Regime: both (GDPR terms with the DPDP equivalents in brackets: data principal, data fiduciary). Controller (data fiduciary): unconfirmed, the organisation that runs Docket. Privacy contact: unconfirmed.
Source: `docs/design/data-model.md` (95 columns, 14 personal-data columns), `docs/design/schema.sql`, `app/` as of 2026-10-05. Last reviewed: 2026-10-05, Proposed, no reviewer named.

Status of everything below: **Proposed.** No privacy notice, retention schedule, processor contract or accepted privacy ADR exists, so no promise could be tested against the system. The application does not store anything yet: the tables are designed, not migrated.

Identifiers this map looks for: email, phone, name, address, date of birth, ip address, device id, national id, tax id, pan, aadhaar, passport, payment card, location, photo, biometric, health, employment, financial.

## Whose data this is

Applicants to a university are mostly minors (the seed's dates of birth start in 2006). The product also records a community category, which is sensitive in practice. `brg_privacy` is mandatory (`spec.md:L113`). A DPIA is required before real data is used: `docs/privacy/DPIA-admissions-verification.md`.

## Is the data synthetic?

Unchanged from the earlier check: every name, date, roll number and id in the seed comes from fixed lists or the seeded generator, carries a `SYN` marker, and every rendered page says "SAMPLE, SYNTHETIC DOCUMENT" (`seed/dataset.py`, `seed/pages.py`, `tests/test_seed_documents.py`). The repository holds no real student data that I read. **Not checked:** I could not search the whole tree or the git history for real-looking data (no grep tool), so a person runs a repository PII and secret scan before the first push.

## Elements

Retention and deletion are `UNDEFINED` because nobody has decided them; erasure is a designed mechanism (data model section 8), not a built one.

| # | Kind | Store.table.column | Purpose | Lawful basis | Collected from | Shared with | Retention | Deletion mechanism | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | username (staff identity) | `postgres.users.username` | sign-in | UNDEFINED | seed script | none | UNDEFINED | deactivate, never delete | unconfirmed |
| 2 | name (staff) | `postgres.users.display_name` | name in the decision log | UNDEFINED | seed script | none | UNDEFINED | deactivate, never delete | unconfirmed |
| 3 | application id | `postgres.applications.application_ref` | key of the imported record | UNDEFINED | admissions CSV | none by design | UNDEFINED | erase in place | unconfirmed |
| 4 | name (child) | `postgres.applications.full_name` | compare with documents | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 5 | name (father) | `postgres.applications.father_name` | compare with documents | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 6 | date of birth | `postgres.applications.date_of_birth` | compare with documents | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 7 | roll number | `postgres.applications.roll_number` | compare with marksheets | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 8 | academic marks | `postgres.applications.marks` | compare with marksheets | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 9 | community category | `postgres.applications.category` | admission record | UNDEFINED | CSV | none | UNDEFINED | erase in place | unconfirmed |
| 10 | document image (holds rows 4 to 9 on the page) | `postgres.document_blobs.content` | verification evidence | UNDEFINED | staff upload | the OCR engine in process | UNDEFINED | cascade with the document | unconfirmed |
| 11 | extracted field value | `postgres.extracted_fields.value` | stored evidence (REQ-018) | UNDEFINED | OCR output | none | UNDEFINED | cascade with the document | unconfirmed |
| 12 | verifier reason | `postgres.decisions.reason` | accountability, free text | UNDEFINED | verifier | none | UNDEFINED | replace with `[erased]` | unconfirmed |
| 13 | corrected old value | `postgres.decisions.old_value` | audit of a correction, holds what the engine read | UNDEFINED | verifier | none | UNDEFINED | replace with `[erased]` | unconfirmed |
| 14 | corrected new value | `postgres.decisions.new_value` | audit of a correction | UNDEFINED | verifier | none | UNDEFINED | replace with `[erased]` | unconfirmed |
| 15 | request logs | stdout from `app/core/middleware.py:60` (method, path, status, duration) | operations | UNDEFINED | requests | the host's log store (unconfirmed) | UNDEFINED | host default | unconfirmed |
| 16 | exported verified list | CSV downloaded by staff (copies outside the system) | hand the result on | UNDEFINED | `GET /api/exports/verified.csv` | whoever receives it | UNDEFINED | none: a file on a laptop is outside the system | unconfirmed |

map: 16 elements, UNDEFINED retention 16.

Columns the review removed because no criterion read them: `documents.original_name` (a file name can hold a name) and `extracted_fields.engine_value` (the old value is already in row 13). The client's file name is received on upload and discarded.

Notes that change what is needed before real data is used:

- **Erasure** anonymises in place instead of deleting the application: `decisions` references `applications` with `RESTRICT` and is append-only, so the application row stays, its personal columns become placeholders and `erased_at` is set (data model section 8). That keeps a pseudonymous row for every erased child.
- **Request logs (row 15)** carry the path, which will hold uuids, never names, and no query string (`middleware.py:38` binds `scope["path"]`, not the query). Safe only while no route puts personal data in a path.
- **Row 16** is the weakest link: one export is a bulk copy of children's data that leaves every control. The threat model has T-23 and a new story for an audit entry per export.

## Processors and third parties

| Name | Elements | Purpose | Contract / DPA | Deletion API or contact |
| --- | --- | --- | --- | --- |
| none for the default design | the OCR engine runs inside the API process (ADR-0001, `CONSTRAINTS.md:L34-L36`) | | | |
| Render, Neon, Cloudflare (proposed demo hosts, ADR-0004) | rows 1 to 15 if real data were ever uploaded | hosting | none, free tiers | not found. **Synthetic data only, so they hold no personal data** |
| Gemini API | not used (ADR-0003: no LLM fallback) | | | |

## Consent purposes

None designed. For children's data the question is whether consent (of a parent or guardian), a legal obligation or a statutory exemption is the basis; that is a legal decision, not a design one, and it is open (DPIA section 2).

## Backups

Retention of backups: UNDEFINED. Neon Free backup behaviour was not found (`docs/research/free-hosting.md`); the local compose database has no backup at all. A restore would bring back erased rows unless it replays the erasure list, which is not designed.

## Logs

Scanned: the five logging calls in `app/` (`app/core/middleware.py:60`, `app/core/errors.py` the unhandled-error line, `app/api/health/router.py:46`, `app/main.py` startup and shutdown). logs: 5 calls scanned, PII hits 1.

- **Hit, fixed in this change:** the unhandled-error line used `log.exception`, which rendered the traceback with its exception message through `structlog.processors.format_exc_info` (`app/core/logging.py:35`). A PostgreSQL unique violation names the key, so a duplicate CSV row would have written an applicant id into the logs. It now logs the exception class and up to eight `file:line function` frames, never the message. Test: `tests/test_errors.py::test_unhandled_error_log_keeps_the_class_but_not_the_message` fails on the old code.
- **Configuration hazard, not changed:** `db_echo` (`app/core/config.py`, used at `app/db/session.py:24`) logs SQL with its parameters. It is off by default; turning it on with real data writes personal values to logs. Listed in the DPIA as a rule, not as code.
- Validation errors already drop the submitted input from the response (`app/core/errors.py:96` excludes `input`), which is a good control.

## DPIA

Required, because the scope processes children's data and a community category at admission scale: `docs/privacy/DPIA-admissions-verification.md`. Status: Proposed, unsigned.
