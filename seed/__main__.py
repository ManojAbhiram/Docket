"""Write the synthetic dataset: `python -m seed [--out data/seed] [--png]`.

Always writes applications.csv, labels.json and one HTML page per document.
`--png` also renders the noisy PNGs, which needs playwright and pillow.
"""

import argparse
import sys
from pathlib import Path

from seed.dataset import applications_csv, build_dataset, labels_json
from seed.pages import render_html


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m seed", description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/seed"))
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--png", action="store_true", help="render noisy PNGs (needs playwright)")
    args = parser.parse_args()

    dataset = build_dataset(args.seed)
    out: Path = args.out
    html_dir = out / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    (out / "applications.csv").write_text(applications_csv(dataset), encoding="utf-8")
    (out / "labels.json").write_text(labels_json(dataset), encoding="utf-8")
    apps = {app.application_id: app for app in dataset.applications}
    for doc in dataset.documents:
        page = render_html(doc, apps[doc.application_id])
        (html_dir / f"{doc.application_id}_{doc.doc_type}.html").write_text(page, encoding="utf-8")
    summary = f"{len(dataset.applications)} applications, {len(dataset.documents)} documents"

    if args.png:
        from seed.render import render_all

        render_all(dataset, out / "png")
        summary += ", PNGs rendered"
    sys.stdout.write(f"seed: {summary} in {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
