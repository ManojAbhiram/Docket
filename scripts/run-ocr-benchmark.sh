#!/usr/bin/env bash
# Run the whole OCR benchmark: generate the synthetic set, screenshot it with
# playwright-cli, add OpenCV photo noise, benchmark every shortlisted engine with and
# without preprocessing (one process per run), then write docs/research/ocr-benchmark.md.
#
# Run from the repository root, after:
#   uv sync --all-groups
#   uv venv .venv-ocr --python 3.12
#   uv pip install --python .venv-ocr/bin/python -r evals/requirements-ocr.txt
# and with tesseract (eng, hin) and playwright-cli installed.
set -euo pipefail

PY="${PY:-.venv-ocr/bin/python}"

uv run python -m seed
bash data/seed/render-clean.sh
uv run python -m seed --noise

for pre in "" "--preprocess"; do
  for run in "tesseract" "rapidocr" "rapidocr --devanagari" "paddleocr" "doctr"; do
    echo "== $run $pre"
    # shellcheck disable=SC2086  # the flags are meant to split into words
    "$PY" -m evals.ocr_bench $run $pre || echo "run failed: $run $pre"
  done
done

"$PY" -m evals.report
