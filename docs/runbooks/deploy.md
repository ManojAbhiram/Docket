# Runbook: deploy Docket

Owner: the engineer who deploys (agents prepare, they do not deploy). Verified on 2026-10-11 with
`docker-compose.prod.yml` on one machine: sign-in, import, upload, read, review, approve and CSV
export through nginx, with the API under a 512 MB limit (peak 403 MB, no OOM kill).

## What runs

```
browser --TLS--> [your ingress] --> web (nginx :8080) --/api--> api (gunicorn + uvicorn, one worker)
                                                                  |-- RapidOCR child process
                                                                  `-- Postgres 16
```

- One origin: the browser only talks to `web`; nginx forwards `/api/` to `api` (ADR-0004, ADR-0006), so the session cookie stays first party.
- One API worker, always (`WEB_CONCURRENCY=1`): the document worker and the OCR child live in that process (ADR-0011).
- Only `web` publishes a port. Never publish `api` or `postgres`.
- Needs: Docker Compose v2, 1 CPU, about 1 GB of RAM for the whole stack (API up to 640 MB, Postgres, nginx), a domain and TLS in front of `web`.

## Before you deploy (checklist)

1. The branch is merged to `main` and CI is green. `make check` and `make -C frontend check` pass.
2. **Rotate the OpenRouter key** that was pasted into a chat during development, even if you do not plan to use Vision.
3. Decide who may sign up. Sign-up is open and lets the person choose staff or verifier (ADR-0013), so anyone who can reach the site could approve applications. This is fine for a synthetic-data demo behind a private address. For anything else, gate or remove it first. This is an open decision for the owner.
4. Choose the host (see the options at the end). No hosting ADR exists yet; write one when you choose.
5. Data is synthetic only (`CONSTRAINTS.md` section 2). Do not load real student documents.

## Deploy

```
git clone <repo> && cd Docket && git checkout main
cp deploy/production.env.example deploy/production.env     # then edit: see the comments in it
# set a long random POSTGRES_PASSWORD and PUBLIC_ORIGIN=https://your.domain (no trailing slash)
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
```

`migrate` runs `alembic upgrade head` once, then `api` starts, then `web`. Create the first accounts:

```
docker compose --env-file deploy/production.env -f docker-compose.prod.yml \
  run --rm api python -m app.db.seed_accounts          # prints two demo passwords ONCE, copy them
```

Put TLS in front of `web` (your platform's ingress, Caddy, or a load balancer) and forward to `WEB_PORT`.
The session cookie is `Secure`: browsers only send it over HTTPS (or `http://localhost`).

## Verify after every deploy

1. `docker compose --env-file deploy/production.env -f docker-compose.prod.yml ps`: `api` healthy, `web` healthy, `migrate` exited 0.
2. Open `PUBLIC_ORIGIN/healthz`: `{"status":"ok"}` (the web container).
3. Sign in as `staff.demo`, import `data/seed/applications.csv` (20 rows), open one application and upload `data/seed/png/SYN-APP-001_10th_marksheet.png`: it shows Read within a few seconds.
4. Sign in as `verifier.demo`, open the Review queue, approve one application, then check the Dashboard shows Verified 1 and `/export` downloads a CSV.
5. Memory: `docker stats --no-stream` on the `api` container stays under its limit. A restart or `OOMKilled=true` (`docker inspect <api container> --format '{{.State.OOMKilled}}'`) means raise `API_MEM_LIMIT`.
6. Logs are JSON: `docker compose ... logs api`. They never contain document values, passwords or the OpenRouter key.

## Vision (optional, off by default)

Leave `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` empty to keep it off. To turn it on, set both in `deploy/production.env`
(model must end in `:free`, for example `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`) and run `up -d` again. Then page images
go to OpenRouter when staff choose it on upload, and only synthetic data is allowed. Free models are intermittent; a failed
call is read locally and the reason is shown. At most 40 Vision calls in 24 hours. Turn it off by emptying both values.

## Update and roll back

- Update: `git pull`, set `DOCKET_VERSION` to the new short commit id, `docker compose ... up -d --build`. Migrations run automatically.
- Roll back: set `DOCKET_VERSION` to the previous value and `up -d` (the old image is still on the host if you did not prune). Migration `0003` only adds columns with defaults, so the previous version still runs on the new schema.
- A schema rollback is `docker compose ... run --rm migrate alembic downgrade -1`. Take a backup first.

## Backup and restore

```
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U docket docket | gzip > docket-$(date +%F).sql.gz
gunzip -c docket-YYYY-MM-DD.sql.gz | docker compose --env-file deploy/production.env \
  -f docker-compose.prod.yml exec -T postgres psql -U docket docket
```

Page images live in Postgres (ADR-0007), so the dump holds everything.

## Known limits

- Docker images were built and run on one machine; no cloud deployment has been tried.
- The API holds about 400 to 450 MB at peak with the OCR engine. On a 512 MB host the margin is about 12 percent; prefer 1 GB or more.
- Behind a platform load balancer, nginx sees the balancer's address, so the sign-in limiter groups users by it. Configure nginx `real_ip` for that platform before relying on per-user throttling.
- The security scan of the Vision upload path is manual and partial (`docs/security/NOTASK-17-vision-upload.md`). Run a scanner before public exposure.
- WebKit and Safari were not tested.

## Hosting options (a decision for the owner, none is made)

| Option | Fits? | Notes |
| --- | --- | --- |
| One small VM with Docker (1 CPU, 1 to 2 GB) running this compose file | Yes, verified shape | Simplest and closest to what was tested. Needs a host that does not require a card, per `CONSTRAINTS.md`. |
| Render free web service + Neon free Postgres + a second service for the web container | Possible, unverified | The API alone peaked at 403 MB under a 512 MB limit here, which is tight. Free instances sleep and the second service doubles the setup. Proposed in `docs/research/free-hosting.md`. |
| Local `docker compose` on your own machine | Yes | The demo-day safety net. |
