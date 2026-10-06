import { createMemoryHistory } from "@tanstack/react-router";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import type { Role } from "@/features/auth/schemas";
import { fakeSession } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

// A page waits on the session check, then its own request; a loaded machine needs more than 1 s.
configure({ asyncUtilTimeout: 4000 });

const APP_ID = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b";

function renderAt(path: string, role: Role = "staff") {
  fakeSession({ startAs: role });
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: [path] })}
    />,
  );
}

function csv(name = "applications.csv") {
  return new File(["application_id,name\n"], name, { type: "text/csv" });
}

function failure(status: number, code: string, headers: Record<string, string> = {}) {
  return HttpResponse.json({ error: { code, message: "x" } }, { status, headers });
}

const IMPORT_RESULT = {
  id: "i1",
  rows_read: 3,
  rows_created: 1,
  rows_rejected: 2,
  errors: [
    { row_number: 2, column_name: "date_of_birth", reason_code: "bad_date" },
    { row_number: 3, column_name: null, reason_code: "malformed_row" },
  ],
};

async function chooseAndImport(file = csv()) {
  const user = userEvent.setup();
  await user.upload(await screen.findByLabelText("Choose a CSV file"), file);
  return user;
}

describe("import", () => {
  it("keeps the button off until a file is chosen", async () => {
    renderAt("/import");

    expect(await screen.findByRole("button", { name: "Import applications" })).toBeDisabled();
  });

  it("sends the file once and shows what was created and which rows were refused and why", async () => {
    let parts: string[] = [];
    server.use(
      http.post("*/api/imports", async ({ request }) => {
        const form = await request.formData();
        parts = [...form.keys()];
        return HttpResponse.json(IMPORT_RESULT, { status: 201 });
      }),
    );
    renderAt("/import");

    const user = await chooseAndImport();
    await user.click(screen.getByRole("button", { name: "Import applications" }));

    expect(
      await screen.findByRole("heading", { name: "Imported 1 of 3 rows." }),
    ).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText("date_of_birth")).toBeInTheDocument();
    expect(within(table).getByText("Unreadable date")).toBeInTheDocument();
    expect(within(table).getByText("whole row")).toBeInTheDocument();
    expect(within(table).getByText("Wrong number of columns")).toBeInTheDocument();
    expect(parts).toEqual(["file"]);
  });

  it("sends one request when the button is clicked twice", async () => {
    let requests = 0;
    server.use(
      http.post("*/api/imports", async () => {
        requests += 1;
        await delay(50);
        return HttpResponse.json(IMPORT_RESULT, { status: 201 });
      }),
    );
    renderAt("/import");

    const user = await chooseAndImport();
    const button = screen.getByRole("button", { name: "Import applications" });
    await user.dblClick(button);

    expect(await screen.findByRole("heading", { name: /Imported/ })).toBeInTheDocument();
    expect(requests).toBe(1);
  });

  it("shows the file is being imported while the request runs", async () => {
    server.use(
      http.post("*/api/imports", async () => {
        await delay(100);
        return HttpResponse.json(IMPORT_RESULT, { status: 201 });
      }),
    );
    renderAt("/import");

    const user = await chooseAndImport(csv("july.csv"));
    await user.click(screen.getByRole("button", { name: "Import applications" }));

    expect(await screen.findByText("Importing july.csv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importing" })).toBeDisabled();
  });

  it.each([
    [413, "That file is too large."],
    [415, "That is not a CSV file."],
    [422, "That file cannot be read."],
    [403, "Only staff can import applications."],
    [500, "The import did not finish."],
  ])("explains a %i answer", async (status, title) => {
    server.use(http.post("*/api/imports", () => failure(status, "x")));
    renderAt("/import");

    const user = await chooseAndImport();
    await user.click(screen.getByRole("button", { name: "Import applications" }));

    expect(await screen.findByText(title)).toBeInTheDocument();
  });

  it("says the person is offline when the request never arrives", async () => {
    server.use(http.post("*/api/imports", () => HttpResponse.error()));
    renderAt("/import");

    const user = await chooseAndImport();
    await user.click(screen.getByRole("button", { name: "Import applications" }));

    expect(await screen.findByText("You are offline.")).toBeInTheDocument();
  });

  it("clears an old result when another file is chosen", async () => {
    server.use(http.post("*/api/imports", () => HttpResponse.json(IMPORT_RESULT, { status: 201 })));
    renderAt("/import");
    const user = await chooseAndImport();
    await user.click(screen.getByRole("button", { name: "Import applications" }));
    await screen.findByRole("heading", { name: /Imported/ });

    await user.upload(screen.getByLabelText("Choose a CSV file"), csv("next.csv"));

    expect(screen.queryByRole("heading", { name: /Imported/ })).not.toBeInTheDocument();
  });

  it("opens the applications list from the result", async () => {
    server.use(
      http.post("*/api/imports", () => HttpResponse.json(IMPORT_RESULT, { status: 201 })),
      http.get("*/api/applications", () =>
        HttpResponse.json({ data: [], page: { next_cursor: null, has_more: false } }),
      ),
    );
    renderAt("/import");
    const user = await chooseAndImport();
    await user.click(screen.getByRole("button", { name: "Import applications" }));

    await user.click(await screen.findByRole("button", { name: "View applications" }));

    expect(await screen.findByRole("heading", { name: "Applications" })).toBeInTheDocument();
  });
});

function listed(count: number, from = 1) {
  return Array.from({ length: count }, (_, index) => ({
    id: `app-${String(from + index)}`,
    application_ref: `SYN-APP-${String(from + index).padStart(3, "0")}`,
    full_name: `Applicant ${String(from + index)}`,
    status: index % 2 === 0 ? "needs_review" : "verified",
    rejected: false,
    updated_at: "2026-10-05T04:12:41Z",
  }));
}

describe("applications", () => {
  it("lists each application with its status and links to review it", async () => {
    server.use(
      http.get("*/api/applications", () =>
        HttpResponse.json({ data: listed(2), page: { next_cursor: null, has_more: false } }),
      ),
    );
    renderAt("/applications");

    const open = await screen.findAllByRole("link", { name: "Open SYN-APP-001" });
    expect(open[0]).toHaveAttribute("href", "/applications/app-1");
    expect(screen.getAllByText("Needs review").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
  });

  it("gives staff a link to add documents and gives a verifier none", async () => {
    server.use(
      http.get("*/api/applications", () =>
        HttpResponse.json({ data: listed(1), page: { next_cursor: null, has_more: false } }),
      ),
    );
    const staff = renderAt("/applications", "staff");
    const upload = await screen.findAllByRole("link", { name: "Add documents for SYN-APP-001" });
    expect(upload[0]).toHaveAttribute("href", "/applications/app-1/upload");
    staff.unmount();

    renderAt("/applications", "verifier");

    await screen.findAllByRole("link", { name: "Open SYN-APP-001" });
    expect(screen.queryByRole("link", { name: /Add documents/ })).not.toBeInTheDocument();
  });

  it("shows a rejected application as rejected", async () => {
    server.use(
      http.get("*/api/applications", () =>
        HttpResponse.json({
          data: [{ ...listed(1)[0], status: "needs_review", rejected: true }],
          page: { next_cursor: null, has_more: false },
        }),
      ),
    );
    renderAt("/applications");

    expect((await screen.findAllByText("Rejected")).length).toBeGreaterThan(0);
  });

  it("loads the next page when asked and stops offering more at the end", async () => {
    const cursors: (string | null)[] = [];
    server.use(
      http.get("*/api/applications", ({ request }) => {
        const cursor = new URL(request.url).searchParams.get("cursor");
        cursors.push(cursor);
        return cursor
          ? HttpResponse.json({ data: listed(1, 21), page: { next_cursor: null, has_more: false } })
          : HttpResponse.json({
              data: listed(20),
              page: { next_cursor: "page-2", has_more: true },
            });
      }),
    );
    renderAt("/applications");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Load more" }));

    expect(await screen.findAllByRole("link", { name: "Open SYN-APP-021" })).toHaveLength(2);
    expect(cursors).toEqual([null, "page-2"]);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("asks the API for one status when a filter is chosen", async () => {
    const asked: (string | null)[] = [];
    server.use(
      http.get("*/api/applications", ({ request }) => {
        asked.push(new URL(request.url).searchParams.get("filter[status]"));
        return HttpResponse.json({ data: [], page: { next_cursor: null, has_more: false } });
      }),
    );
    renderAt("/applications");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Needs review" }));

    await waitFor(() => {
      expect(asked).toContain("needs_review");
    });
    expect(await screen.findByText("No applications are Needs review.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filter" }));
    await waitFor(() => {
      expect(asked.at(-1)).toBeNull();
    });
  });

  it("invites staff to import when there are no applications at all", async () => {
    server.use(
      http.get("*/api/applications", () =>
        HttpResponse.json({ data: [], page: { next_cursor: null, has_more: false } }),
      ),
    );
    renderAt("/applications", "staff");

    expect(await screen.findByText("No applications yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Import applications" })).toHaveAttribute(
      "href",
      "/import",
    );
  });

  it("says what failed and reloads on request", async () => {
    let calls = 0;
    server.use(
      http.get("*/api/applications", () => {
        calls += 1;
        return calls === 1
          ? failure(500, "internal")
          : HttpResponse.json({ data: listed(1), page: { next_cursor: null, has_more: false } });
      }),
    );
    renderAt("/applications");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Reload" }));

    expect(await screen.findAllByRole("link", { name: "Open SYN-APP-001" })).toHaveLength(2);
    expect(screen.queryByText("The list did not load.")).not.toBeInTheDocument();
  });

  it("says the person is offline when the list cannot be fetched", async () => {
    server.use(http.get("*/api/applications", () => HttpResponse.error()));
    renderAt("/applications");

    expect(await screen.findByText("You are offline.")).toBeInTheDocument();
  });
});

function doc(id: string, status: string, type: string | null = null, reason: string | null = null) {
  return {
    id,
    application_id: APP_ID,
    detected_type: type,
    status,
    failure_reason: reason,
    is_current: true,
    created_at: "2026-10-05T04:12:41Z",
  };
}

function documentList(...docs: ReturnType<typeof doc>[]) {
  return HttpResponse.json({ data: docs, page: { next_cursor: null, has_more: false } });
}

function knownApplication() {
  return http.get(`*/api/applications/${APP_ID}`, () =>
    HttpResponse.json({ id: APP_ID, application_ref: "SYN-APP-007" }),
  );
}

function png(name: string) {
  return new File([name], name, { type: "image/png" });
}

describe("upload", () => {
  it("names the application and lists its documents with what was read", async () => {
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () =>
        documentList(doc("d1", "read", "10th_marksheet"), doc("d2", "failed", null, "timeout")),
      ),
    );
    renderAt(`/applications/${APP_ID}/upload`);

    expect(
      await screen.findByRole("heading", { name: "Documents for SYN-APP-007" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Read: 10th marksheet")).toBeInTheDocument();
    expect(screen.getByText(/Reading took too long\. Upload the file again\./)).toBeInTheDocument();
    expect(screen.getByText("1 read, 0 reading, 1 failed.")).toBeInTheDocument();
  });

  it("uploads files one at a time and a refused file does not stop the rest", async () => {
    const order: string[] = [];
    let active = 0;
    let overlap = 0;
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => documentList()),
      http.post(`*/api/applications/${APP_ID}/documents`, async ({ request }) => {
        active += 1;
        overlap = Math.max(overlap, active);
        const form = await request.formData();
        const file = { name: await (form.get("file") as Blob).text() };
        order.push(file.name);
        await delay(20);
        active -= 1;
        if (file.name === "bad.png") {
          return failure(415, "unsupported_media_type");
        }
        return HttpResponse.json(doc(`new-${file.name}`, "uploaded"), { status: 202 });
      }),
    );
    renderAt(`/applications/${APP_ID}/upload`);
    const user = userEvent.setup();

    await user.upload(await screen.findByLabelText("Choose files"), [
      png("a.png"),
      png("bad.png"),
      png("c.png"),
    ]);

    expect(
      await screen.findByText("bad.png is not a JPG, PNG or PDF. Choose one of those formats."),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText("Stored")).toHaveLength(2);
    });
    expect(order).toEqual(["a.png", "bad.png", "c.png"]);
    expect(overlap).toBe(1);
  });

  it.each([
    [413, "big.png is over 8 MiB. Choose a smaller scan or photo."],
    [422, "big.png could not be read as an image or PDF. Check the file and upload it again."],
    [500, "big.png did not upload. Check your connection and upload it again."],
  ])("explains a %i answer for one file", async (status, message) => {
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => documentList()),
      http.post(`*/api/applications/${APP_ID}/documents`, () => failure(status, "x")),
    );
    renderAt(`/applications/${APP_ID}/upload`);

    await userEvent.setup().upload(await screen.findByLabelText("Choose files"), png("big.png"));

    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("says a file is already stored when the API answers with a document it holds", async () => {
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () =>
        documentList(doc("d1", "read", "id_proof")),
      ),
      http.post(`*/api/applications/${APP_ID}/documents`, () =>
        HttpResponse.json(doc("d1", "read", "id_proof"), { status: 200 }),
      ),
    );
    renderAt(`/applications/${APP_ID}/upload`);
    await screen.findByText("Read: ID proof");

    await userEvent.setup().upload(screen.getByLabelText("Choose files"), png("same.png"));

    expect(await screen.findByText("Already stored")).toBeInTheDocument();
  });

  it("asks again every three seconds while a document is being read and stops when it is read", async () => {
    let lists = 0;
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => {
        lists += 1;
        return lists === 1
          ? documentList(doc("d1", "processing"))
          : documentList(doc("d1", "read", "12th_marksheet"));
      }),
    );
    renderAt(`/applications/${APP_ID}/upload`);

    expect(await screen.findByText("Reading")).toBeInTheDocument();
    expect(
      await screen.findByText("Read: 12th marksheet", {}, { timeout: 7000 }),
    ).toBeInTheDocument();
    const seen = lists;
    await delay(3500);

    expect(lists).toBe(seen);
  }, 15_000);

  it("shows a not-found notice and no file picker for an unknown application", async () => {
    server.use(
      http.get(`*/api/applications/${APP_ID}`, () => failure(404, "not_found")),
      http.get(`*/api/applications/${APP_ID}/documents`, () => failure(404, "not_found")),
    );
    renderAt(`/applications/${APP_ID}/upload`);

    expect(await screen.findByText("That application does not exist.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Choose files")).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Go to Applications" }));
  });

  it("does not send more than 100 files in one batch", async () => {
    let posts = 0;
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => documentList()),
      http.post(`*/api/applications/${APP_ID}/documents`, () => {
        posts += 1;
        return HttpResponse.json(doc("x", "uploaded"), { status: 202 });
      }),
    );
    renderAt(`/applications/${APP_ID}/upload`);
    const files = Array.from({ length: 101 }, (_, index) => png(`f${String(index)}.png`));

    await userEvent.setup().upload(await screen.findByLabelText("Choose files"), files);

    expect(await screen.findByText("Choose up to 100 files at a time.")).toBeInTheDocument();
    expect(posts).toBe(0);
  });

  it("stops before the next file when the person leaves the page", async () => {
    const sent: string[] = [];
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => documentList()),
      http.post(`*/api/applications/${APP_ID}/documents`, async ({ request }) => {
        const form = await request.formData();
        sent.push(await (form.get("file") as Blob).text());
        await delay(150);
        return HttpResponse.json(doc("n", "uploaded"), { status: 202 });
      }),
    );
    const view = renderAt(`/applications/${APP_ID}/upload`);
    const user = userEvent.setup();
    await user.upload(await screen.findByLabelText("Choose files"), [
      png("one.png"),
      png("two.png"),
    ]);
    await waitFor(() => {
      expect(sent).toEqual(["one.png"]);
    });

    view.unmount();
    await delay(400);

    expect(sent).toEqual(["one.png"]);
  });

  it("shows a reload notice when the documents cannot be fetched", async () => {
    server.use(
      knownApplication(),
      http.get(`*/api/applications/${APP_ID}/documents`, () => failure(500, "internal")),
    );
    renderAt(`/applications/${APP_ID}/upload`);

    expect(await screen.findByText("The documents did not load.")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Reload" }));
  });
});
