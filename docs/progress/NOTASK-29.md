# Progress: NOTASK-29 StaleDocsPass

- Task: NOTASK-29
- Title: StaleDocsPass
- Branch: docs/NOTASK-29-StaleDocsPass
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 4

## Next
- engineer pushes the branch

## Done
- docs/security/threat-model-docket.md: section 4a re-checks every planned and mitigated threat against code and tests (20 mitigated, 9 partly, 1 planned, 1 accepted of 31); counts and entry point note corrected; threats_check.py run and its output recorded
- docs/design/data-model.md: counts checked from the migrations (106 columns and 20 indexes at 0002, 109 and 21 now), sections 9, 11 and 12 checked against the code
- docs/privacy/DATA_MAP.md: the 95 column figure is wrong, noted with the true number
- docs/product/estimate.md: dated table of assumptions A1 to A13 and claims that code has overtaken
- docs/DEBT.md: seed scan run and recorded, DEBT-001 and DEBT-004 moved to Paid, DEBT-002, 003, 005, 006 annotated, DEBT-007 added

## Blockers
- threats_check.py fails on T-34 and T-35 because its path pattern needs a file extension and the cells cite Dockerfile and Makefile; this predates the task and the cells were kept as written
- Docs only: no code, test or schema change, so the gaps found are listed under Noticed in the report, not fixed

## Decisions
- none

## Links
- MR: none
- Ticket: none
