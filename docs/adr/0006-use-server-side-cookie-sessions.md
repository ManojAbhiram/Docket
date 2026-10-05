# ADR-0006: Use server-side cookie sessions

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: auth (session or token)
- Reversibility: awkward: moving to tokens later means a new credential flow, a refresh table with reuse detection and a change to every client; the `users` and `sessions` tables are cheap to keep.

## Context

Two roles, staff and verifier, sign in to a browser app (`docs/product/backlog.md` US-00-011; roles from `spec.md:L27-L30`). The demo runs locally behind one origin (ADR-0004), so the frontend and the API share a site. There are no mobile or third-party clients. A hosted variant would put the frontend (Cloudflare Pages) and the API (Render) on separate origins, which complicates cookies. Identity is seeded accounts with argon2id passwords, no password reset (assumption A11 in `docs/product/estimate.md`). The auth skill's default is a cookie session for a browser on one origin and short-lived tokens with rotation for mobile or third parties.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Server-side cookie session (chosen) | needs a CSRF check on state-changing requests, a `sessions` lookup per request, and credentialed CORS if the API moves to another origin | a browser app on one site, which is today's design |
| Short-lived JWT access token with rotating refresh token | a JWT cannot be logged out before it expires without a server-side version check, rotation with reuse detection needs its own table, and the access token must live somewhere script can read or in a cookie anyway | a separate-origin frontend, a mobile client or a third-party API consumer |

## Decision

We will use an opaque random session token in an `HttpOnly; Secure; SameSite=Lax` cookie, store only its SHA-256 hash in the `sessions` table, and check `users.session_version` on every request so one increment ends every session of a user, because the product is one browser app on one origin and a session must be revocable at once.

## Consequences

- Easier: sign-out and deactivation take effect immediately; no token to steal and replay after a leak of the database (only hashes are stored); no refresh logic.
- Harder: every state-changing request needs a CSRF defence (the threat model's T-03 story: an anti-forgery token or an `Origin` check); one `sessions` lookup per request (tens of live rows, negligible); a separate-origin hosted frontend needs `SameSite=None; Secure` and credentialed CORS, which weakens CSRF protection and would reopen this decision.
- Lifetimes are assumptions, unconfirmed by the product owner: absolute 8 hours and idle 30 minutes (`sessions.expires_at`, `last_seen_at`). A sweeper deletes expired rows.
- Revisit if the frontend and API must live on different sites, if a mobile or third-party client appears, or if the live session count passes about 10^4.

## Commits us to

PostgreSQL `sessions` table (`docs/design/schema.sql`), argon2id for password hashes (library chosen in the auth design), a CSRF mechanism (outside the standard stack until chosen).
