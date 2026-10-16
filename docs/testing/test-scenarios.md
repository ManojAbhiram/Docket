# Test scenarios

Source: `docs/product/backlog.md` as of 2026-10-05 (US-00-004) and 2026-10-16 (the other 14 stories). One block per story, in backlog order. Written by
`test-cases`; change the backlog, not this file, to change a scenario.
Each row names the cases in `test-cases.md` that cover it. Scope of this run: all 15 stories.

## US-00-001: Import applications from a CSV file

Requirements: REQ-001, REQ-002, REQ-003
Acceptance criteria: AC-US-00-001-1, AC-US-00-001-2, AC-US-00-001-3

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-001-1 | Happy | A CSV with the eight columns and valid rows is imported and shown in the browser | a valid file becomes applications holding exactly the values of the file | AC-US-00-001-1, AC-US-00-001-2, AC-US-00-001-3 | TC-0027, TC-0028, TC-0051 |
| TS-US-00-001-2 | Alternate | The valid rows are created and the malformed ones listed, and a BOM file reads the same | one bad row never costs the good rows | AC-US-00-001-1, AC-US-00-001-3 | TC-0029, TC-0047, TC-0048 |
| TS-US-00-001-3 | Error | Missing values, unreadable or out-of-range dates, bad marks, long names, short rows, repeated ids and a wrong or non-CSV file are refused with reasons | a bad row or file is refused with a reason and creates nothing | AC-US-00-001-1, AC-US-00-001-2, AC-US-00-001-3 | TC-0030, TC-0033, TC-0036, TC-0037, TC-0038, TC-0039, TC-0040, TC-0042, TC-0043, TC-0044, TC-0049, TC-0050 |
| TS-US-00-001-4 | Edge | The size cap, the row cap, the edge days of the date range, the empty file button and a double click | limits are decided the same way every time | AC-US-00-001-1, AC-US-00-001-2, AC-US-00-001-3 | TC-0031, TC-0032, TC-0041, TC-0052, TC-0053 |
| TS-US-00-001-5 | Security | A request with no token or from another Origin, and a refused row, are tried | nobody but staff creates applications and no child's value leaks | AC-US-00-001-1, AC-US-00-001-2 | TC-0034, TC-0035, TC-0045, TC-0046 |

Not applicable: Performance: the PRD gives no speed target for import and the size and row caps bound the work (imp5, imp6); Accessibility: no criterion of this story names it
Invariants: a refused row never carries the value that failed (imp19, imp20); a bad row never stops a good row (imp22)

## US-00-002: Upload scanned documents for an application

Requirements: REQ-004, REQ-005, REQ-006
Acceptance criteria: AC-US-00-002-1, AC-US-00-002-2, AC-US-00-002-3, AC-US-00-002-4

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-002-1 | Happy | Each is stored against its application and a page is uploaded in the browser | a scan of an accepted type is stored against the right application | AC-US-00-002-1, AC-US-00-002-3 | TC-0054, TC-0055, TC-0056, TC-0061, TC-0068 |
| TS-US-00-002-2 | Alternate | The same bytes again, the same bytes for another application, a different file and a newer file of the same type | a re-upload never loses an earlier document | AC-US-00-002-1, AC-US-00-002-4 | TC-0057, TC-0058, TC-0072, TC-0073, TC-0074, TC-0075 |
| TS-US-00-002-3 | Error | A GIF, a text file disguised as an image, broken JPEG or PDF bytes and a bad application id or empty form are tried | a file that is not an accepted scan is refused and nothing is stored | AC-US-00-002-1, AC-US-00-002-2, AC-US-00-002-3 | TC-0060, TC-0062, TC-0063, TC-0066, TC-0067, TC-0070 |
| TS-US-00-002-4 | Edge | A file one byte over the size cap, a pixel-count bomb in a PNG and in a PDF first page | limits are decided the same way every time | AC-US-00-002-2, AC-US-00-002-3 | TC-0064, TC-0065, TC-0069 |
| TS-US-00-002-5 | Security | No token, and a PDF rasterised with the network blocked | nobody but staff uploads and no page leaves this machine | AC-US-00-002-1, AC-US-00-002-3 | TC-0059, TC-0071 |
| TS-US-00-002-6 | Performance | Uploads wait for capacity before the body is read, time out when busy, and bodies past the cap are cut off | an upload cannot exhaust the memory budget | AC-US-00-002-2 | TC-0340, TC-0341, TC-0342, TC-0343 |
| TS-US-00-002-7 | Security | A client file name never reaches a header or a log, a file name with path parts is replaced, EXIF is dropped and the type is sniffed | nothing the client typed becomes a stored name or a log value | AC-US-00-002-1, AC-US-00-002-2 | TC-0337, TC-0338, TC-0339, TC-0344, TC-0345, TC-0346 |

Not applicable: Accessibility: no criterion of this story names it
Invariants: an earlier document is never deleted by a newer one (up19, up20)

## US-02-001: Route all OCR and vision calls through one gateway

Requirements: REQ-030, REQ-031, REQ-032, REQ-033, REQ-034, REQ-044
Acceptance criteria: AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-3, AC-US-02-001-4, AC-US-02-001-5, AC-US-02-001-6

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-001-1 | Happy | A call returns the engine result and logs one row with cost 0 | every call is made and logged through one gateway | AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-3, AC-US-02-001-5 | TC-0076, TC-0078, TC-0080, TC-0081, TC-0083, TC-0091 |
| TS-US-02-001-2 | Alternate | The engine is chosen by name, a recorded engine replays, a Vision failure is logged with its class | callers do not change when the engine does | AC-US-02-001-2, AC-US-02-001-3 | TC-0079, TC-0084 |
| TS-US-02-001-3 | Error | An engine failure is logged as an error and raised without the engine text | a failing engine never leaks its message and never loses its row | AC-US-02-001-3, AC-US-02-001-5 | TC-0082, TC-0093 |
| TS-US-02-001-4 | Edge | A call past the cap, a refused call, the last slot taken at once, a restart, a refused document | the cap is exact, survives a restart and holds the application in review | AC-US-02-001-1, AC-US-02-001-4 | TC-0077, TC-0085, TC-0086, TC-0087, TC-0088, TC-0089, TC-0090 |
| TS-US-02-001-5 | Security | Free mode never reaches Vision, uploads default to Free, the local engine and the recorded engine open no connection, Vision is capped | no page image leaves this machine unless Vision is chosen | AC-US-02-001-5, AC-US-02-001-6 | TC-0092, TC-0094, TC-0095, TC-0096, TC-0097, TC-0098, TC-0099, TC-0100 |
| TS-US-02-001-6 | Performance | A local read waits for capacity, cancelled native work keeps its slot and stuck documents are failed | the engine cannot be pushed past its memory budget | AC-US-02-001-3 | TC-0352, TC-0353, TC-0354, TC-0355 |
| TS-US-02-001-7 | Security | Personal fields are redacted at every depth, a read writes no values and the dependency audit runs in CI | no child's value is logged and no known-vulnerable package is shipped | AC-US-02-001-3, AC-US-02-001-6 | TC-0349, TC-0350, TC-0351, TC-0356, TC-0357, TC-0358, TC-0359 |

Not applicable: Accessibility: the story has no screen
Invariants: engine calls never exceed the cap (gw12); every call has a cost of 0 (gw6)

## US-00-003: Read the type and fields of an uploaded document

Requirements: REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-044
Acceptance criteria: AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-5, AC-US-00-003-6

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-003-1 | Happy | One gateway call types the page and splits it into fields with confidences | a good scan is typed and split into fields with one local call | AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-6 | TC-0101, TC-0105, TC-0111, TC-0112, TC-0116, TC-0123 |
| TS-US-00-003-2 | Alternate | A Vision document is read by Vision alone, falls back to the local reader, stores null confidences and always goes to review | the opt-in Vision path is explicit and always reviewed by a person | AC-US-00-003-1, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-6 | TC-0102, TC-0103, TC-0113, TC-0114, TC-0124, TC-0127 |
| TS-US-00-003-3 | Error | An unknown title, a field below the cutoff, an unreadable date, a missing field, a failed read and a failed fallback | anything the engine is not sure of goes to a person | AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-4, AC-US-00-003-5 | TC-0104, TC-0107, TC-0109, TC-0110, TC-0115, TC-0117, TC-0118, TC-0120, TC-0121 |
| TS-US-00-003-4 | Edge | Class XII against class X, a page with no text, a field exactly at the cutoff, a blank image and a noisy photo | boundary values are decided the same way every time | AC-US-00-003-2, AC-US-00-003-5 | TC-0106, TC-0108, TC-0119, TC-0122 |
| TS-US-00-003-5 | Security | Reads with the network blocked, a repeat upload in another mode and the Vision warning | no page leaves the machine unless the person chose Vision | AC-US-00-003-6 | TC-0125, TC-0126 |

Not applicable: Performance: the PRD gives no per-document time in this story; memory and time are measured in docs/performance/NOTASK-17-memory.md; Accessibility: the upload page has component checks only
Invariants: no field is silently dropped (rd19, rd20); a Vision field is never stored with an invented confidence (rd13)

## US-00-004: Compare extracted fields with the application

Requirements: REQ-012, REQ-013, REQ-014, REQ-015, REQ-016
Acceptance criteria: AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4, AC-US-00-004-5

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-004-1 | Happy | An identical name, date, roll number and set of marks all match | a correct document is recognised as correct on every rule | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0001, TC-0011, TC-0015 |
| TS-US-00-004-2 | Alternate | The same name in the other order, the same date in another print format, and an ID proof without marks all still match | harmless differences in print do not create work for a verifier | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-5 | TC-0002, TC-0007, TC-0019, TC-0021 |
| TS-US-00-004-3 | Error | A different given name, a date one day off, a roll number off by one digit and a mark off by one each mismatch | a wrong document is never accepted as right | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0003, TC-0008, TC-0012, TC-0016, TC-0006 |
| TS-US-00-004-4 | Edge | Empty name, single-word name, leap day, impossible date, letter O for zero, trailing space, marks 0 and 100, missing subject | boundary values are decided the same way every time | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0004, TC-0005, TC-0009, TC-0010, TC-0013, TC-0014, TC-0017, TC-0018 |
| TS-US-00-004-5 | Error | A document from which nothing could be compared is not a match | an application cannot be verified on no evidence | AC-US-00-004-5 | TC-0020, TC-0022 |
| TS-US-00-004-6 | Security | Comparing a document writes no name, date of birth or roll number to the logs | a child's personal data does not leak through logs | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3 | TC-0023, TC-0024 |
| TS-US-00-004-7 | Edge | Malformed or hostile values never crash the comparison, and the same input always gives the same result | one bad document cannot block the queue | AC-US-00-004-2 | TC-0025, TC-0026 |

Not applicable: Performance: the PRD gives no speed target for matching (the comparison is local string work); Accessibility: the story has no screen.
Invariants: a comparison never raises on malformed input (TC-0025); the same input gives the same result twice (TC-0026).

## US-00-005: Set each application's status automatically

Requirements: REQ-017, REQ-018, REQ-019, REQ-020
Acceptance criteria: AC-US-00-005-1, AC-US-00-005-2, AC-US-00-005-3, AC-US-00-005-4, AC-US-00-005-5

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-005-1 | Happy | Three required documents match and the application becomes Verified with the evidence stored | a fully matching application is verified without a person | AC-US-00-005-1 | TC-0128, TC-0129, TC-0130 |
| TS-US-00-005-2 | Alternate | Two of three documents give Missing documents and the queue lists the flagged ones | each application lands in exactly one of the three statuses | AC-US-00-005-2, AC-US-00-005-3 | TC-0135, TC-0136, TC-0139 |
| TS-US-00-005-3 | Error | A different name, a roll number off by one, a weak field, missing marks and a mismatch with a missing document | a doubtful application always reaches a person | AC-US-00-005-2, AC-US-00-005-3 | TC-0132, TC-0133, TC-0134, TC-0138 |
| TS-US-00-005-4 | Edge | No documents, a document still being read, a field not yet compared | unfinished work never counts as a match | AC-US-00-005-1, AC-US-00-005-3, AC-US-00-005-4 | TC-0131, TC-0137, TC-0144 |
| TS-US-00-005-5 | Security | A direct request, an approval over a missing document, a staff member, an anonymous caller and a stale upload | Verified only comes from a match or a verifier decision | AC-US-00-005-4, AC-US-00-005-5 | TC-0140, TC-0141, TC-0142, TC-0143, TC-0145, TC-0147 |
| TS-US-00-005-6 | Edge | Every combination of document states and the database enum | no fourth status can exist | AC-US-00-005-5 | TC-0146, TC-0148 |

Not applicable: Performance: no criterion names it; Accessibility: the story has no screen
Invariants: the status is always one of verified, needs_review, missing_documents (st19); an uncompared field is never a match (st17)

## US-00-011: Sign in as staff or verifier

Requirements: REQ-021, REQ-027
Acceptance criteria: AC-US-00-011-1, AC-US-00-011-2, AC-US-00-011-3

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-011-1 | Happy | Each role signs in and sees its own start page and links | each role reaches its own work | AC-US-00-011-1, AC-US-00-011-2, AC-US-00-011-3 | TC-0149, TC-0150, TC-0152, TC-0161, TC-0167, TC-0168, TC-0169, TC-0170 |
| TS-US-00-011-2 | Alternate | Re-running the seed and a sign-in through the real API | the demo accounts are stable and sign-in works end to end | AC-US-00-011-1, AC-US-00-011-2 | TC-0151, TC-0173 |
| TS-US-00-011-3 | Error | An unknown user, a wrong password, a deactivated user, a bad body and a signed-out visitor | a failed sign-in gives nothing away and opens nothing | AC-US-00-011-1 | TC-0153, TC-0155, TC-0156, TC-0171, TC-0172 |
| TS-US-00-011-4 | Edge | The fifth wrong password and a session idle for thirty minutes | lockout and expiry are decided the same way every time | AC-US-00-011-1 | TC-0154, TC-0159 |
| TS-US-00-011-5 | Security | Staff and verifier crossing roles, anonymous callers on gated routes, logout without a token or from another Origin | no role acts outside its own work | AC-US-00-011-1, AC-US-00-011-2, AC-US-00-011-3 | TC-0157, TC-0158, TC-0160, TC-0162, TC-0163, TC-0164, TC-0165, TC-0166 |
| TS-US-00-011-6 | Security | Logout, server-side session end, token hashing, deactivation and a state-changing route without a token | a stolen or forged session cannot be used to act | AC-US-00-011-1 | TC-0316, TC-0317, TC-0318, TC-0319, TC-0320 |
| TS-US-00-011-7 | Security | Registration with the verifier role, a taken name, the stored hash and the per-source limit | the accepted risk of open sign-up is stated and limited | AC-US-00-011-1, AC-US-00-011-2 | TC-0321, TC-0322, TC-0323, TC-0324 |
| TS-US-00-011-8 | Security | Locking by source, locking an unknown name like a known one and a response with no hash | sign-in gives an attacker nothing to learn from | AC-US-00-011-1 | TC-0325, TC-0326, TC-0327 |
| TS-US-00-011-9 | Security | Errors without detail, docs off in production, non-root image, one published port, TLS and a least-privilege role | the deployment shows no internals | AC-US-00-011-1 | TC-0328, TC-0329, TC-0330, TC-0331, TC-0332, TC-0333, TC-0334, TC-0335 |

Not applicable: Performance: no criterion names it; Accessibility: the sign-in page has component checks only
Invariants: a session cookie is never readable by script (si4); a password is never stored in clear (si2)

## US-00-006: Review a flagged application side by side

Requirements: REQ-021, REQ-022
Acceptance criteria: AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-006-1 | Happy | The queue lists the flagged applications and the detail pairs each value with the application value | a verifier can see exactly what to check | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3 | TC-0174, TC-0176, TC-0177, TC-0183, TC-0184, TC-0185, TC-0191, TC-0192 |
| TS-US-00-006-2 | Alternate | Rejected applications move to their own list, the queue pages without repeats and failed fields come first | the queue stays short and complete | AC-US-00-006-1, AC-US-00-006-3 | TC-0175, TC-0180, TC-0193 |
| TS-US-00-006-3 | Error | An empty queue, an application with no documents, an unknown id and a not-flagged row | a missing record is explained, never a blank or a crash | AC-US-00-006-1, AC-US-00-006-2 | TC-0178, TC-0179, TC-0186, TC-0187 |
| TS-US-00-006-4 | Edge | A flagged field read without colour on a phone | a mismatch is not signalled by colour alone | AC-US-00-006-3 | TC-0194 |
| TS-US-00-006-5 | Security | An anonymous caller, a staff account on the queue, the image headers and an erased application | only signed-in people with the right role see a child's records | AC-US-00-006-1, AC-US-00-006-2 | TC-0181, TC-0182, TC-0188, TC-0189, TC-0190 |
| TS-US-00-006-6 | Security | Staff read a stored image and an unknown id is 404 | images are served to signed-in roles only | AC-US-00-006-2 | TC-0336 |

Not applicable: Performance: no criterion names a list speed, paging is tested in rv7
Invariants: every shown field pairs a document value with an application value (rv10); a flagged field always has a reason in words (rv19)

## US-00-007: Decide a flagged application

Requirements: REQ-023, REQ-024, REQ-025, REQ-026, REQ-027
Acceptance criteria: AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-3, AC-US-00-007-4, AC-US-00-007-5

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-007-1 | Happy | A verifier approves a flagged application and corrects a wrong value, and the log records both | a decision is applied once and logged with who, when and why | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-5 | TC-0195, TC-0206, TC-0209, TC-0213, TC-0222 |
| TS-US-00-007-2 | Alternate | A rejection with a reason keeps the status Needs review, sets the rejected flag and leaves the queue | a rejected application is out of the queue and still unverified | AC-US-00-007-3, AC-US-00-007-4, AC-US-00-007-5 | TC-0219, TC-0221, TC-0223 |
| TS-US-00-007-3 | Error | No reason, no value, a bad or missing If-Match, a stale version, a decided application, an unknown id and a wrong field | a bad decision is refused and writes nothing | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-3, AC-US-00-007-4, AC-US-00-007-5 | TC-0196, TC-0197, TC-0202, TC-0205, TC-0210, TC-0211, TC-0212, TC-0214, TC-0215, TC-0216, TC-0217, TC-0218, TC-0220, TC-0224 |
| TS-US-00-007-4 | Edge | Two decisions at once, a decision that waited for the row and an approval followed by new evidence | only one decision wins and an old approval does not outlive new evidence | AC-US-00-007-1 | TC-0198, TC-0199, TC-0200, TC-0201, TC-0207 |
| TS-US-00-007-5 | Security | No token, another Origin, a staff member, no route to edit, and database guards | only a verifier decides and no entry is ever changed | AC-US-00-007-1, AC-US-00-007-5 | TC-0203, TC-0204, TC-0208, TC-0225, TC-0226, TC-0227, TC-0228 |
| TS-US-00-007-6 | Security | A correction and a rejection are made with known values and the log is read | no child's value is written to an application log | AC-US-00-007-2, AC-US-00-007-3 | TC-0347, TC-0348 |

Not applicable: Performance: no criterion names it
Invariants: one decision per version of an application (dc5); a logged decision is never changed (dc32, dc33)

## US-00-010: See field crops beside the values

Requirements: REQ-046
Acceptance criteria: AC-US-00-010-1, AC-US-00-010-2

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-010-1 | Happy | The crop is drawn from the loaded page, centred on the field, beside its value | the verifier sees the field in the scan | AC-US-00-010-1, AC-US-00-010-2 | TC-0229, TC-0230, TC-0231, TC-0237 |
| TS-US-00-010-2 | Error | A field without a box and an image that fails to load | the verifier is told when no crop can be shown and sees the full page | AC-US-00-010-2 | TC-0234, TC-0235, TC-0236 |
| TS-US-00-010-3 | Edge | A field at a page edge and a field wider than the page | a crop never leaves the page | AC-US-00-010-1 | TC-0232, TC-0233 |

Not applicable: Security: the story adds no input or route; Performance: no criterion names it
Invariants: a crop is always inside the page (cr4, cr5)

## US-00-008: See counts of applications by status

Requirements: REQ-028
Acceptance criteria: AC-US-00-008-1, AC-US-00-008-2

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-008-1 | Happy | Each status shows a count equal to the stored records | the overview matches the database | AC-US-00-008-1 | TC-0238, TC-0242, TC-0245 |
| TS-US-00-008-2 | Alternate | An approval and a rejection change the counts as built | the overview follows the work | AC-US-00-008-2 | TC-0246, TC-0247, TC-0248, TC-0249 |
| TS-US-00-008-3 | Error | The page explains a failure and reloads | staff are told when counts cannot be read | AC-US-00-008-1 | TC-0244 |
| TS-US-00-008-4 | Edge | All counts are zero | an empty system shows zeros, not an error | AC-US-00-008-1 | TC-0239, TC-0243 |
| TS-US-00-008-5 | Security | The answer holds numbers only and an anonymous caller gets 401 | the dashboard exposes no child's data | AC-US-00-008-1 | TC-0240, TC-0241 |

Not applicable: Performance: no criterion names it
Invariants: the counts equal the stored records at the moment they are read (db1)

## US-00-009: Export the verified list to CSV

Requirements: REQ-029
Acceptance criteria: AC-US-00-009-1, AC-US-00-009-2

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-009-1 | Happy | One row per Verified application with the documented columns and the decision | the file lists exactly the verified applications | AC-US-00-009-1 | TC-0250, TC-0252, TC-0253, TC-0254, TC-0258, TC-0259, TC-0266, TC-0267 |
| TS-US-00-009-2 | Alternate | Names with commas and quotes stay one cell | the file opens correctly in a spreadsheet | AC-US-00-009-1 | TC-0255, TC-0268 |
| TS-US-00-009-3 | Error | An anonymous caller, and no Verified application | no export without a session and an empty list is a header only | AC-US-00-009-1, AC-US-00-009-2 | TC-0260, TC-0262, TC-0263, TC-0264, TC-0265 |
| TS-US-00-009-4 | Edge | A rejected and an erased application are not exported | only Verified applications are in the file | AC-US-00-009-1 | TC-0251, TC-0261 |
| TS-US-00-009-5 | Security | A formula-like name and the audit row | a spreadsheet never runs a name as a formula and every export is recorded | AC-US-00-009-1 | TC-0256, TC-0257, TC-0259 |

Not applicable: Performance: no criterion names it
Invariants: the file holds a row for a Verified application and for no other (ex1, ex2)

## US-02-003: Seed synthetic applications and documents

Requirements: REQ-040, REQ-041, REQ-042, REQ-043
Acceptance criteria: AC-US-02-003-1, AC-US-02-003-2, AC-US-02-003-3, AC-US-02-003-4, AC-US-02-003-5

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-003-1 | Happy | 20 applications and 30 documents are built and loaded through the API | the system can be filled with a known synthetic set | AC-US-02-003-1, AC-US-02-003-2, AC-US-02-003-5 | TC-0269, TC-0270, TC-0275, TC-0282, TC-0292, TC-0293 |
| TS-US-02-003-2 | Alternate | A second load adds nothing and the same seed gives the same set | the seed is repeatable | AC-US-02-003-1, AC-US-02-003-2 | TC-0271, TC-0276, TC-0280, TC-0281 |
| TS-US-02-003-3 | Error | An invalid or remote destination and incompatible stored values | the loader stops before it does harm | AC-US-02-003-1 | TC-0272, TC-0273, TC-0274 |
| TS-US-02-003-4 | Edge | Blur, shadow, skew, eight mismatches and the fields that may differ | noise and mismatches are exact and repeatable | AC-US-02-003-2, AC-US-02-003-3 | TC-0277, TC-0278, TC-0279, TC-0283, TC-0284, TC-0285, TC-0286 |
| TS-US-02-003-5 | Security | Pools, SYN prefixes, the synthetic mark on every page and a generator that cannot read outside data | no real person is in any seeded record | AC-US-02-003-4 | TC-0287, TC-0288, TC-0289, TC-0290, TC-0291 |

Not applicable: Performance: no criterion names it; Accessibility: the story has no screen
Invariants: every seeded identifier carries a synthetic prefix (sd21, sd22)

## US-02-002: Choose the engine by measurement

Requirements: REQ-035, REQ-036
Acceptance criteria: AC-US-02-002-1, AC-US-02-002-2, AC-US-02-002-3, AC-US-02-002-4, AC-US-02-002-5, AC-US-02-002-6

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-002-1 | Happy | The record names RapidOCR, its numbers and Tesseract as runner-up | the choice can be audited | AC-US-02-002-1, AC-US-02-002-3, AC-US-02-002-5 | TC-0294, TC-0299, TC-0301 |
| TS-US-02-002-2 | Alternate | A free identifier is accepted | the free path stays open | AC-US-02-002-2 | TC-0296 |
| TS-US-02-002-3 | Error | A paid model and a disqualified engine | nothing that costs money is accepted | AC-US-02-002-2 | TC-0295, TC-0298 |
| TS-US-02-002-4 | Edge | The 40 call cap, hardware never recorded and calibration unproven | the limits of the evidence are stated | AC-US-02-002-2, AC-US-02-002-4, AC-US-02-002-6 | TC-0297, TC-0300, TC-0302 |

Not applicable: Security: no input or route; Performance: latency is covered by en7; Accessibility: the story has no screen
Invariants: the daily Vision cap never exceeds 40 (en4)

## US-02-004: Report extraction accuracy

Requirements: REQ-037, REQ-038, REQ-039
Acceptance criteria: AC-US-02-004-1, AC-US-02-004-2, AC-US-02-004-3

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-004-1 | Happy | A correct read scores correct and the report carries the numbers | per field type accuracy is reported | AC-US-02-004-1 | TC-0303, TC-0307 |
| TS-US-02-004-2 | Alternate | The comparison set of ten documents and the side-by-side report | the chosen engine and the runner-up are compared on the same documents | AC-US-02-004-2 | TC-0308, TC-0309, TC-0310 |
| TS-US-02-004-3 | Error | A wrong value, a missing field, an engine that reads nothing and an unreadable image | mistakes are counted, never hidden | AC-US-02-004-1 | TC-0304, TC-0305, TC-0306 |
| TS-US-02-004-4 | Edge | No baseline, a score below the delta and read errors in a replay | the gate never passes by default | AC-US-02-004-3 | TC-0312, TC-0313, TC-0314 |
| TS-US-02-004-5 | Security | Replay with no engine call and a clean checkout with free tools | the eval needs no paid service | AC-US-02-004-3 | TC-0311, TC-0315 |

Not applicable: Performance: no criterion names it; Accessibility: the story has no screen
Invariants: no document is dropped from a report (rp3, rp4)

## Needs rewording

Criteria with no testable expected result. Each one counts as uncovered
until the backlog is fixed.

- none
