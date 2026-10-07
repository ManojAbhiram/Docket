import { Ban, Check, Flag, Minus, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusKind = "verified" | "needs_review" | "missing_documents" | "rejected";

const STATUS: Record<StatusKind, { label: string; icon: LucideIcon; tone: string }> = {
  verified: { label: "Verified", icon: Check, tone: "bg-success-subtle text-success" },
  needs_review: { label: "Needs review", icon: Flag, tone: "bg-warning-subtle text-warning" },
  missing_documents: {
    label: "Missing documents",
    icon: Minus,
    tone: "bg-info-subtle text-info",
  },
  rejected: { label: "Rejected", icon: Ban, tone: "bg-danger-subtle text-destructive" },
};

/**
 * A status as a word and a shape, never colour alone. When the status of a mounted badge changes
 * (a decision saved, a refresh that moved an application on) the new badge pops in once; a badge
 * that first appears with its data, and a refresh that changes nothing, stay still.
 */
export function StatusBadge({ status }: { status: StatusKind }) {
  const [shown, setShown] = useState(status);
  const [changes, setChanges] = useState(0);
  if (shown !== status) {
    setShown(status);
    setChanges(changes + 1);
  }
  const { label, icon: Icon, tone } = STATUS[status];
  return (
    <Badge
      key={changes}
      variant="outline"
      data-changed={changes > 0 ? "true" : undefined}
      className={cn("border-transparent py-1 text-sm", tone, changes > 0 && "badge-changed")}
    >
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  );
}
