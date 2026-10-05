# Test risks

Source: `docs/product/backlog.md` as of 2026-10-05, story US-00-004 (matching rules, REQ-012 to REQ-016); threat models: none.
Ids are permanent; a risk that no longer applies keeps its row with level
`Low` and "closed: <reason>" in the risk text.

## How the level is set

Likelihood (L, M, H) is how probable the failure is, from the evidence named
in the row: the size of the change, branching or concurrency in it, a new
integration or dependency, defects in the same files (`git log --grep=fix`
over the paths), and how settled the requirement is.
Impact (L, M, H) is what it costs when it happens: H for money, auth, data
loss, PII or a legal duty; M for a core flow; L for cosmetics.

| Likelihood / Impact | L | M | H |
| --- | --- | --- | --- |
| L | Low | Low | Medium |
| M | Low | Medium | High |
| H | Medium | High | High |

Depth by level, counted in live cases: High needs three, one with a `not:`
oracle and one of type integration or e2e; Medium needs two, one with a
`not:` oracle; Low needs one.

## Register

No code for the matching rules exists yet (`app/domain/` is empty), and no defect history applies; likelihood comes from the change being new and from open questions Q-003 (name threshold), Q-011 (date formats) and Q-017 (field map).

| Risk | Story | What could go wrong | Source | Likelihood | Impact | Level | Cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | US-00-004 | Another person's document is accepted as a match for an application, so a wrong applicant is verified | AC-US-00-004-1, Q-003 (threshold undefined), new code | M | H | High | TC-0003, TC-0004, TC-0006 |
| R-002 | US-00-004 | A correct date printed in another format is flagged, sending verifiers needless work | AC-US-00-004-2, Q-011 | M | M | Medium | TC-0007, TC-0009 |
| R-003 | US-00-004 | A roll number that differs by one character is accepted | AC-US-00-004-3, new code | L | H | Medium | TC-0012, TC-0013 |
| R-004 | US-00-004 | A changed mark in one subject is accepted | AC-US-00-004-4, new code | L | H | Medium | TC-0016, TC-0018 |
| R-005 | US-00-004 | A document from which nothing could be compared counts as a match, so an application is verified on no evidence | AC-US-00-004-5, Q-017 (field map undefined) | M | H | High | TC-0019, TC-0020, TC-0022 |
| R-006 | US-00-004 | The comparison writes a name, date of birth or roll number into the logs | AC-US-00-004-1 to 4, `.claude/rules/python.md` (never log PII), minors' data | L | H | Medium | TC-0023, TC-0024 |
| R-007 | US-00-004 | Malformed OCR output (an empty or impossible value) crashes the comparison and blocks the queue | AC-US-00-004-2, noisy OCR from `docs/research/ocr-landscape.md` | M | M | Medium | TC-0010, TC-0025 |
