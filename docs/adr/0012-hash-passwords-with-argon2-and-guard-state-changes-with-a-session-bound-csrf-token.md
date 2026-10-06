# ADR-0012: Hash passwords with argon2id and guard state changes with a session-bound CSRF token

- Status: Accepted
- Date: 2026-10-06
- Task: US-00-011
- Deciders: Manoj Abhiram (chose the recommended options in session)

## Context

ADR-0006 chose server-side cookie sessions and left two choices open (`docs/security/AUTH.md`, Decisions): the password hashing library and the CSRF mechanism. Accounts are seeded, there is no self sign-up and no reset. The API is one process (ADR-0011) and the frontend shares its origin (ADR-0004). The hash is memory hard, so many parallel logins could exhaust a 512 MB service (threat T-06).

## Options considered

### Option A: argon2-cffi for hashing; a derived CSRF token plus an Origin check
`argon2-cffi` is the reference binding for argon2id and the only new dependency. The CSRF token is the SHA-256 of a label and the session token, sent as a readable `docket_csrf` cookie and returned in an `X-CSRF-Token` header. Nothing is stored for it, and it ends with the session.

### Option B: the standard library's scrypt; an Origin check alone
No new dependency, but ADR-0006 and AUTH.md already name argon2id, and an Origin check alone leaves a hole when a browser omits the header or the API later moves to another origin.

### Option C: a stored per-session CSRF secret
Same protection as A, with a new column and a migration for no extra benefit.

## Decision

We will use argon2id through `argon2-cffi` (64 MiB, 3 iterations, 1 lane by default, set by environment) and require both an allowed `Origin` and a matching `X-CSRF-Token` on every state-changing request, because argon2id is what the threat model asks for, and a token derived from the session needs no storage and cannot outlive it.

## Consequences

- Easier: no migration, no extra table, sign-out ends the CSRF token with the session.
- Harder: every state-changing route must list `verify_csrf` next to `current_user`; the frontend must copy the `docket_csrf` cookie into the header.
- Hashing runs in a worker thread behind a slot count (`LOGIN_HASH_CONCURRENCY`, default 2), so at most two 64 MiB hashes run at once.
- Login failures are counted in memory, so a restart clears a lock. Revisit if the API runs in more than one process.
- The 64 MiB cost is the library default, unmeasured on the target service. Measure before hosting.
