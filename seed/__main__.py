"""Write the synthetic dataset in two steps around a playwright-cli screenshot step.

    uv run python -m seed            # CSV, labels, eval cases, HTML pages, render script
    bash data/seed/render-clean.sh   # playwright-cli: one clean screenshot per page
    uv run python -m seed --noise    # OpenCV photo noise: data/seed/png/*.png

Everything is generated from a fixed seed and is synthetic (REQ-043).
"""

import argparse
import sys
from pathlib import Path

from seed.dataset import Dataset, applications_csv, build_dataset, cases_jsonl, labels_json
from seed.pages import render_html

_VIEWPORT = "800 1100"


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m seed", description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/seed"))
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--noise", action="store_true", help="add OpenCV photo noise to clean/")
    args = parser.parse_args()

    dataset = build_dataset(args.seed)
    out: Path = args.out
    if args.noise:
        from seed.render import render_noisy

        written = render_noisy(dataset, out / "clean", out / "png")
        sys.stdout.write(f"seed: {len(written)} noisy PNGs in {out / 'png'}\n")
        return 0

    write_data(dataset, out)
    sys.stdout.write(
        f"seed: {len(dataset.applications)} applications, {len(dataset.documents)} documents "
        f"in {out}\nnext: bash {out / 'render-clean.sh'}, then python -m seed --noise\n"
    )
    return 0


def write_data(dataset: Dataset, out: Path) -> None:
    """CSV, labels, eval cases, one HTML page per document and the playwright-cli script."""
    html_dir = out / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    (out / "applications.csv").write_text(applications_csv(dataset), encoding="utf-8")
    (out / "labels.json").write_text(labels_json(dataset), encoding="utf-8")
    (out / "cases.jsonl").write_text(cases_jsonl(dataset), encoding="utf-8")
    apps = {app.application_id: app for app in dataset.applications}
    commands: list[str] = []
    for doc in dataset.documents:
        stem = f"{doc.application_id}_{doc.doc_type}"
        page = render_html(doc, apps[doc.application_id])
        (html_dir / f"{stem}.html").write_text(page, encoding="utf-8")
        commands.append(f'$PW goto "file://$PWD/{out}/html/{stem}.html"')
        commands.append(f'$PW screenshot --filename="{out}/clean/{stem}.png"')
    script = [
        "#!/usr/bin/env bash",
        "# Screenshots every synthetic page with playwright-cli. Run from the repository root.",
        "# Needs playwright-cli (npm install -g @playwright/cli@latest),",
        "# or set PW='npx playwright cli' to use a local install.",
        "set -euo pipefail",
        'PW="${PW:-playwright-cli}"',
        f'mkdir -p "{out}/clean"',
        "$PW open",
        f"$PW resize {_VIEWPORT}",
        *commands,
        "$PW close",
        "",
    ]
    (out / "render-clean.sh").write_text("\n".join(script), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
