# Progress: NOTASK-37 ContinuousDeploy

- Task: NOTASK-37
- Title: ContinuousDeploy
- Branch: chore/NOTASK-37-ContinuousDeploy
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 4

## Next
- engineer adds the deploy job to ci.yml (text in the session), sets the GitHub environment and variables, then enables DEPLOY_ENABLED

## Done
- ADR-0019 written: deploy main automatically when CI is green
- runbook section: set up, check, switch off, roll back
- decision log and ADR index rows

## Blockers
- The deploy job itself is NOT in ci.yml: the agent's write to it was refused by the permission classifier (Production Deploy) and by the Bearing hook. The engineer adds it.
- GitHub environment, secret and variables are the engineer's to create

## Decisions
- none

## Links
- MR: none
- Ticket: none
