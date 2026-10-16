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
- deploy job added to .github/workflows/ci.yml after the engineer granted edit permission; YAML parsed, needs checked, make -n deploy dry run shows the SSH_OPTS override
- ADR-0019 written: deploy main automatically when CI is green
- runbook section: set up, check, switch off, roll back
- decision log and ADR index rows

## Blockers
- GitHub environment `production`, secret DEPLOY_SSH_KEY and variables DEPLOY_HOST, DEPLOY_DOMAIN, DEPLOY_KNOWN_HOSTS, DEPLOY_ENABLED are the engineer's to create; the job is skipped until DEPLOY_ENABLED is true
- The deploy job has not run in CI (needs a push and the settings above)
- ADR-0019's Status line still says the job is applied by the engineer; the Implementation section is current. One edit to that line was refused by the permission classifier

## Decisions
- none

## Links
- MR: none
- Ticket: none
