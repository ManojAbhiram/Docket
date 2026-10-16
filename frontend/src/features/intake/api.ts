import { z } from "zod";

import { apiFetch } from "@/lib/api";

import {
  applicationListSchema,
  capabilitiesSchema,
  documentListSchema,
  documentSchema,
  importResultSchema,
  type DocumentBody,
  type ReadMode,
  type Status,
} from "./schemas";

const PAGE = 20;

/** importApplications sends one CSV. The API answers with counts and the refused rows. */
export function importApplications(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiFetch("/api/imports", importResultSchema, { method: "POST", body });
}

export interface ApplicationFilter {
  status?: Status | undefined;
}

export function listApplications(
  filter: ApplicationFilter,
  cursor: string | undefined,
  init: Pick<RequestInit, "signal"> = {},
) {
  const query = new URLSearchParams({ limit: String(PAGE) });
  if (filter.status) {
    query.set("filter[status]", filter.status);
  }
  if (cursor) {
    query.set("cursor", cursor);
  }
  return apiFetch(`/api/applications?${query.toString()}`, applicationListSchema, init);
}

/** uploadDocument stores one scan against an application, to be read the way `mode` says. */
export function uploadDocument(
  applicationId: string,
  file: File,
  mode: ReadMode,
): Promise<DocumentBody> {
  const body = new FormData();
  body.append("file", file);
  body.append("mode", mode);
  return apiFetch(`/api/applications/${applicationId}/documents`, documentSchema, {
    method: "POST",
    body,
  });
}

/** reprocessDocument queues a failed document to be read again. The API answers 409 if it is not failed. */
export function reprocessDocument(documentId: string): Promise<DocumentBody> {
  return apiFetch(`/api/documents/${documentId}/reprocess`, documentSchema, { method: "POST" });
}

const applicationRefSchema = z.object({
  id: z.string(),
  application_ref: z.string(),
  missing_document_types: z.array(z.string()).default([]),
});

/** The application's reference, to name the page. The rest of the detail is the review screen's. */
export function fetchApplicationRef(applicationId: string, init: Pick<RequestInit, "signal"> = {}) {
  return apiFetch(`/api/applications/${applicationId}`, applicationRefSchema, init);
}

export function listDocuments(applicationId: string, init: Pick<RequestInit, "signal"> = {}) {
  return apiFetch(
    `/api/applications/${applicationId}/documents?limit=100`,
    documentListSchema,
    init,
  );
}

/** What this server can do for the signed-in person, such as reading with Vision. */
export function fetchCapabilities(init: Pick<RequestInit, "signal"> = {}) {
  return apiFetch("/api/capabilities", capabilitiesSchema, init);
}
