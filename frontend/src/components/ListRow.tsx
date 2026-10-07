import { ChevronRight } from "lucide-react";
import type { ComponentProps } from "react";

import { staggerStyle } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface ListRowProps extends ComponentProps<"li"> {
  /** The keyboard cursor is on this row. It gets a fill, a drawn marker and aria-current. */
  selected?: boolean;
  /** The row answers a pointer, so it shows a hover fill. A row that only reports does not. */
  interactive?: boolean;
  /** "card" stands alone with its own border; "ruled" sits in a list the parent rules with dividers. */
  variant?: "card" | "ruled";
  /**
   * Place the row in an entrance wave: its position in the list. Leave it out for a row that should
   * not enter, or that the verifier works fast (see `quiet`).
   */
  index?: number;
  /** A fade only, no travel and no wave: for the review queue and compare screens. */
  quiet?: boolean;
  /** A card row rises a little under the pointer. Not for rows in a ruled list. */
  lift?: boolean;
}

/**
 * One row of a list, drawn once: border, fill, hover and the selected cue (docs/design/DESIGN.md
 * section 4). Hover and selected look different on purpose, so the keyboard cursor stays easy to
 * find while the mouse rests on another row. Focus stays the global 2 px ring.
 */
export function ListRow({
  selected = false,
  interactive = false,
  variant = "card",
  index,
  quiet = false,
  lift = false,
  className,
  style,
  children,
  ...props
}: ListRowProps) {
  return (
    <li
      aria-current={selected ? "true" : undefined}
      style={index === undefined ? style : { ...staggerStyle(index), ...style }}
      className={cn(
        "relative",
        variant === "card" && "rounded-lg border border-border bg-card",
        interactive && "transition-colors hover:bg-muted",
        lift && "lift",
        index !== undefined && !quiet && "enter",
        quiet && "enter-quiet",
        selected && "bg-accent hover:bg-accent",
        className,
      )}
      {...props}
    >
      {selected && (
        <>
          <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-primary" />
          <ChevronRight
            aria-hidden="true"
            className="absolute top-1/2 left-1 size-3 -translate-y-1/2 text-muted-foreground"
          />
        </>
      )}
      {children}
    </li>
  );
}
