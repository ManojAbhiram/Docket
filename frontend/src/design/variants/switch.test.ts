import { afterEach, describe, expect, it } from "vitest";

import { applyVariantFromUrl } from "./switch";

afterEach(() => {
  delete document.documentElement.dataset.variant;
});

describe("applyVariantFromUrl", () => {
  it("sets the direction named in the query string", async () => {
    await applyVariantFromUrl("?variant=3-ledger");

    expect(document.documentElement.dataset.variant).toBe("3-ledger");
  });

  it("ignores a name that is not a direction file", async () => {
    await applyVariantFromUrl("?variant=../../secret");

    expect(document.documentElement.dataset.variant).toBeUndefined();
  });

  it("does nothing without a variant in the query string", async () => {
    await applyVariantFromUrl("");

    expect(document.documentElement.dataset.variant).toBeUndefined();
  });
});
