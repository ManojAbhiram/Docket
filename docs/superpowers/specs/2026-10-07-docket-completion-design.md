# Docket completion: accounts, evals, UI redesign

Date: 2026-10-07   Status: draft for review   Task: NOTASK-7

## Intent

The engineer wants Docket finished against the admissions verification spec, with a much better
looking interface. Three things are missing or weak: there is no sign up, the accuracy evidence is
overstated, and the UI is plain shadcn defaults with almost no motion.

Baseline for "remaining": `CONSTRAINTS.md` wins over `spec.md` (zero cost, local OCR gateway,
`docs/spec-changes.md`). OpenRouter, Haiku, the USD 8 cap and the stronger-model comparison are
intentional deviations, not gaps.

## Decisions already made

- Sign up is open, with the user choosing the role (staff or verifier). This was chosen against the
  recommendation of invite-only accounts. Risk: anyone can register as a verifier and approve
  applications. To be recorded as an ADR.
- Visual direction: deep teal (solid teal tiles on a cool light ground, calmer motion).
- Order: accounts, then evals, then UI redesign. Each is its own plan and branch.

## Out of scope

Transfer certificate type (Q-007 open), password reset (needs email, which the zero-cost rule
excludes), the containerised one-command demo, DigiLocker, fee payment, bulk upload over 100 files.

## Gap report (against the amended spec)

| Item | State |
| --- | --- |
| CSV import, upload (JPG, PNG, PDF), gateway with call cap and logging | Done |
| Name fuzzy match, exact for dates, rolls, marks; three statuses | Done |
| Verifier approve, correct, reject with reason; decision log | Done |
| Per-field view, field crops, dashboard, CSV export | Done |
| 20 applications, 30 synthetic PNGs | Done |
| Field-level extraction accuracy on 30 labelled documents | Missing |
| Chosen engine against runner-up on 10 documents | Partial, no accepted result |
| CI replay with no live engine calls | Not verified |
| Sign up | Missing, not in the PRD |
| IBM Plex fonts | Missing |
| Every story in `docs/progress` | "in review", none closed |

## Progress (updated 2026-10-07, after the sign up and evals merges)

The gap report above is the state at the start of the work. This table is the state now.

| Item | State now | Where |
| --- | --- | --- |
| Sign up (piece 1) | Merged to `main` (pull request #4). Task reviews and a final read-only review done; its blockers (source address contract, actor wording) are documented. Browser check and accessibility audit of the sign up screen not run | ADR 0013, `docs/progress/NOTASK-7.md` |
| Evals: real extraction accuracy, 10-document comparison, replay gate (piece 2) | Merged to `main` (pull request #5). RapidOCR 0.995 on all 30, 1.0 on the 10-document set, 0.9863 on the noisiest 10; Tesseract 0.2475, 0.2027, 0.0274. No independent review of the evals code yet | `docs/testing/extraction-accuracy.md`, `docs/progress/NOTASK-8.md` |
| Baseline in `evals/ocr/gate.yaml` | Not accepted. A person must set `accepted_baseline: 0.995` and drop `EVAL_ALLOW_NO_BASELINE=1` from the CI step; until then CI gates nothing on accuracy | `docs/progress/NOTASK-8.md` |
| Runner-up comparison | Tesseract needed three adjustments to be scored, and its page segmentation mode was chosen on the comparison set, which favours it. `pytesseract` is not in `pyproject.toml` | `docs/progress/NOTASK-8.md` |
| UI redesign, deep teal (piece 3) | In progress, not merged: tokens, motion layer and shared components committed; screens being finished; fonts still on the old stack; no full gate, accessibility audit or browser check yet | branch `feature/NOTASK-9-UiRedesign` |
| IBM Plex fonts | Not added; a package or font files need the engineer's decision (no new dependency without it) | piece 3 |
| Transfer certificate type (stretch) | The seed data and the classifier already handle it and the eval counts it; the product decision in Q-007 is still open | `docs/product/questions.md` |
| CI replay with no live engine call | Done for the eval gate (it replays a 68 KB recording); the models are still downloaded on first live use (DEBT-004) | `docs/DEBT.md` |
| Password reset, containerised one-command demo | Out of scope here | none |
| Every story in `docs/progress` still "in review" | Unchanged; to be closed by the engineer after review | none |

## Piece 1: accounts

`POST /auth/register` takes `username`, `display_name`, `password`, `role`. Bodies use
`extra="forbid"` and length bounds like `LoginRequest`. On success it creates the user and starts a
session, setting the same session and CSRF cookies as login, and returns `UserOut`.

Rules, in `app/domain/auth.py` with no database or request access:

- Username: lowercase, 3 to 64 characters, letters, digits, `.`, `_`, `-`. Unique in the database.
- Password: 10 to 256 characters, not equal to the username.
- A taken username returns 409. This reveals which usernames exist; accepted with open sign up.
- Hashing uses the existing Argon2 `Passwords` and `hash_slots`.
- A registration limiter, shaped like `LoginLimiter`: N per source per hour, then 429 with
  `Retry-After`.

Data: expected to need no new column (the user table holds username, display name, role, hash). The
plan must confirm this against `app/db/models.py` before the first edit. If a column is needed, it
is a schema change and needs its own migration and plan approval.

Screen: a Sign up page beside Sign in, linked both ways, with a role choice that states what each
role can do. After sign up, staff land on Import and verifiers on the Review queue.

Tests: domain rules and limiter; API success, 409, 422 weak password, 429; front-end form; session
and CSRF cookies set on success. Also update `api/openapi.yaml`, `docs/security/permission-matrix.md`
and the threat model for the new open endpoint.

## Piece 2: evals

The existing 100% figures in `evals/ocr/results` only test that the printed value appears in the
OCR text, which `evals/report.py` calls an upper bound.

- A new eval runs the 30 labelled documents through the real gateway, classifier and extractor and
  compares each extracted field with `data/seed/labels.json`. It reports accuracy per field and per
  document type, plus classification accuracy.
- The same 10 documents run through RapidOCR and the runner-up (Tesseract).
- A noisier subset (blur, skew, shadow) so the engines can be told apart. If both score near 100% on
  clean pages the report says the set cannot separate them.
- A person accepts a baseline in `evals/ocr/gate.yaml`. A CI job replays recorded responses with no
  live engine and fails if the score falls by more than `delta` (0.02).

## Piece 3: UI redesign, deep teal

- Tokens: `docs/design/tokens.json` and `frontend/src/index.css` get a teal primary, deep teal tiles,
  amber and red for status, a tinted neutral ground, light and dark themes. Contrast pairs are
  re-checked with `contrast.test.ts`.
- Type: IBM Plex Sans, Condensed and Mono, self-hosted.
- Motion replaces the "one moment per page" rule in `docs/design/motion.md`: staggered entrance of
  tiles and rows, count-up on dashboard tiles, hover lift, progress fill while a document is read,
  status badge transitions, route transitions, dialog open and close.
- Rules kept: only `transform` and `opacity` move; `prefers-reduced-motion` turns everything into
  instant state changes; review-compare selection and the OCR box stay instant.
- Screens: sign in, sign up, dashboard, applications, import, upload, review queue, compare,
  decision dialog, export, and the shared header and sidebar, on desktop and phone.
- Checks: existing front-end tests, an accessibility audit, and a look in a real browser. None run
  yet.

## Risks

- Open role choice lets anyone become a verifier (ADR, accepted by the engineer).
- Sign up is an unauthenticated write endpoint: abuse, enumeration, resource use (limiter, Argon2
  slots).
- Near-perfect scores on clean synthetic pages may hide weakness on noisy photos.
- Heavier motion must not slow the verifier's working screens.

## Next step

After this spec is approved: `writing-plans` for piece 1 only. Pieces 2 and 3 get their own plans
when reached.
