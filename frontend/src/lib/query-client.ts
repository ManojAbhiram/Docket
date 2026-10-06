import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api";

/** createQueryClient builds the app's client; tests build their own with retry off. */
export function createQueryClient(): QueryClient {
  // A 401 from anywhere but the session check itself means the session ended: forget who was
  // signed in, and the route guard sends the browser to sign-in with its notice.
  const endSession = (error: unknown, key: readonly unknown[] | undefined) => {
    if (error instanceof ApiError && error.status === 401 && key?.[0] !== "auth") {
      client.setQueryData(["auth", "me"], null);
    }
  };
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        endSession(error, query.queryKey);
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        endSession(error, mutation.options.mutationKey);
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // A 4xx will not change on retry; one retry covers a blip elsewhere.
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            return false;
          }
          return failureCount < 1;
        },
      },
    },
  });
  return client;
}

export const queryClient = createQueryClient();
