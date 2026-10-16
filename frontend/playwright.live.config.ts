import { defineConfig, devices } from "@playwright/test";

import {
  API_ORIGIN,
  API_PORT,
  DATABASE_URL,
  REPO_ROOT,
  WEB_ORIGIN,
  WEB_PORT,
} from "./e2e-live/support/stack";

// The live suite (NOTASK-31): the real API, a real Postgres and the real RapidOCR reader behind
// the built UI. It is separate from playwright.config.ts on purpose: its own testDir, ports and
// servers, one worker, long timeouts, one browser. `make test-e2e-live` starts the database and
// drops it afterwards; this file starts the API and the preview server.
const isCI = Boolean(process.env.CI);
const databaseUrl = process.env.E2E_LIVE_DATABASE_URL ?? DATABASE_URL;

export default defineConfig({
  testDir: "e2e-live",
  outputDir: "test-results/live",
  globalSetup: "./e2e-live/global-setup.ts",
  // Journeys share one database and run in order: each leaves the data the next one reads.
  fullyParallel: false,
  workers: 1,
  forbidOnly: isCI,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: isCI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report/live" }]]
    : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: WEB_ORIGIN,
    actionTimeout: 10_000,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      // The real API with the real reader. Vision is blanked so a developer's .env cannot turn
      // it on; the process environment wins over .env in Settings.
      command: `uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port ${String(API_PORT)}`,
      cwd: REPO_ROOT,
      url: `${API_ORIGIN}/healthz`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_URL: databaseUrl,
        GATEWAY_ENGINE: "rapidocr",
        WORKER_ENABLED: "true",
        WORKER_IDLE_SECONDS: "0.5",
        SESSION_COOKIE_SECURE: "false",
        ALLOWED_ORIGINS: WEB_ORIGIN,
        OPENROUTER_API_KEY: "",
        OPENROUTER_MODEL: "",
        LOG_LEVEL: "warning",
      },
    },
    {
      // VITE_API_URL is blank so the build calls its own origin and the preview proxy forwards
      // /api to the API (a frontend/.env value would otherwise go cross-origin). dist-live keeps
      // the mocked suite's dist/ untouched.
      command: `pnpm exec vite build --outDir dist-live && pnpm exec vite preview --outDir dist-live --port ${String(WEB_PORT)} --strictPort`,
      url: WEB_ORIGIN,
      reuseExistingServer: false,
      timeout: 180_000,
      env: { VITE_API_URL: "", API_PROXY_TARGET: API_ORIGIN },
    },
  ],
  projects: [{ name: "chromium-live" }],
});
