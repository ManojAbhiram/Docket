import { expect, test } from "@playwright/test";

import { mockApi, PASSWORD } from "./support/mockApi";

test.describe("sign in and out", () => {
  test("a staff member signs in, sees the staff links and signs out", async ({ page }) => {
    const api = await mockApi(page);

    await page.goto("/");
    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
    await page.getByLabel("Username").fill("staff.one");
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("heading", { name: "Applications" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Import applications" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Export verified list" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Review queue" })).toHaveCount(0);

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
    expect(api.session()).toBeNull();
  });

  test("a verifier lands on the review queue and has no import link", async ({ page }) => {
    await mockApi(page);

    await page.goto("/sign-in");
    await page.getByLabel("Username").fill("verifier.one");
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Import applications" })).toHaveCount(0);
  });

  test("a wrong password keeps the person on the sign-in page with a message", async ({ page }) => {
    const api = await mockApi(page);

    await page.goto("/sign-in");
    await page.getByLabel("Username").fill("staff.one");
    await page.getByLabel("Password").fill("not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/sign-in(\?|$)/);
    await expect(page.getByRole("alert")).toBeVisible();
    expect(api.session()).toBeNull();
  });

  test("a signed-out visitor is sent to sign in from a protected page", async ({ page }) => {
    await mockApi(page);

    await page.goto("/dashboard");

    await expect(page).toHaveURL(/\/sign-in/);
  });
});
