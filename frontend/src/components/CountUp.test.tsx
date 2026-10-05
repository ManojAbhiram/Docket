import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CountUp } from "./CountUp";

const grouping = new Intl.NumberFormat("en-IN");
const format = (value: number) => grouping.format(value);

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CountUp", () => {
  it("shows the final figure at once when the person asked for less motion", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );

    render(<CountUp value={3812} format={format} />);

    expect(screen.getByText("3,812")).toBeInTheDocument();
  });

  it("shows the final figure with no animation frame when the duration token is zero", () => {
    render(<CountUp value={611} format={format} />);

    expect(screen.getByText("611")).toBeInTheDocument();
  });

  it("holds the figure once in the text, with no live region around it", () => {
    const { container } = render(<CountUp value={37} format={format} />);

    expect(container.querySelector("[aria-live]")).toBeNull();
    expect(container.textContent).toBe("37");
  });
});
