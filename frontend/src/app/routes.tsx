import type { QueryClient } from "@tanstack/react-query";
import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  type RouterHistory,
} from "@tanstack/react-router";

import { HomePage } from "@/app/HomePage";
import { HomeRedirect } from "@/app/HomeRedirect";
import { NotFound } from "@/app/NotFound";
import { RootLayout } from "@/app/RootLayout";
import { RouteError } from "@/app/RouteError";
import { GalleryIndex, GalleryScreen } from "@/design/Gallery";
import { parseGallerySearch } from "@/design/registry";
import { AuthGate, RequireRole } from "@/features/auth/components/AuthGate";
import { SignInPage } from "@/features/auth/components/SignInPage";
import { ApplicationsPage } from "@/features/intake/pages/ApplicationsPage";
import { ImportPage } from "@/features/intake/pages/ImportPage";
import { UploadPage } from "@/features/intake/pages/UploadPage";
import { DashboardPage } from "@/features/reports/pages/DashboardPage";
import { ExportPage } from "@/features/reports/pages/ExportPage";
import { ComparePage } from "@/features/review/pages/ComparePage";
import { QueuePage } from "@/features/review/pages/QueuePage";

// Code-based routes. A route that needs data adds
// `loader: ({ context }) => context.queryClient.ensureQueryData(options)`
// and its component calls `useSuspenseQuery(options)`; a route that reads the
// URL adds `validateSearch: searchSchema.parse`. A loader or component that
// throws lands in RouteError (the root errorComponent) with the layout intact.
interface RouterContext {
  queryClient: QueryClient;
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  errorComponent: RouteError,
  notFoundComponent: NotFound,
});

const signInRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sign-in",
  validateSearch: (search: Record<string, unknown>): { reason?: "ended" } =>
    search.reason === "ended" ? { reason: "ended" } : {},
  component: function SignInRoute() {
    const { reason } = signInRoute.useSearch();
    return <SignInPage ended={reason === "ended"} />;
  },
});

const statusRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/status",
  component: HomePage,
});

// Everything below needs a session: AuthGate sends the browser to sign-in without one.
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  component: AuthGate,
});

const homeRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  component: HomeRedirect,
});

const applicationsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/applications",
  component: ApplicationsPage,
});

const importRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/import",
  component: function ImportRoute() {
    return (
      <RequireRole roles={["staff"]}>
        <ImportPage />
      </RequireRole>
    );
  },
});

const uploadRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/applications/$id/upload",
  component: function UploadRoute() {
    return (
      <RequireRole roles={["staff"]}>
        <UploadPage />
      </RequireRole>
    );
  },
});

const compareRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/applications/$id",
  component: ComparePage,
});

const queueRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/queue",
  // `decided` is set when the verifier arrives from a saved decision, so focus lands on Review newest.
  validateSearch: (search: Record<string, unknown>): { decided?: true } =>
    search.decided === true || search.decided === "true" ? { decided: true } : {},
  component: QueuePage,
});

const dashboardRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/dashboard",
  component: DashboardPage,
});

const exportRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/export",
  component: function ExportRoute() {
    return (
      <RequireRole roles={["staff"]}>
        <ExportPage />
      </RequireRole>
    );
  },
});

// The design gallery: every *.screen.tsx in every state, inside this layout.
// On in `vite dev`, and in a build only with VITE_DESIGN_GALLERY=1 (the
// design review and the smoke run use it); a production build drops it.
export const designGalleryEnabled =
  import.meta.env.DEV || import.meta.env.VITE_DESIGN_GALLERY === "1";

const galleryIndexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/__design",
  component: () => <GalleryIndex />,
});

const galleryScreenRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/__design/$id",
  validateSearch: parseGallerySearch,
  component: function GalleryScreenRoute() {
    const { id } = galleryScreenRoute.useParams();
    const search = galleryScreenRoute.useSearch();
    return <GalleryScreen id={id} search={search} />;
  },
});

const appRoutes = appRoute.addChildren([
  homeRoute,
  applicationsRoute,
  importRoute,
  uploadRoute,
  compareRoute,
  queueRoute,
  dashboardRoute,
  exportRoute,
]);

export const routeTree = rootRoute.addChildren([
  signInRoute,
  statusRoute,
  appRoutes,
  ...(designGalleryEnabled ? [galleryIndexRoute, galleryScreenRoute] : []),
]);

interface AppRouterOptions {
  queryClient: QueryClient;
  /** Memory history for tests; browser history by default. */
  history?: RouterHistory;
}

export function createAppRouter({ queryClient, history }: AppRouterOptions) {
  return createRouter({
    routeTree,
    context: { queryClient },
    defaultPreload: "intent",
    defaultErrorComponent: RouteError,
    scrollRestoration: true,
    ...(history ? { history } : {}),
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
