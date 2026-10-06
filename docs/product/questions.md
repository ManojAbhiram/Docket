# Open questions: Docket

PRD: docs/product/PRD.md   Updated: 2026-10-04
Entries: 18   Open: 18   Needs your confirmation: 18

Basis, for every entry:
- stated: the input answers it elsewhere; the passage that wins is named.
- inferred: only one reading is consistent with the rest of the input.
- convention: the input is silent and the team's standards settle it.
- assumption: nothing settles it; a choice was made so the team is not blocked.

## Needs your confirmation

- Q-001 What does "handled" mean for noisy phone photos? Assumed: processed without failing, with weak fields sent to Needs review. (US-00-003)
- Q-002 What counts as a low-confidence field? Assumed: below a configured confidence threshold, whose value is set from the eval. (US-00-003)
- Q-003 What is the name-match threshold? Assumed: configured, value set from the eval. (US-00-004)
- Q-004 When is an application Missing documents? Assumed: when it lacks any of a 10th marksheet, a 12th marksheet or an ID proof. (US-00-005)
- Q-005 What does Correct change? Assumed: the extracted value, then the comparison re-runs. (US-00-007)
- Q-006 What does approve or reject leave? Assumed: approve makes Verified; reject keeps Needs review, adds a rejected decision flag and removes the application from the queue. (US-00-007, US-00-005, US-00-008)
- Q-007 Is the transfer certificate type in scope? Assumed: out of scope until every other requirement is done. (US-00-003, where a transfer certificate type would be added)
- Q-008 How do 5,000 applications get documents in if bulk upload over 100 files is out? Assumed: 5,000 is use-case context, not a build target; uploads are by batches of up to 100 files. (US-00-001, US-00-002)
- Q-009 What is the call cap and does the count persist? Assumed: set in the engine decision record and kept in the database across restarts. (US-02-001)
- Q-010 What happens with a second document of the same type or an unknown type? Assumed: the latest replaces the earlier one, which is kept; an unknown type goes to Needs review. (US-00-002, US-00-003)
- Q-011 How are dates normalised and what does the export contain? Assumed: ISO dates after normalising; export has application id, name and decision. (US-00-004, US-00-009)
- Q-012 Who can read the decision log? Assumed: staff and verifiers, read only. (US-00-007)
- Q-013 How do people sign in and which role sees what? Assumed: seeded role-based accounts; staff manage data, verifiers work the queue. (US-00-011, US-00-006, US-00-007)
- Q-014 Are the 30 eval documents the 30 seeded ones, and are the 10 a subset? Assumed: yes to both. (US-02-003, US-02-004)
- Q-015 How does "nothing else" in the runtime (spec.md:L23) meet a self-hosted engine? Assumed: the chosen engine's runtime is allowed if free; nothing else is added. (US-02-001, US-02-002)
- Q-016 Does a free engine give a per-field confidence that tracks correctness, and may the synthetic set's noise be lowered as a fallback? Assumed: found out by a spike on the seeded set before the confidence rule is built; noise stays the same for every candidate. (US-00-003, US-02-002, US-02-003)
- Q-017 Which extracted field on which document type is compared with which application column? Assumed: a field map written in design, with fields a document does not carry skipped. (US-00-004, US-00-005)
- Q-018 Does the demo run locally or on free hosting? Assumed: locally first; hosting only if the chosen engine fits free limits. (US-02-002)

## Register

| Q | Status | Kind | Where | Basis | Question | Readings | Decision | Why | Affects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | open | contradiction | REQ-007, REQ-011 | assumption | What does "must be handled" mean when the spec also says not to chase accuracy on noisy photos? | (a) processed, weak fields to Needs review; (b) a minimum accuracy on noisy photos | (a) | spec.md:L44 and spec.md:L50 disagree; (a) satisfies both | US-00-003 |
| Q-002 | open | gap | REQ-011 | assumption | What counts as low-confidence? | (a) below a configured per-field confidence; (b) any engine-flagged field; (c) a fixed number | (a), value from eval | no value in the input | US-00-003 |
| Q-003 | open | gap | REQ-013 | assumption | What is the name similarity threshold? | (a) configured, set from eval; (b) fixed in the spec | (a) | spec.md:L144 says "configured" with no value | US-00-004 |
| Q-004 | open | gap | REQ-017 | assumption | When is an application Missing documents? | (a) any of the three document types absent; (b) per application, by board or category | (a) | only the three types are named (spec.md:L49) | US-00-005 |
| Q-005 | answered 2026-10-06: (a) | gap | REQ-024 | assumption | What does Correct edit and what status follows? | (a) the extracted value, then re-compare; (b) the application value | (a) | the application record is the reference (spec.md:L9) | US-00-007 |
| Q-006 | answered 2026-10-06: (c) | gap | REQ-023, REQ-025 | assumption | What do approve and reject leave, given only three statuses? | (a) approve Verified, reject stays Needs review; (b) a fourth status Rejected; (c) approve Verified, reject keeps Needs review with a rejected decision flag and leaves the queue | (c) | spec.md:L65-L69 allows three statuses; (a) alone leaves a rejected item looking untouched in the queue and the counts (critic finding) | US-00-007, US-00-005, US-00-008 |
| Q-007 | open | contradiction | REQ-045 | assumption | Transfer certificates are out of scope but a transfer certificate type is a stretch item | (a) out of scope, stretch last; (b) in scope | (a) | spec.md:L131 and spec.md:L136 | US-00-003 |
| Q-008 | open | contradiction | B1, REQ-004 | assumption | 5,000 applications in July but bulk upload over 100 files is out of scope | (a) 5,000 is context, uploads in batches of up to 100; (b) build bulk upload | (a) | spec.md:L11 and spec.md:L132 | US-00-001, US-00-002 |
| Q-009 | open | gap | REQ-033 | assumption | What is the call cap and is the count kept across restarts? | (a) decided in the decision record, persisted; (b) per run only | (a) | CONSTRAINTS.md:L38 leaves the value open | US-02-001 |
| Q-010 | open | gap | REQ-009 | assumption | What happens on a duplicate or unknown document type? | (a) latest replaces, unknown to Needs review; (b) reject the upload | (a) | not covered in the input | US-00-002, US-00-003 |
| Q-011 | open | gap | REQ-014, REQ-029 | assumption | How are dates normalised and what columns does the export have? | (a) ISO dates, id/name/decision; (b) as printed | (a) | exact match needs one format | US-00-004, US-00-009 |
| Q-012 | answered 2026-10-06: (a) | gap | REQ-027 | assumption | Who can read the decision log? | (a) staff and verifiers, read only; (b) verifiers only | (a) | spec.md:L74 requires logging only | US-00-007 |
| Q-013 | answered 2026-10-06: (a) | gap | section 4 | assumption | How do users sign in and what does each role see? | (a) seeded role-based accounts; (b) no sign-in | (a) | roles exist (spec.md:L27-L30), sign-in is not described | US-00-011, US-00-006, US-00-007 |
| Q-014 | open | gap | REQ-037, REQ-038, REQ-040 | assumption | Are the eval documents the seeded ones, and are the 10 a subset of the 30? | (a) same 30, 10 a subset; (b) separate sets, with a held-out set for reporting | (a) | counts match (spec.md:L100, L106); with n=30 the engine, thresholds and the reported accuracy share one sample, so (b) is the safer reading if the owner allows it | US-02-003, US-02-004 |
| Q-015 | open | contradiction | section 6 | assumption | "Nothing else" in the runtime against a self-hosted engine | (a) engine runtime allowed if free; (b) hosted free API only | (a) | spec.md:L23 and CONSTRAINTS.md:L43-L51 | US-02-001, US-02-002 |
| Q-016 | open | gap | REQ-010, REQ-011, REQ-041 | assumption | Does a free engine's per-field confidence separate right from wrong fields, and may the synthetic noise be lowered as spec.md:L124 says? | (a) spike first, same noise for all; (b) lower the noise; (c) drop confidence, review every field | (a) | critic finding; spec.md:L124 against CONSTRAINTS.md:L46. Measured 2026-10-05 (docs/research/ocr-benchmark.md, 30 synthetic documents): RapidOCR's own score does not separate documents read fully from documents with a miss (0.992 against 0.987); Tesseract with preprocessing separates somewhat (0.816 against 0.634) but reads far less. The engine score alone cannot drive REQ-011; format checks per field are the candidate signal | US-00-003, US-02-002, US-02-003 |
| Q-017 | open | gap | REQ-012, REQ-018 | assumption | Which document field is compared with which application column? | (a) a field map in design, absent fields skipped; (b) every column on every document | (a) | an ID proof does not carry marks | US-00-004, US-00-005 |
| Q-018 | open | gap | REQ-035, REQ-036 | assumption | Does the demo run locally or on free hosting? | (a) local first; (b) free hosting required | (a) | an engine needing a GPU may not fit free hosting (CONSTRAINTS.md:L13) | US-02-002 |
