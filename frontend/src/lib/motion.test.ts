import { afterEach, describe, expect, it, vi } from "vitest";

import {
  STAGGER_STEPS,
  countFrame,
  easeOut,
  parseDuration,
  prefersReducedMotion,
  staggerDelay,
  staggerStep,
  staggerStyle,
} from "./motion";

describe("parseDuration", () => {
  it("reads milliseconds and seconds with their unit", () => {
    expect(parseDuration("240ms")).toBe(240);
    expect(parseDuration(" 0.24s")).toBe(240);
    expect(parseDuration("0s")).toBe(0);
  });

  it("reads anything it does not understand as no motion", () => {
    expect(parseDuration("")).toBe(0);
    expect(parseDuration("fast")).toBe(0);
  });
});

describe("countFrame", () => {
  it("ends on exactly the real value", () => {
    expect(countFrame(0, 3812, 1)).toBe(3812);
    expect(countFrame(0, 3812, 1.4)).toBe(3812);
  });

  it("shows whole numbers between the start and the end", () => {
    const frame = countFrame(0, 3812, 0.4);

    expect(Number.isInteger(frame)).toBe(true);
    expect(frame).toBeGreaterThan(0);
    expect(frame).toBeLessThan(3812);
  });

  it("starts from zero when there was no earlier value", () => {
    expect(countFrame(null, 100, 0)).toBe(0);
  });

  it("counts down as well as up", () => {
    expect(countFrame(611, 600, 0.5)).toBeLessThan(611);
    expect(countFrame(611, 600, 0.5)).toBeGreaterThanOrEqual(600);
  });
});

describe("easeOut", () => {
  it("runs from 0 to 1 and never leaves that range", () => {
    expect(easeOut(-1)).toBe(0);
    expect(easeOut(0)).toBe(0);
    expect(easeOut(2)).toBe(1);
  });
});

describe("staggerStep and staggerStyle", () => {
  it("caps the wave so a long list never cascades slowly", () => {
    expect(staggerStep(0)).toBe(0);
    expect(staggerStep(3)).toBe(3);
    expect(staggerStep(500)).toBe(STAGGER_STEPS);
  });

  it("treats a negative, fractional or missing index as a safe step", () => {
    expect(staggerStep(-4)).toBe(0);
    expect(staggerStep(2.9)).toBe(2);
    expect(staggerStep(Number.NaN)).toBe(0);
  });

  it("hands the step to the stylesheet as --i", () => {
    expect(staggerStyle(2)).toEqual({ "--i": 2 });
  });
});

describe("staggerDelay", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.style.removeProperty("--stagger");
  });

  it("multiplies the step by the stagger token", () => {
    document.documentElement.style.setProperty("--stagger", "40ms");

    expect(staggerDelay(3)).toBe(120);
  });

  it("is zero when the person asked for less motion", () => {
    document.documentElement.style.setProperty("--stagger", "40ms");
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));

    expect(prefersReducedMotion()).toBe(true);
    expect(staggerDelay(3)).toBe(0);
  });
});
