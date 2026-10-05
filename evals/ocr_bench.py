"""Measure one OCR engine on the synthetic set, with or without preprocessing.

One engine per process, so the peak-RSS figure belongs to that engine:

    uv run python -m seed && bash data/seed/render-clean.sh && uv run python -m seed --noise
    uv run python -m evals.ocr_bench tesseract
    uv run python -m evals.ocr_bench tesseract --preprocess
    uv run python -m evals.ocr_bench rapidocr --devanagari --preprocess

`scripts/run-ocr-benchmark.sh` runs every shortlisted engine both ways and then
`python -m evals.report` writes docs/research/ocr-benchmark.md.

Writes `evals/ocr/results/<variant>.jsonl` (one line per document, failures included)
and `<variant>.summary.json`. An engine error on a page is recorded and counts as every
field missed, so a crash never makes an engine look better.

Measures: field accuracy per field type (presence in the OCR text, an upper bound on
extraction), CER (see `evals.scoring.field_cer`), seconds per page (preprocessing
included, and reported separately), and peak RSS of this process and its children.
Only Tesseract and RapidOCR calls follow documented usage; the PaddleOCR and docTR
adapters follow their READMEs from memory and are unverified until they run here.
"""

import argparse
import json
import resource
import sys
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from evals.preprocess import preprocess
from evals.scoring import (
    FieldScore,
    accuracy_by_field,
    all_fields_found,
    field_cer,
    score_document,
)
from seed.dataset import build_dataset

type Image = npt.NDArray[np.uint8]
type Recognise = Callable[[Image], tuple[str, float | None]]

ENGINES = ("tesseract", "rapidocr", "paddleocr", "doctr")


def make_tesseract(lang: str, psm: int) -> Recognise:
    import pytesseract
    from pytesseract import Output

    def recognise(image: Image) -> tuple[str, float | None]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(
            rgb, lang=lang, config=f"--psm {psm}", output_type=Output.DICT
        )
        words = [
            (w, float(c)) for w, c in zip(data["text"], data["conf"], strict=True) if w.strip()
        ]
        confidences = [c for _, c in words if c >= 0]
        mean = sum(confidences) / len(confidences) / 100 if confidences else None
        return " ".join(w for w, _ in words), mean

    return recognise


def make_rapidocr(devanagari: bool) -> Recognise:
    from rapidocr import RapidOCR

    params: dict[str, object] = {}
    if devanagari:
        try:
            from rapidocr import LangRec, OCRVersion
        except ImportError as exc:
            msg = (
                "this RapidOCR version does not export LangRec and OCRVersion; the Devanagari "
                "setting is unverified, check the model list and config.yaml in the RapidOCR docs"
            )
            raise SystemExit(msg) from exc
        params = {"Rec.lang_type": LangRec.DEVANAGARI, "Rec.ocr_version": OCRVersion.PPOCRV5}
    engine = RapidOCR(params=params)

    def recognise(image: Image) -> tuple[str, float | None]:
        result = engine(image)
        texts = list(result.txts or ())
        scores = [float(s) for s in (result.scores or ())]
        return "\n".join(texts), (sum(scores) / len(scores) if scores else None)

    return recognise


def make_paddleocr(devanagari: bool) -> Recognise:
    from paddleocr import PaddleOCR

    engine = PaddleOCR(
        lang="devanagari" if devanagari else "en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    def recognise(image: Image) -> tuple[str, float | None]:
        texts: list[str] = []
        scores: list[float] = []
        for page in engine.predict(image):
            texts.extend(str(t) for t in page["rec_texts"])
            scores.extend(float(s) for s in page["rec_scores"])
        return "\n".join(texts), (sum(scores) / len(scores) if scores else None)

    return recognise


def make_doctr() -> Recognise:
    from doctr.models import ocr_predictor

    model = ocr_predictor(pretrained=True)

    def recognise(image: Image) -> tuple[str, float | None]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        exported = model([rgb]).export()
        words = [
            word
            for page in exported["pages"]
            for block in page["blocks"]
            for line in block["lines"]
            for word in line["words"]
        ]
        scores = [float(w["confidence"]) for w in words]
        text = " ".join(str(w["value"]) for w in words)
        return text, (sum(scores) / len(scores) if scores else None)

    return recognise


def build_engine(name: str, devanagari: bool, tesseract_lang: str, psm: int) -> Recognise:
    if name == "tesseract":
        return make_tesseract(tesseract_lang, psm)
    if name == "rapidocr":
        return make_rapidocr(devanagari)
    if name == "paddleocr":
        return make_paddleocr(devanagari)
    return make_doctr()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.ocr_bench", description=__doc__)
    parser.add_argument("engine", choices=ENGINES)
    parser.add_argument("--png-dir", type=Path, default=Path("data/seed/png"))
    parser.add_argument("--out", type=Path, default=Path("evals/ocr/results"))
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--limit", type=int, default=0, help="only the first N documents")
    parser.add_argument("--max-side", type=int, default=0, help="cap the longest image side")
    parser.add_argument("--preprocess", action="store_true", help="flatten light and deskew first")
    parser.add_argument("--devanagari", action="store_true", help="rapidocr and paddleocr")
    parser.add_argument("--tesseract-lang", default="hin+eng")
    parser.add_argument("--tesseract-psm", type=int, default=6, help="page segmentation mode")
    args = parser.parse_args()

    variant = args.engine + ("-devanagari" if args.devanagari else "")
    if args.engine == "tesseract":
        variant += f"-{args.tesseract_lang.replace('+', '_')}-psm{args.tesseract_psm}"
    variant += "-preprocessed" if args.preprocess else "-raw"
    if args.max_side:
        variant += f"-side{args.max_side}"
    if args.png_dir.name != "png":
        variant += f"-{args.png_dir.name}"
    recognise = build_engine(args.engine, args.devanagari, args.tesseract_lang, args.tesseract_psm)
    documents = build_dataset(args.seed).documents
    if args.limit:
        documents = documents[: args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    per_document = []
    seconds: list[float] = []
    prep_seconds: list[float] = []
    cers: list[float] = []
    errors = 0
    found_conf: list[float] = []
    missed_conf: list[float] = []
    lines: list[str] = []
    for doc in documents:
        image = _load(args.png_dir / doc.file_name, args.max_side)
        started = time.perf_counter()
        if args.preprocess:
            image = preprocess(image)
        prepared = time.perf_counter()
        error = ""
        text, confidence = "", None
        try:
            text, confidence = recognise(image)
        except Exception as exc:
            # a failing page is a result, not a crash: it scores as every field missed
            error = f"{type(exc).__name__}: {exc}"
            errors += 1
        finished = time.perf_counter()
        scores = score_document(doc, text)
        cer = field_cer(doc, text)
        per_document.append(scores)
        cers.append(cer)
        seconds.append(finished - started)
        prep_seconds.append(prepared - started)
        if confidence is not None:
            (found_conf if all_fields_found(scores) else missed_conf).append(confidence)
        lines.append(
            json.dumps(
                {
                    "id": doc.document_id,
                    "doc_type": doc.doc_type,
                    "mismatch_field": doc.mismatch_field,
                    "noise": {
                        "blur": doc.noise.blur_radius,
                        "skew": doc.noise.skew_degrees,
                        "shadow": doc.noise.shadow_strength,
                        "low_light": doc.noise.low_light,
                    },
                    "seconds": round(finished - started, 4),
                    "cer": round(cer, 4),
                    "confidence": confidence,
                    "hits": {k: [s.hits, s.total] for k, s in scores.items()},
                    "error": error,
                },
                sort_keys=True,
            )
        )

    summary = _summary(args, variant, seconds, prep_seconds, cers, errors, per_document)
    summary["mean_confidence_docs_all_found"] = _mean(found_conf)
    summary["mean_confidence_docs_with_a_miss"] = _mean(missed_conf)
    (args.out / f"{variant}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out / f"{variant}.summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


def _load(path: Path, max_side: int) -> Image:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        msg = f"cannot read {path} (run the seed pipeline first)"
        raise FileNotFoundError(msg)
    if max_side and max(image.shape[:2]) > max_side:
        scale = max_side / max(image.shape[:2])
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return np.asarray(image, dtype=np.uint8)


def _summary(
    args: argparse.Namespace,
    variant: str,
    seconds: list[float],
    prep_seconds: list[float],
    cers: list[float],
    errors: int,
    per_document: list[dict[str, FieldScore]],
) -> dict[str, object]:
    ordered = sorted(seconds)
    to_mb = 1 / 1024  # ru_maxrss is in KiB on Linux
    self_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * to_mb
    child_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * to_mb
    return {
        "variant": variant,
        "engine": args.engine,
        "devanagari": args.devanagari,
        "preprocess": args.preprocess,
        "max_side": args.max_side,
        "documents": len(seconds),
        "errors": errors,
        "peak_rss_mb": round(max(self_mb, child_mb), 1),
        "peak_rss_mb_self": round(self_mb, 1),
        "peak_rss_mb_children": round(child_mb, 1),
        "seconds_per_page_mean": round(sum(seconds) / len(seconds), 3),
        "seconds_per_page_p50": round(ordered[len(ordered) // 2], 3),
        "seconds_per_page_p95": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        "preprocess_seconds_mean": round(sum(prep_seconds) / len(prep_seconds), 4),
        "cer_mean": round(sum(cers) / len(cers), 4),
        "field_accuracy": {k: round(v, 3) for k, v in accuracy_by_field(per_document).items()},
        "docs_with_all_fields_found": sum(all_fields_found(s) for s in per_document),
    }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


if __name__ == "__main__":
    raise SystemExit(main())
