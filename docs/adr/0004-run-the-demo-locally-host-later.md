# ADR-0004: Run the demo locally with docker compose, host later

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: compute (hosting)
- Reversibility: cheap: the same images move to a host later; the work needed first is listed under Consequences.

## Context

`CONSTRAINTS.md` requires zero cost, no card and free hosting. From `docs/research/free-hosting.md` (pages read 2026-10-05) and the benchmark (ADR-0001):

- The engine peaked at about 509 MB over 30 pages, 99.4% of a 512 MB limit, before FastAPI, SQLAlchemy and tracing are counted.
- Render's free web service: no card to start, 750 hours a month, sleeps after 15 minutes, about 1 minute to wake. Its free instance RAM could not be confirmed from an official page.
- Neon Free: no card, 1 GB, suspends after 5 minutes. Cloudflare Pages: free static hosting, 500 builds a month.
- Excluded: Fly (card after trial), Koyeb (card, 512 MB), Railway (conflicting card rule, 0.5 GB), Hugging Face Docker Spaces (paid plan), Vercel Hobby (non-commercial only), Oracle (card and phone).
- Code facts: two gunicorn workers (`Dockerfile:18`), no CORS (`app/main.py`), a database URL rule that rejects `postgresql://` (`app/core/config.py:37`), uploads would need a persistent store (free-tier disks are ephemeral).

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Local `docker compose` now (chosen) | cannot be shown to anyone outside the room | the demo audience is in the room |
| Cloudflare Pages + Render free + Neon now | likely out of memory at 512 MB, cold starts of a minute, needs CORS, a URL rewrite and uploads in Postgres first | Render's free RAM is confirmed above 800 MB or memory drops below 400 MB |
| Hosted stack with a hosted vision API as the engine | gives up the local engine, sends page images to a third party | the API must stay tiny and the data is synthetic |

## Decision

We will run the demo locally with `docker compose` and move to Cloudflare Pages, a Render free web service and Neon Free only once peak RAM is at or below about 400 MB at one worker, because 509 MB leaves no margin under 512 MB and the host's RAM is unverified.

## Consequences

- Easier: no accounts, no cold starts, no RAM limit, no cost.
- Harder: nothing is reachable by URL. Accepted for now.
- The 400 MB bar is my margin for the API's overhead and has no source. Replace it with a measured figure once the full service runs.
- Before hosting: `WEB_CONCURRENCY=1`, add CORS, convert the database URL, store uploads in Postgres, confirm Render's free RAM on the dashboard, and measure memory over thousands of pages (ADR-0001).
- Revisit when someone outside the room must reach the demo, or when the engine fits.

## Commits us to

Docker Compose, PostgreSQL 16 (already in `docker-compose.yml`). Later: Cloudflare Pages, Render, Neon (outside the standard stack).
