# Data protection impact assessment: Docket (admissions document verification)

| Field | Value |
| --- | --- |
| Date | 2026-10-05 |
| Owner | unconfirmed: the product owner |
| Reviewed by | unconfirmed: no privacy contact named |
| Regime | both (GDPR, DPDP) |
| Trigger | children's data; a community category; processing at admission scale |

Status: Proposed, unsigned. The synthetic demo holds no real personal data, so nothing here is a precondition for it. Everything here is a precondition for real data.

## 1. Processing described

Rows 3 to 14 of `docs/privacy/DATA_MAP.md`: applicant name, father's name, date of birth, roll number, marks, community category, the uploaded marksheets, ID proofs and transfer certificates, what the OCR engine read from them, and the verifiers' decisions with free-text reasons. The data subjects are applicants to a university, most of them minors, about 5,000 in an intake (the use case in `spec.md:L11`). The data comes from the admissions office's CSV and from scans the office uploads. The purpose is to check each application against its documents and route mismatches to a person. It is shared with no one by design: the OCR engine runs inside the service (ADR-0001) and no model API is used (ADR-0003). Retention and lawful basis are undecided (data map rows 3 to 14, all UNDEFINED).

## 2. Necessity and proportionality

- **What is collected is what the office already holds** and what verification compares: name, father's name, date of birth, roll number, marks and board are each compared by a rule (`docs/product/PRD.md` REQ-012 to REQ-016). The community category is stored because the CSV carries it (REQ-002); no rule compares it, so it should be dropped from the table unless a story needs it. Open question for the product owner.
- **Images are kept** as the evidence for a Verified status (REQ-018). Whether they are kept after the decision is undecided.
- **No more data is generated than needed:** import errors store a reason code, never the value (`import_row_errors`); the engine call log stores counts and a class name, not text (`gateway_calls`).
- **Lawful basis for children's data is open.** Whether a parent's or guardian's consent, a legal obligation or a statutory exemption applies is a legal decision. This document does not make it.
- **Retention is open.** "Forever" would need its own basis and "we might need it" is not one.

## 3. Risks to the data subject

| # | Risk | Likelihood | Severity | Source |
| --- | --- | --- | --- | --- |
| 1 | A staff or verifier account is taken over and every applicant record is read | medium | high | `users`, `sessions`; every route returns any applicant to any signed-in role (threat model T-01, T-02) |
| 2 | One export copies all verified applicants out of the system | medium | high | `GET /api/exports/verified.csv`, data map row 16 (T-23) |
| 3 | Personal values reach the logs and a log store with weaker controls | medium | high | `errors.py` traceback (fixed), `db_echo`, any future log of a value (T-13, T-22, T-28) |
| 4 | Records are kept without a limit, so a child's data outlives its purpose | high | medium | all tables, retention UNDEFINED |
| 5 | A wrong OCR read leads to a wrong admission outcome: a genuine applicant flagged or a wrong one verified | medium | high | `extracted_fields`, REQ-019, ADR-0005 (the engine score alone does not separate right from wrong) |
| 6 | An erasure request cannot be honoured because the log must be kept | medium | medium | `decisions` append-only, `RESTRICT` to `applications` |
| 7 | Documents are uploaded to a third-party host with free-tier terms and unknown deletion | low (synthetic only today) | high | ADR-0004 hosted variant, Render, Neon |
| 8 | The community category is used or disclosed beyond admission | low | high | `applications.category` |
| 9 | Re-identification of an erased applicant from the remaining pseudonymous row and the log | low | medium | `applications` row kept after erasure, `decisions.created_at`, `decided_by` |

## 4. Measures

| Risk # | Measure | Where (`path:line` or policy) | Residual |
| --- | --- | --- | --- |
| 1 | Role-based access, server-side sessions with a version to end them at once, login rate limit and lockout | US-00-011, ADR-0006, new stories in `docs/security/threat-model-docket.md` section 6 | medium: any staff or verifier still sees every applicant, by design for one office |
| 2 | Staff role only for export, an audit entry per export, formula-safe CSV | threat model T-23, T-15 | medium: a file on a laptop is outside the system |
| 3 | The log records the error class and frames, never the message; a test proves it; a test for no personal values in logs is a story | `app/core/errors.py` (`_frames`), `tests/test_errors.py`; new story "No personal data in logs or URLs, enforced by tests"; policy: `db_echo` stays off with real data | low once the story lands |
| 4 | Decide retention per table before real data; build a purge only for periods someone decided | `docs/design/data-model.md` section 8, policy | high until decided |
| 5 | A person decides every flagged application; Verified needs all fields matching or a decision; format validators decide review, not the score alone | REQ-019, `docs/adr/0005-route-to-needs-review-by-validators-and-a-confidence-cutoff.md`, `docs/adr/0002-extract-fields-with-box-rules-and-format-validators.md` | medium: the extractor is not built and real layouts are untested |
| 6 | Erase in place: delete documents, replace personal columns and free text with placeholders, set `erased_at` | `docs/design/data-model.md` section 8, `docs/design/schema.sql` (`decisions_guard`) | medium: a pseudonymous row remains |
| 7 | Synthetic data only; no real data to any host until a processor review is done | `CONSTRAINTS.md` section 2, ADR-0004 | low |
| 8 | Drop `category` if no story needs it; never log or export it | open question to the product owner | medium until answered |
| 9 | Erased rows keep no name, date of birth, roll number or marks; `application_ref` replaced by a value built from the id | `docs/design/data-model.md` section 8 | low |

## 5. Rights supported

| Right | Mechanism |
| --- | --- |
| access / export | none yet: open item (a per-applicant extract is not designed) |
| erasure | the erase-in-place procedure in the data model (designed, not built; runs on a request, never on a schedule) |
| rectification | a verifier's correction changes the extracted value (US-00-007); correcting the application's own values has no mechanism: open item |
| withdrawal of consent | open item: the basis is undecided, so there may be nothing to withdraw |
| objection | open item |
| grievance (DPDP) | open item: no contact is named |

## 6. Decision

Do not proceed with real data. The synthetic demo may proceed. Conditions before real data: a lawful basis for children's data (legal), retention per table (product owner), measures 1, 2, 3 and 6 built and tested, a privacy contact named, a processor review for any hosted variant, and rights mechanisms for access, rectification and grievance. Signed: unsigned. Review due: 2026-11-30.
