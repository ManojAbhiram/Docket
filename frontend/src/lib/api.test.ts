import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { jsonResponse } from "@/test/render";

import { ApiError, apiFetch, apiFetchWithHeaders } from "./api";

const schema = z.object({ id: z.string() });

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) {
      return error;
    }
    throw error;
  }
  throw new Error("expected apiFetch to throw");
}

describe("apiFetch", () => {
  it("returns the parsed body and sends JSON headers", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse({ id: "a1", extra: true })));
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch("/things/a1", schema, {
      method: "POST",
      body: JSON.stringify({ name: "x" }),
    });

    expect(result).toEqual({ id: "a1" });
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Accept")).toBe("application/json");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("wraps a network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("offline"))),
    );

    const error = await failure(apiFetch("/things", schema));

    expect(error.code).toBe("network");
    expect(error.status).toBe(0);
  });

  it("wraps a non-2xx status with the body as details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("nope", { status: 404, statusText: "Not Found" }))),
    );

    const error = await failure(apiFetch("/things/x", schema));

    expect(error.code).toBe("http");
    expect(error.status).toBe(404);
    expect(error.details).toBe("nope");
    expect(error.message).toBe("GET /things/x: 404 Not Found");
  });

  it("accepts 204 No Content when the schema allows no body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
    );

    await expect(
      apiFetch("/things/a1", z.undefined(), { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });

  it("rejects a 204 when the schema expects a body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
    );

    const error = await failure(apiFetch("/things/a1", schema));

    expect(error.code).toBe("invalid_response");
  });

  it("rejects a body that is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("<html>", { status: 200 }))),
    );

    const error = await failure(apiFetch("/things", schema));

    expect(error.code).toBe("invalid_json");
  });

  it("rejects a body that fails the schema with the issues as details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ id: 7 }))),
    );

    const error = await failure(apiFetch("/things", schema));

    expect(error.code).toBe("invalid_response");
    expect(Array.isArray(error.details)).toBe(true);
  });
});

describe("apiFetch and the session", () => {
  function stubFetch() {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse({ id: "a1" })));
    vi.stubGlobal("fetch", fetchMock);
    return () => {
      const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      return init;
    };
  }

  it("sends the session cookie with every request", async () => {
    const sent = stubFetch();

    await apiFetch("/api/things", schema);

    expect(sent().credentials).toBe("include");
  });

  it("adds the anti-forgery token from its cookie to a request that changes data", async () => {
    document.cookie = "docket_csrf=abc123; path=/";
    const sent = stubFetch();

    await apiFetch("/api/things", schema, { method: "POST", body: "{}" });

    expect(new Headers(sent().headers).get("X-CSRF-Token")).toBe("abc123");
    document.cookie = "docket_csrf=; path=/; max-age=0";
  });

  it("does not add the token to a read", async () => {
    document.cookie = "docket_csrf=abc123; path=/";
    const sent = stubFetch();

    await apiFetch("/api/things", schema);

    expect(new Headers(sent().headers).has("X-CSRF-Token")).toBe(false);
    document.cookie = "docket_csrf=; path=/; max-age=0";
  });

  it("lets the browser set the content type of a file upload", async () => {
    const sent = stubFetch();
    const form = new FormData();
    form.append("file", new Blob(["a,b"], { type: "text/csv" }), "a.csv");

    await apiFetch("/api/imports", schema, { method: "POST", body: form });

    expect(new Headers(sent().headers).has("Content-Type")).toBe(false);
  });

  it("keeps the error code and the wait the server sent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ error: { code: "too_many_attempts", message: "slow" } }), {
            status: 429,
            headers: { "Retry-After": "42" },
          }),
        ),
      ),
    );

    const error = await failure(apiFetch("/api/auth/login", schema, { method: "POST" }));

    expect(error.status).toBe(429);
    expect(error.serverCode).toBe("too_many_attempts");
    expect(error.retryAfter).toBe(42);
  });

  it("has no server code when the error body is not the API's envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("<html>", { status: 502 }))),
    );

    const error = await failure(apiFetch("/api/things", schema));

    expect(error.serverCode).toBeUndefined();
    expect(error.retryAfter).toBeUndefined();
  });

  it("returns the response headers when asked, for an ETag", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ id: "a1" }), {
            status: 200,
            headers: { ETag: '"v1"', "Content-Type": "application/json" },
          }),
        ),
      ),
    );

    const result = await apiFetchWithHeaders("/api/things/a1", schema);

    expect(result.data).toEqual({ id: "a1" });
    expect(result.headers.get("ETag")).toBe('"v1"');
  });
});
