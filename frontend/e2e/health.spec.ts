import { expect, test, type Route } from "@playwright/test";

// The API is mocked with page.route; no spec reaches a real server.
function ok(route: Route) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "ok", version: "e2e" }),
  });
}

function down(route: Route) {
  return route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ status: "down" }),
  });
}

test.describe("health", () => {
  // Regression: ISSUE-001 [NOTASK-14], found by /qa on 2026-10-10.
  // Report: .scratch/qa-NOTASK-14/qa-report-docket-2026-10-10.md
  // The public health route must work without a session or a running API server.
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "unauthorized", message: "sign in" } }),
      }),
    );
  });

  test("shows the API status and version", async ({ page }) => {
    await page.route("**/healthz", ok);

    await page.goto("/status");

    await expect(page.getByRole("heading", { name: "API health" })).toBeVisible();
    await expect(page.getByRole("status")).toContainText("ok");
    await expect(page.getByRole("status")).toContainText("e2e");
  });

  test("recovers through a keyboard-reachable retry", async ({ page }) => {
    let apiDown = true;
    await page.route("**/healthz", (route) => (apiDown ? down(route) : ok(route)));

    await page.goto("/status");

    const retry = page.getByRole("button", { name: "Retry" });
    await expect(retry).toBeVisible();
    await expect(page.getByRole("status")).toContainText("503");
    apiDown = false;
    await retry.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("status")).toContainText("ok");
  });

  test("shows the not-found page for an unknown path", async ({ page }) => {
    await page.goto("/nowhere");

    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
    await page.getByRole("link", { name: "Back to the start" }).click();
    await expect(page).toHaveURL(/\/sign-in$/);
  });
});
