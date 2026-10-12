const LABELS: Record<string, string> = {
  "10th_marksheet": "10th marksheet",
  "12th_marksheet": "12th marksheet",
  id_proof: "id proof",
};

interface StillNeededProps {
  types: readonly string[];
}

/** The required documents no read document gives yet, so a person need not know the rule. */
export function StillNeeded({ types }: StillNeededProps) {
  if (types.length === 0) {
    return null;
  }
  return (
    <p className="text-sm text-muted-foreground">
      Still needed: {types.map((type) => LABELS[type] ?? type).join(", ")}
    </p>
  );
}
