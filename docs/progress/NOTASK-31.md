# Progress: NOTASK-31 LiveE2e

- Task: NOTASK-31
- Title: LiveE2e
- Branch: chore/NOTASK-31-LiveE2e
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 6

## Next
- engineer pushes the branch; CI job is non-required until stable for a week

## Done
- frontend/e2e-live: global setup, 15 journey tests over six journeys, support helpers; playwright.live.config.ts
- make test-e2e-live, e2e-live-up, e2e-live-down (project docket-e2e, port 55432, down -v); frontend alias
- ci.yml job e2e-live (needs integration, not required); docs/testing/live-e2e.md
- spike: SYN-APP-003 lands in needs_review 3 of 3 runs with real RapidOCR, about 4.1 s for two pages

## Blockers
- CI job not run here; needs the engineer to push

## Decisions
- real RapidOCR kept for every journey, no recorded engine

## Links
- MR: none
- Ticket: none
