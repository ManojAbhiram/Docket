import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchMe, login, logout } from "./api";
import type { Role, User } from "./schemas";

export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
  login: () => [...authKeys.all, "login"] as const,
  logout: () => [...authKeys.all, "logout"] as const,
};

/** The signed-in user, or null. Shared by the route guards and every component that asks. */
export function meQueryOptions() {
  return queryOptions({
    queryKey: authKeys.me(),
    queryFn: ({ signal }) => fetchMe({ signal }),
    staleTime: 60_000,
  });
}

export function useMe() {
  return useQuery(meQueryOptions());
}

/** Where each role starts: the verifier works the queue, staff look after applications. */
export function homeFor(role: Role): "/queue" | "/applications" {
  return role === "verifier" ? "/queue" : "/applications";
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation<User, Error, Parameters<typeof login>[0]>({
    mutationKey: authKeys.login(),
    mutationFn: login,
    onSuccess: (user) => {
      client.setQueryData(authKeys.me(), user);
    },
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationKey: authKeys.logout(),
    mutationFn: logout,
    onSettled: () => {
      // Nothing a signed-out browser holds may outlive the session.
      client.setQueryData(authKeys.me(), null);
      client.removeQueries({ predicate: (query) => query.queryKey[0] !== authKeys.all[0] });
    },
  });
}
