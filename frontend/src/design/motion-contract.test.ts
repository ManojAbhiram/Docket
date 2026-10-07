import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * The motion rules in docs/design/motion.md that a stylesheet can break: only transform and opacity
 * move, colour may fade, and a reduced-motion request ends every animation and transition at once.
 * This reads the stylesheet and the screens' class names and never writes anything.
 */
const root = resolve(process.cwd(), "src");
const css = readFileSync(resolve(root, "index.css"), "utf-8");

const MOVING = new Set(["transform", "opacity"]);
const FADING = new Set([...MOVING, "color", "background-color", "border-color"]);

function keyframeBlocks(source: string): { name: string; body: string }[] {
  const blocks: { name: string; body: string }[] = [];
  for (const match of source.matchAll(/@keyframes\s+([\w-]+)\s*{/g)) {
    const start = match.index + match[0].length;
    let depth = 1;
    let end = start;
    while (depth > 0 && end < source.length) {
      depth += source[end] === "{" ? 1 : source[end] === "}" ? -1 : 0;
      end += 1;
    }
    blocks.push({ name: match[1] ?? "", body: source.slice(start, end - 1) });
  }
  return blocks;
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      return sourceFiles(path);
    }
    return path.endsWith(".tsx") && !path.endsWith(".test.tsx") ? [path] : [];
  });
}

describe("motion contract", () => {
  it("animates only transform and opacity in every keyframe", () => {
    const offenders: string[] = [];
    for (const { name, body } of keyframeBlocks(css)) {
      for (const property of body.matchAll(/([a-z-]+)\s*:/g)) {
        const word = property[1] ?? "";
        if (!MOVING.has(word)) {
          offenders.push(`${name}: ${word}`);
        }
      }
    }

    expect(keyframeBlocks(css).length).toBeGreaterThanOrEqual(4);
    expect(offenders).toEqual([]);
  });

  it("transitions only transform, opacity and colour in the stylesheet", () => {
    const offenders: string[] = [];
    for (const match of css.matchAll(/transition(?:-property)?\s*:\s*([^;]+);/g)) {
      const first = (match[1] ?? "").split(",").map((part) => part.trim().split(/\s+/)[0] ?? "");
      for (const property of first) {
        if (!FADING.has(property) && !/^(var|0)/.test(property) && !/^\d/.test(property)) {
          offenders.push(property);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("never transitions layout in the screens and shared components", () => {
    const offenders = sourceFiles(root)
      .filter((path) => !path.includes(join("components", "ui")))
      .filter((path) =>
        /transition-all|transition-\[[^\]]*(width|height|margin|padding|left|right|top|bottom)/.test(
          readFileSync(path, "utf-8"),
        ),
      )
      .map((path) => path.replace(root, "src"));

    expect(offenders).toEqual([]);
  });

  it("ends every animation and transition at once under reduced motion", () => {
    const reduced = css.slice(css.indexOf("@media (prefers-reduced-motion: reduce)"));

    expect(reduced).toMatch(/animation-duration:\s*0\.01ms\s*!important/);
    expect(reduced).toMatch(/animation-delay:\s*0s\s*!important/);
    expect(reduced).toMatch(/transition-duration:\s*0\.01ms\s*!important/);
    expect(reduced).toMatch(/transition-delay:\s*0s\s*!important/);
    expect(reduced).toMatch(
      /\.lift:hover,\s*button:not\(:disabled\):active\s*{\s*transform:\s*none/,
    );
  });

  it("fills entrance animations backwards so a finished one never holds a hover transform", () => {
    const entrances = [
      ...css.matchAll(/^\.(?:enter|enter-quiet|route-enter|badge-changed)\s*{[^}]*}/gm),
    ];

    expect(entrances.length).toBe(4);
    expect(entrances.every((block) => /\bbackwards;/.test(block[0]))).toBe(true);
  });
});
