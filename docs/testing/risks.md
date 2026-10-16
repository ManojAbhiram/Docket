# Test risks

Source: `docs/product/backlog.md`, story US-00-004 as of 2026-10-05 (R-001 to R-007) and the other 14 stories as of 2026-10-16 (R-008 onward); threat models: none.
Ids are permanent; a risk that no longer applies keeps its row with level
`Low` and "closed: <reason>" in the risk text.

## How the level is set

Likelihood (L, M, H) is how probable the failure is, from the evidence named
in the row: the size of the change, branching or concurrency in it, a new
integration or dependency, defects in the same files (`git log --grep=fix`
over the paths), and how settled the requirement is.
Impact (L, M, H) is what it costs when it happens: H for money, auth, data
loss, PII or a legal duty; M for a core flow; L for cosmetics.

| Likelihood / Impact | L | M | H |
| --- | --- | --- | --- |
| L | Low | Low | Medium |
| M | Low | Medium | High |
| H | Medium | High | High |

Depth by level, counted in live cases: High needs three, one with a `not:`
oracle and one of type integration or e2e; Medium needs two, one with a
`not:` oracle; Low needs one.

## Register

US-00-004 (written 2026-10-05): No code for the matching rules exists yet (`app/domain/` is empty), and no defect history applies; likelihood comes from the change being new and from open questions Q-003 (name threshold), Q-011 (date formats) and Q-017 (field map).

Other stories (2026-10-16, NOTASK-28): the code exists, so likelihood comes from the acceptance audit `docs/testing/NOTASK-17-acceptance-audit.md` (Partial, Drift and Unproven rows), the fix commits in the same files (`git log --grep=fix`: 4a3e49f gateway cap race; da6b85f, f4301d0, d4fedc7, d2774c0 Vision; 7476eb2 missing marks; 58e41c6 password rules; 0fc0394 correction picker; dfc8d96 seed rendering) and the open questions Q-006 and Q-013. Where no such evidence exists the Source says the criterion and the story is rated Low or on impact alone. No threat models exist, so no `T-nn` is traced.

| Risk | Story | What could go wrong | Source | Likelihood | Impact | Level | Cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | US-00-004 | Another person's document is accepted as a match for an application, so a wrong applicant is verified | AC-US-00-004-1, Q-003 (threshold undefined), new code | M | H | High | TC-0003, TC-0004, TC-0006 |
| R-002 | US-00-004 | A correct date printed in another format is flagged, sending verifiers needless work | AC-US-00-004-2, Q-011 | M | M | Medium | TC-0007, TC-0009 |
| R-003 | US-00-004 | A roll number that differs by one character is accepted | AC-US-00-004-3, new code | L | H | Medium | TC-0012, TC-0013 |
| R-004 | US-00-004 | A changed mark in one subject is accepted | AC-US-00-004-4, new code | L | H | Medium | TC-0016, TC-0018 |
| R-005 | US-00-004 | A document from which nothing could be compared counts as a match, so an application is verified on no evidence | AC-US-00-004-5, Q-017 (field map undefined) | M | H | High | TC-0019, TC-0020, TC-0022 |
| R-006 | US-00-004 | The comparison writes a name, date of birth or roll number into the logs | AC-US-00-004-1 to 4, `.claude/rules/python.md` (never log PII), minors' data | L | H | Medium | TC-0023, TC-0024 |
| R-007 | US-00-004 | Malformed OCR output (an empty or impossible value) crashes the comparison and blocks the queue | AC-US-00-004-2, noisy OCR from `docs/research/ocr-landscape.md` | M | M | Medium | TC-0010, TC-0025 |
| R-008 | US-00-001 | A malformed row is created, or one bad row stops the good rows, so applications hold wrong data or are lost | AC-US-00-001-2, AC-US-00-001-3, new importer | L | H | Medium | TC-0037, TC-0047, TC-0048 |
| R-009 | US-00-001 | A refused row's value, a child's name or date of birth, is stored or sent back in the error list | AC-US-00-001-2, T-18, REQ-003, minors' data | L | H | Medium | TC-0045, TC-0046 |
| R-010 | US-00-001 | A CSV from a forged, cross-site or unauthorised caller creates applications | AC-US-00-001-1, ADR-0012 (CSRF token and Origin), AC-US-00-011-3 | L | H | Medium | TC-0034, TC-0035, TC-0163 |
| R-011 | US-00-001 | A repeated import overwrites or duplicates applications | AC-US-00-001-3, T-17 | M | M | Medium | TC-0036, TC-0049 |
| R-012 | US-00-001 | An oversized, over-long or non-UTF-8 file exhausts memory or half-imports | AC-US-00-001-1, T-16, import_max_bytes and import_max_rows | M | M | Medium | TC-0030, TC-0031, TC-0032 |
| R-013 | US-00-002 | A hostile or wrong file is stored: a wrong format, a disguised type, an oversized file or a pixel bomb | AC-US-00-002-2, T-10, T-12, ADR-0009, ADR-0010 | M | H | High | TC-0062, TC-0063, TC-0064, TC-0065, TC-0066, TC-0345 |
| R-014 | US-00-002 | A newer upload loses or replaces the older document, or the older document is the one compared | AC-US-00-002-4, Q-010 | L | H | Medium | TC-0072, TC-0073, TC-0075 |
| R-015 | US-00-002 | A multi-page PDF is stored whole, the wrong page is used, or the conversion leaves this machine | AC-US-00-002-3, REQ-006, REQ-044 | M | H | High | TC-0056, TC-0068, TC-0071 |
| R-016 | US-00-002 | A forged, cross-site or unauthorised upload stores a child's document | AC-US-00-011-3, ADR-0012 | L | H | Medium | TC-0059, TC-0164 |
| R-017 | US-00-002 | The same bytes uploaded twice create duplicate documents | AC-US-00-002-1 | L | L | Low | TC-0057, TC-0058 |
| R-018 | US-02-001 | A module outside the gateway calls an engine, so the cap, the log and the mode are bypassed | AC-US-02-001-1, the architecture test checks named clients only (audit NOTASK-17) | M | M | Medium | TC-0076, TC-0077 |
| R-019 | US-02-001 | Calls go past the cap, or the cap is lost on restart, so the free quota is exceeded | AC-US-02-001-4, Q-009, fix 4a3e49f (cap race) | M | H | High | TC-0085, TC-0087, TC-0088, TC-0100 |
| R-020 | US-02-001 | A page image leaves this machine in the default mode | AC-US-02-001-6, REQ-044, ADR-0015 | M | H | High | TC-0092, TC-0095, TC-0096, TC-0097 |
| R-021 | US-02-001 | The call log loses or misstates a call: engine, latency, outcome or cost | AC-US-02-001-3 | L | M | Low | TC-0080, TC-0081, TC-0083 |
| R-022 | US-02-001 | Swapping the engine changes the result shape and breaks a caller | AC-US-02-001-2 | L | M | Low | TC-0078, TC-0079 |
| R-023 | US-02-001 | The test suite or CI makes a live engine call | AC-US-02-001-5, REQ-034 | L | M | Low | TC-0091, TC-0093, TC-0094 |
| R-024 | US-00-003 | A weak, missing or unreadable field is accepted as read, so a wrong value can be verified | AC-US-00-003-4, AC-US-00-003-5, Q-001, Q-016, ADR-0017 (calibration unproven) | M | H | High | TC-0115, TC-0117, TC-0119, TC-0120 |
| R-025 | US-00-003 | A document gets the wrong type or none, so the wrong comparison runs | AC-US-00-003-2 | M | M | Medium | TC-0106, TC-0107, TC-0109, TC-0110 |
| R-026 | US-00-003 | A noisy phone photo crashes or stalls the read and blocks the queue | AC-US-00-003-5, REQ-007 | M | M | Medium | TC-0119, TC-0121, TC-0122 |
| R-027 | US-00-003 | A page leaves the machine without the person choosing Vision, or Vision is used past its cap | AC-US-00-003-6, ADR-0015, fixes da6b85f, f4301d0, d4fedc7 and d2774c0 in the Vision path | M | H | High | TC-0123, TC-0124, TC-0125, TC-0126 |
| R-028 | US-00-003 | Vision answers are trusted without a person looking at them | AC-US-00-003-3, AC-US-00-003-4, ADR-0015 | L | H | Medium | TC-0113, TC-0114 |
| R-029 | US-00-003 | More or fewer gateway calls are made per document than the story states | AC-US-00-003-1 | L | M | Low | TC-0101, TC-0102, TC-0103 |
| R-030 | US-00-005 | An application is marked Verified without every field matching or without a verifier | AC-US-00-005-1, AC-US-00-005-4, REQ-019, ADR-0016 changed precedence, fix 7476eb2 (missing marks) | M | H | High | TC-0128, TC-0131, TC-0140, TC-0144 |
| R-031 | US-00-005 | A mismatch or weak field leaves the application out of review | AC-US-00-005-2 | L | H | Medium | TC-0132, TC-0133, TC-0134 |
| R-032 | US-00-005 | Missing documents hides a mismatch, or a failed read is called a missing upload | AC-US-00-005-3, ADR-0016 | M | M | Medium | TC-0138, TC-0139 |
| R-033 | US-00-005 | A caller sets Verified directly or without authority | AC-US-00-005-4, T-21 | M | H | High | TC-0140, TC-0141, TC-0142, TC-0143 |
| R-034 | US-00-005 | A stale Verified survives a new upload | AC-US-00-005-4, AC-US-00-007-1 | L | H | Medium | TC-0145, TC-0201 |
| R-035 | US-00-005 | A status outside the three values exists | AC-US-00-005-5 | L | M | Low | TC-0146, TC-0148 |
| R-036 | US-00-011 | An account is taken over by guessing or credential stuffing | AC-US-00-011-1, T-01, ADR-0012, ADR-0013 (open sign-up), fix 58e41c6 (password rules) | M | H | High | TC-0153, TC-0154, TC-0155, TC-0171, TC-0325 |
| R-037 | US-00-011 | A wrong role performs another role's action | AC-US-00-011-3, T-08, Q-013 | M | H | High | TC-0160, TC-0162, TC-0163, TC-0164, TC-0165 |
| R-038 | US-00-011 | A stolen session cookie is replayed, or a session outlives its purpose | AC-US-00-011-1, T-02, ADR-0012 | M | H | High | TC-0152, TC-0159, TC-0316, TC-0317, TC-0319 |
| R-039 | US-00-011 | Seeded accounts keep a default or shared password, or a password is stored in clear | AC-US-00-011-1, T-07 | M | H | High | TC-0149, TC-0150, TC-0151, TC-0323 |
| R-040 | US-00-011 | An unauthenticated caller reaches a gated route | AC-US-00-011-1, AC-US-00-011-2, AC-US-00-011-3 | L | H | Medium | TC-0166, TC-0172 |
| R-041 | US-00-011 | A person sees the links of the wrong role | AC-US-00-011-2 | L | L | Low | TC-0167, TC-0168, TC-0170 |
| R-042 | US-00-011 | Browser sign-in works only against the mock and fails on the real stack | AC-US-00-011-1, the browser journeys run on a mocked API (audit NOTASK-17) | M | M | Medium | TC-0169, TC-0173 |
| R-043 | US-00-006 | A flagged application is missing from the queue, or a settled one is listed | AC-US-00-006-1, Q-006 changed what leaves the queue | M | M | Medium | TC-0174, TC-0175 |
| R-044 | US-00-006 | The verifier sees a document value beside the wrong application value, or only one side | AC-US-00-006-2 | L | H | Medium | TC-0183, TC-0184 |
| R-045 | US-00-006 | A failed field is not marked, so the verifier misses the mismatch | AC-US-00-006-3 | L | H | Medium | TC-0191, TC-0192 |
| R-046 | US-00-006 | A role that should not see the queue can list it, a drift found by the audit | AC-US-00-006-1, Q-013 (only verifiers see the queue), audit NOTASK-17 | M | M | Medium | TC-0360, TC-0182 |
| R-047 | US-00-006 | A child's document image is served to an unauthenticated caller, kept after erasure or sent with unsafe headers | AC-US-00-006-2, T-09, ADR-0009 | M | H | High | TC-0188, TC-0189, TC-0190, TC-0336 |
| R-048 | US-00-007 | A decision is applied to a stale view of the application, so a wrong approval is saved | AC-US-00-007-1, REQ-023, If-Match rule | M | H | High | TC-0196, TC-0198, TC-0199, TC-0207 |
| R-049 | US-00-007 | A correction changes another application's value or leaves the comparison stale | AC-US-00-007-2, fix 0fc0394 (correction picker) | L | H | Medium | TC-0209, TC-0211 |
| R-050 | US-00-007 | A rejection is saved with no reason, or a rejected application returns to the queue | AC-US-00-007-3, AC-US-00-007-4, Q-006 option c | M | M | Medium | TC-0215, TC-0216, TC-0219 |
| R-051 | US-00-007 | A logged decision is edited or deleted, so the audit trail is lost | AC-US-00-007-5, T-19, REQ-027 | L | H | Medium | TC-0225, TC-0226 |
| R-052 | US-00-007 | Staff, an anonymous caller or a cross-site page decides an application | AC-US-00-007-1, ADR-0012, Q-013 | M | H | High | TC-0143, TC-0203, TC-0204, TC-0208 |
| R-053 | US-00-007 | A log entry lacks who, when, what or why | AC-US-00-007-5, T-20 | M | M | Medium | TC-0195, TC-0222 |
| R-054 | US-00-010 | The crop shows the wrong region or runs off the page, so the verifier reads the wrong value | AC-US-00-010-1 | L | M | Low | TC-0229, TC-0231, TC-0232, TC-0233 |
| R-055 | US-00-010 | A field with no position shows nothing, so the verifier cannot judge it | AC-US-00-010-2 | L | M | Low | TC-0234, TC-0235, TC-0236 |
| R-056 | US-00-008 | Counts differ from the stored records, so staff see the wrong workload | AC-US-00-008-1, Q-006 (rejected counted inside Needs review) | M | M | Medium | TC-0238, TC-0242, TC-0246, TC-0247 |
| R-057 | US-00-008 | The dashboard answer carries applicant data | AC-US-00-008-1, minors' data | L | H | Medium | TC-0240, TC-0241 |
| R-058 | US-00-008 | Counts do not move after a decision | AC-US-00-008-2, browser journeys run on a mocked API | L | M | Low | TC-0246, TC-0248 |
| R-059 | US-00-009 | A non-Verified or rejected application is exported as verified | AC-US-00-009-1, Q-006 (rejected stays needs_review) | M | H | High | TC-0250, TC-0251, TC-0261 |
| R-060 | US-00-009 | A name that starts with = runs as a spreadsheet formula, a CSV injection | AC-US-00-009-1, T-15 | L | H | Medium | TC-0256, TC-0257 |
| R-061 | US-00-009 | An empty export crashes or looks like a failure | AC-US-00-009-2 | L | M | Low | TC-0262, TC-0263, TC-0265 |
| R-062 | US-00-009 | The export is taken by the wrong role or without an audit row | AC-US-00-009-1, AC-US-00-011-3, T-23 | M | H | High | TC-0165, TC-0259, TC-0260, TC-0264 |
| R-063 | US-02-003 | A real person's data enters the seed or the eval sets | AC-US-02-003-4, REQ-043, minors' data | L | H | Medium | TC-0287, TC-0288, TC-0289, TC-0290, TC-0291 |
| R-064 | US-02-003 | Loading pollutes a real database, duplicates records or sends credentials to a remote host | AC-US-02-003-1, fix dfc8d96 (seed rendering) | L | H | Medium | TC-0271, TC-0272, TC-0273 |
| R-065 | US-02-003 | Labels or planted mismatches are wrong, so the evals judge against a wrong truth | AC-US-02-003-3, AC-US-02-003-5 | M | M | Medium | TC-0284, TC-0285, TC-0292 |
| R-066 | US-02-003 | The noise effects are absent, so accuracy is overstated | AC-US-02-003-2, extraction-accuracy.md caveat on clean pages | L | M | Low | TC-0277, TC-0278, TC-0279 |
| R-067 | US-02-003 | The seed is not repeatable | AC-US-02-003-1 | L | L | Low | TC-0276, TC-0281 |
| R-068 | US-02-002 | The engine is chosen on thin or unrecorded evidence: two candidates measured, hardware of the first benchmark unknown, calibration unproven | AC-US-02-002-3, AC-US-02-002-4 (Partial), AC-US-02-002-6, ADR-0017 | M | M | Medium | TC-0299, TC-0300, TC-0302 |
| R-069 | US-02-002 | A paid or non-free model or engine is configured | AC-US-02-002-2, REQ-036 | L | H | Medium | TC-0295, TC-0297, TC-0298 |
| R-070 | US-02-002 | Eligibility or the decision is not recorded | AC-US-02-002-1, AC-US-02-002-5 | L | M | Low | TC-0294, TC-0301 |
| R-071 | US-02-004 | The report overstates accuracy or hides read errors | AC-US-02-004-1, extraction-accuracy.md caveat (clean synthetic pages, one wrong field) | M | M | Medium | TC-0304, TC-0305, TC-0306 |
| R-072 | US-02-004 | The regression gate passes without a baseline or on read errors | AC-US-02-004-3, gate.yaml accepted_baseline none | M | M | Medium | TC-0312, TC-0313, TC-0314 |
| R-073 | US-02-004 | The comparison covers different documents per engine | AC-US-02-004-2 | L | M | Low | TC-0308, TC-0309, TC-0310 |
| R-074 | US-02-004 | The eval needs a paid service or a card | AC-US-02-004-3, REQ-039 | L | M | Low | TC-0311, TC-0315 |
| R-075 | US-00-011 | A signed-in person's browser is made by another site to import, upload or decide | AC-US-00-011-1, T-03, ADR-0012 (session-bound CSRF token and Origin check) | M | H | High | TC-0034, TC-0059, TC-0157, TC-0158, TC-0203, TC-0320 |
| R-076 | US-00-011 | The sign-in response or its timing reveals which usernames exist | AC-US-00-011-1, T-05 | M | L | Low | TC-0153, TC-0326, TC-0327 |
| R-077 | US-00-011 | Many sign-in attempts exhaust CPU through the password hash | AC-US-00-011-1, T-06 | M | M | Medium | TC-0156, TC-0325 |
| R-078 | US-00-011 | An anonymous caller registers as a verifier and approves applications, an accepted risk | AC-US-00-011-2, T-38, ADR-0013 (accepted by the engineer on 2026-10-07) | H | H | High | TC-0321, TC-0322, TC-0323, TC-0324 |
| R-079 | US-00-011 | Database traffic is unencrypted and the API database role has more rights than it needs | AC-US-00-011-1, T-30 (mitigation planned, no test exists) | L | H | Medium | TC-0334, TC-0335 |
| R-080 | US-00-011 | The API documentation and schema are exposed in production | AC-US-00-011-1, T-32 (mitigated in app/main.py:132) | L | L | Low | TC-0331 |
| R-081 | US-00-011 | An error or readiness response leaks a stack trace or internal detail | AC-US-00-011-1, T-33 (mitigated in app/main.py) | L | M | Low | TC-0328, TC-0329, TC-0330 |
| R-082 | US-00-011 | The API container runs as root or publishes a port it should not | AC-US-00-011-1, T-34 (Dockerfile:18 to 22 sets uid 10001) | L | H | Medium | TC-0332, TC-0333 |
| R-083 | US-00-002 | A decompression bomb or a huge page exhausts the 512 MB budget | AC-US-00-002-2, T-11, ADR-0009 | H | H | High | TC-0064, TC-0065, TC-0069, TC-0340, TC-0341, TC-0343 |
| R-084 | US-00-002 | A client file name that contains a name is written to logs or URLs | AC-US-00-002-1, T-13, minors' data | M | M | Medium | TC-0337, TC-0338, TC-0339 |
| R-085 | US-00-002 | Path traversal through the client file name | AC-US-00-002-1, T-14 | L | M | Low | TC-0337, TC-0346 |
| R-086 | US-00-007 | A decision's reason, old value or new value carries personal data into logs | AC-US-00-007-2, T-22 | L | M | Low | TC-0347, TC-0348 |
| R-087 | US-02-001 | Model files downloaded on first use are replaced in transit or at the source | AC-US-02-001-6, T-26 (no test exists for the checksum) | L | H | Medium | TC-0097, TC-0356 |
| R-088 | US-02-001 | One request pushes the engine past available memory, or a read never ends | AC-US-02-001-4, T-27, 509 MB measured (docs/performance/NOTASK-17-memory.md) | H | M | High | TC-0340, TC-0352, TC-0353, TC-0354, TC-0355 |
| R-089 | US-02-001 | Recognised text or field values are written to the gateway log | AC-US-02-001-3, T-28, minors' data | M | H | High | TC-0349, TC-0350, TC-0351 |
| R-090 | US-02-001 | A vulnerable or malicious dependency enters through the lockfile | AC-US-02-001-6, T-35 | M | H | High | TC-0357, TC-0358, TC-0359 |
