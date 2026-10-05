import type { ReactNode } from "react";

/** A keyboard key, for the shortcuts dialog and beside a control that has one. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex min-w-6 items-center justify-center rounded-sm border border-border bg-muted px-1.5 font-mono text-sm text-foreground">
      {children}
    </kbd>
  );
}
