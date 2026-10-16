import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { csvRows } from "./support/fixtures";
import { getAccounts, PASSWORD, SEED_DIR, WEB_ORIGIN, type LiveAccount } from "./support/stack";

// The live suite (NOTASK-31): the same journeys as e2e/*.spec.ts, but against the real API, a real
// Postgres and the real RapidOCR reader. Locators are copied from the mocked specs on purpose, so a
// drift between the fake and the server shows up as a failure in one suite and not the other.
// The journeys run in order on one database; each leaves the data the next one reads.
test.describe.configure({ mode: "serial" });

const REF = "SYN-APP-003"; // two deliberate date-of-birth mismatches: the reader flags it
const OTHER_REF = "SYN-APP-011"; // imported, never given a document
const BAD_ROW_REF = "SYN-APP-099";
const CLEAN_REF = "SYN-APP-001"; // three clean documents: Verified once all three are read

async function signInThroughUi(page: Page, account: LiveAccount) {
  await page.goto("/sign-in");
  await page.getByLabel("Username").fill(account.username);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

/** Start a session without the sign-in form; the cookies land in the browser context. */
async function signInThroughApi(page: Page, account: LiveAccount) {
  const response = await page.request.post("/api/auth/login", {
    headers: { Origin: WEB_ORIGIN },
    data: { username: account.username, password: account.password },
  });
  expect(response.status()).toBe(200);
}

/** The two headers a state-changing request needs: the page's origin and the CSRF token. */
async function writeHeaders(page: Page) {
  const cookies = await page.context().cookies(WEB_ORIGIN);
  const token = cookies.find((c) => c.name === "docket_csrf")?.value ?? "";
  return { Origin: WEB_ORIGIN, "X-CSRF-Token": token };
}

interface DocumentRow {
  status: string;
  failure_reason: string | null;
}

/** Wait for every document of one application to be read; a failed read ends the wait loudly. */
async function expectAllRead(page: Page, applicationId: string, count: number) {
  await expect
    .poll(
      async () => {
        const response = await page.request.get(`/api/applications/${applicationId}/documents`);
        const body = (await response.json()) as { data: DocumentRow[] };
        const failed = body.data.find((d) => d.status === "failed");
        if (failed) {
          throw new Error(`a document failed to read: ${failed.failure_reason ?? "no reason"}`);
        }
        return body.data.map((d) => d.status);
      },
      { timeout: 120_000, intervals: [500, 1000, 2000] },
    )
    .toEqual(Array<string>(count).fill("read"));
}

/** Import SYN-APP-001 and upload its three pages through the API (setup, not the journey). */
async function readOneApplication(page: Page) {
  const headers = await writeHeaders(page);
  const imported = await page.request.post("/api/imports", {
    headers,
    multipart: {
      file: { name: "clean.csv", mimeType: "text/csv", buffer: Buffer.from(csvRows([CLEAN_REF])) },
    },
  });
  expect(imported.status()).toBe(201);
  const list = await page.request.get("/api/applications?limit=100");
  const rows = ((await list.json()) as { data: { id: string; application_ref: string }[] }).data;
  const id = rows.find((a) => a.application_ref === CLEAN_REF)?.id ?? "";
  expect(id).not.toBe("");
  for (const type of ["10th_marksheet", "12th_marksheet", "id_proof"]) {
    const uploaded = await page.request.post(`/api/applications/${id}/documents`, {
      headers,
      multipart: {
        mode: "free",
        file: {
          name: `${CLEAN_REF}_${type}.png`,
          mimeType: "image/png",
          buffer: readFileSync(path.join(SEED_DIR, "png", `${CLEAN_REF}_${type}.png`)),
        },
      },
    });
    expect(uploaded.status()).toBe(202);
  }
  await expectAllRead(page, id, 3);
}

test.describe("sign in and out", () => {
  test("a staff member signs in, sees the staff links and signs out", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
    await page.getByLabel("Username").fill(getAccounts().staff.username);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("heading", { name: "Applications" })).toBeVisible();
    // Scoped to the main navigation: on an empty database the page body offers a second
    // "Import applications" link, which the fake (always three rows) never shows.
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Import applications" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Export verified list" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Review queue" })).toHaveCount(0);

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
  });

  test("a verifier lands on the review queue and has no import link", async ({ page }) => {
    await signInThroughUi(page, getAccounts().verifier);

    await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
    await expect(
      page
        .getByRole("navigation", { name: "Main" })
        .getByRole("link", { name: "Import applications" }),
    ).toHaveCount(0);
  });

  test("a wrong password keeps the person on the sign-in page with a message", async ({ page }) => {
    // A name that is not an account, so the five-failure lockout cannot hit a shared account.
    await page.goto("/sign-in");
    await page.getByLabel("Username").fill("e2e.nobody");
    await page.getByLabel("Password").fill("not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("a signed-out visitor is sent to sign in from a protected page", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page).toHaveURL(/\/sign-in/);
  });

  test("the status page shows the real API as ok", async ({ page }) => {
    await page.goto("/status");

    await expect(page.getByRole("heading", { name: "API health" })).toBeVisible();
    await expect(page.getByRole("status")).toContainText("ok");
  });
});

test.describe("sign up", () => {
  // Real only: the mocked suite has no register route. One test, because the server allows 10
  // sign-ups per source per hour and global setup already used two.
  test("a weak password is refused, then a new verifier is created and signed in", async ({
    page,
  }) => {
    const username = `e2e.signup.${Date.now().toString(36)}`;

    await page.goto("/sign-up");
    await page.getByLabel("Your name").fill("E2E Signup");
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill("weakpass1!");
    await page.getByRole("radio", { name: /^Verifier/ }).click();
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("The password needs a capital letter.")).toBeVisible();

    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  });
});

test.describe("intake", () => {
  test("an import reports what was created and why a row was refused", async ({ page }) => {
    await signInThroughApi(page, getAccounts().staff);
    const badRow = csvRows([REF])
      .split("\n")[1]
      ?.replace(REF, BAD_ROW_REF)
      .replace("2008-11-14", "31/02/2008");
    const csv = `${csvRows([REF, OTHER_REF])}${badRow ?? ""}\n`;

    await page.goto("/import");
    await page
      .locator('input[type="file"]')
      .setInputFiles({ name: "apps.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
    await page.getByRole("button", { name: "Import applications" }).click();

    await expect(page.getByRole("heading", { name: "Imported 2 of 3 rows." })).toBeVisible();
    // The fake says "2 rows were refused"; the singular is the real wording for one row.
    await expect(page.getByText("1 row was refused")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Unreadable date" })).toBeVisible();
  });

  test("an application with no documents says which are still needed", async ({ page }) => {
    await signInThroughApi(page, getAccounts().staff);

    await page.goto("/applications");
    await page
      .getByRole("row", { name: new RegExp(OTHER_REF) })
      .getByRole("link", { name: "Open" })
      .click();

    await expect(page.getByText(/^Still needed: /)).toContainText("id proof");
  });

  test("two pages are uploaded, read by the real reader and counted", async ({ page }) => {
    test.setTimeout(180_000);
    await signInThroughApi(page, getAccounts().staff);

    await page.goto("/applications");
    await page
      .getByRole("row", { name: new RegExp(REF) })
      .getByRole("link", { name: /Add documents/ })
      .click();
    await expect(page.getByRole("heading", { name: `Documents for ${REF}` })).toBeVisible();
    const applicationId = /\/applications\/([0-9a-f-]{36})/.exec(page.url())?.[1] ?? "";
    await page
      .locator('input[type="file"]')
      .setInputFiles(
        ["10th_marksheet", "transfer_certificate"].map((type) =>
          path.join(SEED_DIR, "png", `${REF}_${type}.png`),
        ),
      );

    await expectAllRead(page, applicationId, 2);

    await page.reload();
    await expect(page.getByText("2 read, 0 reading, 0 failed.")).toBeVisible();
  });

  test("Vision is not offered because no key is configured", async ({ page }) => {
    await signInThroughApi(page, getAccounts().staff);

    const response = await page.request.get("/api/capabilities");

    expect(await response.json()).toEqual({ vision: false });
  });
});

test.describe("review and decide", () => {
  test("a rejection needs a reason, is saved, and the application leaves the queue", async ({
    page,
  }) => {
    await signInThroughApi(page, getAccounts().verifier);

    await page.goto("/queue");
    await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
    await page.getByRole("button", { name: /Review newest/ }).click();
    await expect(page.getByRole("heading", { name: REF })).toBeVisible();
    await page.getByRole("button", { name: /^Decide/ }).click();
    await page.getByRole("radio", { name: /^Reject/ }).click();
    await page.getByRole("button", { name: "Save decision" }).click();
    await expect(page.getByText("Give a reason for the rejection.")).toBeVisible();

    await page.getByLabel("Reason").fill("Scan is of another person");
    await page.getByRole("button", { name: "Save decision" }).click();

    await expect(page.getByText("Decision saved")).toBeVisible();
    await expect(page.getByText("Nothing needs review.")).toBeVisible();
  });

  // The stale-page 409 needs two verifiers racing; it stays in the mocked suite (e2e/review.spec.ts).
  test("a staff member opening the review page cannot decide", async ({ page }) => {
    await signInThroughApi(page, getAccounts().staff);

    await page.goto("/applications");
    await page
      .getByRole("row", { name: new RegExp(REF) })
      .getByRole("link", { name: "Open" })
      .click();

    await expect(page.getByRole("heading", { name: REF })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Decide/ })).toHaveCount(0);
  });
});

test.describe("reports", () => {
  test("the overview counts what this run imported and the rejection", async ({ page }) => {
    await signInThroughApi(page, getAccounts().staff);

    await page.goto("/dashboard");

    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("2 applications")).toBeVisible();
    await expect(page.getByText("of which 1 rejected")).toBeVisible();
  });

  test("the export page says nothing is Verified yet and offers no file", async ({ page }) => {
    // Real only: the fake always has one Verified row ("1 rows"). On a database with none, the
    // real page shows an empty state and no Download button.
    await signInThroughApi(page, getAccounts().staff);

    await page.goto("/export");

    await expect(page.getByText("No applications are Verified yet.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Download CSV" })).toHaveCount(0);
  });

  test("an approved application is counted and downloads as a CSV file", async ({ page }) => {
    test.setTimeout(180_000);
    // Real OCR leaves SYN-APP-001 flagged ("Low confidence on marks: English"), so it is Verified
    // by a person's approval, which is the path a real export depends on.
    await signInThroughApi(page, getAccounts().staff);
    await readOneApplication(page);
    await signInThroughApi(page, getAccounts().verifier);
    await page.goto("/queue");
    await page.getByRole("button", { name: /Review newest/ }).click();
    await expect(page.getByRole("heading", { name: CLEAN_REF })).toBeVisible();
    await page.getByRole("button", { name: /^Decide/ }).click();
    await page.getByRole("radio", { name: /^Approve/ }).click();
    await page.getByRole("button", { name: "Save decision" }).click();
    await expect(page.getByText("Decision saved")).toBeVisible();

    await signInThroughApi(page, getAccounts().staff);
    await page.goto("/export");
    await expect(page.getByText("1 rows")).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download CSV" }).click();

    const file = await download;
    // The fake names the file verified.csv; the real server stamps the time into the name.
    expect(file.suggestedFilename()).toMatch(/^verified-\d{8}-\d{6}\.csv$/);
    expect(readFileSync(await file.path(), "utf8")).toContain(CLEAN_REF);
  });
});
