import { Ban, Check, Flag, Minus, type LucideIcon } from "lucide-react";

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

/** A status as a word and a shape, never colour alone. */
export function StatusBadge({ status }: { status: StatusKind }) {
  const { label, icon: Icon, tone } = STATUS[status];
  return (
    <Badge variant="outline" className={cn("border-transparent text-sm", tone)}>
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  );
}
