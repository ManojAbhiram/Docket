# ADR-0018: Host on at least 1 GB of RAM on Oracle Cloud Always Free and waive the no-card rule

- Status: Accepted
- Date: 2026-10-16
- Task: NOTASK-23
- Deciders: Manoj Abhiram (chose in session)
- Area: compute (hosting)
- Reversibility: cheap: no hosted state exists yet, and the stack runs the same under `docker-compose.prod.yml` on any host with enough RAM.
- Supersedes: the 400 MB hosting bar in ADR-0004. The rest of ADR-0004 (local first) is unchanged.

## Context

ADR-0004 held back hosting until peak memory was at or below about 400 MB, because Render's free plan has 512 MB and the engine peaked near 509 MB (ADR-0001). The owner now has a 1 GB host available and says memory tuning is not an issue.

Measured facts that bear on a 1 GB host (`docs/performance/NOTASK-17-memory.md`, `docs/runbooks/deploy.md`):

- One worker, tuned engine, 34 documents plus concurrent sign-ins, strict 512,000,000-byte cgroup: peak 449,486,848 bytes, zero OOM events.
- The deploy runbook run through nginx under 512 MB peaked at 403 MB.
- Neither run includes Postgres. On one 1 GB machine the database, nginx and the OS share the same RAM, and that combination has not been measured.

`CONSTRAINTS.md` section 1 says no credit card at any point and that a free tier that asks for a card at sign-up is not allowed. Oracle Cloud Always Free is understood to ask for a card to verify an account. That was not checked against Oracle's current terms in this session.

## Options considered

### Option A: Oracle Cloud Always Free, 1 GB, waive the card rule for this host
The owner already has this machine class. Fits the measured peak with about 550 MB spare before Postgres. Breaks the stated no-card rule for the one account.

### Option B: Keep the no-card rule and stay local
Nothing is reachable by URL. Costs nothing and breaks nothing. Leaves the hosting blocker open.

### Option C: Cloudflare Pages + Render free + Neon (ADR-0004's plan)
No card, but Render free has 512 MB, which the stack fits only barely and not with margin.

## Decision

We will host the demo on a machine with at least 1 GB of RAM, using Oracle Cloud Always Free, and record that the owner waives the `CONSTRAINTS.md` no-card rule for that account, because the owner chose this host and the measured peak fits it.

`CONSTRAINTS.md` itself is not edited here. This ADR is the record that the owner accepted the exception.

## Consequences

- Easier: hosting is unblocked. The 400 MB bar no longer gates it, and memory tuning is dropped from the backlog.
- Harder: a card is on file for the account, so the "cannot be billed without a card" protection is gone for that host. Stay inside the Always Free resource shapes and set a billing alert at the provider.
- The data stays synthetic (REQ-043). The unsigned DPIA still blocks real student data on any host.
- Open: the real peak with Postgres and nginx on the same 1 GB machine is not measured. Measure it with `make bench-memory-runtime` style workload on the host before relying on it. If the free shape is x86 the current images apply as they are. If it is Arm, the dependencies have not been checked for Arm builds.
- Revisit if the host changes, if the account is converted to a paid plan, or before real student data.

## Commits us to

An Oracle Cloud account with a card on file, held by the owner.
