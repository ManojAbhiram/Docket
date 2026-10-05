import type { ScreenModule } from "@/design/screen";
import { ExportView } from "@/features/reports/components/ExportView";

export const screen: ScreenModule["screen"] = {
  id: "S-09",
  name: "Export verified list",
  feature: "reports",
  job: "Downloads the Verified applications as a CSV.",
  states: {
    loading: () => <ExportView verifiedCount={3812} busy />,
    empty: () => <ExportView verifiedCount={0} />,
    "error: forbidden": () => (
      <ExportView
        verifiedCount={null}
        notice={{ title: "Only staff can export the verified list." }}
      />
    ),
    "error: internal": () => (
      <ExportView
        verifiedCount={3812}
        notice={{
          title: "The export did not finish.",
          body: "Try again, or quote request 9b2d1c7a to the engineering team.",
          action: "Try again",
        }}
      />
    ),
    "error: unavailable": () => (
      <ExportView
        verifiedCount={3812}
        notice={{
          title: "Docket cannot reach its database.",
          body: "Try again in a minute.",
          action: "Try again",
        }}
      />
    ),
    success: () => (
      <ExportView verifiedCount={3812} done="Downloaded verified.csv with 3,812 rows." />
    ),
    offline: () => <ExportView verifiedCount={3812} offline />,
  },
};
