import { describe, expect, it } from "vitest";

import { countFrame, easeOut, parseDuration } from "./motion";

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
