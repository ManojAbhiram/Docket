import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import type { Role } from "@/features/auth/schemas";
import { fakeSession } from "@/test/auth";
import { createTestQueryClient } from "@/test/render";

function renderHelp(role: Role) {
  fakeSession({ startAs: role });
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: ["/help"] })}
    />,
  );
}

describe("the Help Center", () => {
  it("opens for staff with a guide for each role, the statuses and the FAQ", async () => {
    renderHelp("staff");

    expect(await screen.findByRole("heading", { level: 1, name: "Help Center" })).toBeVisible();
    for (const name of [
      "Getting started",
      "Guide for staff",
      "Guide for verifiers",
      "What the statuses mean",
      "Questions people ask",
    ]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("opens for a verifier too", async () => {
    renderHelp("verifier");

    expect(await screen.findByRole("heading", { level: 1, name: "Help Center" })).toBeVisible();
  });

  it("explains the three statuses and the rule behind missing documents", async () => {
    renderHelp("staff");

    const statuses = within(await screen.findByRole("region", { name: "What the statuses mean" }));
    expect(statuses.getByText("Verified", { selector: "dt" })).toBeInTheDocument();
    expect(statuses.getByText("Needs review", { selector: "dt" })).toBeInTheDocument();
    expect(statuses.getByText("Missing documents", { selector: "dt" })).toBeInTheDocument();
    expect(
      statuses.getByText(/10th marksheet, a 12th marksheet and an ID proof/),
    ).toBeInTheDocument();
  });

  it("lists the parts of the page and jumps to them", async () => {
    renderHelp("staff");

    const contents = await screen.findByRole("navigation", { name: "On this page" });
    const link = within(contents).getByRole("link", { name: "Questions people ask" });
    expect(link).toHaveAttribute("href", "#questions");
    await userEvent.click(link);
    expect(screen.getByRole("heading", { level: 2, name: "Questions people ask" })).toHaveAttribute(
      "id",
      "questions",
    );
  });

  it("is marked as the current page in the sidebar", async () => {
    renderHelp("verifier");

    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(await within(nav).findByRole("link", { name: "Help Center" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
