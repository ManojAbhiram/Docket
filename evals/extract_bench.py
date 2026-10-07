"""Run an engine over the labelled documents and write a summary of real extraction accuracy.

    uv run python -m evals.extract_bench rapidocr --out evals/ocr/extraction
    uv run python -m evals.extract_bench recorded --recording evals/recordings/rapidocr.json

Every document is scored. A document that cannot be read counts as all fields wrong and is
reported as a read error, so the denominator never shrinks.
"""

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from app.core.config import Settings
from app.domain.classify import classify
from app.domain.extract import extract_fields
from app.gateway.types import Engine, EngineError, RecordingMissingError
from evals.extraction import DocumentScore, expected_values, score_document
from seed.dataset import DocumentRecord, build_dataset

READ_ERROR = "read_error"
ENGINE_NAMES = ("rapidocr", "recorded")
SUBSET_NAMES = ("all",)


def run_documents(
    engine: Engine, docs: Sequence[DocumentRecord], png_dir: Path, cutoff: float
) -> list[DocumentScore]:
    scores: list[DocumentScore] = []
    for doc in docs:
        try:
            image = (png_dir / doc.file_name).read_bytes()
            words = engine.read(image).words
        except EngineError, RecordingMissingError, ValueError, OSError, RuntimeError:
            scores.append(_failed(doc))
            continue
        predicted = classify(words)
        fields = extract_fields(words, predicted, confidence_cutoff=cutoff)
        scores.append(score_document(doc, predicted, fields))
    return scores


def _failed(doc: DocumentRecord) -> DocumentScore:
    return DocumentScore(
        document_id=doc.document_id,
        doc_type=doc.doc_type,
        predicted_type=READ_ERROR,
        type_ok=False,
        correct=dict.fromkeys(expected_values(doc), False),
    )


def summarise(scores: Sequence[DocumentScore], engine_name: str, subset: str) -> dict[str, object]:
    by_field: dict[str, list[bool]] = defaultdict(list)
    by_type: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for score in scores:
        for (name, _subject), ok in score.correct.items():
            by_field[name].append(ok)
            by_type[score.doc_type][name].append(ok)
    every = [ok for oks in by_field.values() for ok in oks]
    return {
        "engine": engine_name,
        "subset": subset,
        "documents": len(scores),
        "read_errors": sum(1 for s in scores if s.predicted_type == READ_ERROR),
        "type_accuracy": _mean([s.type_ok for s in scores]),
        "field_accuracy": {name: _mean(oks) for name, oks in sorted(by_field.items())},
        "by_doc_type": {
            doc_type: {name: _mean(oks) for name, oks in sorted(fields.items())}
            for doc_type, fields in sorted(by_type.items())
        },
        "mean_field_accuracy": _mean(every),
        "failed_documents": [s.document_id for s in scores if not all(s.correct.values())],
    }


def _mean(values: Sequence[bool]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _build_engine(name: str, recording: Path | None) -> Engine:
    if name == "recorded":
        if recording is None:
            msg = "the recorded engine needs --recording"
            raise SystemExit(msg)
        from app.gateway.engines import RecordedEngine

        return RecordedEngine(recording)
    if name == "rapidocr":
        from app.gateway.rapidocr_engine import RapidOcrEngine

        return RapidOcrEngine()
    msg = f"unknown engine {name}"
    raise SystemExit(msg)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=ENGINE_NAMES)
    parser.add_argument("--png-dir", type=Path, default=Path("data/seed/png"))
    parser.add_argument("--out", type=Path, default=Path("evals/ocr/extraction"))
    parser.add_argument("--recording", type=Path, default=None)
    parser.add_argument("--subset", choices=SUBSET_NAMES, default="all")
    args = parser.parse_args(argv)

    engine = _build_engine(args.engine, args.recording)
    docs = list(build_dataset().documents)
    cutoff = Settings(_env_file=None).review_confidence_cutoff
    scores = run_documents(engine, docs, args.png_dir, cutoff)
    summary = summarise(scores, args.engine, args.subset)

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.engine}-{args.subset}"
    (args.out / f"{stem}.summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        json.dumps(
            {
                "document_id": s.document_id,
                "doc_type": s.doc_type,
                "predicted_type": s.predicted_type,
                "type_ok": s.type_ok,
                "correct": {f"{n}|{subj or ''}": ok for (n, subj), ok in s.correct.items()},
            },
            sort_keys=True,
        )
        for s in scores
    ]
    (args.out / f"{stem}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write(
        f"{args.engine} {args.subset}: mean field accuracy {summary['mean_field_accuracy']}, "
        f"type accuracy {summary['type_accuracy']}, read errors {summary['read_errors']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
