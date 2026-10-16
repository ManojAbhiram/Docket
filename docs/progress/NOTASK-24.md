# Progress: NOTASK-24 E2eJourneys

- Task: NOTASK-24
- Title: E2eJourneys
- Branch: chore/NOTASK-24-E2eJourneys
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 5

## Next
- engineer pushes the branch; run make test-e2e-matrix in CI

## Done
- frontend/e2e: auth, intake, review, reports specs and support/mockApi.ts (stateful API fake, shapes from the Zod schemas); 17 chromium tests pass, 5 of them new files
- lint, typecheck and frontend make check pass

## Blockers
- Firefox, WebKit and phone projects not run here (make test-e2e-matrix, CI)
- API is mocked: no real-backend journey yet

## Decisions
- none

## Links
- MR: none
- Ticket: none
