import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { server } from "@/test/msw";

import { downloadVerifiedList, fetchDashboard } from "./api";

// jsdom's Blob has no text(), so the test reads it the way a browser page would.
function textOf(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve(typeof reader.result === "string" ? reader.result : "");
    };
    reader.onerror = () => {
      reject(new Error("could not read the blob"));
    };
    reader.readAsText(blob);
  });
}

describe("fetchDashboard", () => {
  it("reads the counts and names them the way the screens do", async () => {
    server.use(
      http.get("*/api/dashboard", () =>
        HttpResponse.json({ verified: 12, needs_review: 3, missing_documents: 5, rejected: 1 }),
      ),
    );

    expect(await fetchDashboard()).toEqual({
      verified: 12,
      needsReview: 3,
      missingDocuments: 5,
      rejected: 1,
    });
  });

  it("refuses an answer that is not the counts", async () => {
    server.use(http.get("*/api/dashboard", () => HttpResponse.json({ verified: "many" })));

    await expect(fetchDashboard()).rejects.toMatchObject({ code: "invalid_response" });
  });
});

describe("downloadVerifiedList", () => {
  const csv = "application_id,name\nSYN-APP-001,Latha Sharma\nSYN-APP-002,Diya Gupta\n";

  it("returns the file, the name the server gave it and the number of data rows", async () => {
    server.use(
      http.get(
        "*/api/exports/verified.csv",
        () =>
          new HttpResponse(csv, {
            headers: {
              "Content-Type": "text/csv; charset=utf-8",
              "Content-Disposition": 'attachment; filename="verified-20261006T101200Z.csv"',
            },
          }),
      ),
    );

    const file = await downloadVerifiedList();

    expect(file.fileName).toBe("verified-20261006T101200Z.csv");
    expect(file.rows).toBe(2);
    expect(await textOf(file.blob)).toBe(csv);
  });

  it("counts no rows for a file that holds only its header", async () => {
    server.use(
      http.get("*/api/exports/verified.csv", () => new HttpResponse("application_id,name\n")),
    );

    expect((await downloadVerifiedList()).rows).toBe(0);
  });

  it("falls back to a plain file name when the server sent none", async () => {
    server.use(http.get("*/api/exports/verified.csv", () => new HttpResponse("a,b\n1,2\n")));

    expect((await downloadVerifiedList()).fileName).toBe("verified.csv");
  });

  it("keeps the status and the server's code when the export is refused", async () => {
    server.use(
      http.get("*/api/exports/verified.csv", () =>
        HttpResponse.json({ error: { code: "forbidden", message: "no" } }, { status: 403 }),
      ),
    );

    const failure = await downloadVerifiedList().catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ status: 403, serverCode: "forbidden" });
  });

  it("wraps a network failure", async () => {
    server.use(http.get("*/api/exports/verified.csv", () => HttpResponse.error()));

    await expect(downloadVerifiedList()).rejects.toMatchObject({ code: "network" });
  });
});
