import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { allScreens } from "./registry";

afterEach(cleanup);

describe("design gallery screens", () => {
  const screens = allScreens();

  it("has every Docket screen in the inventory", () => {
    const ids = screens.map((spec) => spec.id);

    for (const id of ["S-01", "S-02", "S-03", "S-04", "S-05", "S-06", "S-07", "S-08", "S-09"]) {
      expect(ids).toContain(id);
    }
  });

  for (const spec of screens) {
    for (const [state, renderState] of Object.entries(spec.states)) {
      it(`${spec.id} ${spec.name}: ${state} renders something`, () => {
        render(<>{renderState()}</>);

        expect(document.body.textContent).toMatch(/\S/);
      });
    }
  }
});
