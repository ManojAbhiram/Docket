# Progress: NOTASK-17 MemorySecurityAcceptance

- Task: NOTASK-17
- Title: MemorySecurityAcceptance
- Branch: chore/NOTASK-17-MemorySecurityAcceptance
- Status: in review
- Started: 2026-10-11
- Updated: 2026-10-11
- Acceptance criteria: 3

## Next
- Engineer review of the uncommitted task branch and the two remaining security findings.

## Done
- Bounded OCR inference and per-page recycling, including failed reads; three repeat measurements recorded.
- Independent Vision upload source assessment recorded with scanner and persistence limitations.
- All 15 stories and 60 criteria audited with implementation and test evidence.
- Strict 512,000,000-byte container: peak 449,486,848 bytes, zero OOM events, 34 RapidOCR reads
  and four concurrent sign-ins completed in 97.29 seconds with zero unexpected HTTP errors.
- `make check`: 531 passed, 216 deselected, 81.44% coverage; 73 packages without known
  vulnerabilities; `check: 5 gates run, 0 skipped`; `check: passed`.
- `make test-integration POSTGRES_PORT=55417`: 216 passed in 22.86s; 9 test files checked.
- Frontend gate passed: 5 gates, 0 skipped; 93.04% line coverage; 652 packages audited.
- Independent review found no remaining material defect in the shared admission repair.
- Real Docker API smoke: `smoke: 5262 requests checked, 0 failed`; request evidence retained
  in `.scratch/smoke-NOTASK-17.md`. Task API and database containers and network stopped and
  removed after measurement; the isolated local database volume remains for review.
- Prose check: 4 files, 488 lines, zero hits. No commits, pushes, requests or deployments.

## Blockers
- Formal CSO finding persistence failed after its deadline; qualified offline Semgrep image unavailable.
- `make eval-gate` fails because no baseline has been accepted. No threshold or baseline changed.
- Acceptance audit: 46 Pass, 7 Partial, 3 Revised, 2 Drift, 1 Fail, 1 Unproven.
- Provider response byte ceiling and parsed multipart file cap remain recommendations, unfixed.

## Decisions
- Continue the existing engine and models; retain Argon2 memory strength and serialize large compute allocations.

## Links
- MR: none
- Ticket: none

## Definition of done evidence

| Check | Outcome and evidence |
| --- | --- |
| Gate and collection | Pass: base 523 unit tests versus final 531; integration 213 versus 216; final 5 gates, 0 skipped. |
| Regressions | Pass: recycling, failed-read recycling and upload admission assertions failed before the fixes and passed afterward; cancellation covered by focused units. |
| Boundary schemas | Pass: existing upload/auth schemas retained; 503 added to OpenAPI upload responses. |
| Error mapping | Pass: existing safe ServiceUnavailableError envelope for upload timeout; no exception text exposed. |
| Observability | Pass: existing request middleware and upload/worker logs retained; all smoke requests recorded. |
| Analytics | Not applicable: no events added. |
| Dependencies and guardrails | Pass: no dependency or threshold changes; no skipped test or lint suppression introduced. |
| Configuration | Pass: existing defaults and matching example values updated for recycle and hash admission. |
| Documentation | Pass: performance, manual security assessment, acceptance matrix and handoff recorded. |
| Scope | Pass: changed code and tests address memory admission, OCR allocation and documented overload behavior. |
| Commits | Not applicable: no commits created. |
| Prose | Pass: four report/progress files, zero hits. |
| Product smoke | Pass: real built API, isolated database, authenticated imports/uploads/reads/sign-ins, 5262 requests and zero failures. |

The scoped changes are ready for review. Release acceptance remains open for the 14 non-Pass
criteria, the unaccepted evaluation baseline and the security assurance limits above.
