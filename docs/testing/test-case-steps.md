# Test case steps

Cases: docs/testing/test-cases.md as of 2026-10-16. Step ids are permanent;
a retired case keeps its steps.

## Steps

Rows exist for every `e2e` and `manual` case. Unit and integration cases (including every US-00-004 case) have no rows here. Browser steps use the mocked API of `frontend/e2e/support/mockApi.ts` unless the case says real API. Step text quotes the on-screen text the browser tests assert.

| Step | Case | Action | Expected |
| --- | --- | --- | --- |
| TC-0051.1 | TC-0051 | Open /import signed in as staff and choose apps.csv (three rows) with the file picker | The file name apps.csv shows and the button Import applications is enabled |
| TC-0051.2 | TC-0051 | Press Import applications | One import request is sent and the heading `Imported 1 of 3 rows.` appears |
| TC-0051.3 | TC-0051 | Read the refused rows table | The text `2 rows were refused` shows with the cells `Unreadable date` and `Missing value` |
| TC-0052.1 | TC-0052 | Open /import signed in as staff and do not choose a file | The page shows the button Import applications |
| TC-0052.2 | TC-0052 | Look at the button | The button is disabled and no import request is sent |
| TC-0061.1 | TC-0061 | Open /applications signed in as staff and choose Add documents on the second application | The heading `Documents for SYN-APP-005` shows |
| TC-0061.2 | TC-0061 | Choose marksheet.png with the file picker | One upload request is sent for SYN-APP-005 |
| TC-0169.1 | TC-0169 | Open the site root with no session | The browser goes to /sign-in |
| TC-0169.2 | TC-0169 | Enter Username `staff.one` and the mock password and press Sign in | The heading Applications shows with the links Import applications and Export verified list and no Review queue link |
| TC-0169.3 | TC-0169 | Press Sign out | The browser goes to /sign-in and the session is empty |
| TC-0170.1 | TC-0170 | Open /sign-in with no session | The sign-in form shows |
| TC-0170.2 | TC-0170 | Enter Username `verifier.one` and the mock password and press Sign in | The heading Review queue shows and there is no Import applications link |
| TC-0171.1 | TC-0171 | Open /sign-in and enter Username `staff.one` and Password `not-the-password` | The form holds both values |
| TC-0171.2 | TC-0171 | Press Sign in | The URL stays /sign-in, a role=alert message shows and no session exists |
| TC-0172.1 | TC-0172 | Open /queue with no session | The browser goes to /sign-in |
| TC-0172.2 | TC-0172 | Read the page | Only the sign-in form shows and no queue content |
| TC-0173.1 | TC-0173 | Run make seed-accounts and note the printed passwords, then open the site | The browser shows the sign-in page |
| TC-0173.2 | TC-0173 | Sign in as the seeded staff account and press Sign out | The Applications page shows with staff links, then the sign-in page shows |
| TC-0173.3 | TC-0173 | Sign in as the seeded verifier account | The Review queue page shows and there is no Import applications link |
| TC-0194.1 | TC-0194 | Open the seeded flagged application SYN-APP-004 on a phone or a 390 by 844 window as a verifier | The review page shows the fields stacked |
| TC-0194.2 | TC-0194 | Turn colour off in the browser (grayscale mode) and read the flagged name field | The flagged field still shows its reason in words |
| TC-0194.3 | TC-0194 | Compare with a matching field | The matching field shows no reason text, so the two are told apart without colour |
| TC-0207.1 | TC-0207 | Sign in as a verifier on the mock that answers 409 on the first decision and open /queue | The heading Review queue shows |
| TC-0207.2 | TC-0207 | Press Review newest, then Decide, choose Approve and press Save decision | The text `This application changed while you were looking at it.` shows |
| TC-0207.3 | TC-0207 | Check the recorded decisions on the mock | The list of recorded decisions is empty |
| TC-0208.1 | TC-0208 | Sign in as staff on the mock and open /applications | The applications list shows |
| TC-0208.2 | TC-0208 | Press Open on the first application | The heading SYN-APP-004 shows and no Decide button exists |
| TC-0221.1 | TC-0221 | Sign in as a verifier on the mock and open /queue, press Review newest | The heading SYN-APP-004 shows |
| TC-0221.2 | TC-0221 | Press Decide, choose Reject and press Save decision with the Reason empty | The text `Give a reason for the rejection.` shows and no decision is recorded |
| TC-0221.3 | TC-0221 | Type `Scan is of another person` into Reason and press Save decision | The text `Decision saved` shows, then `Nothing needs review.`, and one reject decision with that reason is recorded |
| TC-0237.1 | TC-0237 | Open SYN-APP-004 as a verifier on a 390 by 844 window | The field list and the crops show |
| TC-0237.2 | TC-0237 | Read the crop beside the name | The name printed on the scan is legible in the crop |
| TC-0237.3 | TC-0237 | Select a field that has no position on the page | The full page shows and no crop is drawn for that field |
| TC-0245.1 | TC-0245 | Sign in as staff on the mock and open /dashboard | The heading Overview shows |
| TC-0245.2 | TC-0245 | Read the counts | The text `3 applications` and the text `of which 0 rejected` show |
| TC-0247.1 | TC-0247 | Sign in as a verifier on the mock, open /queue and press Review newest | The heading SYN-APP-004 shows |
| TC-0247.2 | TC-0247 | Press Decide, choose Reject, type `Not legible` into Reason and press Save decision | The text `Nothing needs review.` shows |
| TC-0247.3 | TC-0247 | Press the Overview link | The text `of which 1 rejected` shows |
| TC-0248.1 | TC-0248 | Run make seed-load against a local API and sign in as staff, open /dashboard and note the Verified and Needs review counts | The Verified count and the Needs review count are written down |
| TC-0248.2 | TC-0248 | Sign in as the seeded verifier, open /queue, press Review newest, press Decide, choose Approve and press Save decision | The text `Decision saved` shows |
| TC-0248.3 | TC-0248 | Sign in as staff again and open /dashboard | Verified is one higher and Needs review one lower than the noted counts |
| TC-0267.1 | TC-0267 | Sign in as staff on the mock and open /export | The text `1 rows` shows |
| TC-0267.2 | TC-0267 | Press Download CSV | A file named verified.csv is saved |
| TC-0283.1 | TC-0283 | Run the seed screenshot step then the noise step from the documented commands and open three PNG files with noise levels above 0.4 | The three images open |
| TC-0283.2 | TC-0283 | Look for blur, tilt and an uneven shadow in each image | Each image shows all three effects and the text SYNTHETIC DOCUMENT is still readable |
| TC-0294.1 | TC-0294 | Open docs/research/ocr-landscape.md and read the Candidates table | The candidate engines are listed |
| TC-0294.2 | TC-0294 | Read the section `Eligibility before any run` | Every candidate in the Candidates table has a row marked Eligible or Disqualified with a reason |
| TC-0298.1 | TC-0298 | Open the Eligibility table in docs/research/ocr-landscape.md and list the Disqualified engines | A list of Disqualified engines is written down |
| TC-0298.2 | TC-0298 | Search docs/testing/extraction-accuracy.md for each of them | None of the Disqualified engines has an accuracy row; only rapidocr, recorded and tesseract sections exist |
| TC-0299.1 | TC-0299 | Open docs/testing/extraction-accuracy.md and read the `rapidocr: accuracy by field` and `tesseract: accuracy by field` sections | Both sections give accuracy for names, dates, roll numbers and marks |
| TC-0299.2 | TC-0299 | Read the two `accuracy by document type` sections | Both give classification accuracy on the same 30 documents |
| TC-0300.1 | TC-0300 | Open evals/ocr/results and read one result file | Each document has a latency |
| TC-0300.2 | TC-0300 | Open docs/performance/NOTASK-17-memory.md and find the section `Measurement hardware` | The hardware of the memory runs is described |
| TC-0300.3 | TC-0300 | Search docs/research/ocr-benchmark.md for the hardware of the 2026-10-05 benchmark | The document says the laptop was not recorded, which is the known Partial |
| TC-0301.1 | TC-0301 | Open docs/adr/0001-use-rapidocr-with-preprocessing-as-the-ocr-engine.md | The record names RapidOCR as the chosen engine |
| TC-0301.2 | TC-0301 | Compare its numbers and its runner-up with docs/testing/extraction-accuracy.md | Tesseract is named as the runner-up and the numbers agree with the report |
| TC-0302.1 | TC-0302 | Open docs/adr/0017-narrow-the-engine-comparison-and-accept-the-calibration-limit.md | The decision on calibration is stated |
| TC-0302.2 | TC-0302 | Read the confidence statement in docs/testing/extraction-accuracy.md | RapidOCR confidence is said to separate and Tesseract is said to give no confidence |
| TC-0315.1 | TC-0315 | On a clean checkout with the free tools installed run `make eval-extract` | The command exits 0 and reports zero read errors |
| TC-0315.2 | TC-0315 | Run `make eval-gate` | The command fails and its message names the missing accepted baseline, not an engine or a paid service |
| TC-0315.3 | TC-0315 | Check the environment for paid keys or a card | No paid key is set and none is needed |
