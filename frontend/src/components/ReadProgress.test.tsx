import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReadProgress } from "@/components/ReadProgress";

describe("ReadProgress", () => {
  it("has no value while reading, and says Reading", () => {
    render(<ReadProgress state="reading" label="Reading marksheet.png" />);

    const bar = screen.getByRole("progressbar", { name: "Reading marksheet.png" });
    expect(bar).toHaveAttribute("aria-valuetext", "Reading");
    expect(bar).not.toHaveAttribute("aria-valuenow");
  });

  it("is full once read", () => {
    render(<ReadProgress state="done" label="marksheet.png" />);

    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "100");
    expect(bar).toHaveAttribute("aria-valuetext", "Read");
  });

  it("marks the fill with its state so the stylesheet can animate it", () => {
    const { container } = render(<ReadProgress state="reading" label="a.png" />);

    expect(container.querySelector("[data-state='reading']")).toHaveClass("read-fill");
  });

  it("shows a failed read as a full bar in the error colour", () => {
    const { container } = render(<ReadProgress state="failed" label="a.png" />);

    expect(container.querySelector("[data-state='failed']")).toHaveClass("bg-destructive");
  });
});
