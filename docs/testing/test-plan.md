# Test plan: Docket, all 15 stories

Backlog: `docs/product/backlog.md` as read on 2026-10-16 (the US-00-004 cases were written against the 2026-10-05 backlog)   Cases: docs/testing/test-cases.md
Version: v2   Author: unattributed

## 1. Headline

Scenarios: 85

test-cases: 60 ACs, 60 with cases, 359 live cases, 359 with oracles, 90 risks (high 25, medium 44, low 21), 31 threats traced from 1 threat models, 0 problems
test-types: unit 170, integration 164, e2e 15, manual 10; by machine 349 (automated 311, planned 38), by hand 10

## 2. Risk summary

| Risk | Story | What could go wrong | Level | Cases |
| --- | --- | --- | --- | --- |
| R-001 | US-00-004 | Another person's document is accepted as a match for an application, so a wrong applicant is verified | High | TC-0003, TC-0004, TC-0006 |
| R-005 | US-00-004 | A document from which nothing could be compared counts as a match, so an application is verified on no evidence | High | TC-0019, TC-0020, TC-0022 |
| R-013 | US-00-002 | A hostile or wrong file is stored: a wrong format, a disguised type, an oversized file or a pixel bomb | High | TC-0062, TC-0063, TC-0064, TC-0065, TC-0066, TC-0345 |
| R-015 | US-00-002 | A multi-page PDF is stored whole, the wrong page is used, or the conversion leaves this machine | High | TC-0056, TC-0068, TC-0071 |
| R-019 | US-02-001 | Calls go past the cap, or the cap is lost on restart, so the free quota is exceeded | High | TC-0085, TC-0087, TC-0088, TC-0100 |
| R-020 | US-02-001 | A page image leaves this machine in the default mode | High | TC-0092, TC-0095, TC-0096, TC-0097 |
| R-024 | US-00-003 | A weak, missing or unreadable field is accepted as read, so a wrong value can be verified | High | TC-0115, TC-0117, TC-0119, TC-0120 |
| R-027 | US-00-003 | A page leaves the machine without the person choosing Vision, or Vision is used past its cap | High | TC-0123, TC-0124, TC-0125, TC-0126 |
| R-030 | US-00-005 | An application is marked Verified without every field matching or without a verifier | High | TC-0128, TC-0131, TC-0140, TC-0144 |
| R-033 | US-00-005 | A caller sets Verified directly or without authority | High | TC-0140, TC-0141, TC-0142, TC-0143 |
| R-036 | US-00-011 | An account is taken over by guessing or credential stuffing | High | TC-0153, TC-0154, TC-0155, TC-0171, TC-0325 |
| R-037 | US-00-011 | A wrong role performs another role's action | High | TC-0160, TC-0162, TC-0163, TC-0164, TC-0165 |
| R-038 | US-00-011 | A stolen session cookie is replayed, or a session outlives its purpose | High | TC-0152, TC-0159, TC-0316, TC-0317, TC-0319 |
| R-039 | US-00-011 | Seeded accounts keep a default or shared password, or a password is stored in clear | High | TC-0149, TC-0150, TC-0151, TC-0323 |
| R-047 | US-00-006 | A child's document image is served to an unauthenticated caller, kept after erasure or sent with unsafe headers | High | TC-0188, TC-0189, TC-0190, TC-0336 |
| R-048 | US-00-007 | A decision is applied to a stale view of the application, so a wrong approval is saved | High | TC-0196, TC-0198, TC-0199, TC-0207 |
| R-052 | US-00-007 | Staff, an anonymous caller or a cross-site page decides an application | High | TC-0143, TC-0203, TC-0204, TC-0208 |
| R-059 | US-00-009 | A non-Verified or rejected application is exported as verified | High | TC-0250, TC-0251, TC-0261 |
| R-062 | US-00-009 | The export is taken by the wrong role or without an audit row | High | TC-0165, TC-0259, TC-0260, TC-0264 |
| R-075 | US-00-011 | A signed-in person's browser is made by another site to import, upload or decide | High | TC-0034, TC-0059, TC-0157, TC-0158, TC-0203, TC-0320 |
| R-078 | US-00-011 | An anonymous caller registers as a verifier and approves applications, an accepted risk | High | TC-0321, TC-0322, TC-0323, TC-0324 |
| R-083 | US-00-002 | A decompression bomb or a huge page exhausts the 512 MB budget | High | TC-0064, TC-0065, TC-0069, TC-0340, TC-0341, TC-0343 |
| R-088 | US-02-001 | One request pushes the engine past available memory, or a read never ends | High | TC-0340, TC-0352, TC-0353, TC-0354, TC-0355 |
| R-089 | US-02-001 | Recognised text or field values are written to the gateway log | High | TC-0349, TC-0350, TC-0351 |
| R-090 | US-02-001 | A vulnerable or malicious dependency enters through the lockfile | High | TC-0357, TC-0358, TC-0359 |

Medium: 44 (R-002, R-003, R-004, R-006, R-007, R-008, R-009, R-010, R-011, R-012, R-014, R-016, R-018, R-025, R-026, R-028, R-031, R-032, R-034, R-040, R-042, R-043, R-044, R-045, R-046, R-049, R-050, R-051, R-053, R-056, R-057, R-060, R-063, R-064, R-065, R-068, R-069, R-071, R-072, R-077, R-079, R-082, R-084, R-087)   Low: 21 (R-017, R-021, R-022, R-023, R-029, R-035, R-041, R-054, R-055, R-058, R-061, R-066, R-067, R-070, R-073, R-074, R-076, R-080, R-081, R-085, R-086). Levels, sources and likelihood are in `docs/testing/risks.md`; none is re-rated here.

## 3. Scenarios

| Scenario | Story | Title | Proves that | Cases | Run by |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-001-1 | US-00-001 | Valid rows are imported | a valid file becomes applications holding exactly the values of the file | TC-0027, TC-0028, TC-0051 | machine |
| TS-US-00-001-2 | US-00-001 | A file mixes valid and malformed rows | one bad row never costs the good rows | TC-0029, TC-0047, TC-0048 | machine |
| TS-US-00-001-3 | US-00-001 | A row or file is refused | a bad row or file is refused with a reason and creates nothing | TC-0030, TC-0033, TC-0036, TC-0037, TC-0038, TC-0039, TC-0040, TC-0042, TC-0043, TC-0044, TC-0049, TC-0050 | machine |
| TS-US-00-001-4 | US-00-001 | Limits of the file | limits are decided the same way every time | TC-0031, TC-0032, TC-0041, TC-0052, TC-0053 | machine |
| TS-US-00-001-5 | US-00-001 | A forged request or a leaked value | nobody but staff creates applications and no child's value leaks | TC-0034, TC-0035, TC-0045, TC-0046 | machine |
| TS-US-00-002-1 | US-00-002 | A PNG, a JPEG and a PDF are uploaded | a scan of an accepted type is stored against the right application | TC-0054, TC-0055, TC-0056, TC-0061, TC-0068 | machine |
| TS-US-00-002-2 | US-00-002 | Re-uploads | a re-upload never loses an earlier document | TC-0057, TC-0058, TC-0072, TC-0073, TC-0074, TC-0075 | machine |
| TS-US-00-002-3 | US-00-002 | A file is refused | a file that is not an accepted scan is refused and nothing is stored | TC-0060, TC-0062, TC-0063, TC-0066, TC-0067, TC-0070 | machine |
| TS-US-00-002-4 | US-00-002 | Limits | limits are decided the same way every time | TC-0064, TC-0065, TC-0069 | machine |
| TS-US-00-002-5 | US-00-002 | Forged request and local conversion | nobody but staff uploads and no page leaves this machine | TC-0059, TC-0071 | machine |
| TS-US-00-002-6 | US-00-002 | Memory admission and size limits | an upload cannot exhaust the memory budget | TC-0340, TC-0341, TC-0342, TC-0343 | machine |
| TS-US-00-002-7 | US-00-002 | Names, logs and metadata | nothing the client typed becomes a stored name or a log value | TC-0337, TC-0338, TC-0339, TC-0344, TC-0345, TC-0346 | machine |
| TS-US-02-001-1 | US-02-001 | One call through the gateway | every call is made and logged through one gateway | TC-0076, TC-0078, TC-0080, TC-0081, TC-0083, TC-0091 | machine |
| TS-US-02-001-2 | US-02-001 | Engine choice and replay | callers do not change when the engine does | TC-0079, TC-0084 | machine |
| TS-US-02-001-3 | US-02-001 | Engine failure | a failing engine never leaks its message and never loses its row | TC-0082, TC-0093 | machine |
| TS-US-02-001-4 | US-02-001 | Cap behaviour | the cap is exact, survives a restart and holds the application in review | TC-0077, TC-0085, TC-0086, TC-0087, TC-0088, TC-0089, TC-0090 | machine |
| TS-US-02-001-5 | US-02-001 | Nothing leaves this machine by default | no page image leaves this machine unless Vision is chosen | TC-0092, TC-0094, TC-0095, TC-0096, TC-0097, TC-0098, TC-0099, TC-0100 | machine |
| TS-US-02-001-6 | US-02-001 | Memory and stuck reads | the engine cannot be pushed past its memory budget | TC-0352, TC-0353, TC-0354, TC-0355 | machine |
| TS-US-02-001-7 | US-02-001 | Logs and supply chain | no child's value is logged and no known-vulnerable package is shipped | TC-0349, TC-0350, TC-0351, TC-0356, TC-0357, TC-0358, TC-0359 | machine |
| TS-US-00-003-1 | US-00-003 | A document is read in Free mode | a good scan is typed and split into fields with one local call | TC-0101, TC-0105, TC-0111, TC-0112, TC-0116, TC-0123 | machine |
| TS-US-00-003-2 | US-00-003 | Vision mode | the opt-in Vision path is explicit and always reviewed by a person | TC-0102, TC-0103, TC-0113, TC-0114, TC-0124, TC-0127 | machine |
| TS-US-00-003-3 | US-00-003 | Reads that cannot be trusted | anything the engine is not sure of goes to a person | TC-0104, TC-0107, TC-0109, TC-0110, TC-0115, TC-0117, TC-0118, TC-0120, TC-0121 | machine |
| TS-US-00-003-4 | US-00-003 | Boundaries | boundary values are decided the same way every time | TC-0106, TC-0108, TC-0119, TC-0122 | machine |
| TS-US-00-003-5 | US-00-003 | Where the page goes | no page leaves the machine unless the person chose Vision | TC-0125, TC-0126 | machine |
| TS-US-00-004-1 | US-00-004 | Everything matches | a correct document is recognised as correct on every rule | TC-0001, TC-0011, TC-0015 | machine |
| TS-US-00-004-2 | US-00-004 | Harmless differences | harmless differences in print do not create work for a verifier | TC-0002, TC-0007, TC-0019, TC-0021 | machine |
| TS-US-00-004-3 | US-00-004 | A wrong value is caught | a wrong document is never accepted as right | TC-0003, TC-0006, TC-0008, TC-0012, TC-0016 | machine |
| TS-US-00-004-4 | US-00-004 | Boundary values | boundary values are decided the same way every time | TC-0004, TC-0005, TC-0009, TC-0010, TC-0013, TC-0014, TC-0017, TC-0018 | machine |
| TS-US-00-004-5 | US-00-004 | No evidence | an application cannot be verified on no evidence | TC-0020, TC-0022 | machine |
| TS-US-00-004-6 | US-00-004 | No personal data in logs | a child's personal data does not leak through logs | TC-0023, TC-0024 | machine |
| TS-US-00-004-7 | US-00-004 | Malformed input and repeatability | one bad document cannot block the queue | TC-0025, TC-0026 | machine |
| TS-US-00-005-1 | US-00-005 | All three documents match | a fully matching application is verified without a person | TC-0128, TC-0129, TC-0130 | machine |
| TS-US-00-005-2 | US-00-005 | Review and missing paths | each application lands in exactly one of the three statuses | TC-0135, TC-0136, TC-0139 | machine |
| TS-US-00-005-3 | US-00-005 | Something does not match | a doubtful application always reaches a person | TC-0132, TC-0133, TC-0134, TC-0138 | machine |
| TS-US-00-005-4 | US-00-005 | Boundaries | unfinished work never counts as a match | TC-0131, TC-0137, TC-0144 | machine |
| TS-US-00-005-5 | US-00-005 | Nobody can set Verified by hand | Verified only comes from a match or a verifier decision | TC-0140, TC-0141, TC-0142, TC-0143, TC-0145, TC-0147 | machine |
| TS-US-00-005-6 | US-00-005 | The three-value invariant | no fourth status can exist | TC-0146, TC-0148 | machine |
| TS-US-00-011-1 | US-00-011 | Seeded staff and verifier sign in | each role reaches its own work | TC-0149, TC-0150, TC-0152, TC-0161, TC-0167, TC-0168, TC-0169, TC-0170 | machine |
| TS-US-00-011-2 | US-00-011 | Seed rerun and real stack | the demo accounts are stable and sign-in works end to end | TC-0151, TC-0173 | machine |
| TS-US-00-011-3 | US-00-011 | Sign-in fails | a failed sign-in gives nothing away and opens nothing | TC-0153, TC-0155, TC-0156, TC-0171, TC-0172 | machine |
| TS-US-00-011-4 | US-00-011 | Lockout and idle | lockout and expiry are decided the same way every time | TC-0154, TC-0159 | machine |
| TS-US-00-011-5 | US-00-011 | Roles and forged requests | no role acts outside its own work | TC-0157, TC-0158, TC-0160, TC-0162, TC-0163, TC-0164, TC-0165, TC-0166 | machine |
| TS-US-00-011-6 | US-00-011 | Session life and CSRF | a stolen or forged session cannot be used to act | TC-0316, TC-0317, TC-0318, TC-0319, TC-0320 | machine |
| TS-US-00-011-7 | US-00-011 | Open sign-up as accepted | the accepted risk of open sign-up is stated and limited | TC-0321, TC-0322, TC-0323, TC-0324 | machine |
| TS-US-00-011-8 | US-00-011 | Sign-in leaks nothing | sign-in gives an attacker nothing to learn from | TC-0325, TC-0326, TC-0327 | machine |
| TS-US-00-011-9 | US-00-011 | Error and deployment hardening | the deployment shows no internals | TC-0328, TC-0329, TC-0330, TC-0331, TC-0332, TC-0333, TC-0334, TC-0335 | machine |
| TS-US-00-006-1 | US-00-006 | The verifier reviews a flagged application | a verifier can see exactly what to check | TC-0174, TC-0176, TC-0177, TC-0183, TC-0184, TC-0185, TC-0191, TC-0192 | machine |
| TS-US-00-006-2 | US-00-006 | Queue paging and rejected list | the queue stays short and complete | TC-0175, TC-0180, TC-0193 | machine |
| TS-US-00-006-3 | US-00-006 | Nothing or nobody to show | a missing record is explained, never a blank or a crash | TC-0178, TC-0179, TC-0186, TC-0187 | machine |
| TS-US-00-006-4 | US-00-006 | Real device | a mismatch is not signalled by colour alone | TC-0194 | hand |
| TS-US-00-006-5 | US-00-006 | Who may see the queue and the images | only signed-in people with the right role see a child's records | TC-0360, TC-0182, TC-0188, TC-0189, TC-0190 | machine |
| TS-US-00-006-6 | US-00-006 | Staff reading an image | images are served to signed-in roles only | TC-0336 | machine |
| TS-US-00-007-1 | US-00-007 | Approve and correct | a decision is applied once and logged with who, when and why | TC-0195, TC-0206, TC-0209, TC-0213, TC-0222 | machine |
| TS-US-00-007-2 | US-00-007 | Reject with a reason | a rejected application is out of the queue and still unverified | TC-0219, TC-0221, TC-0223 | machine |
| TS-US-00-007-3 | US-00-007 | Refused decisions | a bad decision is refused and writes nothing | TC-0196, TC-0197, TC-0202, TC-0205, TC-0210, TC-0211, TC-0212, TC-0214, TC-0215, TC-0216, TC-0217, TC-0218, TC-0220, TC-0224 | machine |
| TS-US-00-007-4 | US-00-007 | Concurrency and evidence | only one decision wins and an old approval does not outlive new evidence | TC-0198, TC-0199, TC-0200, TC-0201, TC-0207 | machine |
| TS-US-00-007-5 | US-00-007 | Who may decide and who may edit the log | only a verifier decides and no entry is ever changed | TC-0203, TC-0204, TC-0208, TC-0225, TC-0226, TC-0227, TC-0228 | machine |
| TS-US-00-007-6 | US-00-007 | No personal data in decision logs | no child's value is written to an application log | TC-0347, TC-0348 | machine |
| TS-US-00-010-1 | US-00-010 | A located field is cropped | the verifier sees the field in the scan | TC-0229, TC-0230, TC-0231, TC-0237 | both |
| TS-US-00-010-2 | US-00-010 | No position or no image | the verifier is told when no crop can be shown and sees the full page | TC-0234, TC-0235, TC-0236 | machine |
| TS-US-00-010-3 | US-00-010 | Field at an edge | a crop never leaves the page | TC-0232, TC-0233 | machine |
| TS-US-00-008-1 | US-00-008 | Staff open the overview | the overview matches the database | TC-0238, TC-0242, TC-0245 | machine |
| TS-US-00-008-2 | US-00-008 | Counts move after a decision | the overview follows the work | TC-0246, TC-0247, TC-0248, TC-0249 | machine |
| TS-US-00-008-3 | US-00-008 | The API fails | staff are told when counts cannot be read | TC-0244 | machine |
| TS-US-00-008-4 | US-00-008 | Zero applications | an empty system shows zeros, not an error | TC-0239, TC-0243 | machine |
| TS-US-00-008-5 | US-00-008 | Counts only and who may read | the dashboard exposes no child's data | TC-0240, TC-0241 | machine |
| TS-US-00-009-1 | US-00-009 | Staff export the verified list | the file lists exactly the verified applications | TC-0250, TC-0252, TC-0253, TC-0254, TC-0258, TC-0259, TC-0266, TC-0267 | machine |
| TS-US-00-009-2 | US-00-009 | Cells with commas and quotes | the file opens correctly in a spreadsheet | TC-0255, TC-0268 | machine |
| TS-US-00-009-3 | US-00-009 | Refused or empty export | no export without a session and an empty list is a header only | TC-0260, TC-0262, TC-0263, TC-0264, TC-0265 | machine |
| TS-US-00-009-4 | US-00-009 | Rejected applications | only Verified applications are in the file | TC-0251, TC-0261 | machine |
| TS-US-00-009-5 | US-00-009 | CSV injection and audit | a spreadsheet never runs a name as a formula and every export is recorded | TC-0256, TC-0257, TC-0259 | machine |
| TS-US-02-003-1 | US-02-003 | The dataset is built and loaded | the system can be filled with a known synthetic set | TC-0269, TC-0270, TC-0275, TC-0282, TC-0292, TC-0293 | machine |
| TS-US-02-003-2 | US-02-003 | Rerun and determinism | the seed is repeatable | TC-0271, TC-0276, TC-0280, TC-0281 | machine |
| TS-US-02-003-3 | US-02-003 | Bad destination or stored values | the loader stops before it does harm | TC-0272, TC-0273, TC-0274 | machine |
| TS-US-02-003-4 | US-02-003 | Noise and mismatch counts | noise and mismatches are exact and repeatable | TC-0277, TC-0278, TC-0279, TC-0283, TC-0284, TC-0285, TC-0286 | both |
| TS-US-02-003-5 | US-02-003 | No real data | no real person is in any seeded record | TC-0287, TC-0288, TC-0289, TC-0290, TC-0291 | machine |
| TS-US-02-002-1 | US-02-002 | The decision is recorded | the choice can be audited | TC-0294, TC-0299, TC-0301 | hand |
| TS-US-02-002-2 | US-02-002 | Free model policy | the free path stays open | TC-0296 | machine |
| TS-US-02-002-3 | US-02-002 | Non-free choices | nothing that costs money is accepted | TC-0295, TC-0298 | both |
| TS-US-02-002-4 | US-02-002 | Limits of the evidence | the limits of the evidence are stated | TC-0297, TC-0300, TC-0302 | both |
| TS-US-02-004-1 | US-02-004 | Accuracy is reported | per field type accuracy is reported | TC-0303, TC-0307 | machine |
| TS-US-02-004-2 | US-02-004 | Two engines side by side | the chosen engine and the runner-up are compared on the same documents | TC-0308, TC-0309, TC-0310 | machine |
| TS-US-02-004-3 | US-02-004 | Misreads and read errors | mistakes are counted, never hidden | TC-0304, TC-0305, TC-0306 | machine |
| TS-US-02-004-4 | US-02-004 | Gate behaviour | the gate never passes by default | TC-0312, TC-0313, TC-0314 | machine |
| TS-US-02-004-5 | US-02-004 | Free and offline | the eval needs no paid service | TC-0311, TC-0315 | both |

## 4. Entry criteria

- `make check` passes on the branch before new tests are added (the lead confirms).
- Postgres from `docker-compose.yml` is up and migrated (`make db`, `make migrate`) for every integration case (the lead confirms).
- Poppler and the RapidOCR models are installed for the PDF and real-engine cases, for example TC-0068, TC-0069 and TC-0119 (the engineer who runs them confirms).
- `make seed-accounts` has printed the two demo passwords, and `make seed-load` has loaded the 20 applications and 30 documents, before TC-0173 and TC-0248 (the tester confirms).
- Q-003 (name threshold), Q-011 (date formats) and Q-017 (field map) are answered, or the assumed readings in `docs/product/questions.md` are accepted (the product owner confirms).
- The two contradictions in section 7 were settled on 2026-10-16: the engineer kept both as built (TC-0181 is retired and replaced by TC-0360; TC-0265 stands). Product still confirms the wording of the backlog notes.

## 5. Exit criteria

- Every P1 case passes (TC-0003, TC-0004, TC-0006, TC-0008, TC-0012, TC-0016, TC-0020, TC-0022, TC-0023, TC-0025, TC-0034, TC-0035, TC-0045, TC-0046, TC-0059, TC-0062, TC-0063, TC-0065, TC-0068, TC-0071, TC-0072, TC-0075, TC-0085, TC-0087, TC-0088, TC-0089, TC-0092, TC-0095, TC-0096, TC-0097, TC-0100, TC-0106, TC-0107, TC-0110, TC-0114, TC-0115, TC-0117, TC-0119, TC-0120, TC-0123, TC-0125, TC-0128, TC-0131, TC-0132, TC-0133, TC-0134, TC-0138, TC-0140, TC-0141, TC-0142, TC-0143, TC-0144, TC-0145, TC-0147, TC-0150, TC-0152, TC-0153, TC-0154, TC-0155, TC-0157, TC-0158, TC-0160, TC-0161, TC-0162, TC-0163, TC-0164, TC-0165, TC-0166, TC-0169, TC-0170, TC-0171, TC-0173, TC-0174, TC-0175, TC-0182, TC-0183, TC-0188, TC-0189, TC-0190, TC-0191, TC-0192, TC-0195, TC-0196, TC-0198, TC-0199, TC-0201, TC-0203, TC-0204, TC-0206, TC-0207, TC-0208, TC-0209, TC-0211, TC-0215, TC-0216, TC-0219, TC-0221, TC-0225, TC-0226, TC-0227, TC-0240, TC-0246, TC-0250, TC-0251, TC-0256, TC-0257, TC-0260, TC-0261, TC-0271, TC-0272, TC-0273, TC-0287, TC-0288, TC-0289, TC-0290, TC-0291, TC-0295, TC-0316, TC-0317, TC-0319, TC-0320, TC-0321, TC-0323, TC-0324, TC-0325, TC-0326, TC-0327, TC-0328, TC-0337, TC-0338, TC-0340, TC-0341, TC-0343, TC-0344, TC-0345, TC-0347, TC-0349, TC-0351, TC-0352, TC-0353, TC-0357).
- The gate `cases_check.py` exits 0 with `--steps` and `--plan` on these files.
- No open defect on a P1 case; a waiver names the product owner.
- Coverage of the Python code is above the repository gate of 80 percent (`pyproject.toml` `fail_under`).
- Every case still `planned` has a named owner or a retire decision, and every case marked `automated` has been run once on the release commit (not run by this task).

## 6. Environments

| Environment | Browsers and devices | Data and controls |
| --- | --- | --- |
| local and CI backend (`make test`, `make test-integration`) | none: no screen | synthetic data only (`seed/`, `CONSTRAINTS.md` section 2); Postgres from `docker-compose.yml`; log capture and a socket block for the privacy and offline cases; Poppler and RapidOCR models for the real-engine cases |
| frontend component tests (`pnpm test` in `frontend/`, vitest) | jsdom, no real browser | mocked network (msw); typed `unit` in the case table |
| browser tests (`pnpm test:e2e`, Playwright, `frontend/playwright.config.ts`) | chromium, firefox, webkit, mobile-chrome (Pixel 7), mobile-safari (iPhone 15); a separate `visual` project is not used by any case here | mocked API from `frontend/e2e/support/mockApi.ts`; the flows run in the whole matrix |
| manual and real-stack cases (TC-0173, TC-0248, TC-0194, TC-0237, TC-0283, TC-0315) | a real browser at 1280 by 800 and at 390 by 844, one phone | real API and database seeded with `make seed-accounts` and `make seed-load`; synthetic data only; no real student data |

## 7. What QA raised while writing this

- [undefined] Q-003 gives no similarity threshold for names. TC-0001 to TC-0005 use values that are clearly equal or clearly different, so none sits near any threshold. A near-miss spelling (one letter changed) has no case until the threshold is set.
- [assumption] Dates are normalised to one format before an exact comparison (Q-011). TC-0007 assumes `04/03/2006` is day first and means 4 March 2006; the day-month order of other print formats is not covered.
- [assumption] TC-0014 assumes surrounding whitespace on a roll number is ignored. REQ-015 says only "exact". If exact means byte for byte, TC-0014 changes to a mismatch.
- [undefined] AC-US-00-004-3 does not say whether letter case matters in a roll number. No case asserts it; the roll numbers in the seed are all upper case.
- [undefined] A subject missing from a marksheet extraction is not covered by the PRD; TC-0018 assumes a mismatch, not a skipped field.
- [assumption] AC-US-00-004-5 says fields a document type does not carry are skipped, but the field map is open (Q-017). TC-0019 and TC-0021 take the map from the seed: an ID proof carries name and date of birth; a transfer certificate adds father's name.
- [risk] US-00-004: the 26 cases were written on 2026-10-05 before any comparison code existed. The code now exists (`app/domain/compare.py`, `app/domain/match.py`) and nine of the rows were matched to tests on 2026-10-16 (see the note in test-cases.md); the other 17 stay `planned`. None was run by this task.
- [risk] TC-0023 asserts the logs hold none of three values. A log line built from a whole object (for example a dict of the application) would leak them; the case catches only the three values it names.
- [risk] No test was run by this task. `automated: path:test_name` means the test exists in that file, checked by search. The acceptance audit (`docs/testing/NOTASK-17-acceptance-audit.md`) says its test names are assertions in the repository, not a claim that each was run alone. The exit criteria ask for one run on the release commit.
- [risk] All 15 browser cases run on a mocked API (`frontend/e2e/support/mockApi.ts`). The audit found no unmocked journey from sign-in to export; TC-0173 and TC-0248 are planned for the real stack.
- [contradiction] AC-US-00-006-1 and Q-013 say only verifiers see the queue, but `GET /api/applications` lets either signed-in role list (TC-0182 asserts the as-built reading). Resolved 2026-10-16: the engineer kept the as-built reading, TC-0181 is retired and TC-0360 asserts that either role may list.
- [contradiction] AC-US-00-009-2 says an export with no Verified application holds the header row only. The API does (TC-0262); the export page declines to save a file and says nothing is Verified yet (TC-0265). Resolved 2026-10-16: the engineer kept this as built; TC-0265 stands and Product confirms the backlog note.
- [undefined] AC-US-00-008-1 names staff, but the dashboard also answers a verifier (TC-0241). Nothing says whether that is wanted.
- [assumption] AC-US-00-001-1 does not say which date formats a CSV may carry. The importer reads ISO dates only, accepts 1950-01-01 to 2020-12-31 and a name of up to 120 characters (`app/domain/importing.py`); TC-0039, TC-0041 and TC-0043 take their limits from the code, not from the backlog.
- [assumption] Limits quoted in cases come from `app/core/config.py`: import_max_bytes 5,000,000, import_max_rows 20,000, upload_max_bytes 8 MiB, gateway_call_cap 1000, review_confidence_cutoff 0.9804 and a Vision daily cap of 40. A test may override them.
- [undefined] AC-US-00-007-4 says the rejected application "is not Verified and leaves the flagged queue". As built (Q-006 option c) it keeps status needs_review with rejected true. TC-0219, TC-0247 and TC-0251 assert the as-built reading; AC-US-00-008-2 does not say how a rejection moves the counts.
- [undefined] AC-US-00-003-1 says one call in Free mode, and two logged calls when Vision fails and falls back (ADR-0015). TC-0101 and TC-0103 hold the two readings apart.
- [untestable] AC-US-02-002-4 is Partial in the audit: the hardware of the 2026-10-05 benchmark was never recorded and cannot be recovered. TC-0300 asserts the gap, not a measurement.
- [undefined] AC-US-02-002-6: calibration of the engine's confidence is unproven by design (ADR-0017); one wrong field on the tuning set cannot establish it. TC-0302 checks the statement only.
- [untestable] AC-US-02-003-4 asks for absence from real data, which cannot be shown directly. TC-0287 to TC-0291 test provenance, as the backlog was reworded on 2026-10-11.
- [risk] Origin enforcement is tested only on logout (TC-0158). TC-0035 and TC-0204 are `planned` for import and decide.
- [risk] Accessibility: TC-0194 is the only manual accessibility case. No accessibility scan was run on any screen and the backlog has no accessibility criterion.
- [risk] TC-0094: the audit ran the offline gateway modules with a temporary make target and an audit hook that blocks sockets. No committed target exists, so the case is `planned`.
- [assumption] The threat model `docs/security/threat-model-docket.md` was written on 2026-10-05, before the code. Its 31 rated threats are each the Source of a risk in risks.md. The backlog has no story for T-26, T-30 and T-32 to T-35; they are attached to US-02-001 (T-26, T-35) and US-00-011 (T-30, T-32, T-33, T-34). The model's Status column still says planned for mitigations the code now has; that file was not changed.
- [risk] T-30 (database TLS, least-privilege role) and T-26 (model checksum) have no test: TC-0334, TC-0335 and TC-0356 are `planned`.
- [risk] T-38 (open sign-up with a self-chosen role) is an accepted risk (ADR-0013). TC-0321 records that a caller can register as a verifier; it documents the risk and is not a defect case.
- [assumption] The first plan reported "0 threats traced from 0 threat models" because it ran the gate with `--story US-00-004`. The gate now runs over all 15 stories and reads the threat model.
- [assumption] Frontend component tests (vitest) are typed `unit` and have no rows in the steps file; browser tests (Playwright) are typed `e2e` and have steps. A row that cites several tests (for example TC-0227) counts once.
- [risk] Several rows cite the same test (for example TC-0250, TC-0251 and TC-0261). When that test fails every row that cites it turns red, so read a failure by test name, not by TC count.

## 8. How the gate is run

```
python3 "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/test-cases/scripts/cases_check.py" --steps docs/testing/test-case-steps.md --plan docs/testing/test-plan.md
```

The case table, the step table and this plan passed the gate with 0 problems on 2026-10-16:

```
test-types: unit 170, integration 164, e2e 15, manual 10; by machine 349 (automated 311, planned 38), by hand 10
test-steps: 25 manual or e2e cases, 25 with steps, 61 steps
test-plan: 85 scenarios over 15 stories, 359 of 359 live cases placed, 29 concerns raised, 0 problems
```

The gate reads the whole backlog and the threat model; the 2026-10-05 run used `--story US-00-004` and could not.
