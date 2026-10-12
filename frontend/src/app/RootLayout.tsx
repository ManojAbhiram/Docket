import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { Suspense } from "react";

import { AppSidebar } from "@/app/AppSidebar";
import { mainWidthClass } from "@/app/layout";
import { DocketLogo } from "@/components/DocketLogo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Toaster } from "@/components/ui/sonner";
import { useMe } from "@/features/auth/hooks";

const ON_HEADER =
  "text-header-foreground hover:bg-header-foreground/15 hover:text-header-foreground focus-visible:ring-header-foreground";

function Page({ pathname }: { pathname: string }) {
  return (
    <>
      <p className="flex min-h-8 items-center justify-center bg-muted px-4 py-1 text-center text-sm text-muted-foreground">
        Synthetic data only. No real student records.
      </p>
      <div className={`mx-auto w-full ${mainWidthClass(pathname)} px-4 py-8`}>
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
      </div>
    </>
  );
}

const SKIP =
  "sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:text-foreground";

/**
 * RootLayout frames every route. A signed-in person gets the sidebar shell: the logo, the work for
 * their role, the Help Center and their account, with the page beside it (a drawer on a phone). The
 * sign in and sign up screens have no navigation to offer, so they keep a slim teal bar with the logo.
 * The Suspense boundary is where a lazy route or a useSuspenseQuery waits, so the shell stays put
 * while a page loads. The page is keyed by the path, so a new route fades up once and a refresh of
 * the same route does not.
 */
export function RootLayout() {
  const { data: me, isPending } = useMe();
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  // Until the session check answers, neither chrome is right, so show neither (no flash of the
  // wrong one, and no <main> that is replaced a moment later).
  if (isPending) {
    return (
      <div className="min-h-svh bg-background p-6 text-foreground">
        <p role="status" aria-live="polite" className="text-muted-foreground">
          Loading
        </p>
      </div>
    );
  }

  if (me) {
    return (
      <SidebarProvider className="bg-background text-foreground">
        <a href="#content" className={SKIP}>
          Skip to the page
        </a>
        <AppSidebar />
        <SidebarInset id="content" className="min-w-0">
          <header className="app-header flex min-h-14 items-center gap-2 bg-header px-3 text-header-foreground md:hidden">
            <SidebarTrigger className={`min-h-11 ${ON_HEADER}`} />
            <DocketLogo withName />
          </header>
          <Page pathname={pathname} />
        </SidebarInset>
        <Toaster />
      </SidebarProvider>
    );
  }

  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="app-header bg-header text-header-foreground">
        <nav
          aria-label="Main"
          className="mx-auto flex max-w-5xl items-center gap-2 px-4 py-1 sm:py-2"
        >
          <Link to="/" aria-label="Docket" className="inline-flex min-h-11 items-center lg:min-h-9">
            <DocketLogo withName />
          </Link>
          <div className="ml-auto">
            <ThemeToggle className={ON_HEADER} />
          </div>
        </nav>
      </header>
      <main>
        <Page pathname={pathname} />
      </main>
      <Toaster />
    </div>
  );
}
