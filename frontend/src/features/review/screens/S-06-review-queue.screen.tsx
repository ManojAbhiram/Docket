import type { ScreenModule } from "@/design/screen";
import { QUEUE } from "@/features/applications/fixtures";
import { QueueView } from "@/features/review/components/QueueView";

export const screen: ScreenModule["screen"] = {
  id: "S-06",
  name: "Review queue",
  feature: "review",
  job: "Lists the flagged applications a verifier still has to decide.",
  states: {
    loading: () => <QueueView items={[]} loading />,
    empty: () => <QueueView items={[]} />,
    "error: internal": () => (
      <QueueView
        items={[]}
        notice={{
          title: "The queue did not load.",
          body: "Reload, or quote request 5d3b7e02 to the engineering team.",
          action: "Reload",
        }}
      />
    ),
    "error: forbidden": () => (
      <QueueView
        items={[]}
        notice={{
          title: "Only verifiers work the review queue.",
          action: "Go to the dashboard",
        }}
      />
    ),
    "error: unavailable": () => (
      <QueueView
        items={[]}
        notice={{
          title: "Docket cannot reach its database.",
          body: "Try again in a minute.",
          action: "Try again",
        }}
      />
    ),
    success: () => <QueueView items={QUEUE} total={QUEUE.length} />,
    partial: () => <QueueView items={QUEUE} total={611} />,
    offline: () => <QueueView items={QUEUE} total={611} offline />,
  },
};
