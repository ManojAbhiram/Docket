# ADR-0017: Narrow the engine comparison and accept the calibration limit

- Status: Accepted
- Date: 2026-10-11
- Task: NOTASK-17
- Deciders: Manoj Abhiram (asked in session to close the acceptance audit gaps, recommended option)
- Area: engine selection evidence (US-02-002)
- Reversibility: cheap: the engine sits behind the gateway, and the evals can be rerun with more engines or more documents.

## Context

AC-US-02-002-3 asks every eligible candidate to run on the same labelled set, and AC-US-02-002-6 asks whether each candidate's confidence separates correct from wrong fields. Only RapidOCR and Tesseract were run. PaddleOCR peaked at 2,220 MB on its own published measurement, docTR and EasyOCR need PyTorch (wheels for Python 3.14 unchecked, DEBT-006), and every vision-language model was excluded for size, licence or missing Hindi (`docs/research/ocr-landscape.md`, eligibility table). On the 202 recorded RapidOCR fields, 201 were correct and 1 wrong; the wrong field was sent to review, and 10 correct fields were also sent at cutoff 0.9804. One wrong field cannot establish calibration.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Accept the two-engine comparison and the calibration limit (chosen) | the confidence cutoff is unproven beyond this set | the chosen engine fits the host and the cutoff routes conservatively |
| Run PaddleOCR and docTR first | about a day of setup and 2 GB or more of downloads, and neither fits the 512 MB host | a larger host were chosen |
| Generate hundreds more labelled pages to calibrate | useful, but it measures only synthetic noise | real photographed documents were available |

## Decision

We will treat RapidOCR versus Tesseract as the complete comparison for v1 and accept that the review cutoff of 0.9804 is conservative but not calibrated, because no other candidate fits the 512 MB budget and the cutoff already sends every wrong field in the measured set to a person.

## Consequences

- Easier: the engine decision stands without more downloads.
- Harder: a wrong field with high confidence is not ruled out on real photographs.
- Revisit when real or much larger labelled sets exist, a larger host is chosen, or the review rate of correct fields becomes a cost.

## Commits us to

The 0.9804 cutoff stays provisional (ADR-0005) and the eval gate in `evals/ocr/gate.yaml` stays in CI.
