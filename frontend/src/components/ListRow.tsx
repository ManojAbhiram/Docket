import { ChevronRight } from "lucide-react";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

interface ListRowProps extends ComponentProps<"li"> {
  /** The keyboard cursor is on this row. It gets a fill, a drawn marker and aria-current. */
  selected?: boolean;
  /** The row answers a pointer, so it shows a hover fill. A row that only reports does not. */
  interactive?: boolean;
  /** "card" stands alone with its own border; "ruled" sits in a list the parent rules with dividers. */
  variant?: "card" | "ruled";
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
  className,
  children,
  ...props
}: ListRowProps) {
  return (
    <li
      aria-current={selected ? "true" : undefined}
      className={cn(
        "relative",
        variant === "card" && "rounded-md border border-border bg-card",
        interactive && "transition-colors hover:bg-muted",
        selected && "bg-accent hover:bg-accent",
        className,
      )}
      {...props}
    >
      {selected && (
        <ChevronRight
          aria-hidden="true"
          className="absolute top-1/2 left-0.5 size-3.5 -translate-y-1/2 text-muted-foreground"
        />
      )}
      {children}
    </li>
  );
}
