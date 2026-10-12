import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { reportKeys } from "@/features/reports/hooks";
import { reviewKeys } from "@/features/review/hooks";
import { server } from "@/test/msw";

import { intakeKeys, useApplications, useDocuments } from "./hooks";

const APP_ID = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b";

function wrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function page(data: unknown[]) {
  return HttpResponse.json({ data, page: { next_cursor: null, has_more: false } });
}

function document(status: string, type: string | null) {
  return {
    id: "d1",
    application_id: APP_ID,
    detected_type: type,
    status,
    failure_reason: null,
    is_current: true,
    created_at: "2026-10-05T04:12:41Z",
    requested_mode: "free",
    read_engine: null,
    fallback_reason: null,
  };
}

describe("status after a document is read", () => {
  it("marks every screen that shows a status as out of date once a waiting document is read", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const keys = [
      intakeKeys.applications({}),
      reviewKeys.queue(),
      reviewKeys.application(APP_ID),
      intakeKeys.application(APP_ID),
      reportKeys.dashboard(),
    ];
    for (const key of keys) {
      client.setQueryData(key, { stale: true });
    }
    let reads = 0;
    server.use(
      http.get(`*/api/applications/${APP_ID}/documents`, () => {
        reads += 1;
        return reads === 1
          ? page([document("processing", null)])
          : page([document("read", "12th_marksheet")]);
      }),
    );
    const { result } = renderHook(() => useDocuments(APP_ID), { wrapper: wrapper(client) });
    await waitFor(() => {
      expect(result.current.data?.data[0]?.status).toBe("processing");
    });
    expect(keys.map((key) => client.getQueryState(key)?.isInvalidated)).toEqual(
      keys.map(() => false),
    );

    await client.invalidateQueries({ queryKey: intakeKeys.documents(APP_ID) });

    await waitFor(() => {
      expect(result.current.data?.data[0]?.status).toBe("read");
    });
    await waitFor(() => {
      expect(keys.map((key) => client.getQueryState(key)?.isInvalidated)).toEqual(
        keys.map(() => true),
      );
    });
  });
});

describe("the applications list", () => {
  it("asks the API again each time it is opened, even inside the usual 30 s cache", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 30_000 } },
    });
    let lists = 0;
    server.use(
      http.get("*/api/applications", () => {
        lists += 1;
        return page([]);
      }),
    );
    const first = renderHook(() => useApplications({}), { wrapper: wrapper(client) });
    await waitFor(() => {
      expect(first.result.current.isSuccess).toBe(true);
    });
    first.unmount();

    const second = renderHook(() => useApplications({}), { wrapper: wrapper(client) });
    await waitFor(() => {
      expect(second.result.current.isSuccess).toBe(true);
    });

    await waitFor(() => {
      expect(lists).toBe(2);
    });
  });
});
