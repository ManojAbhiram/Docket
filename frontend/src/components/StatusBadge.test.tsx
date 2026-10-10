import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("names the status in words", () => {
    render(<StatusBadge status="needs_review" />);

    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });

  it("does not animate a badge that first appears with its data", () => {
    render(<StatusBadge status="verified" />);

    expect(screen.getByText("Verified")).not.toHaveAttribute("data-changed");
  });

  it("does not animate a re-render with the same status, as a refresh does", () => {
    const { rerender } = render(<StatusBadge status="verified" />);

    rerender(<StatusBadge status="verified" />);

    expect(screen.getByText("Verified")).not.toHaveAttribute("data-changed");
  });

  it("pops the new badge in when the status changes", () => {
    const { rerender } = render(<StatusBadge status="needs_review" />);

    rerender(<StatusBadge status="verified" />);

    const badge = screen.getByText("Verified");
    expect(badge).toHaveAttribute("data-changed", "true");
    expect(badge).toHaveClass("badge-changed");
    expect(screen.queryByText("Needs review")).toBeNull();
  });
});
