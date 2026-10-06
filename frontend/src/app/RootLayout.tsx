import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Suspense } from "react";

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
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="border-b">
        <nav
          aria-label="Main"
          className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-4 py-3"
        >
          <Link to="/" className="font-semibold">
            Docket
          </Link>
          {me &&
            LINKS.filter((link) => link.roles.includes(me.role)).map((link) => (
              <Link key={link.to} to={link.to} className="text-sm hover:underline">
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
      <main className="mx-auto max-w-5xl px-4 py-8">
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
