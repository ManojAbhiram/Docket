import type { ReactNode } from "react";

import type { ScreenModule } from "@/design/screen";
import { CompareBehindDialog } from "@/features/review/components/CompareBehindDialog";
import { DecisionDialogView } from "@/features/review/components/DecisionDialogView";

const REF = "SYN-APP-004";

/** The dialog opens over the compare screen it was opened from. */
function over(dialog: ReactNode): ReactNode {
  return <CompareBehindDialog reference={REF}>{dialog}</CompareBehindDialog>;
}

export const screen: ScreenModule["screen"] = {
  id: "S-08",
  name: "Decision dialog",
  feature: "review",
  job: "Records an approve, a corrected value or a rejection with its reason.",
  states: {
    loading: () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          initialAction="reject"
          reason="Name does not match."
          busy
        />,
      ),
    empty: () => over(<DecisionDialogView reference={REF} fieldLabel="Name" />),
    "error: validation_error": () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          initialAction="reject"
          reasonError="Add a reason to reject this application."
        />,
      ),
    "error: conflict": () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          initialAction="approve"
          notice={{
            title: "This application changed or was already decided.",
            body: "Close this dialog and reload.",
            action: "Close and reload",
          }}
        />,
      ),
    "error: forbidden": () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          notice={{ title: "Only verifiers can decide applications." }}
        />,
      ),
    "error: idempotency_conflict": () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          initialAction="reject"
          reason="Name does not match the marksheet."
          notice={{
            title: "This decision was already sent with different text.",
            body: "Review it and confirm again.",
          }}
        />,
      ),
    "error: unavailable": () =>
      over(
        <DecisionDialogView
          reference={REF}
          fieldLabel="Name"
          initialAction="approve"
          notice={{
            title: "Docket cannot reach its database.",
            body: "Nothing was saved. Try again in a minute.",
          }}
        />,
      ),
    success: () =>
      over(
        <>
          <DecisionDialogView
            reference={REF}
            fieldLabel="Name"
            initialAction="approve"
            open={false}
          />
          <p role="status" className="py-4 text-success">
            Decision saved: Approved
          </p>
        </>,
      ),
    offline: () =>
      over(
        <DecisionDialogView reference={REF} fieldLabel="Name" initialAction="approve" offline />,
      ),
  },
};
