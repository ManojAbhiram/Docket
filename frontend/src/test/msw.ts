import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

/**
 * Mock Service Worker for unit tests. setup.ts starts this server for every
 * test, so a request that no handler answers fails the test instead of
 * reaching the network. A test that needs another answer calls
 * `server.use(http.get(...))`; handlers reset after each test.
 *
 * VITE_API_URL is set to an absolute origin in vitest.config.ts so the
 * request URLs match these patterns.
 */
export const handlers = [
  http.get("*/healthz", () => HttpResponse.json({ status: "ok", version: "msw" })),
  // The counts are unavailable unless a test provides them, so no screen may depend on them.
  http.get("*/api/dashboard", () =>
    HttpResponse.json({ error: { code: "unavailable", message: "x" } }, { status: 503 }),
  ),
];

export const server = setupServer(...handlers);
