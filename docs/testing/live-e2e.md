# Live end-to-end suite

The mocked suite in `frontend/e2e/` answers "does the UI behave against the API shape we
believe in". The live suite in `frontend/e2e-live/` answers "is that belief true": the same
journeys against the real API, a real Postgres and the real RapidOCR reader. Task NOTASK-31.

## Run it

```
make test-e2e-live          # root; frontend/ has an alias with the same name
```

Needs Docker, uv, pnpm and Chromium (`make setup`). It takes about 35 seconds after the first run
(the first run also builds the 30 synthetic page images, a few seconds more). The target removes
any leftover `docket-e2e` project, starts a fresh Postgres, migrates it, runs Playwright, then
removes the project and its volume, keeping the Playwright exit code. `make e2e-live-up` and
`make e2e-live-down` are the two halves, and both are safe to repeat.

It is not part of `make check` (Docker, two servers, a browser and a cold OCR model).

## What it starts

| What | Where | Notes |
| --- | --- | --- |
| Postgres (compose project `docket-e2e`) | 127.0.0.1:55432 | fresh database every run, `down -v` afterwards |
| API (uvicorn, worker in process) | 127.0.0.1:8090 | `GATEWAY_ENGINE=rapidocr`, `WORKER_ENABLED=true`, `SESSION_COOKIE_SECURE=false`, Vision blanked |
| Built UI (`vite preview`, own `dist-live/`) | localhost:4273 | `VITE_API_URL` blank, `/api` proxied to the API |

None of these collide with the dev ports (5432, 8080, 5173) or the mocked suite (4173).
The origin is `localhost`, not `127.0.0.1`, because the API's CSRF check compares the browser's
`Origin` with `ALLOWED_ORIGINS` exactly. Set `E2E_LIVE_DATABASE_URL` to use a database you already
have (CI does); the make targets then start and remove nothing.

## Journeys

Sign in and out (including a wrong password and the signed-out redirect), sign up, import with a
refused row, upload and real read of two pages, review and decide, the overview counts, and the
export (empty state, then an approved application downloaded). Accounts are created once in
global setup through `/api/auth/register`. The synthetic page images are generated, not committed
(`data/seed` is ignored), so global setup builds them under `.scratch/e2e-live/seed` the way
`seed/__main__.py` documents: HTML, a Chromium screenshot of each, then the OpenCV noise.

## What it does not cover

Firefox, WebKit and the phone projects (the matrix stays on the mocked suite), visual
baselines, the stale-page 409 on a decision (needs two verifiers racing), Vision (no key, and the
suite asserts `/api/capabilities` reports it off), and load. Timing is not asserted anywhere;
waits poll the documents endpoint.

## Differences found between the fake and the server

- Export: the fake says "1 rows" with a Download button. With nothing Verified the real page shows
  "No applications are Verified yet." and no button. The real count appears only after approval.
- File name: the fake downloads `verified.csv`; the real name is `verified-YYYYMMDD-HHMMSS.csv`.
- Refusals: one refused row reads "1 row was refused" (singular), the fake's two read "2 rows were".
- Empty database: the Applications page then has two "Import applications" links (sidebar and
  page body); the fake always has rows, so its locator is unscoped.
- Real OCR flags SYN-APP-001 ("Low confidence on marks: English") instead of verifying it, so the
  export journey approves it as a verifier would. If a different machine renders the page images
  differently and the application verifies on its own, that test fails at the queue step; pick
  another application then.

## CI

Job `e2e-live` in `.github/workflows/ci.yml`, after `integration`, with its own Postgres service.
It is deliberately not in the required-check list: add it after a week of green runs.
