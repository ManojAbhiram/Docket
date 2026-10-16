import { expect, test } from "@playwright/test";

import { FAILED_DOCUMENT_ID, mockApi } from "./support/mockApi";

const UPLOAD_PAGE = "/applications/0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7c/upload";

test.describe("reprocess a failed document", () => {
  test("staff retry a failed document and it leaves the failed state", async ({ page }) => {
    const api = await mockApi(page, { signedInAs: "staff", failedDocument: true });

    await page.goto(UPLOAD_PAGE);

    await expect(page.getByText("Reading took too long. Reprocess it to try again.")).toBeVisible();
    await expect(page.getByText("0 read, 0 reading, 1 failed.")).toBeVisible();
    await page.getByRole("button", { name: "Reprocess" }).click();

    await expect(page.getByRole("button", { name: "Reprocess" })).toHaveCount(0);
    await expect(page.getByText("Reading took too long.")).toHaveCount(0);
    await expect(page.getByText("1 read, 0 reading, 0 failed.")).toBeVisible({ timeout: 10_000 });
    expect(api.reprocesses).toEqual([FAILED_DOCUMENT_ID]);
  });

  test("the button is disabled while the request is pending", async ({ page }) => {
    const api = await mockApi(page, { signedInAs: "staff", failedDocument: true });
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route("**/api/documents/*/reprocess", async (route) => {
      await gate;
      await route.fallback();
    });

    await page.goto(UPLOAD_PAGE);
    const button = page.getByRole("button", { name: "Reprocess" });
    await button.click();

    await expect(button).toBeDisabled();
    expect(api.reprocesses).toHaveLength(0);

    release();
    await expect(button).toHaveCount(0);
    expect(api.reprocesses).toHaveLength(1);
  });

  test("a document that is no longer failed says so and the list refreshes", async ({ page }) => {
    const api = await mockApi(page, {
      signedInAs: "staff",
      failedDocument: true,
      failedDocumentSettlesFirst: true,
    });

    await page.goto(UPLOAD_PAGE);
    await expect(page.getByText("0 read, 0 reading, 1 failed.")).toBeVisible();
    await page.getByRole("button", { name: "Reprocess" }).click();

    await expect(page.getByText("That document is no longer failed.")).toBeVisible();
    await expect(page.getByText("1 read, 0 reading, 0 failed.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Reprocess" })).toHaveCount(0);
    expect(api.reprocesses).toHaveLength(1);
  });

  test("a verifier is not given the upload page or the button", async ({ page }) => {
    const api = await mockApi(page, { signedInAs: "verifier", failedDocument: true });

    await page.goto(UPLOAD_PAGE);

    await expect(
      page.getByRole("heading", { name: "This page is not for your role" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Reprocess" })).toHaveCount(0);
    expect(api.reprocesses).toHaveLength(0);
  });
});
