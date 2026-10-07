import { beforeEach, describe, expect, it } from "vitest";

import { countDecision, decidedThisSitting, resetSitting } from "@/features/review/sitting";

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("the decisions made in this sitting", () => {
  it("starts at zero", () => {
    expect(decidedThisSitting()).toBe(0);
  });

  it("counts each decision", () => {
    countDecision();
    countDecision();

    expect(decidedThisSitting()).toBe(2);
  });

  it("starts again after a reset, for the next person to sign in", () => {
    countDecision();

    resetSitting();

    expect(decidedThisSitting()).toBe(0);
  });

  it("ignores a stored value that is not a count", () => {
    window.sessionStorage.setItem("docket-decided", "many");

    expect(decidedThisSitting()).toBe(0);
  });
});
