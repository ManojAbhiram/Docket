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

/** The ghost buttons on the deep teal header: light text, a faint fill on hover. */
const ON_HEADER =
  "text-header-foreground hover:bg-header-foreground/15 hover:text-header-foreground";

/**
 * RootLayout frames every route: a deep teal header with navigation for the signed-in role, then the
 * outlet. The Suspense boundary is where a lazy route or a useSuspenseQuery waits, so the header
 * stays put while a page loads. The page under it is keyed by the path, so a new route fades up once
 * and a refresh of the same route does not.
 */
export function RootLayout() {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="app-header bg-header text-header-foreground">
        <nav
          aria-label="Main"
          className={`mx-auto flex ${mainWidthClass(pathname)} flex-wrap items-center gap-x-1 gap-y-0 px-4 py-1 sm:gap-x-2 sm:py-2`}
        >
          <Link
            to="/"
            className="mr-2 inline-flex min-h-11 items-center font-display text-lg font-semibold sm:min-h-9"
          >
            Docket
          </Link>
          {me &&
            LINKS.filter((link) => link.roles.includes(me.role)).map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="inline-flex min-h-11 items-center rounded-md px-3 text-sm transition-colors duration-(--duration-fast) hover:bg-header-foreground/15 sm:min-h-9"
                activeProps={{
                  className: "bg-header-foreground/20 font-semibold",
                  "aria-current": "page",
                }}
              >
                {link.label}
              </Link>
            ))}
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            {me && (
              <>
                <span className="hidden text-sm text-header-foreground/90 sm:inline">
                  {me.display_name}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`min-h-11 border border-header-foreground/40 sm:min-h-8 ${ON_HEADER}`}
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
            <ThemeToggle className={ON_HEADER} />
          </div>
        </nav>
      </header>
      <p className="flex min-h-8 items-center justify-center bg-muted px-4 py-1 text-center text-sm text-muted-foreground">
        Synthetic data only. No real student records.
      </p>
      <main className={`mx-auto ${mainWidthClass(pathname)} px-4 py-8`}>
        <div key={pathname} className="route-enter">
          <Suspense
            fallback={
              <p role="status" aria-live="polite" className="text-muted-foreground">
                Loading
              </p>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>
      <Toaster />
    </div>
  );
}
