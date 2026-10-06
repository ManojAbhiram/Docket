import { ApiError, apiFetch } from "@/lib/api";
import { env } from "@/lib/env";

import { dashboardSchema, type DashboardCounts } from "./schemas";

/** fetchDashboard reads GET /api/dashboard: counts by status, no personal data. */
export function fetchDashboard(init: Pick<RequestInit, "signal"> = {}): Promise<DashboardCounts> {
  return apiFetch("/api/dashboard", dashboardSchema, init);
}

export interface VerifiedFile {
  blob: Blob;
  fileName: string;
  /** Data rows, the header excluded. */
  rows: number;
}

const FALLBACK_NAME = "verified.csv";

function fileNameOf(header: string | null): string {
  const match = header ? /filename="?([^";]+)"?/.exec(header) : null;
  return match?.[1] ?? FALLBACK_NAME;
}

function serverCodeOf(body: string): string | undefined {
  try {
    const parsed: unknown = JSON.parse(body);
    if (typeof parsed === "object" && parsed !== null && "error" in parsed) {
      const error = parsed.error;
      if (typeof error === "object" && error !== null && "code" in error) {
        return typeof error.code === "string" ? error.code : undefined;
      }
    }
  } catch {
    return undefined;
  }
  return undefined;
}

/**
 * downloadVerifiedList reads GET /api/exports/verified.csv with the session cookie. apiFetch
 * parses JSON, so the file comes through fetch directly; errors are the same ApiError.
 */
export async function downloadVerifiedList(
  init: Pick<RequestInit, "signal"> = {},
): Promise<VerifiedFile> {
  let response: Response;
  try {
    response = await fetch(`${env.VITE_API_URL}/api/exports/verified.csv`, {
      ...init,
      credentials: "include",
      headers: { Accept: "text/csv" },
    });
  } catch (cause) {
    throw new ApiError("network", 0, "GET /api/exports/verified.csv: network error", cause);
  }
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(
      "http",
      response.status,
      `GET /api/exports/verified.csv: ${String(response.status)}`,
      body,
      { serverCode: serverCodeOf(body) },
    );
  }
  const text = await response.text();
  const lines = text.split(/\r?\n/).filter((line) => line.length > 0);
  return {
    blob: new Blob([text], { type: "text/csv" }),
    fileName: fileNameOf(response.headers.get("Content-Disposition")),
    rows: Math.max(lines.length - 1, 0),
  };
}
