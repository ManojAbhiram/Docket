import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { fakeSession, userWith } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

function renderSignUp() {
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: ["/sign-up"] })}
    />,
  );
}

async function fill(user: ReturnType<typeof userEvent.setup>, role: "Staff" | "Verifier") {
  await user.type(await screen.findByLabelText("Your name"), "Asha Kumar");
  await user.type(screen.getByLabelText("Username"), "asha.k");
  await user.type(screen.getByLabelText("Password"), "a-long-phrase-1");
  await user.click(screen.getByRole("radio", { name: new RegExp(role) }));
  await user.click(screen.getByRole("button", { name: "Create account" }));
}

describe("signing up", () => {
  it("opens the review queue for a new verifier", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/register", () => HttpResponse.json(userWith("verifier"))),
      http.get("*/api/auth/me", () => HttpResponse.json(userWith("verifier"))),
    );
    renderSignUp();
    await fill(userEvent.setup(), "Verifier");
    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
  });

  it("says the username is taken on a 409", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/register", () =>
        HttpResponse.json(
          { error: { code: "conflict", message: "that username is taken" } },
          { status: 409 },
        ),
      ),
    );
    renderSignUp();
    await fill(userEvent.setup(), "Staff");
    expect(await screen.findByText("That username is taken.")).toBeInTheDocument();
  });

  it("links to sign in and back", async () => {
    fakeSession();
    renderSignUp();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Sign in to Docket" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Create an account" }));
    expect(
      await screen.findByRole("heading", { name: "Create your Docket account" }),
    ).toBeInTheDocument();
  });
});
