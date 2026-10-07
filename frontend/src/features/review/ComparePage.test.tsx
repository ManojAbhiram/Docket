import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app/App";
import type { Role } from "@/features/auth/schemas";
import { fakeSession } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

import { APPLICATION_ID, DOCUMENT_ID, detail, field } from "./fixtures";
import type { ApplicationDetail } from "./schemas";
import { stubMatchMedia } from "./testing";

class LoadedImage {
  naturalWidth = 1000;
  naturalHeight = 1400;
  onload: (() => void) | null = null;
  set src(_value: string) {
    queueMicrotask(() => this.onload?.());
  }
}

class BrokenImage {
  onerror: (() => void) | null = null;
  set src(_value: string) {
    queueMicrotask(() => this.onerror?.());
  }
}

beforeEach(() => {
  stubMatchMedia();
  vi.stubGlobal("Image", LoadedImage);
});

interface Served {
  gets: number;
  posts: { body: unknown; ifMatch: string | null }[];
}

function serve(
  application: ApplicationDetail | (() => ApplicationDetail),
  options: { etag?: string; post?: () => Response } = {},
): Served {
  const served: Served = { gets: 0, posts: [] };
  server.use(
    http.get(`*/api/applications/${APPLICATION_ID}`, () => {
      served.gets += 1;
      const body = typeof application === "function" ? application() : application;
      return HttpResponse.json(body, { headers: { ETag: options.etag ?? '"v1"' } });
    }),
    http.get("*/api/applications", () =>
      HttpResponse.json({ data: [], page: { next_cursor: null, has_more: false } }),
    ),
    http.post(`*/api/applications/${APPLICATION_ID}/decisions`, async ({ request }) => {
      served.posts.push({ body: await request.json(), ifMatch: request.headers.get("If-Match") });
      return (
        options.post?.() ??
        HttpResponse.json(
          {
            id: "d1",
            application_id: APPLICATION_ID,
            action: "approve",
            reason: null,
            extracted_field_id: null,
            decided_by: "Demo Verifier",
            created_at: "2026-10-06T10:00:00Z",
            application_status: "verified",
          },
          { status: 201 },
        )
      );
    }),
  );
  return served;
}

function renderCompare(role: Role = "verifier") {
  fakeSession({ startAs: role });
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: [`/applications/${APPLICATION_ID}`] })}
    />,
  );
}

function problem(status: number, code: string) {
  return () => HttpResponse.json({ error: { code, message: "x" } }, { status });
}

describe("the application review screen", () => {
  it("names the application and puts each value beside the application's own", async () => {
    serve(detail());

    renderCompare();

    expect(await screen.findByRole("heading", { name: "SYN-APP-004" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "10th marksheet" })).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    const nameRow = rows.find((row) => within(row).queryByText("Latha Sharmaa"));
    expect(nameRow).toBeDefined();
    expect(within(nameRow!).getByText("Latha Sharma")).toBeInTheDocument();
    expect(within(nameRow!).getByText("Mismatch")).toBeInTheDocument();
  });

  // Design decisions 1D, 2A and 5B, eng R2 [NOTASK-6].
  it("shows a crop of the page beside each value the engine placed, and says when it did not", async () => {
    serve(detail());
    renderCompare();

    await screen.findByRole("heading", { name: "SYN-APP-004" });

    expect(
      (await screen.findAllByRole("img", { name: /as read from the page/ })).length,
    ).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("No position").length).toBeGreaterThanOrEqual(1);
  });

  it("says why a field is flagged in words, not colour", async () => {
    serve(detail());

    renderCompare();

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    expect(screen.getAllByText("Mismatch").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Check value").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Match").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Low 91.0%").length).toBeGreaterThan(0);
  });

  it("lists the fields that need a look before the ones that match", async () => {
    serve(detail());

    renderCompare();

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]!).getByText("Mismatch")).toBeInTheDocument();
    expect(within(rows[rows.length - 1]!).getByText("Match")).toBeInTheDocument();
  });

  it("shows the stored page next to the fields, outlining the selected field", async () => {
    serve(detail());

    const { container } = renderCompare();

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    await waitFor(() => {
      expect(container.querySelector("image")).not.toBeNull();
    });
    expect(container.querySelector("image")?.getAttribute("href")).toBe(
      `http://api.test/api/documents/${DOCUMENT_ID}/image`,
    );
    expect(container.querySelector("[data-box]")).not.toBeNull();
  });

  it("says when the selected field has no position on the page", async () => {
    serve(detail());
    renderCompare();
    await screen.findByRole("heading", { name: "SYN-APP-004" });

    await userEvent.click(screen.getByRole("button", { name: "Roll number" }));

    expect(
      screen.getByText("No position for this field. The full document is shown."),
    ).toBeInTheDocument();
  });

  it("says when the page image could not be loaded and tries again on request", async () => {
    vi.stubGlobal("Image", BrokenImage);
    serve(detail());
    renderCompare();

    const alert = await screen.findByText("The document image did not load.");
    expect(alert).toBeInTheDocument();
    vi.stubGlobal("Image", LoadedImage);
    await userEvent.click(screen.getByRole("button", { name: "Reload the image" }));

    await waitFor(() => {
      expect(screen.queryByText("The document image did not load.")).not.toBeInTheDocument();
    });
  });

  it("keeps an older upload folded away", async () => {
    const base = detail();
    const older = {
      ...base.documents[0]!,
      id: "older-1",
      is_current: false,
      fields: [
        field({
          id: 99,
          value: "Old Value",
          match_result: "mismatch",
          review_reason: "mismatch",
          needs_review: true,
        }),
      ],
    };
    serve({ ...base, documents: [...base.documents, older] });

    const { container } = renderCompare();

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    const folded = container.querySelector("details");
    expect(folded).not.toBeNull();
    expect(folded).not.toHaveAttribute("open");
    expect(screen.getByText("Earlier uploads (1)")).toBeInTheDocument();
  });

  it("explains a document that could not be read, in words", async () => {
    const base = detail();
    serve({
      ...base,
      documents: [
        {
          ...base.documents[0]!,
          status: "failed",
          failure_reason: "cap_reached",
          fields: [],
        },
      ],
    });

    renderCompare();

    expect(await screen.findByText("This document could not be read.")).toBeInTheDocument();
    expect(screen.getByText("The engine's call limit was reached.")).toBeInTheDocument();
  });

  it("explains a document that is not a marksheet or an ID proof", async () => {
    const base = detail();
    serve({
      ...base,
      documents: [
        {
          ...base.documents[0]!,
          detected_type: "unknown",
          fields: [],
        },
      ],
    });

    renderCompare();

    expect(
      await screen.findByText("This document was not recognised as a marksheet or an ID proof."),
    ).toBeInTheDocument();
  });

  it("says a document is still being read", async () => {
    const base = detail();
    serve({
      ...base,
      documents: [
        {
          ...base.documents[0]!,
          status: "processing",
          detected_type: null,
          fields: [],
        },
      ],
    });

    renderCompare();

    expect(await screen.findByText("This document is still being read.")).toBeInTheDocument();
  });

  it("says when no document has been read and, for staff, offers the upload", async () => {
    serve(detail({ documents: [], status: "missing_documents" }));

    renderCompare("staff");

    expect(await screen.findByText("No documents have been read yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload documents" })).toBeInTheDocument();
  });

  it("says an application does not exist and leads back to the queue", async () => {
    fakeSession({ startAs: "verifier" });
    server.use(
      http.get(`*/api/applications/${APPLICATION_ID}`, problem(404, "not_found")),
      http.get("*/api/applications", () =>
        HttpResponse.json({ data: [], page: { next_cursor: null, has_more: false } }),
      ),
    );
    render(
      <App
        queryClient={createTestQueryClient()}
        history={createMemoryHistory({ initialEntries: [`/applications/${APPLICATION_ID}`] })}
      />,
    );

    expect(await screen.findByText("That application does not exist.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to the review queue" }));

    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
  });

  it("explains a failed load and reloads on request", async () => {
    fakeSession({ startAs: "verifier" });
    let calls = 0;
    server.use(
      http.get(`*/api/applications/${APPLICATION_ID}`, () => {
        calls += 1;
        return calls === 1
          ? new HttpResponse(null, { status: 500 })
          : HttpResponse.json(detail(), { headers: { ETag: '"v1"' } });
      }),
    );
    render(
      <App
        queryClient={createTestQueryClient()}
        history={createMemoryHistory({ initialEntries: [`/applications/${APPLICATION_ID}`] })}
      />,
    );

    expect(await screen.findByText("The application did not load.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reload" }));

    expect(await screen.findByRole("heading", { name: "10th marksheet" })).toBeInTheDocument();
  });

  it("shows staff the data and no decision button", async () => {
    serve(detail());

    renderCompare("staff");

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    expect(screen.queryByRole("button", { name: /Decide/ })).not.toBeInTheDocument();
  });

  it("offers a verifier no decision on an application that is not in review", async () => {
    serve(detail({ status: "verified" }));

    renderCompare("verifier");

    await screen.findByRole("heading", { name: "SYN-APP-004" });
    expect(screen.queryByRole("button", { name: /Decide/ })).not.toBeInTheDocument();
  });
});

async function openDialog() {
  await screen.findByRole("heading", { name: "SYN-APP-004" });
  await userEvent.click(screen.getByRole("button", { name: /Decide/ }));
  return screen.findByRole("dialog", { name: "Decide SYN-APP-004" });
}

describe("deciding an application", () => {
  it("opens from the d key and closes with Cancel, giving focus back", async () => {
    serve(detail());
    renderCompare();
    await screen.findByRole("heading", { name: "SYN-APP-004" });

    await userEvent.keyboard("d");
    const dialog = await screen.findByRole("dialog", { name: "Decide SYN-APP-004" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Decide/ })).toHaveFocus();
  });

  it("approves with the version the verifier saw and confirms it", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect((await screen.findAllByText("Decision saved")).length).toBeGreaterThan(0);
    expect(served.posts).toEqual([{ body: { action: "approve" }, ifMatch: '"v1"' }]);
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  // Regression: ISSUE-006 [NOTASK-2], design decision 3A. After a decision the verifier went on
  // looking at the application instead of going back to the queue.
  it("returns to the review queue after a decision, with focus on Review newest", async () => {
    serve(detail());
    server.use(
      http.get("*/api/applications", () =>
        HttpResponse.json({
          data: [
            {
              id: "b",
              application_ref: "SYN-APP-009",
              full_name: "Ishita Nair",
              status: "needs_review",
              rejected: false,
              updated_at: "2026-10-05T09:12:41Z",
            },
          ],
          page: { next_cursor: null, has_more: false },
        }),
      ),
    );
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Review newest/ })).toHaveFocus();
    });
  });

  // Regression: ISSUE-008 [NOTASK-2]. Two documents both carry a Name, and the picker listed
  // "Name: Latha Sharma" twice with nothing to tell them apart.
  it("names the document of each field the verifier can correct", async () => {
    const base = detail();
    const first = base.documents[0]!;
    serve(
      detail({
        documents: [
          first,
          {
            ...first,
            id: "0192b1c4-1111-7c4e-9a1b-2c3d4e5f6a7b",
            detected_type: "12th_marksheet",
            fields: [field({ id: 21, value: "Latha Sharma" })],
          },
        ],
      }),
    );
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Correct a value/ }));

    const picker = within(dialog).getByLabelText("Field");
    expect(within(picker).getByText("Name (10th marksheet): Latha Sharmaa")).toBeInTheDocument();
    expect(within(picker).getByText("Name (12th marksheet): Latha Sharma")).toBeInTheDocument();
  });

  it("corrects the chosen field with its new value", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Correct a value/ }));
    await userEvent.selectOptions(within(dialog).getByLabelText("Field"), "12");
    await userEvent.type(within(dialog).getByLabelText("New value"), "CBSE Board");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    await screen.findAllByText("Decision saved");
    expect(served.posts[0]?.body).toEqual({
      action: "correct",
      extracted_field_id: 12,
      new_value: "CBSE Board",
    });
  });

  it("asks for a value before it corrects anything", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Correct a value/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(within(dialog).getByText("Enter the new value.")).toBeInTheDocument();
    expect(served.posts).toEqual([]);
  });

  it("will not reject without a reason", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Reject/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(within(dialog).getByText("Give a reason for the rejection.")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Reason")).toBeInvalid();
    expect(served.posts).toEqual([]);
  });

  it("rejects with the reason that was typed", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("radio", { name: /Reject/ }));
    await userEvent.type(within(dialog).getByLabelText("Reason"), "Date of birth differs");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    await screen.findAllByText("Decision saved");
    expect(served.posts[0]?.body).toEqual({ action: "reject", reason: "Date of birth differs" });
  });

  it("keeps the button off after the first click, so a double click sends one decision", async () => {
    const served = serve(detail());
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));
    const save = within(dialog).getByRole("button", { name: "Save decision" });

    await userEvent.dblClick(save);

    await screen.findAllByText("Decision saved");
    expect(served.posts).toHaveLength(1);
  });

  it("tells the verifier the application changed and shows the latest version", async () => {
    let calls = 0;
    serve(
      () => {
        calls += 1;
        return calls === 1 ? detail() : detail({ updated_at: "2026-10-06T10:00:00Z" });
      },
      { post: problem(409, "conflict"), etag: '"v1"' },
    );
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(
      await within(dialog).findByText("This application changed while you were looking at it."),
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/The latest version is now shown/)).toBeInTheDocument();
  });

  it("says when the application is no longer in review", async () => {
    let calls = 0;
    serve(
      () => {
        calls += 1;
        return calls === 1 ? detail() : detail({ status: "verified" });
      },
      { post: problem(409, "conflict") },
    );
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(await screen.findByText("This application is no longer in review.")).toBeInTheDocument();
  });

  it("explains that an application cannot be approved while a document is missing", async () => {
    serve(detail(), { post: problem(409, "verification_not_allowed") });
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(
      await within(dialog).findByText("This application cannot be approved yet."),
    ).toBeInTheDocument();
  });

  it("says only a verifier can decide when the server refuses", async () => {
    serve(detail(), { post: problem(403, "forbidden") });
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(await within(dialog).findByText("Only a verifier can decide.")).toBeInTheDocument();
  });

  it("says the decision was not accepted when the server finds it invalid", async () => {
    serve(detail(), { post: problem(422, "validation_error") });
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(await within(dialog).findByText("The decision was not accepted.")).toBeInTheDocument();
  });

  it("says the person is offline and lets them save again", async () => {
    serve(detail(), { post: () => HttpResponse.error() });
    renderCompare();
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("radio", { name: /Approve/ }));

    await userEvent.click(within(dialog).getByRole("button", { name: "Save decision" }));

    expect(await within(dialog).findByText("You are offline.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save decision" })).toBeEnabled();
  });

  it("chooses the action from the a, c and r keys", async () => {
    serve(detail());
    renderCompare();
    const dialog = await openDialog();

    await userEvent.keyboard("r");

    expect(within(dialog).getByRole("radio", { name: /Reject/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
