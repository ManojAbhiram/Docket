import type { ScreenModule } from "@/design/screen";
import { APPLICATIONS } from "@/features/applications/fixtures";
import { ApplicationsView } from "@/features/intake/components/ApplicationsView";

export const screen: ScreenModule["screen"] = {
  id: "S-04",
  name: "Applications",
  feature: "intake",
  job: "Lists every application with its status so staff can find one and add its documents.",
  states: {
    loading: () => <ApplicationsView applications={[]} loading />,
    empty: () => <ApplicationsView applications={[]} />,
    "error: internal": () => (
      <ApplicationsView
        applications={[]}
        notice={{
          title: "The list did not load.",
          body: "Reload, or quote request 7c0e5a19 to the engineering team.",
          action: "Reload",
        }}
      />
    ),
    "error: unavailable": () => (
      <ApplicationsView
        applications={[]}
        notice={{
          title: "Docket cannot reach its database.",
          body: "Try again in a minute.",
          action: "Try again",
        }}
      />
    ),
    success: () => <ApplicationsView applications={APPLICATIONS} total={APPLICATIONS.length} />,
    partial: () => <ApplicationsView applications={APPLICATIONS} total={5000} />,
    "filtered empty": () => <ApplicationsView applications={[]} filter="verified" total={0} />,
    offline: () => <ApplicationsView applications={APPLICATIONS} total={5000} offline />,
  },
};
