# Data map

Regime: both (GDPR terms, DPDP equivalents in brackets: data principal, data fiduciary). Controller (data fiduciary): unconfirmed, the organisation that runs Docket. Privacy contact: unconfirmed.
Source: `spec.md` sections 5 and 9, `docs/product/PRD.md`, `seed/dataset.py`, `app/` and `alembic/versions/0001_init.py` as of 2026-10-05. Last reviewed: 2026-10-05, Proposed, no reviewer named.

Status of everything below: **Proposed.** No privacy notice, retention schedule, processor contract or accepted ADR exists, so no promise could be tested against the system.

Identifiers this map looks for: email, phone, name, address, date of birth, ip address, device id, national id, tax id, pan, aadhaar, passport, payment card, location, photo, biometric, health, employment, financial.

## Is the data synthetic?

`CONSTRAINTS.md` section 2 and `spec.md:L109` require synthetic data only. What was checked, by reading the code:

| Check | Result | Evidence |
| --- | --- | --- |
| Every given name, surname and father's name comes from a fixed list in the code | Yes | `seed/dataset.py` `GIVEN_NAMES`, `FATHER_GIVEN_NAMES`, `SURNAMES`; asserted by `tests/test_seed_documents.py` |
| Dates of birth, roll numbers, marks and ID numbers are generated, not read from a file | Yes | `seed/dataset.py` `SeededRng`, `_build_applications`, `_build_document` |
| Roll numbers and ids carry a synthetic marker | Yes: `SYN`, `SYNID`, `SYNTC` prefixes | `tests/test_seed_documents.py` |
| Every rendered page says it is a sample | Yes: footer "SAMPLE, SYNTHETIC DOCUMENT, NOT A REAL RECORD" | `seed/pages.py` |
| No photographs, no real board seals, no real signatures on the pages | Yes: pages hold text and tables only | `seed/pages.py` |
| Nothing is read from outside the repository | Yes: the seed imports no file, network or database reader | `seed/dataset.py`, `seed/__main__.py` |
| Generated files stay out of git | Yes: `data/seed/` is ignored | `.gitignore` |

The names are common first names and surnames combined from short lists, so a generated name can coincide with a real person's. A name match is not a record match, and the roll numbers and ids cannot match a real board's format.

**Not checked:** I could not search the whole tree or the git history for real-looking student data (no shell, no grep tool). The files I read or wrote this session contain none. A person should run a repository secret and PII scan before the first push.

## Elements

The product stores nothing yet: `alembic/versions/0001_init.py` creates no application or document table (`app/db/models.py` is empty of domain models). The rows are the personal data the PRD says the product will hold, plus the seed's synthetic mirror. Retention and deletion are `UNDEFINED` because nobody has decided them.

| # | Kind | Store.table.column | Purpose | Lawful basis | Collected from | Shared with | Retention | Deletion mechanism | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | name | planned `applications.name` (REQ-002) | match against documents | UNDEFINED | admissions CSV import | none by design | UNDEFINED | none exists | unconfirmed |
| 2 | name (father) | planned `applications.father_name` (REQ-002) | match against documents | UNDEFINED | CSV import | none | UNDEFINED | none exists | unconfirmed |
| 3 | date of birth | planned `applications.date_of_birth` (REQ-002) | match against documents | UNDEFINED | CSV import | none | UNDEFINED | none exists | unconfirmed |
| 4 | national or board id | planned `applications.roll_number` (REQ-002) | match against marksheets | UNDEFINED | CSV import | none | UNDEFINED | none exists | unconfirmed |
| 5 | academic record | planned `applications.marks_by_subject` (REQ-002) | match against marksheets | UNDEFINED | CSV import | none | UNDEFINED | none exists | unconfirmed |
| 6 | community category | planned `applications.category` (REQ-002) | admission records | UNDEFINED | CSV import | none | UNDEFINED | none exists | unconfirmed |
| 7 | document image | planned upload store (REQ-004), holds rows 1 to 5 on the page | verification evidence | UNDEFINED | staff upload | the OCR engine, in process | UNDEFINED | none exists | unconfirmed |
| 8 | extracted fields | planned `documents.extracted` JSON (REQ-010, REQ-018) | stored evidence for Verified applications | UNDEFINED | OCR output | none | UNDEFINED | none exists | unconfirmed |
| 9 | staff and verifier identity | planned decision log "who" (REQ-027, Q-013) | accountability | UNDEFINED | sign-in | none | UNDEFINED | none exists | unconfirmed |
| 10 | free-text reason | planned decision log reason (REQ-026, REQ-027) | accountability; may contain personal data typed by a verifier | UNDEFINED | verifier | none | UNDEFINED | none exists | unconfirmed |
| 11 | request logs | stdout logs from `app/core/logging.py`, `app/core/middleware.py` | operations | UNDEFINED | requests | the host's log store (unconfirmed) | UNDEFINED | host default | unconfirmed |
| 12 | synthetic mirror of rows 1 to 8 | `data/seed/` (ignored), the dev database | tests and evals | not personal data: synthetic | `seed/` | none | until `rm -r data/seed` | delete the folder; rebuild with `python -m seed` | engineering |

map: 12 elements, UNDEFINED retention 11 (row 12 has a defined end).

Notes that change what is needed before real data is used:

- **Children's data.** Applicants are mostly minors (dates of birth in `seed/dataset.py` start in 2006). `brg_privacy` is mandatory (`spec.md:L113`). Under DPDP the processing of a child's data needs verifiable parental consent; GDPR sets its own age rules. Neither is designed.
- **Community category** (row 6) is sensitive in practice even where the law does not name it a special category.
- **OCR text is personal data.** The gateway must log engine, latency and counts, never the OCR text or the field values (`CONSTRAINTS.md:L37` lists what it logs, and it does not include them).
- **Logs (row 11).** Logging calls in `app/` were not scanned (no search tool). Request ids are bound; whether any call logs a body or a name is unchecked.

## Processors and third parties

| Name | Elements | Purpose | Contract / DPA | Deletion API or contact |
| --- | --- | --- | --- | --- |
| none for the default design | the OCR engine runs inside the API process (`CONSTRAINTS.md:L34-L36`) | | | |
| Render, Neon, Cloudflare (proposed demo hosts, `docs/research/free-hosting.md`) | rows 7 to 11 if real data were ever uploaded | hosting | none; free tiers | not found. **Synthetic data only, so they receive no personal data** |
| Gemini API (fallback 2 only) | page images | OCR | none; free-tier terms allow training use and human review | none. **Never with real data** |

## Consent purposes

None designed. Not applicable to the synthetic demo.

## Backups

Retention of backups: UNDEFINED. Neon Free backup behaviour was not found (`docs/research/free-hosting.md`). A restore replaying a deletion log is not designed because no deletion exists.

## DPIA

Not required for the synthetic demo because it holds no real personal data, no special category, no real children's data, no monitoring and no profiling. **Required before any real data** because the product processes children's data and a community category at admission scale; a draft belongs in `docs/privacy/DPIA-admissions-verification.md` and needs a decider.
