# Progress: NOTASK-36 LiveE2eDashboardText

- Task: NOTASK-36
- Title: LiveE2eDashboardText
- Branch: bugfix/NOTASK-36-LiveE2eDashboardText
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 2

## Next
- engineer pushes the branch

## Done
- e2e-live: the dashboard assertion now expects '1 rejected' (NOTASK-26 changed the tile; the live suite from NOTASK-31 still expected 'of which 1 rejected'); test-case rows and steps TC-0245 and TC-0247 updated
- make test-e2e-live: 15 passed on the second run

## Blockers
- First local run failed once in global setup (Page.captureScreenshot: Unable to capture screenshot) while building the page images; the second run passed. Watch for it in CI

## Decisions
- none

## Links
- MR: none
- Ticket: none
