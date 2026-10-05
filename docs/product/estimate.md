# Estimate

Backlog: docs/product/backlog.md   Sized: 2026-10-05   Team: unconfirmed: 1 person assumed (no team file in the repository)
Previous estimate: none

## 1. Verdict

**Not answerable as a date.** 62 points remain (Must 54, Should 5, Could 3), but the repository has no sprint log, no team file and no release plan, so there is no velocity, no capacity and no freeze date to compare against. A margin would be invented.

What the points do say, with velocity as the only unknown (assumed values, not measurements):

| Velocity (points per sprint, assumed) | Musts (54) | Musts and Should (59) | Everything (62) |
| --- | --- | --- | --- |
| 10 | 5.4 sprints | 5.9 sprints | 6.2 sprints |
| 15 | 3.6 sprints | 3.9 sprints | 4.1 sprints |
| 20 | 2.7 sprints | 3.0 sprints | 3.1 sprints |

To turn this into a verdict, give me: how many people, sprint length, completed points per sprint (or a rough pace), and the last day story work can merge. Until then nothing here says "fits".

Two sizes carry most of the uncertainty: US-00-003 (extraction, 8) and US-02-001 (gateway, 8). Both are XL and flagged for splitting. Proposed splits are in section 5, awaiting product.

## 2. Scope

Excluded and not re-sized:

- **US-02-003 Seed synthetic applications and documents: Done.** All five acceptance criteria are met in code (commits 60bd677 and dfc8d96): 20 applications, 30 documents, HTML to PNG with OpenCV noise, deliberate mismatches, labels, synthetic-only checks in `tests/test_seed_documents.py`. Points were never recorded (TBD in the backlog), so none are counted.

Sized for what is left (In progress):

- **US-02-002 Choose the engine by measurement.** Done: candidate list and exclusions (`docs/research/ocr-landscape.md`), per-field accuracy, latency, hardware and the confidence check (`docs/research/ocr-benchmark.md`), the decision record (ADR-0001). Left: document-type classification accuracy (AC-3 asks for it and it was never measured), the PaddleOCR and docTR runs, and the memory growth measurement.
- **US-02-004 Report extraction accuracy.** Done: the harness, per-field accuracy on 30 documents, runs without a paid service. Left: the 10-document comparison of the chosen engine against the runner-up as a named step (AC-2), and a clean-checkout run.

No story is withdrawn. No story lacks acceptance criteria, so none is refused. REQ-045 (transfer certificate) has no live story: see section 5.

## 3. Story sizes

Scale: XS 1, S 2, M 3, L 5, XL 8. Previous sizes: none (all TBD).

| Story | Priority | Previous | Size | Points | Drivers | Assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| US-02-001 Gateway | Must | TBD | XL | 8 | 6 AC; call count that survives restarts (a table and a migration); per-call logging; engine swap by configuration; replay fixtures for CI; an architecture test; `app/domain/` and `app/db/` are empty (checked) | A1, A2 |
| US-00-003 Read type and fields | Must | TBD | XL | 8 | extractor with box rules per document type (ADR-0002); four document types; validators; classification; per-field confidence; 6 AC; the engine returns text and boxes only (checked in `evals/ocr_bench.py`) | A3, A4 |
| US-00-001 Import CSV | Must | TBD | L | 5 | new route; new table and migration; row validation with reasons; Q-008 batch size | A5 |
| US-00-002 Upload documents | Must | TBD | L | 5 | new route; image bytes stored in Postgres because free disks are ephemeral (ADR-0004); PDF rasterising needs a system package (poppler) | A6 |
| US-00-004 Compare fields | Must | TBD | L | 5 | pure functions plus an integration path; threshold, date format and field map open (Q-003, Q-011, Q-017); 26 cases already written | A7 |
| US-00-005 Set status automatically | Must | TBD | L | 5 | status model; evidence storage; guard that the service itself refuses Verified (AC-4); schema change; Q-004 | A8 |
| US-00-006 Review a flagged application | Must | TBD | L | 5 | first real screen; queue route; document image beside values; frontend has only the health screen (checked) | A9 |
| US-00-007 Decide a flagged application | Must | TBD | L | 5 | three actions; decision log table; correct re-runs the comparison; 5 AC | A10 |
| US-00-011 Sign in | Should | TBD | L | 5 | auth with role checks per resource; seeded accounts only; supports REQ-021 and REQ-027, no requirement names sign-in itself | A11 |
| US-00-008 Dashboard counts | Must | TBD | M | 3 | one route plus a new screen | none |
| US-00-010 Field crops | Could | TBD | M | 3 | needs box positions from the engine; acceptance is set in design | A12 |
| US-00-009 Export verified list | Must | TBD | S | 2 | one route; columns open (Q-011) | none |
| US-02-002 Engine (remaining) | Must | TBD | S | 2 | classification accuracy plus the unrun engines; mostly measuring | A13 |
| US-02-004 Accuracy report (remaining) | Must | TBD | XS | 1 | harness exists; add the named comparison step | none |

Total: 62 points. Must 54, Should 5, Could 3.

Assumptions:

- A1. The call count persists across restarts, in the database (Q-009, unconfirmed).
- A2. The gateway starts with one engine adapter, RapidOCR (ADR-0001, confirmed).
- A3. Four document types are in scope, because the seed and ADR-0002 include the transfer certificate even though the backlog's AC list three (unconfirmed: Q-007).
- A4. One template per document type; real layouts are out of reach (`CONSTRAINTS.md` section 2).
- A5. Batches of up to 100 documents, 5,000 applications are context, not a build target (Q-008, unconfirmed).
- A6. Poppler can be installed in the image (unconfirmed: not checked).
- A7. Name threshold, date normalisation and the field map are settled in design (Q-003, Q-011, Q-017, unconfirmed).
- A8. Required documents are the three types of Q-004 (unconfirmed).
- A9. React, TanStack Router and shadcn components from the scaffold are used as they are (confirmed: `frontend/package.json`).
- A10. A correction edits the extracted value (Q-005, unconfirmed); reject keeps Needs review plus a flag (Q-006, unconfirmed).
- A11. Seeded role-based accounts, no password reset or account management (Q-013, unconfirmed).
- A12. The engine returns where each field sits; RapidOCR boxes are assumed enough (unconfirmed).
- A13. PaddleOCR and docTR install and run on Python 3.12 in the separate environment (unconfirmed: DEBT-006).

## 4. Capacity

**Unconfirmed: no sprint log.** `docs/product/sprints.md` does not exist and no file in the repository records completed points per sprint, so velocity, the window, holidays and leave are all unknown. The only history is this work stream: the seed story (US-02-003) and most of US-02-002 and US-02-004 were produced over a few working sessions, with the build, tests and documents written alongside. That is one data point from one person with AI assistance and I am not converting it into a velocity.

## 5. Gaps and calendar risks

Gaps (proposed; the backlog is not edited here):

- **REQ-045 (transfer certificate) has no live story,** yet the seed already generates 7 transfer certificates and ADR-0002 plans rules for them. Q-007 says "out of scope until every other requirement is done". Either add an AC to US-00-003 or confirm the stretch. Not counted in the 62.
- **US-00-003 and US-02-001 are XL.** Proposed splits, awaiting product: US-00-003 by document type, marksheets first (about 5 points), then ID proof and transfer certificate (about 3); US-02-001 into the gateway call, logging and replay (about 5) and the persisted call cap (about 3). Sizes stay as they are until the backlog splits.
- **Hosting work has no story.** ADR-0004 lists what must happen before hosting: one worker, CORS, a database URL conversion, uploads in Postgres, confirming Render's free RAM. Roughly S to M (2 to 3 points), conditional on the memory trigger, not counted in the 62.
- **No story for the review threshold configuration** (ADR-0005: `NEEDS_REVIEW_CONFIDENCE`, target share). Folded into US-00-005's size; flag if product wants it separate.
- **No requirement names sign-in itself.** US-00-011 now supports REQ-021 and REQ-027 (the owner chose to keep it), and sits in the Should tier because REQ-027 needs a "who". Confirm Q-013.
- **Data the AC assume with nothing creating it:** the application and document tables, the decision log table, the stored comparison result (AC-US-00-007-5, AC-US-00-006), and the field map (Q-017). Each lands in the story that first needs it.
- **Contradicted claims:** none; the backlog claims nothing is built and the code agrees (`app/domain/` is empty).
- **Dependency cycles:** none found by following Depends on edges.
- **ADR consequences as drivers:** ADR-0001 (memory growth unmeasured) drives US-02-001 and US-00-002; ADR-0002 drives US-00-003; ADR-0004 drives US-00-002 and the unsized hosting work; ADR-0005 drives US-00-005.

Calendar risks:

- No external lead time exists: the stack is free and needs no vendor onboarding. The one external dependency is the product owner's answers to the 18 open questions, which have no date.
- If a hosted demo becomes a requirement, a new account on each of Render, Neon and Cloudflare is needed, with no card (unverified for Cloudflare).

## 6. Plan

Proposed order, respecting Depends on; each phase ends with something a person can do. No sprint is assigned because capacity is unknown.

1. **Foundation.** US-02-001 gateway, US-00-001 import, US-00-011 sign in, and the remaining US-02-002 measurements. Ends with applications in the system and an engine behind the gateway.
2. **Reading.** US-00-002 upload, then US-00-003 extraction (marksheets first). Ends with a document producing fields.
3. **Deciding.** US-00-004 compare, US-00-005 status. Ends with an application getting a status automatically.
4. **Verifying.** US-00-006 review, US-00-007 decide. Ends with a verifier working the queue.
5. **Reporting.** US-00-008 dashboard, US-00-009 export, US-02-004. Ends with the result and the evidence.
6. **Could.** US-00-010 crops.

The test cases for US-00-004 (26, `docs/testing/`) are ready to automate when phase 3 starts.

## 7. Task hours

0 tasks: hours not estimated. `docs/product/tasks.md` does not exist, because tasks were not requested when the backlog was written.
