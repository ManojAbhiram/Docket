import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocketLogo } from "@/components/DocketLogo";

describe("DocketLogo", () => {
  it("is an image named for the product", () => {
    render(<DocketLogo />);

    expect(screen.getByRole("img", { name: "Docket logo" })).toBeInTheDocument();
  });

  it("can show the name beside the mark", () => {
    render(<DocketLogo withName />);

    expect(screen.getByText("Docket")).toBeInTheDocument();
  });
});
