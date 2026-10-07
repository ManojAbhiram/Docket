import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ListRow } from "@/components/ListRow";

function renderRow(props: Parameters<typeof ListRow>[0] = {}) {
  return render(
    <ul>
      <ListRow {...props}>SYN-APP-004</ListRow>
    </ul>,
  );
}

describe("ListRow", () => {
  it("is a list item that holds what it is given", () => {
    renderRow();

    expect(screen.getByRole("listitem")).toHaveTextContent("SYN-APP-004");
  });

  it("marks the row the keyboard cursor is on, for a screen reader and by a drawn marker", () => {
    renderRow({ selected: true });

    const row = screen.getByRole("listitem");
    expect(row).toHaveAttribute("aria-current", "true");
    expect(row.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });

  it("marks nothing on a row that is not selected", () => {
    renderRow();

    const row = screen.getByRole("listitem");
    expect(row).not.toHaveAttribute("aria-current");
    expect(row.querySelector("svg")).toBeNull();
  });

  it("passes other attributes through to the list item", () => {
    renderRow({ "data-motion": "settle" } as Parameters<typeof ListRow>[0]);

    expect(screen.getByRole("listitem")).toHaveAttribute("data-motion", "settle");
  });
});
