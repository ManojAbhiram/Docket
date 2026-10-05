# Threat model: Docket (admissions document verification)

- Task: US-02-002
- Serves: US-00-001, US-00-002, US-00-003, US-00-004, US-00-005, US-00-006, US-00-007, US-00-008, US-00-009, US-00-011, US-02-001, REQ-001 to REQ-044, ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006, ADR-0007
- HLD: docs/design/docket-hld.md; diagram: docs/architecture/docket-c4.md
- Sensitive classes: auth, PII (minors, community category), external input (CSV, images, PDFs)
- Author: draft, unreviewed. 2026-10-05. Status: Draft (v1)
- Abuse-path pass: not run (design only, no application code yet to anchor evidence to)

Scope: the planned system as designed in `docs/design/data-model.md` and the backlog. Application code does not exist yet (`app/domain/` is empty), so every mitigation that depends on it is `planned` and points to a story. Routes are the planned set that `api/openapi.yaml` will carry.

## 1. Assets

| Asset | Where it lives | Owner | Why an attacker wants it |
| --- | --- | --- | --- |
| applicant personal data (names, dates of birth, roll numbers, marks, category) of minors | postgres `applications` | admissions office operations role | identity theft, selling or leaking records of children, tampering with an admission |
| document images (marksheets, ID proofs) | postgres `document_blobs` | admissions office operations role | the same data plus the document itself, usable for fraud |
| verified status and decision log (audit integrity) | postgres `applications.status`, `decisions` | verifier lead role | forcing a Verified outcome, erasing who approved what |
| staff and verifier credentials and sessions | postgres `users.password_hash`, `sessions.token_hash`, cookie | platform rotation | account takeover of a role that can read all applicants |
| exported verified list | `GET /api/exports/verified.csv` response | admissions office operations role | one request that dumps many applicants |
| OCR engine availability | api process (about 509 MB peak measured, growth unmeasured) | platform rotation | taking the verification queue down |
| model files and dependencies | RapidOCR models, python packages | platform rotation | code or result tampering through the supply chain |
| secrets (database URL, session secret) | environment, `.env` (ignored) | platform rotation | database access |

## 2. Trust boundaries

| # | From | To | Protocol | Auth on the edge | Source |
| --- | --- | --- | --- | --- | --- |
| B1 | browser | frontend static server | HTTP locally, TLS from the host when hosted | none (static files) | frontend/Dockerfile:16 |
| B2 | browser | api | HTTP locally, TLS from the host when hosted | session cookie (planned) | Dockerfile:25 |
| B3 | api | postgres | SQL over TCP, no TLS locally | database role and password from the environment | docker-compose.yml:1 |
| B4 | api | OCR engine and image decoders (OpenCV, ONNX Runtime, PDF rasteriser) | in-process library calls on untrusted bytes | none | assumption: no gateway code yet |
| B5 | api | model download host | HTTPS, on first use | none | assumption: RapidOCR downloads models on first use (docs/research/ocr-landscape.md) |
| B6 | staff role | verifier role | in-process authorisation checks | role on the session | assumption: no auth code yet |
| B7 | CI and developer machine | package registries | HTTPS | lockfile (uv.lock) | Makefile:73 |

Assumed boundaries: 4 of 7 (B4, B5, B6 and the TLS statements in B1 to B3).

## 3. Entry points

| # | Entry point | Kind | Auth required | Boundary |
| --- | --- | --- | --- | --- |
| E1 | POST /api/auth/login | route | none (credentials in body) | B2 |
| E2 | POST /api/auth/logout | route | session | B2 |
| E3 | POST /api/imports (CSV upload) | route, external input | session, staff role | B2 |
| E4 | GET /api/applications (queue and list) | route | session | B2 |
| E5 | GET /api/applications/{id} | route | session | B2 |
| E6 | POST /api/applications/{id}/documents (image or PDF upload) | route, external input | session, staff role | B2 |
| E7 | GET /api/documents/{id}/image | route | session | B2 |
| E8 | POST /api/applications/{id}/decisions | route | session, verifier role | B2 |
| E9 | GET /api/dashboard | route | session | B2 |
| E10 | GET /api/exports/verified.csv | route | session, staff role | B2 |
| E11 | GET /healthz and GET /readyz | route | none | B2 (app/api/health/router.py:34, :40) |
| E12 | GET /docs and /openapi.json | route | none, off in production | B2 (app/main.py:46) |
| E13 | document processing worker (reads uploaded bytes, calls the engine) | consumer | internal | B4 |
| E14 | seed and import scripts on the host | cron or CLI | host access | B3 |

Entry points: 14. Admin screens: none beyond the verifier and staff screens behind E4 to E10.

## 4. Threats (STRIDE)

| Id | Entry or boundary | Category | Threat | Likelihood | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-01 | E1 | Spoofing | credential stuffing or brute force against a staff or verifier account | M | H | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-02 | E1, B2 | Spoofing | a stolen session cookie is replayed | M | H | US-00-011 | planned |
| T-03 | E2, E3, E6, E8 | Tampering | cross-site request forgery makes a signed-in user import, upload or decide | M | H | new story: CSRF protection for cookie sessions | planned |
| T-04 | E1 | Repudiation | considered, none: sign-ins are recorded in `users.last_login_at` and every state change names its user (US-00-007) | | | | |
| T-05 | E1 | Information disclosure | the login response or its timing reveals which usernames exist | M | L | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-06 | E1 | Denial of service | many login attempts exhaust CPU through the password hash | M | M | new story: Login hardening: rate limit, lockout and uniform errors | planned |
| T-07 | E1, E14 | Elevation of privilege | seeded accounts keep a default or shared password | M | H | new story: Seed accounts with generated one-time passwords | planned |
| T-08 | B6, E3, E8, E10 | Elevation of privilege | a verifier imports or exports, or a staff member decides, outside the role | M | H | US-00-011 | planned |
| T-09 | E7 | Information disclosure | a document image is fetched without a session, or by a role that has no need | M | H | US-00-011 | planned |
| T-10 | E6, B4 | Tampering | a crafted image or PDF exploits a decoder (OpenCV, ONNX Runtime, the PDF rasteriser) | M | H | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-11 | E6, E13 | Denial of service | a decompression bomb or huge pixel size exhausts the 512 MB budget (509 MB measured at 30 normal pages) | H | H | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-12 | E6 | Spoofing | a file whose content type does not match its bytes passes the format check | M | M | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-13 | E6, E13 | Information disclosure | a client file name that contains a name is written to logs or URLs | M | M | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-14 | E6 | Tampering | path traversal through the client file name | L | M | new story: Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names | planned |
| T-15 | E3, E10 | Tampering | a name starting with `=`, `+`, `-` or `@` runs as a formula when the export opens in a spreadsheet | M | M | new story: CSV hardening: size and row caps, formula-safe export | planned |
| T-16 | E3 | Denial of service | a very large CSV or millions of rows exhausts memory or time | M | M | new story: CSV hardening: size and row caps, formula-safe export | planned |
| T-17 | E3 | Tampering | malformed or duplicate rows overwrite or corrupt applicants | M | M | US-00-001 | planned |
| T-18 | E3 | Information disclosure | a rejected-row error message echoes the personal value that failed | L | M | US-00-001 | planned |
| T-19 | E8 | Tampering | a verifier edits or deletes a decision log entry | L | H | US-00-007 | planned |
| T-20 | E8 | Repudiation | a verifier denies having approved an application | M | M | US-00-007 | planned |
| T-21 | E8 | Elevation of privilege | an application is made Verified by a direct request without matching evidence or a decision (REQ-019) | M | H | US-00-005 | planned |
| T-22 | E8 | Information disclosure | the free-text reason, old value or new value of a decision carries personal data into logs | L | M | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-23 | E10 | Information disclosure | one request exports every verified applicant to any signed-in user, with no trace | M | H | new story: Audit entry for every export of applicant data | planned |
| T-24 | E9 | Information disclosure | considered, none: the dashboard returns counts by status only, no personal data (US-00-008) | | | | |
| T-25 | E4, E5 | Information disclosure | considered, none beyond T-08: every staff and verifier may read every applicant by design (single office), so there is no per-record owner to enforce | | | | |
| T-26 | B5 | Tampering | model files downloaded on first use are replaced in transit or at the source | L | H | new story: Pin and checksum the OCR models, bake them into the image | planned |
| T-27 | B4, E13 | Denial of service | one request pushes the engine past available memory (509 MB measured, growth beyond 30 pages unmeasured) | H | M | US-02-001 | planned |
| T-28 | B4, E13 | Information disclosure | recognised text or field values are written to the gateway log | M | H | new story: No personal data in logs or URLs, enforced by tests | planned |
| T-29 | B4, E13 | Repudiation | considered, none: every engine call is a `gateway_calls` row with engine, version and outcome (US-02-001) | | | | |
| T-30 | B3 | Information disclosure | database traffic is unencrypted and the API role has more rights than it needs | L | H | new story: Database TLS and a least-privilege API role | planned |
| T-31 | B3 | Tampering | considered, none beyond T-30: parameterised queries only (`.claude/rules/database.md`), asyncpg through SQLAlchemy (app/db/session.py:19) | | | | |
| T-32 | E12 | Information disclosure | the API documentation and schema are exposed in production | L | L | app/main.py:46 | mitigated |
| T-33 | E11, B2 | Information disclosure | an error response leaks a stack trace or internal detail | L | M | app/main.py:57 | mitigated |
| T-34 | B2 | Elevation of privilege | the API container runs as root | L | H | Dockerfile:19 | mitigated |
| T-35 | B7 | Tampering | a vulnerable or malicious dependency enters through the lockfile | M | H | Makefile:73 | mitigated |
| T-36 | B1, B2 | Spoofing | considered, none for the local demo: traffic is plain HTTP on localhost; a hosted deployment gets TLS from the host (ADR-0004) | | | | |
| T-37 | E14 | Elevation of privilege | considered, none: scripts run with host access by the operator, outside the application's trust model | | | | |

Categories: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.

Not threats here and why: dependence on a third-party model API (none, ADR-0003); payments (none); webhooks and callbacks (none); multi-tenant isolation (single office, `docs/design/data-model.md` section 10); minors' consent and retention are privacy matters handled in `docs/privacy/DATA_MAP.md`.

## 5. Residual risks

| Threat | Risk accepted or planned | Owner (role) | Revisit |
| --- | --- | --- | --- |
| T-01 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-02 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-03 | planned: new story CSRF protection | backend lead rotation | 2026-11-15 |
| T-05 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-06 | planned: new story Login hardening | backend lead rotation | 2026-11-15 |
| T-07 | planned: new story Seed accounts | backend lead rotation | 2026-11-15 |
| T-08 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-09 | planned in US-00-011 | backend lead rotation | 2026-11-15 |
| T-10 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-11 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-12 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-13 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-14 | planned: new story Upload hardening | security champion rotation | 2026-11-15 |
| T-15 | planned: new story CSV hardening | backend lead rotation | 2026-11-15 |
| T-16 | planned: new story CSV hardening | backend lead rotation | 2026-11-15 |
| T-17 | planned in US-00-001 | backend lead rotation | 2026-11-15 |
| T-18 | planned in US-00-001 | backend lead rotation | 2026-11-15 |
| T-19 | planned in US-00-007 | verifier lead role | 2026-11-15 |
| T-20 | planned in US-00-007 | verifier lead role | 2026-11-15 |
| T-21 | planned in US-00-005 | backend lead rotation | 2026-11-15 |
| T-22 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-23 | planned: new story Audit entry for every export | admissions office operations role | 2026-11-15 |
| T-26 | planned: new story Pin and checksum the OCR models | platform rotation | 2026-11-15 |
| T-27 | planned in US-02-001, memory growth still to measure (ADR-0001) | platform rotation | 2026-11-15 |
| T-28 | planned: new story No personal data in logs | security champion rotation | 2026-11-15 |
| T-30 | planned: new story Database TLS and least-privilege role | platform rotation | 2026-11-15 |

## 6. New stories needed

- Login hardening: rate limit, lockout and uniform errors (mitigates T-01, T-05, T-06), acceptance: after five failed attempts in a minute from one source the sixth is refused with the same message as a wrong password, and an unknown user and a wrong password take comparable time.
- CSRF protection for cookie sessions (mitigates T-03), acceptance: a state-changing request without the anti-forgery token or a matching `Origin` gets 403 and changes nothing.
- Seed accounts with generated one-time passwords (mitigates T-07), acceptance: the seed script prints a random password once, no password appears in the repository, and the first sign-in forces a change.
- Upload hardening: magic-byte check, pixel and page caps, processing timeout, generated names (mitigates T-10, T-11, T-12, T-14), acceptance: a file whose bytes are not a PNG, JPEG or PDF is refused whatever its name, an image over the pixel cap or a PDF over the page cap is refused before decoding, a document that takes longer than the timeout is marked failed, and stored names never come from the client.
- No personal data in logs or URLs, enforced by tests (mitigates T-13, T-22, T-28), acceptance: a test runs an import, an upload and a decision with known values and asserts none appears in the captured logs or any URL.
- CSV hardening: size and row caps, formula-safe export (mitigates T-15, T-16), acceptance: a file over the size or row cap is refused, and an exported cell that starts with `=`, `+`, `-` or `@` is prefixed so a spreadsheet shows it as text.
- Audit entry for every export of applicant data (mitigates T-23), acceptance: every export writes who, when and how many rows, and the entry cannot be edited.
- Pin and checksum the OCR models, bake them into the image (mitigates T-26), acceptance: the image build fails if a model file's checksum differs and the running service never downloads a model.
- Database TLS and a least-privilege API role (mitigates T-30), acceptance: a hosted configuration refuses a database URL without TLS, and the API role cannot run DDL or update `decisions` beyond the erase marker.

## 7. Counts

Not run. `threats_check.py` could not run in this session (no shell). Run:

```
python3 "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/threat-model/scripts/threats_check.py" docs/security/threat-model-docket.md
```

and paste its "Threats by category:", "threat-model:" and "Gate:" lines here. By my own count, not the gate's: assets 8, boundaries 7, entry points 14, 37 rows of which 30 are threats (mitigated 4, planned 26) and 7 are "considered, none".
