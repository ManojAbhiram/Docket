import { expect, test } from "@playwright/test";

import { mockApi } from "./support/mockApi";

const CSV = "application_id,name\nSYN-1,Asha Rao\n";

test.describe("intake", () => {
  test("an import reports what was created and why rows were refused", async ({ page }) => {
    const api = await mockApi(page, {
      signedInAs: "staff",
      importOutcome: {
        rows_read: 3,
        rows_created: 1,
        errors: [
          { row_number: 2, column_name: "date_of_birth", reason_code: "bad_date" },
          { row_number: 3, column_name: "name", reason_code: "missing_value" },
        ],
      },
    });

    await page.goto("/import");
    await page
      .locator('input[type="file"]')
      .setInputFiles({ name: "apps.csv", mimeType: "text/csv", buffer: Buffer.from(CSV) });
    await page.getByRole("button", { name: "Import applications" }).click();

    await expect(page.getByRole("heading", { name: "Imported 1 of 3 rows." })).toBeVisible();
    await expect(page.getByText("2 rows were refused")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Unreadable date" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Missing value" })).toBeVisible();
    expect(api.imports).toBe(1);
  });

  test("the import button waits for a file", async ({ page }) => {
    await mockApi(page, { signedInAs: "staff" });

    await page.goto("/import");

    await expect(page.getByRole("button", { name: "Import applications" })).toBeDisabled();
  });

  test("an application with no documents says which are still needed", async ({ page }) => {
    await mockApi(page, { signedInAs: "staff" });

    await page.goto("/applications");
    await page.getByRole("link", { name: "Open" }).nth(1).click();

    await expect(page.getByText("Still needed: 10th marksheet, id proof")).toBeVisible();
  });

  test("a page is uploaded against an application", async ({ page }) => {
    const api = await mockApi(page, { signedInAs: "staff" });

    await page.goto("/applications");
    await page
      .getByRole("link", { name: /Add documents/ })
      .nth(1)
      .click();
    await expect(page.getByRole("heading", { name: "Documents for SYN-APP-005" })).toBeVisible();
    await page.locator('input[type="file"]').setInputFiles({
      name: "marksheet.png",
      mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgo=", "base64"),
    });

    await expect.poll(() => api.uploads).toBe(1);
  });
});
