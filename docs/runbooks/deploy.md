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

## Deploy with make (one VM over SSH)

Every step below is a `make` target run from your laptop. Run `make help | grep deploy` for the list.
The images are built on your laptop and sent to the server, so a 1 GB server never compiles anything.

### One-time setup

1. Create the VM and open ports 80 and 443 in the cloud firewall (see "Oracle Always Free notes" below).
2. Point a domain at the VM's public IP and check it: `nslookup your.domain` must print that IP.
3. Create `deploy/deploy.local.mk` (ignored by git) with your own values:
   ```
   DEPLOY_HOST   = ubuntu@<public-ip>
   DEPLOY_KEY    = $(HOME)/Downloads/<your-ssh-private-key-file>
   DEPLOY_DOMAIN = your.domain
   ```
4. From the repository on `main`, run `make deploy-first`. It prepares the server (firewall, swap, Docker,
   Caddy), clones the repository, writes `deploy/production.env` with a random database password that is
   never printed, builds and sends the images, starts them, sets up HTTPS and checks `/healthz`.
5. Run `make deploy-seed-accounts` and copy the two passwords it prints. They show once.

### Every later deploy

`make deploy`. It refuses to run unless you are on `main`, the tree is clean and `main` equals
`origin/main`. Then it builds, sends, starts the new containers (migrations run first) and checks the site.

## Changing something: what to run

| You changed | Do this |
| --- | --- |
| Application code, frontend, a dependency, a Dockerfile, nginx config or the compose file | Merge to `main`, then `make deploy` |
| A database migration | `make deploy-backup`, then `make deploy`. The migration runs on start. Check with `make deploy-logs SERVICE=migrate` |
| A setting in `deploy/production.env` (Vision key, memory limit, port) | `make deploy-env` to edit it on the server, then `make deploy-apply` |
| Turn Vision on or off | Same as a setting: set or empty `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`, then `make deploy-apply` |
| The domain | Change `DEPLOY_DOMAIN`, run `make deploy-clone` (updates `PUBLIC_ORIGIN`, keeps the password), `make deploy-apply`, `make deploy-caddy` |
| Only the Caddy or HTTPS setup | `make deploy-caddy` |
| Something broke after a deploy | `make deploy-status` lists the image versions, then `make deploy-rollback VERSION=<short commit>` |
| You want to look around | `make deploy-status`, `make deploy-logs SERVICE=api LINES=200`, `make deploy-ssh` |
| Before a risky change, and now and then | `make deploy-backup` (writes to `.scratch/backups`; copy it somewhere safe) |
| Restore a backup | `make deploy-restore FILE=<dump.sql.gz> CONFIRM=yes`. It takes a backup first, then replaces every table. Not yet tried on a server |
| The server disk is filling | `make deploy-prune` removes dangling images only. Tagged versions stay for rollback |
| Lost or leaked demo passwords | There is no reset. Delete the two demo users in Postgres and run `make deploy-seed-accounts` again |

After any deploy, `make deploy-verify` prints the container states and calls the public `/healthz`.
A server reboot needs nothing from you: the containers use `restart: unless-stopped`, and Docker and
Caddy start on boot. The HTTPS certificate renews by itself.

Nothing in these targets deletes the database volume. They never run `down -v`.

## Oracle Always Free notes (learned on 2026-10-11)

- Sign-up asks for a card for verification. Always Free resources are not charged. Do not click Upgrade.
- The Ampere A1 shape (ARM, up to 4 OCPU and 24 GB) was out of capacity in Hyderabad, and that region has
  one availability domain, so there was no other place to try. The AMD `VM.Standard.E2.1.Micro` (1 OCPU, 1 GB)
  was available. Capacity changes through the day, so retrying later can work. The home region cannot be changed.
- Peak memory on the 1 GB machine was about 485 MB with the stack idle. Keep the 2 GB swap file that
  `make deploy-bootstrap` creates.
- Open ports 80 and 443 in two places: the VCN security list (Networking, your VCN, Security Lists, Add Ingress
  Rules) and the server's own firewall. Oracle's Ubuntu image ships a `REJECT` rule in the `INPUT` chain, and
  rules added below it never match. `make deploy-bootstrap` inserts the ACCEPT rules above it.
- A free DuckDNS name must point at the server's public IP. If you leave the IP blank, DuckDNS uses the address you
  are browsing from, and Let's Encrypt then fails with a timeout. Let's Encrypt allows five failed attempts per hour
  for one name, so fix DNS and the firewall first and then restart Caddy once.
- The private SSH key is shown once at creation. Keep it, never commit it, never paste it into chat.

## Deploy by hand

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

## Automatic deploy from CI (ADR-0019)

Once the engineer has added the `deploy` job to `.github/workflows/ci.yml`, a push to `main` deploys
by itself when the required jobs pass. Manual `make deploy` still works.

### Set up once (GitHub settings, not in the repository)
1. Create a deploy user on the server and a key pair used only by CI. Add the public key to that user's `authorized_keys`. Run `ssh-keyscan -H <host>` from a trusted machine to get the host key line.
2. Settings > Environments > New environment named `production`. Add environment secret `DEPLOY_SSH_KEY` (the private key) and variables `DEPLOY_HOST` (for example `ubuntu@1.2.3.4`), `DEPLOY_DOMAIN` and `DEPLOY_KNOWN_HOSTS` (the `ssh-keyscan` line).
3. Optional but recommended for the first releases: tick "Required reviewers" on that environment. Each release then waits for one click.
4. Settings > Secrets and variables > Actions > Variables: set `DEPLOY_ENABLED` to `true`. Until you do, the job is skipped.

### Check a deploy
Open the run in the Actions tab: the `deploy` job prints the version that was running, then the new one, and its summary lists commit, previous version, site and result. Then `make deploy-status` from your laptop.

### Switch it off, or go back
- Stop automatic deploys: set `DEPLOY_ENABLED` to anything but `true` (or delete the variable). Nothing else changes.
- A failed deploy rolls itself back to the version that was running, and the run is red.
- To go back by hand: `make deploy-status` lists the versions on the server, then `make deploy-rollback VERSION=<short commit>`.

### Things to know
- A run that finds a newer commit already on `main` skips itself and says so; the newer commit's own run deploys it.
- `e2e-live` is not required for a deploy until it has been green for a week. Add it to the job's `needs` then.
- Rotate `DEPLOY_SSH_KEY` if the environment secret may have been exposed. The key is effectively root on the server through Docker.

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

- Deployed once on an Oracle Always Free VM (2026-10-11) with the targets above. Not yet exercised there: `deploy-restore`, `deploy-rollback`, and a second `make deploy`.
- The API holds about 400 to 450 MB at peak with the OCR engine. On a 512 MB host the margin is about 12 percent; prefer 1 GB or more.
- Behind a platform load balancer, nginx sees the balancer's address, so the sign-in limiter groups users by it. Configure nginx `real_ip` for that platform before relying on per-user throttling.
- The security scan of the Vision upload path is manual and partial (`docs/security/NOTASK-17-vision-upload.md`). Run a scanner before public exposure.
- WebKit and Safari were not tested.

## Hosting options (a decision for the owner, none is made)

| Option | Fits? | Notes |
| --- | --- | --- |
| One small VM with Docker (1 CPU, 1 to 2 GB) running this compose file | Yes, chosen and deployed (Oracle Always Free); no hosting ADR is written yet | Simplest and closest to what was tested. Needs a host that does not require a card, per `CONSTRAINTS.md`. |
| Render free web service + Neon free Postgres + a second service for the web container | Possible, unverified | The API alone peaked at 403 MB under a 512 MB limit here, which is tight. Free instances sleep and the second service doubles the setup. Proposed in `docs/research/free-hosting.md`. |
| Local `docker compose` on your own machine | Yes | The demo-day safety net. |
