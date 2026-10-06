import { z } from "zod";

import { apiFetch } from "@/lib/api";

import {
  applicationListSchema,
  documentListSchema,
  documentSchema,
  importResultSchema,
  type DocumentBody,
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

/** uploadDocument stores one scan against an application. */
export function uploadDocument(applicationId: string, file: File): Promise<DocumentBody> {
  const body = new FormData();
  body.append("file", file);
  return apiFetch(`/api/applications/${applicationId}/documents`, documentSchema, {
    method: "POST",
    body,
  });
}

const applicationRefSchema = z.object({ id: z.string(), application_ref: z.string() });

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
