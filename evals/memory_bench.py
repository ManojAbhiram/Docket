"""Sample Linux RSS for the configured API and its real OCR child on the labelled pages.

This constructs the API and sign-in state without connecting to a database. RSS sums shared
pages, so it is conservative, but excludes the gunicorn supervisor and simultaneous requests.
"""

import argparse
import gc
import json
import os
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path


def tree_rss(pid: int) -> int:
    """Sum resident bytes for a Linux process and all of its children."""
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        own = next(
            int(row.split()[1]) * 1024 for row in status.splitlines() if row.startswith("VmRSS:")
        )
        children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        return own + sum(tree_rss(int(child)) for child in children)
    except OSError, StopIteration:
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Read each labelled page and write observed RSS and words for comparison."""
    from app.core.config import Settings
    from app.gateway.process import ProcessEngine
    from app.gateway.rapidocr_engine import make_engine
    from app.main import _start_sign_in, create_app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--png-dir", type=Path, default=Path("data/seed/png"))
    args = parser.parse_args(argv)
    paths = sorted(args.png_dir.glob("*.png"))
    if not paths:
        parser.error("no PNG pages found")
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+asyncpg://postgres:postgres@localhost/test",
    )
    app = create_app(settings)
    _start_sign_in(app, settings)
    samples: list[int] = [tree_rss(os.getpid())]
    stop = threading.Event()

    def sample() -> None:
        while not stop.wait(0.02):
            samples.append(tree_rss(os.getpid()))

    thread = threading.Thread(target=sample)
    thread.start()
    engine = ProcessEngine(
        make_engine,
        name="rapidocr",
        read_timeout=settings.read_timeout_seconds,
        recycle_after=settings.engine_recycle_after,
    )
    readings: list[dict[str, object]] = []
    started = time.monotonic()
    try:
        for path in paths:
            words = engine.read(path.read_bytes()).words
            gc.collect()
            readings.append(
                {
                    "file": path.name,
                    "rss_bytes": tree_rss(os.getpid()),
                    "words": [asdict(word) for word in words],
                }
            )
    finally:
        engine.close()
        stop.set()
        thread.join()
    result = {
        "peak_bytes": max(samples),
        "elapsed_seconds": time.monotonic() - started,
        "pages": len(readings),
        "readings": readings,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    sys.stdout.write(
        json.dumps({key: value for key, value in result.items() if key != "readings"}) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
