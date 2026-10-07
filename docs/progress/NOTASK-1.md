# Progress: NOTASK-1 ConfirmOcrKillAndConflictGuard

- Task: NOTASK-1
- Title: ConfirmOcrKillAndConflictGuard
- Branch: chore/NOTASK-1-ConfirmOcrKillAndConflictGuard
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-07
- Updated: 2026-10-07
- Acceptance criteria: 3

## Next
- You push and merge. No code changed.

## Done
- Criterion 1, a killed or timed-out OCR child ends as a failed document in Needs review. Covered by existing tests, run and passing (133 in the six files): tests/test_process_engine.py (a read past the timeout kills the child; the next read starts a fresh one; a child that dies is an EngineError and the next read works), tests/test_jobs.py (a read that does not finish marks the document failed with a reason code; an EngineError caused by a timeout is recorded as timeout; a late result changes nothing; the sweeper fails documents stuck for five minutes; a failed document is settled too), tests/test_status_rules.py (a failed document sends the application to Needs review).
- Criterion 2, the stale-decision guard is closed. tests/test_decision_store.py (a decision on a version that changed is refused before anything is written), tests/test_decision_etag.py (the version is a quoted timestamp), tests/integration/api/test_decisions.py lines 399 to 402 (a stale If-Match gets 409). Also seen live in the browser on 2026-10-07: "This application is no longer in review. Someone else decided it."
- Criterion 3, no missing guard found, so no new row.

## Blockers
- none. The child's read loop (app/gateway/process.py lines 34 to 46) shows as uncovered because it runs in another process; the tests above do exercise it.

## Decisions
- none

## Links
- MR: none
- Ticket: none
