import type { Page, Route } from "@playwright/test";

// A small stateful stand-in for the Docket API, so a journey can run in the browser without a
// server. The shapes follow src/features/*/schemas.ts; a response a schema would refuse is a
// bug in this file, not in the app. Every spec still mocks with page.route, as health.spec.ts does.

export type Role = "staff" | "verifier";
type Status = "verified" | "needs_review" | "missing_documents";

export const PASSWORD = "Correct!Pass1";

interface MockApplication {
  id: string;
  ref: string;
  name: string;
  status: Status;
  rejected: boolean;
  version: number;
}

export interface ImportOutcome {
  rows_read: number;
  rows_created: number;
  errors: { row_number: number; column_name: string | null; reason_code: string }[];
}

export interface MockOptions {
  /** Who the session belongs to. Null means signed out until a login succeeds. */
  signedInAs?: Role | null;
  /** What the next CSV import returns. */
  importOutcome?: ImportOutcome;
  /** When set, the next decision answers 409 once, as if another verifier decided first. */
  conflictOnNextDecision?: boolean;
  /** The application's document list holds one failed document that Reprocess can retry. */
  failedDocument?: boolean;
  /**
   * With failedDocument: the first list still shows the document as failed, but the server has
   * already read it, so Reprocess answers 409 document_not_failed and the next list says read.
   */
  failedDocumentSettlesFirst?: boolean;
}

export interface MockApi {
  decisions: { action: string; reason?: string }[];
  uploads: number;
  imports: number;
  /** Ids of the documents a reprocess request was sent for, in order. */
  reprocesses: string[];
  /** Where the signed-in session stands now. */
  session: () => Role | null;
}

const ID_FLAGGED = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b";
const ID_MISSING = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7c";
const ID_VERIFIED = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7d";
const DOCUMENT_ID = "0192b1c3-1a2b-7c4e-9a1b-2c3d4e5f6a7c";
export const FAILED_DOCUMENT_ID = "0192b1c3-1a2b-7c4e-9a1b-2c3d4e5f6a7e";

// A one pixel PNG, the page image the compare screen asks for.
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

const NO_SESSION = { error: { code: "unauthorized", message: "sign in" } };

function json(route: Route, status: number, body: unknown, headers: Record<string, string> = {}) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers,
    body: JSON.stringify(body),
  });
}

function detailOf(app: MockApplication) {
  const needsDocuments = app.status === "missing_documents";
  return {
    id: app.id,
    application_ref: app.ref,
    full_name: app.name,
    status: app.status,
    rejected: app.rejected,
    updated_at: "2026-10-05T09:12:41Z",
    father_name: "Salim Sharma",
    date_of_birth: "2006-12-10",
    board: "CBSE",
    roll_number: "SYN0945957",
    marks: { English: 59 },
    category: "General",
    created_at: "2026-10-05T09:00:00Z",
    missing_document_types: needsDocuments ? ["10th_marksheet", "id_proof"] : [],
    documents: needsDocuments
      ? []
      : [
          {
            id: DOCUMENT_ID,
            application_id: app.id,
            detected_type: "10th_marksheet",
            status: "read",
            failure_reason: null,
            is_current: true,
            created_at: "2026-10-05T09:05:00Z",
            requested_mode: "free",
            read_engine: "rapidocr",
            fallback_reason: null,
            fields: [
              {
                id: 11,
                field_name: "name",
                subject: null,
                value: "Latha Sharmaa",
                application_value: "Latha Sharma",
                confidence: 0.99,
                box: [220, 60, 120, 22],
                match_result: "mismatch",
                needs_review: true,
                review_reason: "mismatch",
              },
            ],
          },
        ],
  };
}

function failedDocumentBody(appId: string, status: "failed" | "uploaded" | "read") {
  return {
    id: FAILED_DOCUMENT_ID,
    application_id: appId,
    detected_type: status === "read" ? "10th_marksheet" : null,
    status,
    failure_reason: status === "failed" ? "timeout" : null,
    is_current: true,
    created_at: "2026-10-05T09:05:00Z",
    requested_mode: "free",
    read_engine: status === "read" ? "rapidocr" : null,
    fallback_reason: null,
  };
}

function listItem(app: MockApplication) {
  return {
    id: app.id,
    application_ref: app.ref,
    full_name: app.name,
    status: app.status,
    rejected: app.rejected,
    updated_at: "2026-10-05T09:12:41Z",
  };
}

/** Install the fake API on a page and return what it saw. Call before page.goto. */
export async function mockApi(page: Page, options: MockOptions = {}): Promise<MockApi> {
  let session: Role | null = options.signedInAs ?? null;
  let conflictPending = options.conflictOnNextDecision ?? false;
  const apps: MockApplication[] = [
    {
      id: ID_FLAGGED,
      ref: "SYN-APP-004",
      name: "Latha Sharma",
      status: "needs_review",
      rejected: false,
      version: 1,
    },
    {
      id: ID_MISSING,
      ref: "SYN-APP-005",
      name: "Diya Gupta",
      status: "missing_documents",
      rejected: false,
      version: 1,
    },
    {
      id: ID_VERIFIED,
      ref: "SYN-APP-006",
      name: "Asha Rao",
      status: "verified",
      rejected: false,
      version: 1,
    },
  ];
  let failedStatus: "failed" | "uploaded" | "read" = options.failedDocumentSettlesFirst
    ? "read"
    : "failed";
  let showStaleFailure = options.failedDocumentSettlesFirst ?? false;
  const seen: MockApi = {
    decisions: [],
    uploads: 0,
    imports: 0,
    reprocesses: [],
    session: () => session,
  };

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === "/api/auth/me") {
      return session
        ? json(route, 200, { id: "u1", display_name: "QA User", role: session })
        : json(route, 401, NO_SESSION);
    }
    if (path === "/api/auth/login" && method === "POST") {
      const body = request.postDataJSON() as { username: string; password: string };
      if (body.password !== PASSWORD) {
        return json(route, 401, { error: { code: "unauthorized", message: "wrong credentials" } });
      }
      session = body.username.startsWith("verifier") ? "verifier" : "staff";
      return json(route, 200, { id: "u1", display_name: "QA User", role: session });
    }
    if (path === "/api/auth/logout" && method === "POST") {
      session = null;
      return route.fulfill({ status: 204 });
    }
    if (!session) {
      return json(route, 401, NO_SESSION);
    }
    if (path === "/api/capabilities") {
      return json(route, 200, { vision: false });
    }
    if (path === "/api/dashboard") {
      const count = (status: Status) => apps.filter((a) => a.status === status).length;
      return json(route, 200, {
        verified: count("verified"),
        needs_review: count("needs_review"),
        missing_documents: count("missing_documents"),
        rejected: apps.filter((a) => a.rejected).length,
      });
    }
    if (path === "/api/imports" && method === "POST") {
      seen.imports += 1;
      const outcome = options.importOutcome ?? { rows_read: 1, rows_created: 1, errors: [] };
      return json(route, 201, {
        id: "imp-1",
        rows_read: outcome.rows_read,
        rows_created: outcome.rows_created,
        rows_rejected: outcome.errors.length,
        errors: outcome.errors,
      });
    }
    if (path === "/api/exports/verified.csv") {
      return route.fulfill({
        status: 200,
        contentType: "text/csv",
        headers: { "Content-Disposition": 'attachment; filename="verified.csv"' },
        body: "application_id,name\nSYN-APP-006,Asha Rao\n",
      });
    }
    if (path === "/api/applications" && method === "GET") {
      const status = url.searchParams.get("filter[status]");
      const rejected = url.searchParams.get("filter[rejected]");
      const rows = apps
        .filter((a) => (status ? a.status === status : true))
        .filter((a) => (rejected === null ? true : a.rejected === (rejected === "true")))
        .map(listItem);
      return json(route, 200, { data: rows, page: { next_cursor: null, has_more: false } });
    }
    const reprocess = /^\/api\/documents\/([^/]+)\/reprocess$/.exec(path);
    if (reprocess && method === "POST" && options.failedDocument) {
      if (session !== "staff") {
        return json(route, 403, { error: { code: "forbidden", message: "staff only" } });
      }
      if (reprocess[1] !== FAILED_DOCUMENT_ID) {
        return json(route, 404, { error: { code: "not_found", message: "no such document" } });
      }
      seen.reprocesses.push(reprocess[1]);
      if (failedStatus !== "failed") {
        return json(route, 409, {
          error: { code: "document_not_failed", message: "the document is not failed" },
        });
      }
      failedStatus = "uploaded";
      return json(route, 202, failedDocumentBody(ID_MISSING, "uploaded"));
    }
    const documentImage = /^\/api\/documents\/[^/]+\/image$/.exec(path);
    if (documentImage) {
      return route.fulfill({ status: 200, contentType: "image/png", body: PIXEL });
    }
    const inApplication = /^\/api\/applications\/([^/]+)(\/documents|\/decisions)?$/.exec(path);
    const app = inApplication ? apps.find((a) => a.id === inApplication[1]) : undefined;
    if (inApplication && !app) {
      return json(route, 404, { error: { code: "not_found", message: "no such application" } });
    }
    if (app && inApplication) {
      const tail = inApplication[2];
      if (!tail && method === "GET") {
        return json(route, 200, detailOf(app), { ETag: `"v${String(app.version)}"` });
      }
      if (tail === "/documents" && method === "GET" && options.failedDocument) {
        const shown = showStaleFailure ? "failed" : failedStatus;
        showStaleFailure = false;
        if (failedStatus === "uploaded") {
          failedStatus = "read"; // the worker finishes before the next poll
        }
        return json(route, 200, {
          data: [failedDocumentBody(app.id, shown)],
          page: { next_cursor: null, has_more: false },
        });
      }
      if (tail === "/documents" && method === "GET") {
        return json(route, 200, { data: [], page: { next_cursor: null, has_more: false } });
      }
      if (tail === "/documents" && method === "POST") {
        seen.uploads += 1;
        return json(route, 202, {
          id: DOCUMENT_ID,
          application_id: app.id,
          detected_type: null,
          status: "uploaded",
          failure_reason: null,
          is_current: true,
          created_at: "2026-10-05T09:05:00Z",
          requested_mode: "free",
          read_engine: null,
          fallback_reason: null,
        });
      }
      if (tail === "/decisions" && method === "POST") {
        const body = request.postDataJSON() as { action: string; reason?: string };
        if (conflictPending) {
          conflictPending = false;
          app.version += 1;
          return json(route, 409, {
            error: { code: "conflict", message: "the application changed" },
          });
        }
        if (request.headers()["if-match"] !== `"v${String(app.version)}"`) {
          return json(route, 409, {
            error: { code: "conflict", message: "the application changed" },
          });
        }
        if (body.action === "reject" && !body.reason) {
          return json(route, 422, {
            error: { code: "validation_error", message: "reason needed" },
          });
        }
        seen.decisions.push(body);
        if (body.action === "reject") {
          app.rejected = true;
        } else if (body.action === "approve") {
          app.status = "verified";
        }
        app.version += 1;
        return json(route, 201, {
          id: "d1",
          application_id: app.id,
          action: body.action,
          reason: body.reason ?? null,
          extracted_field_id: null,
          decided_by: "QA User",
          created_at: "2026-10-05T09:20:00Z",
          application_status: app.status,
        });
      }
    }
    return json(route, 404, {
      error: { code: "not_found", message: `unmocked ${method} ${path}` },
    });
  });

  return seen;
}
