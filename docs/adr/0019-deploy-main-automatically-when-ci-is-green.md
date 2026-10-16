# ADR-0019: Deploy main automatically when CI is green

- Status: Accepted (2026-10-16, Manoj Abhiram asked for it). The workflow job is applied by the engineer: the agent was refused write access to it (see Implementation).
- Date: 2026-10-16
- Task: NOTASK-37
- Deciders: Manoj Abhiram (chose in session)
- Area: deployment
- Reversibility: cheap: delete the job or set the repository variable `DEPLOY_ENABLED` to anything but `true`.
- Supersedes: nothing. `make deploy` from a laptop (`docs/runbooks/deploy.md`) stays and still works.

## Context

`make deploy` builds the API and web images, sends them to one VM over SSH, starts them (migrations run first) and checks `/healthz`. It refuses unless the checkout is a clean `main` equal to `origin/main`. The first deploy (`make deploy-first`) has been done by hand on an Oracle Always Free VM. Every later release is still a manual command, so `main` and production can drift.

Facts that shape the choice:
- CI on `main` runs these required jobs: `validate`, `lint`, `unit`, `eval-gate`, `integration`, `dependency-scan` and `build`. `e2e-live` is new and has not yet been stable for a week.
- `deploy-rollback VERSION=<short commit>` exists and the previous version is readable from `deploy/production.env` on the server.
- The data is synthetic, the DPIA is unsigned and sign-up is open (ADR-0013). Nothing real may be loaded.
- `AGENTS.md` rule 2 says agents never deploy. That rule is about agents and does not change.

## Options considered

### Option A: keep deploying by hand
Safest and already works. Production lags `main` until someone remembers, and a deploy depends on one laptop having Docker and the key.

### Option B: a `deploy` job in `ci.yml` that runs `make deploy` once the required jobs pass
Reuses the exact tested command. Needs an SSH key in GitHub secrets. A GitHub Environment can require a reviewer, so the first runs are one click each.

### Option C: build in CI, push to GHCR, the server pulls
Cleaner long term, no key with shell access to the server in CI. Needs changes on the server and in the compose file, and replaces a mechanism that already works.

## Decision

We will add a `deploy` job to `.github/workflows/ci.yml` that runs `make deploy` on a push to `main` only when all required jobs have passed, because it automates the command that is already proven on this server and keeps the manual path.

How it is guarded:
- **Kill switch.** The job runs only when the repository variable `DEPLOY_ENABLED` is `true`. Merging the job deploys nothing until the owner sets it.
- **Environment.** The job uses the GitHub Environment `production`. Required reviewers are a setting there: with one, every release waits for a click; with none, the deploy is fully automatic.
- **Needs.** `validate`, `lint`, `unit`, `eval-gate`, `integration`, `dependency-scan` and `build`. Not `e2e-live`, until it has been green for a week.
- **One at a time.** A concurrency group `deploy-production` with `cancel-in-progress: false`.
- **Stale runs skip.** If a newer commit has reached `main`, the run says so and does nothing, because `make deploy` itself insists on `main == origin/main`.
- **Pinned host.** SSH uses `StrictHostKeyChecking=yes` with a `known_hosts` entry in a variable, not the Makefile's `accept-new`.
- **Rollback.** The job records the version running before the deploy. If any later step fails, it runs `make deploy-rollback VERSION=<that version>` and the run is red.
- **Settings it needs**, all outside the repository: environment secret `DEPLOY_SSH_KEY`; variables `DEPLOY_HOST`, `DEPLOY_DOMAIN`, `DEPLOY_KNOWN_HOSTS`, and repository variable `DEPLOY_ENABLED`.

## Consequences

- Easier: production follows `main` within minutes of a green run, and nobody needs Docker or the key on a laptop to release.
- Harder: the CI runner holds a key that can run Docker on the server, which is root in effect. Use a dedicated deploy user and key, and rotate the key if the environment secret is ever exposed.
- A migration that is wrong reaches production. `migrate-verify` proves every downgrade runs, but rollback only restores the previous images, so keep migrations backward compatible.
- Open sign-up (ADR-0013) means a public demo may be reachable. Keep it synthetic, and prefer a required reviewer on the environment until several releases have behaved.
- Agents still never deploy, approve a deployment or change these settings (`AGENTS.md` rule 2).
- Revisit when real data is planned (DPIA), when the host changes, or when `e2e-live` has been stable for a week (add it to `needs`).

## Implementation

The `deploy` job is the last job in `.github/workflows/ci.yml` (NOTASK-37). The session's permission classifier refused the first two attempts to write it; the engineer then granted the edit permission and it was written. It was validated by parsing the YAML, checking that every `needs` entry exists and a `make -n deploy` dry run that shows the `SSH_OPTS` override reaching the `ssh` call. It has not run in CI: that needs a push, the `production` environment and the variables. The job does nothing until `DEPLOY_ENABLED` is `true`. The first runs should be made with a required reviewer on the `production` environment.

## Commits us to

A GitHub Environment named `production`, the secret and variables listed above, and a deploy user on the server whose key is dedicated to CI.
