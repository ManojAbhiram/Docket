# Proposed stories from the threat model and the high-level design

Status: Proposed. These are not in `docs/product/backlog.md`, so `coverage_check.py` and `docs/product/estimate.md` are unchanged. Adding them needs a decision from the product owner, because each one adds scope and none maps to a REQ (they mitigate threats in `docs/security/threat-model-docket.md`). Ids are placeholders, to be replaced by `backlog` when accepted. Points are not estimated.

| Placeholder | Title | Mitigates | Suggested priority | Depends on |
| --- | --- | --- | --- | --- |
| PS-01 | Login hardening: rate limit, lockout and uniform errors | T-01, T-05, T-06 | Must | US-00-011 |
| PS-02 | CSRF protection for cookie sessions | T-03 | Must | US-00-011 |
| PS-03 | Seed accounts with generated one-time passwords | T-07 | Must | US-00-011 |
| PS-04 | Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | T-10, T-11, T-12, T-14 | Must | US-00-002 |
| PS-05 | No personal data in logs or URLs, enforced by tests | T-13, T-22, T-28 | Must | US-00-001, US-00-002, US-00-007 |
| PS-06 | CSV hardening: size and row caps, formula-safe export | T-15, T-16 | Must | US-00-001, US-00-009 |
| PS-07 | Audit entry for every export of applicant data | T-23 | Should | US-00-009 |
| PS-08 | Pin and checksum the OCR models, bake them into the image | T-26 | Must | US-02-001 |
| PS-09 | Database TLS and a least-privilege API role | T-30 | Should | none |

Also proposed, from the data model, the design and the critic review (PS-12 and PS-13 came from the review):

| Placeholder | Title | Why | Depends on |
| --- | --- | --- | --- |
| PS-10 | Erase an applicant in place (`erase_application`) | No story owns it (`docs/design/data-model.md` section 12); the DPIA needs it before real data | US-00-001 |
| PS-11 | Run the API and frontend in `docker compose` | ADR-0004 chose a local compose demo, but `docker-compose.yml` starts only Postgres | none |
| PS-12 | Reprocess a failed document | A failed document cannot be recovered by re-uploading identical bytes (HLD section 16); `reprocessDocument` is in `api/openapi.yaml` | US-00-003 |
| PS-13 | Sweepers for stale work | Nothing owns marking old `processing` documents failed, old `pending` gateway calls errored, and deleting expired sessions and idempotency keys (data model section 12) | US-02-001, US-00-011 |

## Acceptance criteria

- **PS-01.** (The limit is keyed on account plus the forwarded source, and gunicorn runs with `--forwarded-allow-ips` set to the nginx address, or the whole office behind nginx counts as one source.) Given five failed sign-ins in a minute from one source, when a sixth is made, then it is refused with the same message as a wrong password. Given an unknown user and a known user with a wrong password, when each signs in, then the response and its time are comparable.
- **PS-02.** Given a state-changing request without the anti-forgery token or with a mismatched `Origin`, when it is sent, then it gets 403 and changes nothing.
- **PS-03.** Given the seed script, when it runs, then it prints a random password once, no password is in the repository, and the first sign-in forces a change.
- **PS-04.** Given a file whose bytes are not a PNG, JPEG or PDF, when uploaded under any name, then it is refused. Given an image over the pixel cap or a PDF over the page cap, when uploaded, then it is refused before decoding. Given a document that outruns the timeout, then it is marked failed. Stored names never come from the client.
- **PS-05.** Given an import, an upload and a decision with known values, when a test runs them, then none of those values appears in the captured logs or in any URL.
- **PS-06.** Given a CSV over the size or row cap, when imported, then it is refused. Given an exported cell that starts with `=`, `+`, `-` or `@`, then it is prefixed so a spreadsheet shows text.
- **PS-07.** Given an export, when it runs, then an entry records who, when and how many rows, and the entry cannot be edited.
- **PS-08.** Given a model file whose checksum differs, when the image builds, then the build fails. Given the running service, then it never downloads a model.
- **PS-09.** Given a hosted configuration with a database URL without TLS, when the service starts, then it refuses. Given the API role, then it cannot run DDL or update `decisions` beyond the erase marker.
- **PS-10.** Given an application, when it is erased, then personal columns are replaced in place, its documents and blobs are removed, its decisions keep their text replaced by `[erased]`, and it leaves every list, count and export.
- **PS-11.** Given a clean checkout, when `docker compose up` runs, then the database, the API and the frontend start, and the frontend reaches the API on the same origin.

- **PS-12.** Given a document that is failed, when staff reprocess it, then it becomes uploaded, a new gateway call row is written when it is read, and the application status is recomputed. Given a document that is not failed, then the request is refused with 409.
- **PS-13.** Given a document in `processing` for more than 5 minutes, when the sweeper runs, then it is marked failed with reason `interrupted`. Given a `pending` gateway call older than the read timeout (120 seconds), then it is marked `error`. Given a session past `expires_at` or an idempotency key older than 24 hours, then it is deleted. Hash concurrency for sign-in (PS-01) is one at a time under a semaphore, in a thread.

## Priority conflict found in the backlog

US-00-011 (Sign in) is Priority Should, but US-00-006 and US-00-007 (both Must) depend on it, and so does every role rule. A Must cannot depend on a Should. Proposed: raise US-00-011 to Must. This changes the estimate (Must 54 to 59, Should 5 to 0 points, from `docs/product/estimate.md`). Owner: product owner. Not applied, because the backlog is an agreed document.
