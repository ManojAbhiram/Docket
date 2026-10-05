#!/usr/bin/env bash
# Run the OCR benchmark: generate the synthetic set, screenshot it with playwright-cli, add
# OpenCV photo noise, benchmark each shortlisted engine with and without preprocessing (one
# process per run), then write docs/research/ocr-benchmark.md.
#
# Run from the repository root, after:
#   uv sync --all-groups
#   uv venv .venv-ocr --python 3.12
#   uv pip install --python .venv-ocr/bin/python -r evals/requirements-ocr.txt
# and with tesseract (eng, hin) and playwright-cli installed.
#
#   SKIP_SEED=1   reuse the PNGs already in data/seed/png
#   ENGINES="tesseract rapidocr"   run only these (default: all that are installed)
#   BROWSER=firefox   browser for playwright-cli
set -euo pipefail

PY="${PY:-.venv-ocr/bin/python}"
ENGINES="${ENGINES:-tesseract rapidocr}"

if [ -z "${SKIP_SEED:-}" ]; then
  uv run python -m seed
  bash data/seed/render-clean.sh
  uv run python -m seed --noise
fi

# Old result files are named differently from the current ones; mixing them double counts.
rm -f evals/ocr/results/*.jsonl evals/ocr/results/*.summary.json

run() {
  echo "== $*"
  "$PY" -m evals.ocr_bench "$@" || echo "run failed: $*"
}

for pre in "" "--preprocess"; do
  for engine in $ENGINES; do
    case "$engine" in
      tesseract)
        # page segmentation: 6 block, 4 columns, 11 sparse text
        for psm in 6 4 11; do run tesseract --tesseract-psm "$psm" $pre; done
        ;;
      rapidocr)
        run rapidocr $pre
        run rapidocr --max-side 640 $pre
        ;;
      paddleocr) run paddleocr $pre ;;
      doctr) run doctr $pre ;;
    esac
  done
done

"$PY" -m evals.report
