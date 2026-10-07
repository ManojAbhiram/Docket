# Docket

Admissions document verification. Staff import applications from a CSV and upload scanned
documents (JPG, PNG or PDF). A local OCR engine (RapidOCR) reads each document, the fields are
compared with the application, and applications that match fully are marked Verified. A verifier
works only the flagged queue: approve, correct a value, or reject with a reason. Every decision is
logged. Staff export the verified list as CSV.

Python service (FastAPI, Postgres) in this folder, React web app in `frontend/`. All data in
development, tests and demos is synthetic. `make help` lists every command; `make check` is the gate.

## Prerequisites

- Docker, for Postgres.
- [uv](https://docs.astral.sh/uv/), which installs Python 3.14 and the dependencies.
- Node and pnpm for `frontend/` (`frontend/package.json` asks for Node 24 or newer and pnpm 9.15.9).
- Memory: the OCR engine alone measured about 500 MB, so leave a gigabyte free.

## Run it locally

Three terminals, from the repository root unless stated.

**1. Database and API**

```
cp .env.example .env
make setup
make db && make migrate
make seed-accounts      # prints two one-time passwords. Copy them now, they are shown once.
make dev                # API on http://localhost:8080 (also /healthz, /readyz, /docs)
```

**2. Web app**

```
cd frontend
make setup
make dev                # http://localhost:5173, forwards /api to http://localhost:8080
```

Open http://localhost:5173 and sign in with `staff.demo` or `verifier.demo` and the passwords
`make seed-accounts` printed.

If port 5432 is already taken by another Postgres, pick another port and make `DATABASE_URL` in
`.env` use it:

```
make db POSTGRES_PORT=55432
make migrate POSTGRES_PORT=55432
make seed-accounts POSTGRES_PORT=55432
# in .env: DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:55432/docket
```

## Try it with the synthetic data

Sign in as **staff.demo** first.

1. **Import**: open Import and choose `data/seed/applications.csv`. It creates 20 applications.
2. **Upload**: open Applications, choose Add documents on an application, and pick files from
   `data/seed/png/` named for it (for example `SYN-APP-001_10th_marksheet.png`). Reading takes a few
   seconds per page.
3. **Status**: an application is Verified only if every field matches, Needs review if anything is
   doubtful or a document failed, and Missing documents until a 10th marksheet, a 12th marksheet and
   an ID proof are all read.

Then sign out and sign in as **verifier.demo**: open the Review queue, open an application, and
choose Decide (key `d`) to approve, correct a value or reject. Staff can then export the verified
list from Export.

Only `SYN-APP-001` has all three required documents. The other applications have fewer, and some
documents are mismatched on purpose (a wrong date of birth, name, roll number or mark), so you can
see the flagged queue and the decision log working.

## Tests and checks

```
make check                  # the gate: format, lint, mypy, unit tests, dependency audit
make test-integration       # needs make db and make migrate; use a separate database (below)
cd frontend && make check   # frontend gate; make test-e2e is a separate Playwright job
```

Integration tests write to the database they are given, inside a transaction they roll back. Give
them their own database so they never touch your demo data:

```
docker exec docket-postgres-1 psql -U postgres -c "CREATE DATABASE docket_it"
make migrate DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docket_it
make test-integration DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docket_it
```

## Troubleshooting

- **Lost the demo passwords:** they are never stored. `make db-reset` drops and recreates the
  database (destructive), then run `make migrate` and `make seed-accounts` again.
- **Sign-in works on localhost but not on another host name over plain http:** the session cookie is
  Secure by default. Set `SESSION_COOKIE_SECURE=false` in `.env` for local use only. Production
  refuses `false`.
- **Uploads stay on "reading":** the OCR worker runs inside the API process and needs
  `WORKER_ENABLED=true` and `WEB_CONCURRENCY=1` (two workers would load the engine twice).

## Layout

See `AGENTS.md` and the `python` skill for the conventions. `app/main.py` wires, `app/api` serves,
`app/domain` decides, `app/gateway` reads documents, `app/jobs` runs the read queue, `app/db`
persists, `alembic/` migrates. `make migrate-new name=add_invoices` writes the next migration.
`frontend/README.md` covers the web app, `docs/` holds the design, decisions and security notes,
`data/seed/` the synthetic applications and documents, and `evals/` the OCR benchmark.

## Status

Built: sign-in with two roles, CSV import, upload (including PDF), OCR reading, field comparison,
automatic status, verifier decisions with a log, dashboard counts and CSV export, all through the
web app.

Not built yet: an accuracy report on the 30 labelled documents (`evals/ocr/gate.yaml` has no
accepted baseline), field crops beside each value, the IBM Plex fonts, and a one-command demo that
runs the API and the web app in containers.
