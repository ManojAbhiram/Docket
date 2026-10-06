import type { z } from "zod";

import { env } from "@/lib/env";

export type ApiErrorCode = "network" | "http" | "invalid_json" | "invalid_response";

interface ApiErrorExtra {
  /** The `error.code` the API sent, for example `unauthorized` or `too_many_attempts`. */
  serverCode?: string | undefined;
  /** Seconds from the `Retry-After` header, when the API sent one. */
  retryAfter?: number | undefined;
}

/** ApiError is the only error apiFetch throws; consumers switch on code and status. */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly details: unknown;
  readonly serverCode: string | undefined;
  readonly retryAfter: number | undefined;

  constructor(
    code: ApiErrorCode,
    status: number,
    message: string,
    details?: unknown,
    extra: ApiErrorExtra = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
    this.serverCode = extra.serverCode;
    this.retryAfter = extra.retryAfter;
  }
}

export const CSRF_COOKIE = "docket_csrf";
export const CSRF_HEADER = "X-CSRF-Token";

/** The anti-forgery token the sign-in left in a cookie, or undefined before sign-in. */
function csrfToken(): string | undefined {
  for (const part of document.cookie.split(";")) {
    const [name, ...value] = part.trim().split("=");
    if (name === CSRF_COOKIE) {
      return decodeURIComponent(value.join("="));
    }
  }
  return undefined;
}

export interface ApiResult<T> {
  data: T;
  headers: Headers;
}

/** The `error` object of the API's envelope, when the body has one. */
function serverCodeOf(body: string): string | undefined {
  try {
    const parsed: unknown = JSON.parse(body);
    if (typeof parsed === "object" && parsed !== null && "error" in parsed) {
      const error = parsed.error;
      if (typeof error === "object" && error !== null && "code" in error) {
        const code = error.code;
        return typeof code === "string" ? code : undefined;
      }
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function retryAfterOf(response: Response): number | undefined {
  const seconds = Number(response.headers.get("Retry-After"));
  return Number.isFinite(seconds) && seconds > 0 ? seconds : undefined;
}

/**
 * apiFetchWithHeaders calls the API, validates the JSON body with the schema and returns the typed
 * value with the response headers (an ETag, for example). Every request carries the session
 * cookie; a request that changes data also carries the anti-forgery token. Pass the query's signal
 * so navigation cancels the request.
 */
export async function apiFetchWithHeaders<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<ApiResult<T>> {
  const method = init.method ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD" && !headers.has(CSRF_HEADER)) {
    const token = csrfToken();
    if (token !== undefined) {
      headers.set(CSRF_HEADER, token);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${env.VITE_API_URL}${path}`, {
      ...init,
      headers,
      credentials: "include",
    });
  } catch (cause) {
    throw new ApiError("network", 0, `${method} ${path}: network error`, cause);
  }

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(
      "http",
      response.status,
      `${method} ${path}: ${String(response.status)} ${response.statusText}`.trim(),
      body,
      { serverCode: serverCodeOf(body), retryAfter: retryAfterOf(response) },
    );
  }

  // 204 and 205 have no body: the schema decides whether none is acceptable
  // (z.undefined() for a DELETE), so a no-content call still checks its status.
  if (response.status === 204 || response.status === 205) {
    const parsed = schema.safeParse(undefined);
    if (!parsed.success) {
      throw new ApiError(
        "invalid_response",
        response.status,
        `${method} ${path}: expected a body, got ${String(response.status)}`,
        parsed.error.issues,
      );
    }
    return { data: parsed.data, headers: response.headers };
  }

  let json: unknown;
  try {
    json = await response.json();
  } catch (cause) {
    throw new ApiError(
      "invalid_json",
      response.status,
      `${method} ${path}: body is not JSON`,
      cause,
    );
  }

  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new ApiError(
      "invalid_response",
      response.status,
      `${method} ${path}: response failed validation`,
      parsed.error.issues,
    );
  }
  return { data: parsed.data, headers: response.headers };
}

/** apiFetch is apiFetchWithHeaders for a caller that needs only the body. */
export async function apiFetch<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  return (await apiFetchWithHeaders(path, schema, init)).data;
}
