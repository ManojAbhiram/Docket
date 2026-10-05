#!/usr/bin/env python3
"""Check the colour roles of each Docket design direction against WCAG.

Reads frontend/src/design/variants/*.css (hex colours only), one light and one dark block per file,
and checks text pairs at 4.5:1 and control edges and focus rings at 3:1.

Run from the repository root: python3 docs/design/variants/docket/contrast.py
Exits 1 when any pair fails or when no pair was checked.
"""

import glob
import re
import sys
from pathlib import Path

TEXT_PAIRS = [
    ("foreground", "background"),
    ("foreground", "card"),
    ("card-foreground", "card"),
    ("popover-foreground", "popover"),
    ("primary-foreground", "primary"),
    ("secondary-foreground", "secondary"),
    ("muted-foreground", "background"),
    ("muted-foreground", "card"),
    ("muted-foreground", "muted"),
    ("accent-foreground", "accent"),
    ("destructive", "background"),
    ("destructive", "card"),
    ("primary", "background"),
    ("primary", "card"),
    ("sidebar-foreground", "sidebar"),
    ("sidebar-primary-foreground", "sidebar-primary"),
]
EDGE_PAIRS = [
    ("input", "background"),
    ("input", "card"),
    ("ring", "background"),
    ("ring", "card"),
]


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    high, low = max(la, lb), min(la, lb)
    return (high + 0.05) / (low + 0.05)


def blocks(css: str) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for selector, body in re.findall(r"(:root\[data-variant=[^{]+)\{([^}]*)\}", css):
        if "--background" not in body:
            continue
        theme = "dark" if ".dark" in selector else "light"
        found[theme] = dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6});", body))
    return found


def main() -> int:
    checked = failed = 0
    for path in sorted(glob.glob("frontend/src/design/variants/*.css")):
        for theme, colours in blocks(Path(path).read_text(encoding="utf-8")).items():
            for pairs, need in ((TEXT_PAIRS, 4.5), (EDGE_PAIRS, 3.0)):
                for fg, bg in pairs:
                    if fg not in colours or bg not in colours:
                        continue
                    value = ratio(colours[fg], colours[bg])
                    checked += 1
                    if value < need:
                        failed += 1
                        sys.stdout.write(
                            f"FAIL {path} {theme}: {fg} on {bg} is {value:.2f}, needs {need}\n"
                        )
    sys.stdout.write(f"contrast: {checked} pairs checked, {failed} below the ratio\n")
    return 1 if failed or not checked else 0


if __name__ == "__main__":
    sys.exit(main())
