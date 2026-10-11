# Vision upload security assessment [NOTASK-17]

**Partial.** Independent static review of the Vision upload path on 2026-10-11. Runtime attacks, production systems, provider accounts and dependency vulnerability scanning were not exercised. Memory tuning later added shared admission for the first finding, with local regression evidence described below. The remaining recommendations are proposed.

## Provenance and assurance

The original CSO run was `1791718388790-06773c8ab3c42927`, against snapshot `e3498488`, and finished partial. Semgrep was unavailable because no qualified Linux amd64 scanner image was available. Finding submission was rejected with `DEADLINE` before persistence. **CSO PERSISTENCE_FAILED:** the helper report contains no accepted findings. The findings in this document are an independent manual assessment, not helper-persisted CSO findings, runtime reproductions or authenticated repair bundles. No new CSO run was started and no current-source closure is claimed for the original run.

This review traced authentication and CSRF, multipart reading, mode validation, normalization, duplicate persistence, worker routing and fallback, provider requests and responses, extraction safety, status computation and image retrieval. It also considered accepted ADR-0013 and ADR-0015 and the existing permission matrix. File and line references describe the reviewed source; subsequent memory work may shift line numbers.

## Findings

| ID | Severity | Confidence | Evidence | Location | Impact |
| --- | --- | --- | --- | --- | --- |
| MANUAL-VIS-01 | Medium | High for missing admission control; exhaustion threshold unmeasured | Static | `app/api/documents/router.py:69`, `app/domain/uploads.py:131`, `app/db/repositories/uploads.py:107` | Concurrent staff uploads allocate full decoded images before deduplication and can exhaust the 512 MB host |
| MANUAL-VIS-02 | Medium | High for missing byte bound; malicious upstream prerequisite | Static | `app/gateway/vision.py:148` | An oversized provider response consumes unbounded API memory |
| MANUAL-VIS-03 | Low | High | Static | `app/api/uploads.py:56`, `app/api/uploads.py:75` | Multipart allowance permits a file slightly larger than its configured cap |

### MANUAL-VIS-01: Upload normalization has no aggregate memory limit

An authenticated staff caller with a valid CSRF token can submit several compressible PNG/JPEG files whose dimensions remain within the 25,000,000 pixel allowance. Each route submits normalization to the default thread executor at `app/api/documents/router.py:69`. `app/domain/uploads.py:131` checks the per-image limit, then `:134` decodes a color image before resizing. A full 25 MP color array alone is approximately 75 MB decimal, excluding encoded input, decoder scratch memory and resized output. Multiple active decodes share the API's memory with OCR and password hashing.

The boundary is a permitted upload becoming native decoder work in the API process without an explicit memory-based admission limit. The duplicate check and application advisory lock occur later in `app/db/repositories/uploads.py:107-114`; resending already stored bytes still performs normalization. A finite default executor limits simultaneous threads but its capacity is not derived from the 512 MB budget, and pending requests retain uploaded bytes. This is a supported availability risk, not a demonstrated crash or decoder exploit.

Countercontrols considered: staff authorization and CSRF prevent anonymous direct requests; input byte and pixel limits prevent individually unlimited files; output is resized; the OCR worker reads one document at a time. None bounds aggregate upload normalization. ADR-0013 accepts public role selection, so acquiring a staff account may be possible in the demo; that accepted design is not itself reported as a privilege escalation.

Proposed repair: limit admitted normalization work using the measured API plus OCR memory budget, with a bounded waiting policy that does not accumulate file bodies. Include PDF work under the same admission policy. Consider checking existing hashes before expensive conversion while preserving transactional deduplication. Verify concurrent near-limit images and duplicates alongside OCR before claiming a 512 MB guarantee.

### MANUAL-VIS-02: Provider response accumulation lacks a byte ceiling

`app/gateway/vision.py:148-153` accumulates every decoded response chunk into a `bytearray`, then copies it into a response object. There is no maximum response size before JSON parsing. `max_tokens=600` at `:135` asks the provider to restrict generated output; it does not bound the HTTP response envelope, extra properties or a response from a faulty or hostile upstream.

The attacker prerequisite is control of or a fault at the trusted HTTPS provider response, not ordinary control of the uploaded page. The boundary is remote response bytes entering the API process, potentially causing memory exhaustion during the one permitted worker call. No evidence establishes that the real provider can currently be induced to send a huge response, so this is a conditional upstream resource risk.

Countercontrols considered: the endpoint is fixed HTTPS at `:25`; the request uses no caller URL; redirects are not enabled in client construction at `:90`; a deadline limits duration. Those controls restrict origin and time, but a large body can arrive within the deadline.

Proposed repair: enforce a documented response-byte cap while streaming, including decoded chunks, and convert rejection into a safe Vision failure so existing local fallback applies. Exercise both a declared large body and a streamed body without `Content-Length` using a fake transport.

### MANUAL-VIS-03: File cap includes unused multipart allowance

`app/api/uploads.py:56` caps the entire multipart body at `cap + 8192`, then `:75` reads the file part without checking its length against `cap`. An authenticated staff caller can use short multipart headers and a valid image with extra bytes so the file exceeds `cap` while the complete body remains within the total limit. The excess is less than 8192 bytes because real boundaries and headers consume part of that allowance.

The boundary is the configured file-size contract. Impact is a small policy bypass, not unlimited upload size or a material memory bomb by itself. Normalization, signature checks and the overall body ceiling still apply. The helper is shared by CSV import, so that caller has the same distinction between file and envelope size.

Proposed repair: check actual file-part length against `cap` after parsing, retaining the independent multipart envelope ceiling. Verify a file just above the cap with minimal multipart overhead and a legal file whose headers use the allowance.

## Other observations

- The claimed total Vision deadline is approximate. `app/gateway/vision.py:128-153` checks time only after `iter_bytes()` yields, and HTTPX phase timeouts at `:90` can permit an outstanding read to finish after the deadline. The same applies to entering the stream, and final completion is not checked separately. This does not establish an indefinitely trickling read, because yielded pieces are checked. A strict total bound would require the remaining deadline to constrain blocking operations. This is a timeout-contract limitation, without a demonstrated attack against the fixed provider.
- `app/core/config.py:42-44` accepts any configured model string and any positive daily cap. `vision_configured` at `:73-75` checks presence, not the accepted `:free` policy. An operator can accidentally configure a paid model or raise the cap beyond ADR-0015. This is an operator policy gap, not caller-controlled model selection, and no charge was demonstrated. Fail-fast validation against the accepted free-model policy is a proposed follow-up.
- `app/gateway/core.py:75-81` reserves call slots in process memory, keyed by ledger identity. It does not coordinate multiple API workers. The current single-worker deployment intention and serial queue are countercontrols; rolling call limits should be re-evaluated before increasing worker count. No multi-worker cap bypass was reproduced.

## Controls traced

| Boundary | Static evidence and result |
| --- | --- |
| Session, staff role, CSRF before parsing | `app/api/documents/router.py:51-60`; `app/api/auth/deps.py:41-84`. The route declares no body parameter and only reads the multipart body inside the handler. |
| Mode and configured availability | `app/api/documents/router.py:61-67`. Only `free` and `vision`; missing Vision configuration returns 409. Model and endpoint are not request parameters. |
| Input type and pixels | `app/domain/uploads.py:96-102`, `:127-134`. Declared type must match allowed signatures; headers are checked before image decoding. No claim of full native-decoder containment. |
| PDF handling | `app/domain/pdf.py:24-26`, `:37-45`. First page only, size precheck and 30 second subprocess timeouts. Aggregate resource limits remain covered by MANUAL-VIS-01. |
| Stored image and filename | `app/domain/uploads.py:141-158`; `app/api/documents/router.py:129-145`. Metadata removed through re-encoding; image response uses generated UUID name, fixed media type, `nosniff` and private no-store caching. |
| SQL and deduplication | `app/db/repositories/uploads.py:20-36`, `:106-137`. Parameters bind values; advisory lock prevents duplicate insertion. Expensive normalization precedes this lock. |
| Opt-in egress and fallback | `app/jobs/worker.py:108-126`. Free mode uses local reader; Vision errors/cap refusal fall back locally and retain a reason code. Fallback does not require Vision review policy because its actual reader is local OCR, consistent with ADR-0015. |
| Provider secrecy | `app/gateway/vision.py:109-114`; `app/gateway/core.py:49-61`; `app/jobs/worker.py:129-142`. Errors are mapped to class/reason codes; provider messages are not passed to stored failure reasons. The key is `SecretStr` with hidden repr in `app/core/config.py:41` and is sent only as the fixed-endpoint authorization header. No secret values were read. |
| Structured result safety | `app/gateway/vision.py:65-67`, `:183-217`. Document types are constrained, irrelevant field names are discarded and every retained Vision field requires review. Present fields have no score or box; missing fields use zero confidence plus `not_extracted`, still require review. No model-provided tool call is executed. |
| Approval safety | `app/domain/status.py:47-74`; `app/db/repositories/statuses.py:37-47`, `:151-156`. Review flags and unknown types prevent automatic Verified; explicit current human approval can stand in for field mismatch, as designed. New evidence invalidates old approvals. |
| Resource visibility | `docs/security/AUTH.md:58`. Both authenticated roles can read every application in the accepted single-office product. No tenant isolation vulnerability is inferred from this intentional policy. |

## Verification and gaps

### Fresh manual review of memory admission

Memory tuning subsequently added `app/core/compute.py`. `compute_slot` acquires the existing hashing semaphore and its lease shields native work, deferring release to native task completion when a caller is cancelled. `app/api/documents/router.py` now acquires that admission before body reading, retains it through normalization, persistence and status recomputation, and drops raw upload bytes after hashing and measuring them. Body reading has a 30 second ceiling; admission, processing and persistence together use the existing configured read timeout and return the existing safe 503 envelope on expiry. The upload API contract records that outcome in `api/openapi.yaml`.

The same admission now protects password verification/hashing in `app/api/auth/router.py` and local OCR, including Vision fallback, in `app/jobs/worker.py`, wired through `app/jobs/runner.py` and `app/main.py`. Vision HTTP waiting does not hold this CPU admission. The memory tuning default uses one slot and recycles the OCR child after each read; the parent task owns its measured memory evidence.

Evidence: the original parent regression failed because the upload body was read while admission was occupied. A second regression failed with `assert 2 == 1`: a second upload buffered its body while the first waited for persistence. Keeping admission through persistence made the 23 document regression checks pass. Those three admission/timeout checks now live in `tests/integration/api/test_upload_memory.py`, leaving existing document tests in their original file. `tests/test_compute.py` covers cancellation while native work is still running, late native failure, normal failure and cancellation while waiting for admission. `tests/test_jobs.py` covers local-reader waiting and Vision reads proceeding without CPU admission. A focused unit run reported `45 passed`; Ruff reported `All checks passed!`; mypy reported `Success: no issues found in 91 source files`.

These are local regression observations and fresh manual source review. MANUAL-VIS-01's original snapshot finding is retained for traceability; its missing aggregate normalization admission has been addressed in this worktree. This is not helper-certified finding closure or an authenticated CSO repair bundle. The configured semaphore can still be raised by an operator; multi-process deployment needs a separate total budget, and provider response memory remains unbounded under MANUAL-VIS-02. No live overload attack or general guarantee for all upload/provider inputs follows from the focused regressions.

The initial scan used source inspection only. Existing tests were located, including `tests/test_upload_reader.py`, `tests/test_uploads.py`, `tests/test_vision_reader.py`, `tests/test_vision_routing.py`, `tests/integration/api/test_documents_vision.py` and `tests/integration/test_document_queue.py`. The later memory repair exercised focused unit and upload/authentication integration regressions. The parent task reports its broader gates with their own provenance. Passing functional tests does not constitute attack reproduction.

Not run: multipart cap reproduction; concurrent upload memory attack; malicious response simulation; decoder exploit testing; live OpenRouter calls; production database, deployment and bucket checks; external advisory lookups; dependency scanners; qualified runtime CSO reproduction or repair validation. No repair bundle or release clearance is delivered. Any follow-up CSO current-source recheck must supply fresh evidence for each original boundary.
