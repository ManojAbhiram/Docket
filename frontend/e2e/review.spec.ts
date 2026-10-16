import { expect, test, type Page } from "@playwright/test";

import { mockApi } from "./support/mockApi";

async function openFlagged(page: Page) {
  await page.goto("/queue");
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  await page.getByRole("button", { name: /Review newest/ }).click();
  await expect(page.getByRole("heading", { name: "SYN-APP-004" })).toBeVisible();
}

test.describe("review and decide", () => {
  test("a rejection needs a reason, is saved, and the application leaves the queue", async ({
    page,
  }) => {
    const api = await mockApi(page, { signedInAs: "verifier" });

    await openFlagged(page);
    await page.getByRole("button", { name: /^Decide/ }).click();
    await page.getByRole("radio", { name: /^Reject/ }).click();
    await page.getByRole("button", { name: "Save decision" }).click();
    await expect(page.getByText("Give a reason for the rejection.")).toBeVisible();

    await page.getByLabel("Reason").fill("Scan is of another person");
    await page.getByRole("button", { name: "Save decision" }).click();

    await expect(page.getByText("Decision saved")).toBeVisible();
    await expect(page.getByText("Nothing needs review.")).toBeVisible();
    expect(api.decisions).toEqual([{ action: "reject", reason: "Scan is of another person" }]);
  });

  test("the dashboard counts a rejection as part of Needs review", async ({ page }) => {
    await mockApi(page, { signedInAs: "verifier" });

    await openFlagged(page);
    await page.getByRole("button", { name: /^Decide/ }).click();
    await page.getByRole("radio", { name: /^Reject/ }).click();
    await page.getByLabel("Reason").fill("Not legible");
    await page.getByRole("button", { name: "Save decision" }).click();
    await expect(page.getByText("Nothing needs review.")).toBeVisible();

    await page.getByRole("link", { name: "Overview" }).click();

    await expect(page.getByText("1 rejected")).toBeVisible();
  });

  test("an approval of a stale page tells the verifier the application changed", async ({
    page,
  }) => {
    const api = await mockApi(page, { signedInAs: "verifier", conflictOnNextDecision: true });

    await openFlagged(page);
    await page.getByRole("button", { name: /^Decide/ }).click();
    await page.getByRole("radio", { name: /^Approve/ }).click();
    await page.getByRole("button", { name: "Save decision" }).click();

    await expect(
      page.getByText("This application changed while you were looking at it."),
    ).toBeVisible();
    expect(api.decisions).toEqual([]);
  });

  test("a staff member opening the review page cannot decide", async ({ page }) => {
    await mockApi(page, { signedInAs: "staff" });

    await page.goto("/applications");
    await page.getByRole("link", { name: "Open" }).first().click();

    await expect(page.getByRole("heading", { name: "SYN-APP-004" })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Decide/ })).toHaveCount(0);
  });
});
