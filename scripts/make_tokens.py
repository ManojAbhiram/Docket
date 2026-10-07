#!/usr/bin/env python3
"""Write docs/design/tokens.json from the palette below (deep teal).

The hex values here are the source. The oklch strings are computed from them, so the two cannot
disagree. Roles reference primitives ("neutral.900"), the way the schema asks. Run from the
repository root:

    python3 scripts/make_tokens.py

Then check contrast: python3 <design-system>/scripts/contrast.py --tokens docs/design/tokens.json
and keep frontend/src/index.css in step by hand (shadcn's names, written from these roles).
"""

import json
import math
import sys
from pathlib import Path

PRIMITIVES: dict[str, dict[str, str]] = {
    "neutral": {
        "0": "#ffffff", "50": "#f2f7f6", "100": "#e4efed", "200": "#d3e4e1", "300": "#9db8b4",
        "400": "#6f8a86", "500": "#5a7773", "600": "#3f5a56", "700": "#1f3a37", "750": "#234341",
        "800": "#172c2a", "850": "#112321", "900": "#0f1f1e", "950": "#0b1514", "1000": "#070f0e",
    },
    "accent": {
        "0": "#f0fdfa", "100": "#d6ebe8", "200": "#99e6dc", "300": "#5eead4", "400": "#2dd4bf",
        "500": "#14a090", "600": "#0f766e", "700": "#115e59", "800": "#134e4a", "900": "#0d3b38",
        "1000": "#0a2a28",
    },
    "success": {
        "0": "#f1f8f3", "100": "#e3f1e8", "200": "#b6e0c6", "300": "#6fcf97", "400": "#4db77f",
        "500": "#2f9a5d", "600": "#1e6b3a", "700": "#1a5632", "800": "#1a4128", "900": "#17301f",
        "1000": "#0f2015",
    },
    "warning": {
        "0": "#fdf7ea", "100": "#fbeed6", "200": "#f6d9a0", "300": "#f0b44c", "400": "#de9722",
        "500": "#b87510", "550": "#b45309", "600": "#8a5300", "650": "#92400e", "700": "#6f4300", "800": "#553400", "900": "#3a2c10",
        "1000": "#261c0a",
    },
    "danger": {
        "0": "#fdf3f2", "100": "#fbe3e1", "200": "#f6b9b4", "300": "#f0857d", "400": "#d9534a",
        "500": "#c63a31", "600": "#b3261e", "700": "#8f1e18", "800": "#6f1812", "900": "#3a1815",
        "1000": "#260f0d",
    },
}  # fmt: skip

LIGHT = {
    "bg": "neutral.50", "bg-subtle": "neutral.100", "surface": "neutral.0",
    "surface-raised": "neutral.0", "overlay": "neutral.0",
    "text": "neutral.900", "text-muted": "neutral.600", "text-disabled": "neutral.400",
    "link": "accent.600", "border": "neutral.200", "border-strong": "neutral.400",
    "accent": "accent.600", "accent-hover": "accent.700", "accent-active": "accent.800",
    "on-accent": "neutral.0", "accent-subtle": "accent.100",
    "success": "success.600", "on-success": "neutral.0", "success-subtle": "success.100",
    "warning": "warning.600", "on-warning": "neutral.0", "warning-subtle": "warning.100",
    "danger": "danger.600", "on-danger": "neutral.0", "danger-subtle": "danger.100",
    "info": "neutral.600", "on-info": "neutral.0", "info-subtle": "neutral.100",
    "focus": "accent.600", "selection": "accent.100",
    "tile": "accent.600", "tile-deep": "accent.800", "tile-warn": "warning.550",
    "on-tile": "neutral.0", "header": "accent.800", "on-header": "neutral.0",
}  # fmt: skip

DARK = {
    "bg": "neutral.950", "bg-subtle": "neutral.800", "surface": "neutral.850",
    "surface-raised": "neutral.800", "overlay": "neutral.750",
    "text": "neutral.100", "text-muted": "neutral.300", "text-disabled": "neutral.500",
    "link": "accent.400", "border": "neutral.700", "border-strong": "neutral.500",
    "accent": "accent.400", "accent-hover": "accent.300", "accent-active": "accent.200",
    "on-accent": "neutral.950", "accent-subtle": "neutral.750",
    "success": "success.300", "on-success": "neutral.950", "success-subtle": "success.900",
    "warning": "warning.300", "on-warning": "neutral.950", "warning-subtle": "warning.900",
    "danger": "danger.300", "on-danger": "neutral.950", "danger-subtle": "danger.900",
    "info": "neutral.300", "on-info": "neutral.950", "info-subtle": "neutral.750",
    "focus": "accent.400", "selection": "accent.800",
    "tile": "accent.700", "tile-deep": "accent.900", "tile-warn": "warning.650",
    "on-tile": "neutral.0", "header": "accent.900", "on-header": "neutral.100",
}  # fmt: skip


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def oklch(hex_colour: str) -> str:
    """The oklch() form of a #rrggbb colour (Ottosson's OKLab matrices)."""
    r, g, b = (_linear(int(hex_colour[i : i + 2], 16) / 255) for i in (1, 3, 5))
    long = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    medium = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    short = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short
    green_red = 1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short
    blue_yellow = 0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short
    chroma = math.hypot(green_red, blue_yellow)
    hue = math.degrees(math.atan2(blue_yellow, green_red)) % 360
    return f"oklch({lightness:.3f} {chroma:.3f} {hue:.1f})"


def tokens() -> dict[str, object]:
    primitives = {
        scale: {step: {"oklch": oklch(value), "hex": value} for step, value in steps.items()}
        for scale, steps in PRIMITIVES.items()
    }
    return {
        "meta": {
            "name": "Docket",
            "version": 1,
            "source": "NOTASK-9 deep teal redesign, on the instrument panel structure",
            "memorable": "The document and the application side by side, and the wrong field "
            "obvious in seconds, in a calm deep teal.",
        },
        "color": {"primitives": primitives, "roles": {"light": LIGHT, "dark": DARK}},
        "font": {
            "families": {
                "display": '"IBM Plex Sans Condensed", "Arial Narrow", sans-serif',
                "body": '"IBM Plex Sans", system-ui, sans-serif',
                "mono": '"IBM Plex Mono", ui-monospace, monospace',
                "tenantDisplayFaces": [],
            },
            "sizes": {"label": 14, "body": 16, "title": 20, "display": 25},
            "weights": {"regular": 400, "emphasis": 600},
            "lineHeights": {"tight": 1.15, "body": 1.5},
            "letterSpacing": {"normal": "0em", "caps": "0.06em"},
            "roles": {
                "display": _role("display", "display", "emphasis", "tight"),
                "title": _role("display", "title", "emphasis", "tight"),
                "body": _role("body", "body", "regular", "body"),
                "label": _role("body", "label", "emphasis", "body"),
                "code": _role("mono", "label", "regular", "body"),
            },
        },
        "space": {
            "base": 8,
            "half": 4,
            "scale": {"0": 0, "1": 4, "2": 8, "3": 16, "4": 24, "5": 32, "6": 48, "7": 64},
        },
        "radius": {"control": 4, "container": 6, "overlay": 8, "full": 9999},
        "elevation": {
            "rule": "Elevation above 0 means the element is pressable or it overlays the page. "
            "A static block never carries a shadow.",
            "levels": {
                "0": {"light": "none", "dark": "none"},
                "1": {
                    "light": "0 1px 2px rgb(15 31 30 / 0.12)",
                    "dark": "0 1px 2px rgb(0 0 0 / 0.4)",
                },
                "2": {
                    "light": "0 2px 6px rgb(15 31 30 / 0.16)",
                    "dark": "0 2px 6px rgb(0 0 0 / 0.5)",
                },
                "3": {
                    "light": "0 8px 24px rgb(15 31 30 / 0.2)",
                    "dark": "0 8px 24px rgb(0 0 0 / 0.6)",
                },
            },
        },
        "motion": {
            "duration": {"instant": 80, "fast": 150, "base": 240, "slow": 400, "deliberate": 700},
            "easing": {
                "standard": "cubic-bezier(0.2, 0, 0, 1)",
                "enter": "cubic-bezier(0.2, 0.8, 0.2, 1)",
                "exit": "cubic-bezier(0.4, 0, 1, 1)",
                "spring": {"stiffness": 300, "damping": 30, "mass": 1},
            },
            "stagger": 40,
            "staggerSteps": 8,
            "rise": 8,
            "lift": 2,
        },
        "breakpoint": {"sm": 640, "md": 768, "lg": 1024, "xl": 1440},
        "z": {"base": 0, "raised": 10, "sticky": 20, "overlay": 30, "modal": 40, "toast": 50},
        "focus": {"width": 2, "offset": 2, "role": "focus"},
    }


def _role(family: str, size: str, weight: str, line_height: str) -> dict[str, str]:
    tracking = "normal"
    return {
        "family": family,
        "size": size,
        "weight": weight,
        "lineHeight": line_height,
        "tracking": tracking,
    }


def main() -> int:
    target = Path("docs/design/tokens.json")
    target.write_text(json.dumps(tokens(), indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"make_tokens: wrote {target}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
