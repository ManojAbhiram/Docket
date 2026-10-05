# OCR benchmark on the synthetic set

**Status: not run.** No engine has been installed or measured, so this file holds no results. Running `bash scripts/run-ocr-benchmark.sh` regenerates it from the measured summaries with `python -m evals.report`; every number in the generated version is read from `evals/ocr/results/*.summary.json`, and none is typed by hand.

## What will be measured

- **Dataset:** 30 synthetic documents for 20 synthetic applications (`seed/`), four document types: 10th marksheet, 12th marksheet, ID proof and the stretch transfer certificate. 8 documents carry one deliberate mismatch and 3 print the name in reverse order. Each page is rendered from HTML to PNG with `playwright-cli`, then degraded with OpenCV: blur, a shadow toward the bottom, low light (brightness 0.40 to 1.00) and a skew of up to 4 degrees. The noise settings of every document are in `labels.json` and `cases.jsonl`.
- **Engines (the shortlist in `docs/research/ocr-landscape.md`):** Tesseract with `hin+eng`, RapidOCR (default and Devanagari models), PaddleOCR v5, docTR. The PP-OCRv6 detector with a v5 recogniser hybrid is not run because no verified configuration exists.
- **Variants:** each engine raw and with preprocessing (light flattening and deskew, `evals/preprocess.py`).
- **Metrics:** field accuracy per field type (presence in the OCR text), character error rate (`evals.scoring.field_cer`), seconds per page (median, p95, preprocessing reported separately) and peak RAM against the 512 MB budget.
- **Method:** the llm-eval skill's. The 30 documents are a `seed` set, below the 50 cases it asks for in an extraction eval; the labels come from the generator, not a person. No baseline has been accepted and no CI gate runs (`evals/ocr/gate.yaml` sets the delta for when one is).

## How to run

```
uv sync --all-groups
uv venv .venv-ocr --python 3.12
uv pip install --python .venv-ocr/bin/python -r evals/requirements-ocr.txt
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin
npm install -g @playwright/cli@latest
bash scripts/run-ocr-benchmark.sh
```

## Limits to expect

- Scores are presence in the text, an upper bound on extraction, not a field extractor's accuracy.
- Thirty documents from four templates cannot separate engines a few points apart.
- The pages are English only, so the Hindi models are measured on Latin text.
- Peak RAM is this machine's, not a Render instance's.
- The PaddleOCR and docTR adapters in `evals/ocr_bench.py` follow their READMEs from memory; they may need changes on first run.
