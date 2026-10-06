import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

async function signIn(user: ReturnType<typeof userEvent.setup>, password = "right") {
  await user.type(await screen.findByLabelText("Username"), "someone");
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("signing in", () => {
  it("sends a browser with no session from a protected page to sign-in", async () => {
    fakeSession();

    renderAt("/applications");

    expect(await screen.findByRole("heading", { name: "Sign in to Docket" })).toBeInTheDocument();
    expect(screen.getByText("You were signed out.")).toBeInTheDocument();
  });

  it("opens the review queue for a verifier", async () => {
    fakeSession({ loginAs: "verifier" });
    renderAt("/sign-in");

    await signIn(userEvent.setup());

    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
  });

  it("opens the applications for staff", async () => {
    fakeSession({ loginAs: "staff" });
    renderAt("/sign-in");

    await signIn(userEvent.setup());

    expect(await screen.findByRole("heading", { name: "Applications" })).toBeInTheDocument();
  });

  it("does not say which half of a wrong sign-in was wrong, and lets the person try again", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/login", () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "x" } }, { status: 401 }),
      ),
    );
    renderAt("/sign-in");

    await signIn(userEvent.setup(), "wrong");

    expect(await screen.findByText("That username and password do not match.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("holds the button off for the wait the server asked for", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/login", () =>
        HttpResponse.json(
          { error: { code: "too_many_attempts", message: "x" } },
          { status: 429, headers: { "Retry-After": "42" } },
        ),
      ),
    );
    renderAt("/sign-in");

    await signIn(userEvent.setup());

    expect(await screen.findByText("Try again in 42 seconds.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled();
  });

  it("says the server cannot be reached when it answers with an error", async () => {
    fakeSession();
    server.use(http.post("*/api/auth/login", () => new HttpResponse(null, { status: 503 })));
    renderAt("/sign-in");

    await signIn(userEvent.setup());

    expect(await screen.findByText("Docket cannot reach its server.")).toBeInTheDocument();
  });

  it("says the person is offline when the request never arrives", async () => {
    fakeSession();
    server.use(http.post("*/api/auth/login", () => HttpResponse.error()));
    renderAt("/sign-in");

    await signIn(userEvent.setup());

    expect(await screen.findByText("You are offline.")).toBeInTheDocument();
  });
});

describe("the signed-in shell", () => {
  it("shows staff the staff links and not the queue", async () => {
    fakeSession({ startAs: "staff" });

    renderAt("/applications");

    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(await screen.findByRole("link", { name: "Import" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export" })).toBeInTheDocument();
    expect(nav).not.toHaveTextContent("Review queue");
    expect(screen.getByText("Demo Staff")).toBeInTheDocument();
  });

  it("shows a verifier the queue and not import or export", async () => {
    fakeSession({ startAs: "verifier" });

    renderAt("/applications");

    expect(await screen.findByRole("link", { name: "Review queue" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Import" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Export" })).not.toBeInTheDocument();
  });

  it("sends each role to its own start from the index", async () => {
    fakeSession({ startAs: "verifier" });

    renderAt("/");

    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
  });

  it("tells a verifier who opens a staff-only page that it is not for their role", async () => {
    fakeSession({ startAs: "verifier" });

    renderAt("/import");

    expect(
      await screen.findByRole("heading", { name: "This page is not for your role" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Import applications" })).not.toBeInTheDocument();
  });

  it("ends the session on the server when the person signs out", async () => {
    const { calls } = fakeSession({ startAs: "staff" });
    renderAt("/applications");

    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in to Docket" })).toBeInTheDocument();
    await waitFor(() => {
      expect(calls).toContain("logout");
    });
  });

  it("keeps the status page open without a session", async () => {
    fakeSession();
    server.use(http.get("*/healthz", () => HttpResponse.json({ status: "ok", version: "t" })));

    renderAt("/status");

    expect(await screen.findByRole("heading", { name: "API health" })).toBeInTheDocument();
  });
});
