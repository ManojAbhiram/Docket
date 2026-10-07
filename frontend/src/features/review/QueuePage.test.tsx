import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { fakeSession } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

import { APPLICATION_ID, detail, queueItem } from "./fixtures";
import { stubMatchMedia } from "./testing";

beforeEach(() => {
  stubMatchMedia();
});

function renderQueue() {
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: ["/queue"] })}
    />,
  );
}

function page(items: ReturnType<typeof queueItem>[], next: string | null = null) {
  return HttpResponse.json({ data: items, page: { next_cursor: next, has_more: next !== null } });
}

describe("the review queue", () => {
  it("asks only for flagged applications that are not rejected", async () => {
    fakeSession({ startAs: "verifier" });
    const urls: string[] = [];
    server.use(
      http.get("*/api/applications", ({ request }) => {
        urls.push(request.url);
        return page([queueItem()]);
      }),
    );

    renderQueue();

    await screen.findByText("SYN-APP-004");
    const url = new URL(urls[0] ?? "");
    expect(url.searchParams.get("filter[status]")).toBe("needs_review");
    expect(url.searchParams.get("filter[rejected]")).toBe("false");
  });

  it("lists each application with its reference, name and status", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get("*/api/applications", () =>
        page([
          queueItem(),
          queueItem({ id: "b", application_ref: "SYN-APP-009", full_name: "Ishita Nair" }),
        ]),
      ),
    );

    renderQueue();

    expect(await screen.findByText("Ishita Nair")).toBeInTheDocument();
    expect(screen.getByText("SYN-APP-004")).toBeInTheDocument();
    expect(screen.getAllByText("Needs review").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("2 to review")).toBeInTheDocument();
  });

  // Regression: ISSUE-004 [NOTASK-2]. The "why flagged" cell was always empty.
  it("says why each application is flagged", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get("*/api/applications", () =>
        page([queueItem({ flag_reason: "Name does not match, and 2 more" })]),
      ),
    );

    renderQueue();

    expect(await screen.findByText("Name does not match, and 2 more")).toBeInTheDocument();
  });

  // Design decisions 1B and 1C, eng R3 [NOTASK-6].
  it("counts what is left from the dashboard, not from the page loaded", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get("*/api/applications", () => page([queueItem()], "next")),
      http.get("*/api/dashboard", () =>
        HttpResponse.json({ verified: 3, needs_review: 611, missing_documents: 4, rejected: 11 }),
      ),
    );

    renderQueue();

    expect(await screen.findByText("600 to review")).toBeInTheDocument();
  });

  it("adds how many this person decided in this sitting", async () => {
    fakeSession({ startAs: "verifier" });
    window.sessionStorage.setItem("docket-decided", "4");
    server.use(
      http.get("*/api/applications", () => page([queueItem()])),
      http.get("*/api/dashboard", () =>
        HttpResponse.json({ verified: 3, needs_review: 12, missing_documents: 4, rejected: 2 }),
      ),
    );

    renderQueue();

    expect(await screen.findByText("10 to review, 4 decided this sitting")).toBeInTheDocument();
    window.sessionStorage.clear();
  });

  it("shows the loaded count when the dashboard is not available", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(http.get("*/api/applications", () => page([queueItem()])));

    renderQueue();

    expect(await screen.findByText("1 to review")).toBeInTheDocument();
  });

  it("shows a loading state and then the list", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(http.get("*/api/applications", () => page([queueItem()])));

    renderQueue();

    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
    expect(await screen.findByText("SYN-APP-004")).toBeInTheDocument();
  });

  it("says when nothing needs review", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(http.get("*/api/applications", () => page([])));

    renderQueue();

    expect(await screen.findByText("Nothing needs review.")).toBeInTheDocument();
  });

  it("explains a failed load and offers to reload", async () => {
    fakeSession({ startAs: "verifier" });
    let calls = 0;
    server.use(
      http.get("*/api/applications", () => {
        calls += 1;
        return calls === 1 ? new HttpResponse(null, { status: 500 }) : page([queueItem()]);
      }),
    );
    renderQueue();

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("The queue did not load.")).toBeInTheDocument();
    await userEvent.click(within(alert).getByRole("button", { name: "Reload" }));

    expect(await screen.findByText("SYN-APP-004")).toBeInTheDocument();
  });

  it("loads the next page with the cursor the server gave", async () => {
    fakeSession({ startAs: "verifier" });
    const cursors: (string | null)[] = [];
    server.use(
      http.get("*/api/applications", ({ request }) => {
        const cursor = new URL(request.url).searchParams.get("cursor");
        cursors.push(cursor);
        return cursor
          ? page([queueItem({ id: "c", application_ref: "SYN-APP-020", full_name: "Second Page" })])
          : page([queueItem()], "next-1");
      }),
    );
    renderQueue();

    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));

    expect(await screen.findByText("Second Page")).toBeInTheDocument();
    expect(cursors).toEqual([null, "next-1"]);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("opens an application from its row", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get("*/api/applications", () => page([queueItem()])),
      http.get(`*/api/applications/${APPLICATION_ID}`, () =>
        HttpResponse.json(detail(), { headers: { ETag: '"v1"' } }),
      ),
    );
    renderQueue();

    await userEvent.click(await screen.findByRole("button", { name: "Open SYN-APP-004" }));

    expect(await screen.findByRole("heading", { name: "SYN-APP-004" })).toBeInTheDocument();
  });

  it("opens the top of the queue with Review newest", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get("*/api/applications", () => page([queueItem()])),
      http.get(`*/api/applications/${APPLICATION_ID}`, () =>
        HttpResponse.json(detail(), { headers: { ETag: '"v1"' } }),
      ),
    );
    renderQueue();
    await screen.findByText("SYN-APP-004");

    await userEvent.click(screen.getByRole("button", { name: /Review newest/ }));

    expect(await screen.findByRole("heading", { name: "SYN-APP-004" })).toBeInTheDocument();
  });
});
