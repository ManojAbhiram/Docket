import {
  infiniteQueryOptions,
  queryOptions,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/hooks";

import { decide, fetchApplication, fetchQueue } from "./api";
import type { DecisionInput } from "./schemas";

export const reviewKeys = {
  all: ["review"] as const,
  queue: () => [...reviewKeys.all, "queue"] as const,
  application: (id: string) => [...reviewKeys.all, "application", id] as const,
};

export function queueQueryOptions() {
  return infiniteQueryOptions({
    queryKey: reviewKeys.queue(),
    queryFn: ({ pageParam, signal }) => fetchQueue(pageParam, { signal }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.page.next_cursor ?? undefined,
  });
}

export function useQueue() {
  return useInfiniteQuery(queueQueryOptions());
}

export function applicationQueryOptions(id: string) {
  return queryOptions({
    queryKey: reviewKeys.application(id),
    queryFn: ({ signal }) => fetchApplication(id, { signal }),
    // The ETag must be the one the screen shows, so a stale copy is never reused.
    staleTime: 0,
  });
}

export function useApplication(id: string) {
  return useQuery(applicationQueryOptions(id));
}

/** Send a decision, then refresh the application and the queue it leaves. */
export function useDecide(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationKey: [...reviewKeys.all, "decide", id],
    mutationFn: ({ input, etag }: { input: DecisionInput; etag: string }) =>
      decide(id, input, etag),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: reviewKeys.application(id) }),
        client.invalidateQueries({ queryKey: reviewKeys.queue() }),
        client.invalidateQueries({ queryKey: reportKeys.dashboard() }),
      ]);
    },
  });
}
