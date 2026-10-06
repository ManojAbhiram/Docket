# Authentication and authorisation: Docket (staff and verifier roles)

Built on `feature/US-00-011-SignIn` (2026-10-06): login, logout, `/auth/me`, the `current_user` and `require_role` dependencies, CSRF and the login limiter. The import, upload, decision, dashboard and export routes do not exist yet, so their matrix rows are still planned. Decisions are in ADR-0006 and ADR-0012.

| Field | Value |
| --- | --- |
| Session model | server-side cookie session (ADR-0006) |
| Authorisation model | RBAC with two roles, staff and verifier; no attribute rules (the backlog names roles, not attributes) |
| Identity source | own passwords, argon2id, seeded accounts only, no self sign-up, no reset |
| Tenancy | single office: no `tenant_id` anywhere (`docs/design/data-model.md` section 10) |
| Middleware | planned: a router-level `dependencies=[Depends(current_user)]` on the API router in `app/main.py`; the health router and login route opt out by name |
| Last reviewed | 2026-10-06, built for US-00-011, unreviewed by a second person |

## Public routes

Counted from the planned route inventory (`docs/security/threat-model-docket.md` section 3). Routes: 14 entry points, of which public: 4.

| Route | Reason |
| --- | --- |
| `POST /api/auth/login` | the sign-in form; rate limited per account and per source, same error for an unknown user and a wrong password (threat T-01, T-05) |
| `GET /healthz` | liveness probe (`app/api/health/router.py:34`) |
| `GET /readyz` | readiness probe, returns only ok or a failed check name (`app/api/health/router.py:40`) |
| `GET /docs` and `GET /openapi.json` | non-production only: the application does not mount them when `ENV=production` (`app/main.py:46`) |

Every other route requires a session. A new route is protected by default because the dependency sits on the router, so forgetting it is not possible, and a public route has to be added to the public router by name.

## Tokens and sessions

| Item | Value |
| --- | --- |
| Session token | 256 random bits, opaque, in a cookie; only its SHA-256 is stored in `sessions.token_hash` |
| Idle timeout | 30 minutes (`sessions.last_seen_at`), assumption, unconfirmed by the product owner |
| Absolute lifetime | 8 hours (`sessions.expires_at`), assumption, unconfirmed |
| Refresh token | none: this is a cookie session, not a token pair |
| Cookie flags | `HttpOnly; Secure; SameSite=Lax; Path=/`, name `docket_session` |
| CSRF | an anti-forgery token on state-changing requests plus an `Origin` check. `SameSite=Lax` alone is not enough because the planned hosted variant could put the API on another origin (ADR-0006). New story: CSRF protection for cookie sessions |
| Logout | `POST /api/auth/logout` sets `sessions.revoked_at` |
| Logout everywhere | increment `users.session_version`; each session stores the version it was created with and is valid only while it matches, checked on every request |
| Deactivation | `users.is_active = false` makes every request return 401 immediately |
| Storage on mobile | not applicable: there is no mobile client |
| Signing keys | none: the token is random and looked up, so there is no signing secret to leak or rotate |

## Login flows

- Password: argon2id (memory 64 MiB, iterations 3, parallelism 1). The parameters are the auth skill's defaults, unmeasured here; 64 MiB per hash matters on a 512 MB service, so concurrent logins are limited (threat T-06) and the cost is the first thing to tune. Seeded accounts get a generated one-time password printed once and forced to change on first sign-in (threat T-07, new story). A breached-password check is required if people ever choose their own passwords; for generated ones it is not applicable. Rate limit per account and per source, and a generic error on failure.
- Passkey: not built.
- OAuth and OIDC: not built; there is no provider.

## Authorisation

Roles: `staff`, `verifier`. Resources: session, import, application, document, decision, dashboard, export, health, docs. The matrix lives in `docs/security/permission-matrix.md` and every cell is a test, to be written with the routes.

- **staff** imports applications, uploads documents, reads applications, documents, the dashboard and the export (US-00-011 AC-1).
- **verifier** reads applications and documents, works the flagged queue and makes decisions (AC-2) and may not import, upload or export (AC-3).
- Both read the dashboard counts. That is an assumption: the backlog gives the dashboard to staff only (US-00-008) and the counts carry no personal data.

Resource-level rule. The product is one office, so any signed-in staff member or verifier may read any application, by design (threat T-25). There is no owner to scope by, and therefore no tenant or owner column to filter on. What remains per record is that an unknown id answers 404 to every role. Role denials answer 403, not 404, because both roles know every route exists, so 403 reveals nothing the role does not know.

Loads by id: 0 (no code exists to count). The matrix tests and the audit above the unscoped-load count must be rerun when the routes exist.

## Decisions, and what is not done

- Session model, RBAC and the identity source are recorded in ADR-0006 and the backlog. The argon2id library and the CSRF mechanism are recorded in ADR-0012.
- Not built, by request of the mode: the middleware, the roles table logic and the matrix tests. The matrix test ids (`TC-AUTH-...`) are reserved in the matrix. No test is written yet because the routes do not exist, and a failing or skipped placeholder would break the repository's rule against skipped tests.
- A `/logout/everywhere` endpoint and a `session:end` permission are not in any story; the `users.session_version` column makes it one increment later. Recommended, not added.

## Open items

| Item | Owner | Task |
| --- | --- | --- |
| ~~Build the session middleware, login, logout and the role dependency~~ done in US-00-011; the forced password change on first sign-in was not built (no change-password endpoint) | backend lead rotation | US-00-011 |
| Login hardening: rate limit, lockout and uniform errors | backend lead rotation | new story, no id yet |
| CSRF protection for cookie sessions | backend lead rotation | new story, no id yet |
| Seed accounts with generated one-time passwords | backend lead rotation | new story, no id yet |
| Confirm the 30 minute idle and 8 hour absolute lifetimes | product owner | none |
| Confirm that verifiers may read the dashboard | product owner | none |
| Generate the matrix tests when the routes exist | backend lead rotation | with the route stories |
| Measure argon2id time and memory at 64 MiB on the 512 MB service | backend lead rotation | none |
