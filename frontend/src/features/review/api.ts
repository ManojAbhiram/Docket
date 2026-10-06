import { apiFetch, apiFetchWithHeaders } from "@/lib/api";
import { env } from "@/lib/env";

import {
  applicationDetailSchema,
  decisionSchema,
  queuePageSchema,
  type ApplicationDetail,
  type Decision,
  type DecisionInput,
  type QueuePage,
} from "./schemas";

const PAGE_SIZE = 20;

/** The applications waiting for a verifier: needs review and not rejected, newest change first. */
export function fetchQueue(
  cursor: string | undefined,
  init: Pick<RequestInit, "signal"> = {},
): Promise<QueuePage> {
  const query = new URLSearchParams({
    "filter[status]": "needs_review",
    "filter[rejected]": "false",
    limit: String(PAGE_SIZE),
  });
  if (cursor) {
    query.set("cursor", cursor);
  }
  return apiFetch(`/api/applications?${query.toString()}`, queuePageSchema, init);
}

export interface LoadedApplication {
  application: ApplicationDetail;
  /** The version the verifier sees. A decision sends it back so a stale page cannot win. */
  etag: string;
}

export async function fetchApplication(
  id: string,
  init: Pick<RequestInit, "signal"> = {},
): Promise<LoadedApplication> {
  const { data, headers } = await apiFetchWithHeaders(
    `/api/applications/${encodeURIComponent(id)}`,
    applicationDetailSchema,
    init,
  );
  return { application: data, etag: headers.get("ETag") ?? "" };
}

export function decide(id: string, input: DecisionInput, etag: string): Promise<Decision> {
  return apiFetch(`/api/applications/${encodeURIComponent(id)}/decisions`, decisionSchema, {
    method: "POST",
    headers: { "If-Match": etag },
    body: JSON.stringify(input),
  });
}

/** Where a document's stored page is served from. The browser sends the session cookie itself. */
export function documentImageUrl(documentId: string): string {
  return `${env.VITE_API_URL}/api/documents/${encodeURIComponent(documentId)}/image`;
}
