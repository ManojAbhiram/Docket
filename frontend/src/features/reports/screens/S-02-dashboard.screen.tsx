import type { ScreenModule } from "@/design/screen";
import { COUNTS } from "@/features/applications/fixtures";
import { DashboardView } from "@/features/reports/components/DashboardView";

export const screen: ScreenModule["screen"] = {
  id: "S-02",
  name: "Dashboard",
  feature: "reports",
  job: "Shows how many applications are Verified, Needs review and Missing documents, and leads to the next job.",
  states: {
    loading: () => <DashboardView audience="staff" counts={null} loading />,
    empty: () => (
      <DashboardView
        audience="staff"
        counts={{ verified: 0, needsReview: 0, rejected: 0, missingDocuments: 0 }}
      />
    ),
    "error: internal": () => (
      <DashboardView
        audience="staff"
        counts={null}
        notice={{
          title: "The counts did not load.",
          body: "Reload the page, or quote request 4f1c0a8e3b7d4a0c to the engineering team.",
          action: "Reload",
        }}
      />
    ),
    "error: unauthorized": () => (
      <DashboardView
        audience="staff"
        counts={null}
        notice={{
          tone: "info",
          title: "You were signed out.",
          body: "Sign in to continue.",
          action: "Sign in",
        }}
      />
    ),
    "error: unavailable": () => (
      <DashboardView
        audience="staff"
        counts={null}
        notice={{
          title: "Docket cannot reach its database.",
          body: "Try again in a minute.",
          action: "Try again",
        }}
      />
    ),
    success: () => <DashboardView audience="staff" counts={COUNTS} />,
    "success: verifier": () => <DashboardView audience="verifier" counts={COUNTS} />,
    offline: () => <DashboardView audience="staff" counts={COUNTS} asOf="10:12 am" />,
  },
};
