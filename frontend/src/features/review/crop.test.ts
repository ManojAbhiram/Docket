import { describe, expect, it } from "vitest";

import { CROP_ASPECT, cropRect } from "@/features/review/crop";

const PAGE = { width: 1000, height: 1400 };

describe("cropRect", () => {
  it("is centred on the field, with room around it", () => {
    const rect = cropRect([400, 500, 120, 30], PAGE);

    expect(rect.x + rect.width / 2).toBeCloseTo(460);
    expect(rect.y + rect.height / 2).toBeCloseTo(515);
    expect(rect.width).toBeGreaterThan(120);
  });

  it("always has the shape of the slot it is drawn into", () => {
    const rect = cropRect([400, 500, 120, 30], PAGE);

    expect(rect.width / rect.height).toBeCloseTo(CROP_ASPECT);
  });

  it("is wide enough for a long field and tall enough for a tall one", () => {
    const wide = cropRect([100, 100, 600, 20], PAGE);
    const tall = cropRect([100, 100, 40, 200], PAGE);

    expect(wide.width).toBeGreaterThanOrEqual(600);
    expect(tall.height).toBeGreaterThanOrEqual(200);
  });

  it("stays inside the page when the field is at an edge", () => {
    const corner = cropRect([0, 0, 80, 24], PAGE);
    const far = cropRect([960, 1380, 40, 20], PAGE);

    expect(corner.x).toBeGreaterThanOrEqual(0);
    expect(corner.y).toBeGreaterThanOrEqual(0);
    expect(far.x + far.width).toBeLessThanOrEqual(PAGE.width);
    expect(far.y + far.height).toBeLessThanOrEqual(PAGE.height);
  });

  it("shrinks to the page rather than leave it when the field is wider than the page", () => {
    const rect = cropRect([0, 0, 1200, 30], PAGE);

    expect(rect.width).toBeLessThanOrEqual(PAGE.width);
    expect(rect.x).toBeGreaterThanOrEqual(0);
  });
});
