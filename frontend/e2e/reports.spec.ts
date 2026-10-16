import { expect, test } from "@playwright/test";

import { mockApi } from "./support/mockApi";

test.describe("reports", () => {
  test("the overview shows a count for each status", async ({ page }) => {
    await mockApi(page, { signedInAs: "staff" });

    await page.goto("/dashboard");

    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("3 applications")).toBeVisible();
    await expect(page.getByText("of which 0 rejected")).toBeVisible();
  });

  test("the verified list downloads as a CSV file", async ({ page }) => {
    await mockApi(page, { signedInAs: "staff" });

    await page.goto("/export");
    await expect(page.getByText("1 rows")).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download CSV" }).click();

    expect((await download).suggestedFilename()).toBe("verified.csv");
  });
});
