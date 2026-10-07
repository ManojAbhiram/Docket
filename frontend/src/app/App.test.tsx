import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { fakeSession } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

import { App } from "./App";

function renderAt(path: string) {
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: [path] })}
    />,
  );
}

describe("App", () => {
  it("renders the status route with the health card", async () => {
    server.use(http.get("*/healthz", () => HttpResponse.json({ status: "ok", version: "test" })));

    renderAt("/status");

    expect(await screen.findByRole("heading", { name: "API health" })).toBeInTheDocument();
    expect(await screen.findByText("test")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });

  it("renders the not-found route for an unknown path", async () => {
    renderAt("/nowhere");

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the start" })).toHaveAttribute("href", "/");
  });

  // Design decisions 1A and 4A [NOTASK-6].
  it("marks the page the person is on in the navigation", async () => {
    fakeSession({ startAs: "staff" });

    renderAt("/applications");

    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(await within(nav).findByRole("link", { name: "Applications" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Dashboard" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("says on every screen that the data is synthetic", async () => {
    renderAt("/nowhere");

    expect(
      await screen.findByText("Synthetic data only. No real student records."),
    ).toBeInTheDocument();
  });
});
