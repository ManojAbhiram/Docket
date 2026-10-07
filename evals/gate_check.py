"""Compare a replayed extraction summary with the accepted baseline in evals/ocr/gate.yaml.

    uv run python -m evals.gate_check evals/ocr/extraction/recorded-all.summary.json

Exit 0 when the score holds, 1 when it fell by more than `delta` or the run is incomplete, 2 when
no baseline has been accepted yet (a person edits `accepted_baseline` in gate.yaml).
"""

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

GATE_FILE = Path("evals/ocr/gate.yaml")
ALL_DOCUMENTS = 30
EXIT_PASS, EXIT_FAIL, EXIT_NO_BASELINE = 0, 1, 2
NO_BASELINE = "no accepted baseline in gate.yaml; a person must accept one"


def parse_gate(text: str) -> dict[str, str]:
    """Flat `key: value` lines. Comment lines and trailing ` # comments` are dropped."""
    gate: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        gate[key.strip()] = value.split(" #", 1)[0].strip()
    return gate


def check(summary: Mapping[str, object], gate: Mapping[str, str]) -> tuple[bool, str]:
    """Whether the replayed score holds against the baseline, and a message with the numbers."""
    baseline_text = gate.get("accepted_baseline", "none")
    if baseline_text == "none":
        return False, NO_BASELINE
    documents = int(str(summary["documents"]))
    if gate.get("subset", "all") == "all" and documents != ALL_DOCUMENTS:
        return False, f"the run scored {documents} documents; the subset needs {ALL_DOCUMENTS}"
    read_errors = int(str(summary.get("read_errors", 0)))
    if read_errors:
        return False, f"{read_errors} read error(s) in the replay; every document must be read"
    score = float(str(summary["mean_field_accuracy"]))
    baseline = float(baseline_text)
    delta = float(gate.get("delta", "0"))
    detail = f"score {score}, baseline {baseline}, delta {delta}"
    if score >= baseline - delta:
        return True, f"pass: {detail}"
    return False, f"fail: {detail}; the score fell by more than delta"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: python -m evals.gate_check <summary.json>\n")
        return EXIT_FAIL
    summary = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    ok, message = check(summary, parse_gate(GATE_FILE.read_text(encoding="utf-8")))
    sys.stdout.write(message + "\n")
    if ok:
        return EXIT_PASS
    return EXIT_NO_BASELINE if message == NO_BASELINE else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
