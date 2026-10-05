import type { ReactNode } from "react";

import { FIELDS } from "@/features/applications/fixtures";
import { CompareView } from "@/features/review/components/CompareView";

/** The compare screen a decision dialog opens over, so the dialog is judged in its context. */
export function CompareBehindDialog({
  reference,
  children,
}: {
  reference: string;
  children: ReactNode;
}) {
  return (
    <>
      <CompareView
        reference={reference}
        name="Latha Sharma"
        status="needs_review"
        fields={FIELDS}
      />
      {children}
    </>
  );
}
