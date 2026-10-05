# System design tenets: Docket

Rules this team holds itself to on this project. Each is here because somebody could plausibly do the opposite, and a reviewer can point at a breach.

## 1. Every engine call goes through the gateway function

**No module outside the gateway imports `rapidocr` or `onnxruntime`; an architecture test fails the build if one does. OpenCV is allowed elsewhere for the upload re-encode (ADR-0010).**

The cap, the call log and the replay tests only work if no call escapes (US-02-001, REQ-030 to REQ-034), and the engine must stay swappable because ADR-0001 rests on measurements that could change.

_A breach looks like:_ a merge request that imports `rapidocr_onnxruntime` in the upload route to "read the image quickly", skipping the `gateway_calls` row.

## 2. Verified is set in one place, from evidence

**`applications.status` is written only by the status service, and it sets Verified only when every compared field matches or an `approve` decision logged after the latest read of the application exists, read under the application row lock in the same transaction.**

REQ-019 and AC-US-00-005-4 forbid a direct path to Verified; one writer is the only way to prove that.

_A breach looks like:_ a merge request adds `UPDATE applications SET status = 'verified'` to a bulk-approve helper for a demo.

## 3. Personal data never enters logs, URLs or error rows

**Logs, URLs and `import_row_errors` carry ids, error classes and reason codes, never a name, date, roll number, mark or file name.**

The applicants are minors (DPIA) and an exception message can carry a key value, which is why `app/core/errors.py:125` logs the class and frames only.

_A breach looks like:_ `log.info("imported row", name=row["name"])`, or `raise ConflictError(f"duplicate {application_ref}")` whose message is logged.

## 4. The decision log is append-only in the database

**`decisions` is protected by the guard trigger and the API role has no UPDATE or DELETE on it; only `erase_application` may replace text with `[erased]`.**

AC-US-00-007-5 says nobody can edit the log, and an application-level check can be bypassed by any new code path.

_A breach looks like:_ a merge request adds `UPDATE decisions SET reason = ...` to "fix a typo" through the API role.

## 5. Every limit and every role check runs on the server

**The 8 MiB cap, the type check, the row cap and every role rule are enforced in the API and tested there; the frontend only mirrors them.**

Front-end guards are UX, not authorisation (`docs/security/AUTH.md`), and a streaming cap only helps if the server stops reading.

_A breach looks like:_ an upload size check added only in the React form, with the route reading `await file.read()` in full.

## 6. The memory budget is a number we re-measure

**A change to the worker count, the image cap, the engine or its preprocessing reports peak resident memory in its description, and the API runs one engine copy.**

The engine peaks near 509 MB against 512 MB (ADR-0001, ADR-0004), so a quiet doubling, such as `WEB_CONCURRENCY=2` in `Dockerfile:18`, breaks the plan without failing a test.

_A breach looks like:_ a merge request that raises `WEB_CONCURRENCY` for "throughput" and loads the engine at import time.

## 7. Synthetic data only, and nothing leaves the machine

**Tests, evals, demos and screenshots use generated data, and the default configuration makes no outbound request that carries a document (REQ-043, REQ-044).**

CONSTRAINTS.md makes zero cost and no real student data a hard rule, and the DPIA is unsigned.

_A breach looks like:_ a screenshot in the pull request showing a real name, or a test that calls a hosted vision API when an environment variable is set.
