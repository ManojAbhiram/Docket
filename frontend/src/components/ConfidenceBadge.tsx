import { TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** The provisional review cutoff from ADR-0005; the API will supply the configured one. */
export const DEFAULT_CUTOFF = 0.9804;

interface ConfidenceBadgeProps {
  /** 0 to 1, or null when the engine returned no score. */
  confidence: number | null;
  cutoff?: number;
}

/** The engine's confidence as a percentage; below the cutoff it says "Low" and shows a flag. */
export function ConfidenceBadge({ confidence, cutoff = DEFAULT_CUTOFF }: ConfidenceBadgeProps) {
  if (confidence === null) {
    return (
      <Badge variant="outline" className="text-sm">
        No score
      </Badge>
    );
  }
  const text = `${(confidence * 100).toFixed(1)}%`;
  const low = confidence < cutoff;
  return (
    <Badge
      variant="outline"
      data-numeric
      className={cn(
        "border-transparent text-sm",
        low ? "bg-warning-subtle text-warning" : "bg-secondary text-secondary-foreground",
      )}
    >
      {low && <TriangleAlert aria-hidden="true" />}
      {low ? `Low ${text}` : text}
    </Badge>
  );
}
