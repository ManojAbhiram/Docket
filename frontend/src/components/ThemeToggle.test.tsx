import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "@/components/ThemeToggle";

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  window.localStorage.clear();
});

describe("ThemeToggle", () => {
  it("starts on System and names the theme it will switch to", () => {
    render(<ThemeToggle />);

    expect(screen.getByRole("button", { name: "Theme: System. Switch to Light" })).toBeVisible();
  });

  it("cycles System, Light, Dark and paints each one on the root element", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    await user.click(screen.getByRole("button"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(screen.getByRole("button", { name: "Theme: Light. Switch to Dark" })).toBeVisible();

    await user.click(screen.getByRole("button"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem("docket-theme")).toBe("dark");
  });
});
