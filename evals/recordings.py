"""Save an engine's words for each labelled image so CI can replay them with no live engine.

    uv run python -m evals.recordings rapidocr

The file is read by app.gateway.engines.RecordedEngine: a dict keyed by the SHA-256 of the image
bytes, each value `{"words": [{"text", "confidence", "box"}]}`. A document that cannot be read
stops the recording: a partial file would make a replay look smaller instead of failing.
"""

import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from app.gateway.types import Engine
from seed.dataset import DocumentRecord, build_dataset

DEFAULT_OUT = Path("evals/recordings/rapidocr.json")


def record(engine: Engine, docs: Sequence[DocumentRecord], png_dir: Path, out: Path) -> int:
    """Read every document with `engine` and write the recording. Returns documents written."""
    recordings: dict[str, dict[str, list[dict[str, object]]]] = {}
    for doc in docs:
        image = (png_dir / doc.file_name).read_bytes()
        words = engine.read(image).words
        recordings[hashlib.sha256(image).hexdigest()] = {
            "words": [
                {"text": w.text, "confidence": w.confidence, "box": list(w.box)} for w in words
            ]
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recordings, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return len(recordings)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["rapidocr"]:
        sys.stderr.write("usage: python -m evals.recordings rapidocr\n")
        return 1
    from app.gateway.rapidocr_engine import RapidOcrEngine

    written = record(
        RapidOcrEngine(), list(build_dataset().documents), Path("data/seed/png"), DEFAULT_OUT
    )
    sys.stdout.write(f"recorded {written} documents to {DEFAULT_OUT}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
