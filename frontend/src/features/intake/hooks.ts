import {
  infiniteQueryOptions,
  queryOptions,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import type { BatchItem } from "@/features/intake/components/UploadView";
import { ApiError } from "@/lib/api";

import {
  fetchApplicationRef,
  importApplications,
  listApplications,
  listDocuments,
  uploadDocument,
  type ApplicationFilter,
} from "./api";

export const intakeKeys = {
  all: ["intake"] as const,
  applications: (filter: ApplicationFilter) => [...intakeKeys.all, "applications", filter] as const,
  documents: (applicationId: string) => [...intakeKeys.all, "documents", applicationId] as const,
  application: (applicationId: string) =>
    [...intakeKeys.all, "application", applicationId] as const,
};

export function applicationsQueryOptions(filter: ApplicationFilter) {
  return infiniteQueryOptions({
    queryKey: intakeKeys.applications(filter),
    queryFn: ({ pageParam, signal }) => listApplications(filter, pageParam, { signal }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.page.next_cursor ?? undefined,
  });
}

export function useApplications(filter: ApplicationFilter) {
  return useInfiniteQuery(applicationsQueryOptions(filter));
}

export const POLL_MS = 3000;

/** The documents of one application. While one is waiting or being read, it asks again every 3 s. */
export function useDocuments(applicationId: string) {
  return useQuery(
    queryOptions({
      queryKey: intakeKeys.documents(applicationId),
      queryFn: ({ signal }) => listDocuments(applicationId, { signal }),
      refetchInterval: (query) => {
        const pending = query.state.data?.data.some(
          (d) => d.status === "uploaded" || d.status === "processing",
        );
        return pending ? POLL_MS : false;
      },
    }),
  );
}

export function useApplicationRef(applicationId: string) {
  return useQuery(
    queryOptions({
      queryKey: intakeKeys.application(applicationId),
      queryFn: ({ signal }) => fetchApplicationRef(applicationId, { signal }),
    }),
  );
}

export function useImport() {
  return useMutation({ mutationFn: importApplications });
}

/** Why one file was not stored, in words that name the file and the next step. */
export function refusalFor(name: string, error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 413) {
      return `${name} is over 8 MiB. Choose a smaller scan or photo.`;
    }
    if (error.status === 415) {
      return `${name} is not a JPG, PNG or PDF. Choose one of those formats.`;
    }
    if (error.status === 422) {
      return `${name} could not be read as an image or PDF. Check the file and upload it again.`;
    }
    if (error.status === 403) {
      return "Only staff can upload documents.";
    }
    if (error.status === 404) {
      return "That application does not exist.";
    }
  }
  return `${name} did not upload. Check your connection and upload it again.`;
}

/**
 * One-by-one upload of the files a person chose. A file the API refuses does not stop the rest, a
 * second call while one batch runs is ignored, and leaving the page stops before the next file.
 * A file the API answers with a document it already holds is "already stored".
 */
export function useBatchUpload(applicationId: string) {
  const client = useQueryClient();
  const [items, setItems] = useState<BatchItem[]>([]);
  const alive = useRef(true);
  const running = useRef(false);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const start = useCallback(
    async (files: File[], known: ReadonlySet<string>) => {
      if (running.current || files.length === 0) {
        return;
      }
      running.current = true;
      const stamp = Date.now();
      setItems(
        files.map((file, index) => ({
          key: `${String(stamp)}-${String(index)}`,
          name: file.name,
          state: "waiting",
        })),
      );
      const seen = new Set(known);
      const mark = (index: number, patch: Partial<BatchItem>) => {
        if (alive.current) {
          setItems((current) =>
            current.map((item, at) => (at === index ? { ...item, ...patch } : item)),
          );
        }
      };
      try {
        for (const [index, file] of files.entries()) {
          if (!alive.current) {
            break;
          }
          mark(index, { state: "uploading" });
          try {
            const document = await uploadDocument(applicationId, file);
            mark(index, { state: seen.has(document.id) ? "already" : "stored" });
            seen.add(document.id);
          } catch (error) {
            mark(index, { state: "refused", problem: refusalFor(file.name, error) });
          }
          await client.invalidateQueries({ queryKey: intakeKeys.documents(applicationId) });
        }
      } finally {
        running.current = false;
      }
    },
    [applicationId, client],
  );

  const busy = items.some((item) => item.state === "waiting" || item.state === "uploading");
  return { items, start, busy };
}
