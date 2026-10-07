import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { Suspense } from "react";

import { mainWidthClass } from "@/app/layout";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { useLogout, useMe } from "@/features/auth/hooks";
import type { Role } from "@/features/auth/schemas";

const LINKS: {
  to: "/queue" | "/applications" | "/import" | "/dashboard" | "/export";
  label: string;
  roles: Role[];
}[] = [
  { to: "/queue", label: "Review queue", roles: ["verifier"] },
  { to: "/applications", label: "Applications", roles: ["staff", "verifier"] },
  { to: "/import", label: "Import", roles: ["staff"] },
  { to: "/dashboard", label: "Dashboard", roles: ["staff", "verifier"] },
  { to: "/export", label: "Export", roles: ["staff"] },
];

/**
 * RootLayout frames every route: header with navigation for the signed-in role, then the outlet.
 * The Suspense boundary is where a lazy route or a useSuspenseQuery waits, so the header stays
 * put while a page loads.
 */
export function RootLayout() {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return (
    <div className="min-h-svh bg-background text-foreground">
      <p className="flex h-8 items-center justify-center bg-muted px-4 text-center text-sm text-muted-foreground">
        Synthetic data only. No real student records.
      </p>
      <header className="border-b">
        <nav
          aria-label="Main"
          className={`mx-auto flex ${mainWidthClass(pathname)} flex-wrap items-center gap-x-3 gap-y-0 px-4 py-1 sm:gap-x-4 sm:py-3`}
        >
          <Link to="/" className="inline-flex min-h-11 items-center font-semibold sm:min-h-9">
            Docket
          </Link>
          {me &&
            LINKS.filter((link) => link.roles.includes(me.role)).map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="inline-flex min-h-11 items-center px-1 text-sm underline-offset-8 hover:underline sm:min-h-9"
                activeProps={{ className: "font-semibold text-primary underline decoration-2" }}
              >
                {link.label}
              </Link>
            ))}
          <div className="ml-auto flex items-center gap-3">
            {me && (
              <>
                <span className="text-sm text-muted-foreground">{me.display_name}</span>
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-11 sm:min-h-8"
                  disabled={logout.isPending}
                  onClick={() => {
                    logout.mutate(undefined, {
                      onSettled: () => {
                        void navigate({ to: "/sign-in" });
                      },
                    });
                  }}
                >
                  Sign out
                </Button>
              </>
            )}
            <ThemeToggle />
          </div>
        </nav>
      </header>
      <main className={`mx-auto ${mainWidthClass(pathname)} px-4 py-8`}>
        <Suspense
          fallback={
            <p role="status" aria-live="polite" className="text-muted-foreground">
              Loading
            </p>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <Toaster />
    </div>
  );
}
