import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Navigate, Outlet } from "@tanstack/react-router";
import type { ReactNode } from "react";

import { Notice } from "@/components/Notice";
import { authKeys, meQueryOptions } from "@/features/auth/hooks";
import type { Role } from "@/features/auth/schemas";

/**
 * Where to send a browser with no session. It says "you were signed out" only when the session
 * check has answered more than once: the first answer is the visit's own, so a person who never
 * signed in is not told they were.
 */
function SignInRedirect() {
  const client = useQueryClient();
  const answers = client.getQueryState(authKeys.me())?.dataUpdateCount ?? 0;
  return <Navigate to="/sign-in" search={answers > 1 ? { reason: "ended" } : {}} replace />;
}

/**
 * AuthGate wraps every route that needs a session. With no live session it sends the browser to
 * sign-in; the query it reads is the one the sign-in fills and the 401 handler empties, so a
 * session that ends mid-visit lands here too.
 */
export function AuthGate() {
  const { data: me } = useSuspenseQuery(meQueryOptions());
  if (me === null) {
    return <SignInRedirect />;
  }
  return <Outlet />;
}

/** RequireRole shows its children to the named roles and a plain notice to everyone else. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { data: me } = useSuspenseQuery(meQueryOptions());
  if (me === null) {
    return <SignInRedirect />;
  }
  if (!roles.includes(me.role)) {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <h1 className="text-[25px]">This page is not for your role</h1>
        <Notice tone="info" title="You cannot open this page.">
          Ask an administrator if you need access, or go back to your own work.
        </Notice>
      </div>
    );
  }
  return <>{children}</>;
}
