import type { CSSProperties } from "react";

/** Parse a CSS duration such as "240ms", " 0.24s" or "0s" into milliseconds. Anything else is 0. */
export function parseDuration(text: string): number {
  const match = /^\s*(-?\d*\.?\d+)\s*(ms|s)\s*$/.exec(text);
  if (!match) {
    return 0;
  }
  const amount = Number(match[1]);
  return match[2] === "s" ? amount * 1000 : amount;
}

/** A token duration read from the page, in milliseconds. Reduced motion zeroes it in CSS. */
export function tokenDuration(name: string): number {
  return parseDuration(getComputedStyle(document.documentElement).getPropertyValue(name));
}

/** True when the person asked the system for less motion. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Ease out: fast at first, settling at the end. Progress and result are 0 to 1. */
export function easeOut(progress: number): number {
  const clamped = Math.min(Math.max(progress, 0), 1);
  return 1 - (1 - clamped) ** 3;
}

/**
 * The whole number to show at `progress` (0 to 1) of a count from `from` to `to`. The last frame is
 * exactly `to`, and a missing start counts from 0, never from a number that is not there.
 */
export function countFrame(from: number | null, to: number, progress: number): number {
  const start = from ?? 0;
  if (progress >= 1) {
    return to;
  }
  return Math.round(start + (to - start) * easeOut(progress));
}

/** The most steps a stagger adds. A long list enters in one short wave, never a slow cascade. */
export const STAGGER_STEPS = 8;

/** The step (0 to STAGGER_STEPS) a list item at `index` waits before it enters. */
export function staggerStep(index: number): number {
  if (!Number.isFinite(index)) {
    return 0;
  }
  return Math.min(Math.max(Math.trunc(index), 0), STAGGER_STEPS);
}

/**
 * The inline style that places an item in an entrance wave: `--i` is read by `.enter` in index.css
 * as `animation-delay: calc(var(--i) * var(--stagger))`. Reduced motion ends the animation at once
 * in CSS, so this needs no branch.
 */
export function staggerStyle(index: number): CSSProperties {
  return { "--i": staggerStep(index) } as CSSProperties;
}

/** The delay in milliseconds a stagger step adds, from the `--stagger` token. Zero when reduced. */
export function staggerDelay(index: number): number {
  if (prefersReducedMotion()) {
    return 0;
  }
  return staggerStep(index) * tokenDuration("--stagger");
}
