import { describe, expect, it } from "vitest";

import { mainWidthClass } from "@/app/layout";

// Regression: ISSUE-002 [NOTASK-2], found by /qa on 2026-10-07. The compare table was clipped at
// 1536 px because every screen shared the 1024 px column.
describe("mainWidthClass", () => {
  it("gives the compare screen the wide column", () => {
    expect(mainWidthClass("/applications/f8a88257-1665-4f7f-8809-d2a02e75364c")).toBe("max-w-7xl");
  });

  it("keeps the narrow column for the list, the upload screen and the rest", () => {
    expect(mainWidthClass("/applications")).toBe("max-w-5xl");
    expect(mainWidthClass("/applications/f8a88257-1665-4f7f-8809-d2a02e75364c/upload")).toBe(
      "max-w-5xl",
    );
    expect(mainWidthClass("/queue")).toBe("max-w-5xl");
  });
});
