import { useSuspenseQuery } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";

import { homeFor, meQueryOptions } from "@/features/auth/hooks";

/** The index route for a signed-in browser: each role starts where its work is. */
export function HomeRedirect() {
  const { data: me } = useSuspenseQuery(meQueryOptions());
  return <Navigate to={me ? homeFor(me.role) : "/sign-in"} replace />;
}
