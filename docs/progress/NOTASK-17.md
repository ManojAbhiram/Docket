# Progress: NOTASK-17 MemorySecurityAcceptance

- Task: NOTASK-17
- Title: MemorySecurityAcceptance
- Branch: chore/NOTASK-17-MemorySecurityAcceptance
- Status: in review
- Owner: none
- Started: 2026-10-11
- Updated: 2026-10-11
- Acceptance criteria: 3

## Next
- engineer pushes the branch, opens the PR, rotates the OpenRouter key, decides hosting and sign-up policy, then follows docs/runbooks/deploy.md

## Done
- 3 earlier items (see git log)
- Strict 512,000,000-byte container: peak 449,486,848 bytes, zero OOM events, 34 RapidOCR reads
- `make check`: 531 passed, 216 deselected, 81.44% coverage; 73 packages without known
- `make test-integration POSTGRES_PORT=55417`: 216 passed in 22.86s; 9 test files checked.
- Frontend gate passed: 5 gates, 0 skipped; 93.04% line coverage; 652 packages audited.
- Independent review found no remaining material defect in the shared admission repair.
- Real Docker API smoke: `smoke: 5262 requests checked, 0 failed`; request evidence retained
- Prose check: 4 files, 488 lines, zero hits. No commits, pushes, requests or deployments.
- Audit gaps closed: 59 of 60 criteria pass (ADR-0016, ADR-0017, seed loader, provenance tests)
- Hard Vision cutoff in the worker, free-model and blank-setting config fixes
- Production stack, nginx same-origin proxy, runbook; smoke-tested through nginx under 512 MB (peak 403 MB)

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
