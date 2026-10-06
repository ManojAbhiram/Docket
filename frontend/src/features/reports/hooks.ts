import { queryOptions, useMutation, useQuery } from "@tanstack/react-query";

import { downloadVerifiedList, fetchDashboard } from "./api";

export const reportKeys = {
  all: ["reports"] as const,
  dashboard: () => [...reportKeys.all, "dashboard"] as const,
  export: () => [...reportKeys.all, "export"] as const,
};

export const REFRESH_MS = 30_000;

/** The counts, read again every 30 seconds while the tab is in front. */
export function dashboardQueryOptions() {
  return queryOptions({
    queryKey: reportKeys.dashboard(),
    queryFn: ({ signal }) => fetchDashboard({ signal }),
    refetchInterval: REFRESH_MS,
    refetchIntervalInBackground: false,
  });
}

export function useDashboard() {
  return useQuery(dashboardQueryOptions());
}

export function useVerifiedExport() {
  return useMutation({
    mutationKey: reportKeys.export(),
    mutationFn: () => downloadVerifiedList(),
  });
}
