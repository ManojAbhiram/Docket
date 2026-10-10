import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app/App";
import type { Role } from "@/features/auth/schemas";
import { fakeSession } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

function renderAt(path: string) {
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: [path] })}
    />,
  );
}

function counts(overrides: Record<string, number> = {}) {
  return {
    verified: 12,
    needs_review: 3,
    missing_documents: 5,
    rejected: 1,
    ...overrides,
  };
}

function dashboardAnswers(...answers: Response[]) {
  const seen = { requests: 0 };
  server.use(
    http.get("*/api/dashboard", () => {
      const answer = answers[Math.min(seen.requests, answers.length - 1)];
      seen.requests += 1;
      return answer ? answer.clone() : HttpResponse.json(counts());
    }),
  );
  return seen;
}

function json(body: Record<string, unknown>, status = 200): Response {
  return HttpResponse.json(body, { status });
}

describe("the dashboard", () => {
  it("shows staff the four counts, with the rejected ones named as part of needs review", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json(counts()));

    renderAt("/dashboard");

    expect(await screen.findByText("20 applications")).toBeInTheDocument();
    expect(screen.getByText("of which 1 rejected")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See applications" })).toHaveClass(
      "focus-visible:ring-tile-foreground",
    );
    expect(screen.getByRole("button", { name: "Sign out" })).toHaveClass(
      "focus-visible:ring-header-foreground",
    );
    expect(screen.getByRole("button", { name: /Theme:/ })).toHaveClass(
      "focus-visible:ring-header-foreground",
    );
  });

  it("sends staff to import, export and the applications", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json(counts()));

    renderAt("/dashboard");

    expect(await screen.findByRole("link", { name: "Import applications" })).toHaveAttribute(
      "href",
      "/import",
    );
    expect(screen.getByRole("link", { name: "Export verified list" })).toHaveAttribute(
      "href",
      "/export",
    );
    expect(await screen.findByRole("link", { name: "See applications" })).toHaveAttribute(
      "href",
      "/applications",
    );
    expect(screen.queryByRole("link", { name: "Review queue" })).not.toBeInTheDocument();
  });

  it("sends a verifier to the queue and offers no import or export", async () => {
    fakeSession({ startAs: "verifier" });
    dashboardAnswers(json(counts()));

    renderAt("/dashboard");

    const main = within(await screen.findByRole("main"));
    expect(await main.findByRole("link", { name: "Open the queue" })).toHaveAttribute(
      "href",
      "/queue",
    );
    expect(main.getByRole("link", { name: "Review queue" })).toHaveAttribute("href", "/queue");
    expect(main.queryByRole("link", { name: "Import applications" })).not.toBeInTheDocument();
    expect(main.queryByRole("link", { name: "Export verified list" })).not.toBeInTheDocument();
  });

  it("follows a link inside the app without reloading the page", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json(counts()));
    renderAt("/dashboard");

    await userEvent.click(await screen.findByRole("link", { name: "Import applications" }));

    expect(await screen.findByRole("heading", { name: "Import applications" })).toBeInTheDocument();
  });

  it("says there are no applications yet when every count is zero", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(
      json(counts({ verified: 0, needs_review: 0, missing_documents: 0, rejected: 0 })),
    );

    renderAt("/dashboard");

    expect(await screen.findByText("No applications yet.")).toBeInTheDocument();
  });

  it("shows a loading skeleton while the counts are on their way", async () => {
    fakeSession({ startAs: "staff" });
    server.use(
      http.get("*/api/dashboard", async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json(counts());
      }),
    );

    renderAt("/dashboard");

    await waitFor(() => {
      expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    });
    expect(await screen.findByText("20 applications")).toBeInTheDocument();
  });

  it("explains a failure and reads again when the person reloads", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json({ error: { code: "internal", message: "x" } }, 500), json(counts()));
    renderAt("/dashboard");

    expect(await screen.findByText("The counts did not load.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reload" }));

    expect(await screen.findByText("20 applications")).toBeInTheDocument();
    expect(screen.queryByText("The counts did not load.")).not.toBeInTheDocument();
  });

  it("says the database cannot be reached when the API answers 503", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json({ error: { code: "service_unavailable", message: "x" } }, 503));

    renderAt("/dashboard");

    expect(await screen.findByText("Docket cannot reach its database.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("says the person is offline when the request never arrives", async () => {
    fakeSession({ startAs: "staff" });
    server.use(http.get("*/api/dashboard", () => HttpResponse.error()));

    renderAt("/dashboard");

    expect(await screen.findByText("You are offline.")).toBeInTheDocument();
  });

  it("keeps the last counts and says they are old when a refresh goes offline", async () => {
    fakeSession({ startAs: "staff" });
    let offline = false;
    server.use(
      http.get("*/api/dashboard", () =>
        offline ? HttpResponse.error() : HttpResponse.json(counts()),
      ),
    );
    renderAt("/dashboard");
    await screen.findByText("20 applications");

    offline = true;
    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText(/Offline\. Counts as of/)).toBeInTheDocument();
    expect(screen.getByText("20 applications")).toBeInTheDocument();
  });

  it("reads the counts again when the person presses refresh, and announces it politely", async () => {
    fakeSession({ startAs: "staff" });
    const seen = dashboardAnswers(json(counts()), json(counts({ verified: 13 })));
    renderAt("/dashboard");
    await screen.findByText("20 applications");

    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("21 applications")).toBeInTheDocument();
    expect(seen.requests).toBe(2);
    expect(await screen.findByText(/Counts updated at/)).toBeInTheDocument();
  });
});

describe("the dashboard refreshing by itself", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reads the counts again after thirty seconds", async () => {
    fakeSession({ startAs: "staff" });
    const seen = dashboardAnswers(json(counts()), json(counts({ verified: 20 })));
    renderAt("/dashboard");
    await screen.findByText("20 applications");

    await vi.advanceTimersByTimeAsync(30_000);

    expect(await screen.findByText("28 applications")).toBeInTheDocument();
    expect(seen.requests).toBe(2);
  });
});

describe("the export", () => {
  const csv = "application_id,name\nSYN-APP-001,Latha Sharma\nSYN-APP-002,Diya Gupta\n";
  let created: Blob[];
  let revoked: string[];
  let clicked: HTMLAnchorElement[];

  beforeEach(() => {
    created = [];
    revoked = [];
    clicked = [];
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: (blob: Blob) => {
        created.push(blob);
        return "blob:docket/1";
      },
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: (url: string) => {
        revoked.push(url);
      },
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function click(
      this: HTMLAnchorElement,
    ) {
      clicked.push(this);
    });
  });

  function csvAnswer(body = csv, delayMs = 0) {
    const seen = { requests: 0 };
    server.use(
      http.get("*/api/exports/verified.csv", async () => {
        seen.requests += 1;
        if (delayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
        return new HttpResponse(body, {
          headers: {
            "Content-Type": "text/csv",
            "Content-Disposition": 'attachment; filename="verified-20261006T101200Z.csv"',
          },
        });
      }),
    );
    return seen;
  }

  async function openExport(role: Role = "staff") {
    fakeSession({ startAs: role });
    dashboardAnswers(json(counts()));
    renderAt("/export");
    return screen.findByRole("button", { name: "Download CSV" });
  }

  it("shows how many rows the file will hold before anything is downloaded", async () => {
    await openExport();

    expect(await screen.findByText("12 rows")).toBeInTheDocument();
  });

  it("saves the file under the name the server gave it and says how many rows it holds", async () => {
    csvAnswer();
    const button = await openExport();

    await userEvent.click(button);

    expect(
      await screen.findByText("Downloaded verified-20261006T101200Z.csv with 2 rows."),
    ).toBeInTheDocument();
    expect(created).toHaveLength(1);
    expect(clicked[0]?.download).toBe("verified-20261006T101200Z.csv");
    expect(clicked[0]?.href).toBe("blob:docket/1");
    await waitFor(() => {
      expect(revoked).toEqual(["blob:docket/1"]);
    });
  });

  it("does not start two downloads when the button is pressed twice", async () => {
    const seen = csvAnswer(csv, 150);
    const button = await openExport();

    await userEvent.dblClick(button);

    await screen.findByText(/Downloaded verified-/);
    expect(seen.requests).toBe(1);
    expect(created).toHaveLength(1);
  });

  it("says nothing is Verified yet and saves no file when the file holds only its header", async () => {
    csvAnswer("application_id,name\n");
    const button = await openExport();

    await userEvent.click(button);

    expect(await screen.findByText("No applications are Verified yet.")).toBeInTheDocument();
    expect(created).toHaveLength(0);
    expect(screen.queryByText(/Downloaded/)).not.toBeInTheDocument();
  });

  it("says so when the dashboard already shows no Verified applications", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json(counts({ verified: 0 })));

    renderAt("/export");

    expect(await screen.findByText("No applications are Verified yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });

  it("still offers the download when the count could not be read", async () => {
    fakeSession({ startAs: "staff" });
    dashboardAnswers(json({ error: { code: "internal", message: "x" } }, 500));
    csvAnswer();
    renderAt("/export");

    const button = await screen.findByRole("button", { name: "Download CSV" });
    await userEvent.click(button);

    expect(await screen.findByText(/Downloaded verified-/)).toBeInTheDocument();
  });

  it("tells a refused account that only staff can export", async () => {
    server.use(
      http.get("*/api/exports/verified.csv", () =>
        HttpResponse.json({ error: { code: "forbidden", message: "x" } }, { status: 403 }),
      ),
    );
    const button = await openExport();

    await userEvent.click(button);

    expect(await screen.findByText("Only staff can export the verified list.")).toBeInTheDocument();
  });

  it("explains a server error and tries again from the notice", async () => {
    let failing = true;
    server.use(
      http.get("*/api/exports/verified.csv", () =>
        failing
          ? HttpResponse.json({ error: { code: "internal", message: "x" } }, { status: 500 })
          : new HttpResponse(csv, { headers: { "Content-Type": "text/csv" } }),
      ),
    );
    const button = await openExport();
    await userEvent.click(button);
    expect(await screen.findByText("The export did not finish.")).toBeInTheDocument();

    failing = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Downloaded verified.csv with 2 rows.")).toBeInTheDocument();
  });

  it("says the database cannot be reached when the API answers 503", async () => {
    server.use(
      http.get("*/api/exports/verified.csv", () =>
        HttpResponse.json(
          { error: { code: "service_unavailable", message: "x" } },
          { status: 503 },
        ),
      ),
    );
    const button = await openExport();

    await userEvent.click(button);

    expect(await screen.findByText("Docket cannot reach its database.")).toBeInTheDocument();
  });

  it("says the person is offline when the request never arrives", async () => {
    server.use(http.get("*/api/exports/verified.csv", () => HttpResponse.error()));
    const button = await openExport();

    await userEvent.click(button);

    expect(await screen.findByText("You are offline.")).toBeInTheDocument();
  });

  it("keeps a verifier out of the export page", async () => {
    fakeSession({ startAs: "verifier" });

    renderAt("/export");

    expect(
      await screen.findByRole("heading", { name: "This page is not for your role" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Download CSV" })).not.toBeInTheDocument();
  });
});
