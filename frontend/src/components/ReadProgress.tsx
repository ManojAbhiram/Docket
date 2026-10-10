import { cn } from "@/lib/utils";

export type ReadState = "reading" | "done" | "failed";

const WORDS: Record<ReadState, string> = {
  reading: "Reading",
  done: "Read",
  failed: "Failed",
};

/**
 * A thin bar under a document row. While the document is read the fill climbs toward 90 percent
 * and waits (one animation, no loop); when the read ends the fill completes. The bar has no
 * value while reading, because the engine reports none, so assistive technology hears "Reading".
 * Only the fill's transform moves, and reduced motion shows the end state at once.
 */
export function ReadProgress({ state, label }: { state: ReadState; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={state === "reading" ? undefined : 100}
      aria-valuetext={WORDS[state]}
      className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        data-state={state}
        className={cn(
          "read-fill h-full w-full rounded-full",
          state === "failed" ? "bg-destructive" : "bg-primary",
        )}
      />
    </div>
  );
}
