import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * The colour roles in src/index.css, both themes, against WCAG. Text pairs need 4.5:1, a focus ring
 * and a field edge need 3:1. This reads the stylesheet and never writes anything.
 */
const css = readFileSync(resolve(process.cwd(), "src/index.css"), "utf-8");

const TEXT_PAIRS: [string, string][] = [
  ["foreground", "background"],
  ["foreground", "card"],
  ["card-foreground", "card"],
  ["popover-foreground", "popover"],
  ["primary-foreground", "primary"],
  ["secondary-foreground", "secondary"],
  ["muted-foreground", "background"],
  ["muted-foreground", "card"],
  ["muted-foreground", "muted"],
  ["accent-foreground", "accent"],
  ["destructive-foreground", "destructive"],
  ["success-foreground", "success"],
  ["warning-foreground", "warning"],
  ["info-foreground", "info"],
  ["sidebar-foreground", "sidebar"],
  ["primary", "background"],
  ["primary", "card"],
  ["destructive", "background"],
  ["destructive", "card"],
  ["success", "card"],
  ["warning", "card"],
  ["info", "card"],
  ["success", "success-subtle"],
  ["warning", "warning-subtle"],
  ["destructive", "danger-subtle"],
  ["info", "info-subtle"],
];
const EDGE_PAIRS: [string, string][] = [
  ["input", "background"],
  ["input", "card"],
  ["ring", "background"],
  ["ring", "card"],
  ["ring", "popover"],
];

function block(source: string, opener: RegExp): Record<string, string> {
  const start = source.search(opener);
  const body = source.slice(source.indexOf("{", start) + 1, source.indexOf("}", start));
  const colours: Record<string, string> = {};
  for (const match of body.matchAll(/--([a-z-]+):\s*(#[0-9a-fA-F]{6});/g)) {
    const [, name, value] = match;
    if (name && value) {
      colours[name] = value;
    }
  }
  return colours;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((index) => {
    const channel = parseInt(hex.slice(index, index + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0);
}

function ratio(a: string, b: string): number {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((high ?? 0) + 0.05) / ((low ?? 0) + 0.05);
}

const themes = {
  light: block(css, /^:root\s*{/m),
  dark: block(css, /^\.dark,\s*\n\[data-theme="dark"\]\s*{/m),
};

describe("colour roles", () => {
  it("reads both themes from the stylesheet", () => {
    expect(Object.keys(themes.light).length).toBeGreaterThan(30);
    expect(Object.keys(themes.dark).length).toBeGreaterThan(30);
  });

  for (const [theme, colours] of Object.entries(themes)) {
    it(`meets 4.5:1 for text and 3:1 for the ring and field edges in the ${theme} theme`, () => {
      const failures: string[] = [];
      let checked = 0;
      for (const [pairs, need] of [
        [TEXT_PAIRS, 4.5],
        [EDGE_PAIRS, 3],
      ] as const) {
        for (const [foreground, background] of pairs) {
          const fg = colours[foreground];
          const bg = colours[background];
          if (!fg || !bg) {
            failures.push(`${foreground} or ${background} is missing`);
            continue;
          }
          checked += 1;
          const value = ratio(fg, bg);
          if (value < need) {
            failures.push(`${foreground} on ${background} is ${value.toFixed(2)}, needs ${need}`);
          }
        }
      }

      expect(checked).toBe(TEXT_PAIRS.length + EDGE_PAIRS.length);
      expect(failures).toEqual([]);
    });
  }
});
