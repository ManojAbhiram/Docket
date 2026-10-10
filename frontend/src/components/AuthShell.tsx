import type { ReactNode } from "react";

interface AuthShellProps {
  title: string;
  /** One line under the title, for example what the account is for. */
  description?: string;
  children: ReactNode;
}

/**
 * The frame of the sign in and sign up screens: a deep teal panel with the product name beside (or,
 * on a phone, above) a white card with the form. One component, so both screens look the same.
 */
export function AuthShell({ title, description, children }: AuthShellProps) {
  return (
    <div className="mx-auto grid w-full max-w-3xl overflow-hidden rounded-xl border border-border bg-card shadow-[var(--shadow-2)] md:grid-cols-[2fr_3fr]">
      <div className="bg-tile-deep px-6 py-6 text-tile-foreground md:flex md:flex-col md:justify-between md:py-10">
        <p className="font-display text-[25px] font-semibold">Docket</p>
        <p className="mt-2 max-w-xs text-sm text-tile-foreground/90 md:mt-0">
          Admissions documents read on this machine, checked field by field against the application.
        </p>
      </div>
      <div className="enter space-y-5 p-6 md:p-10">
        <div className="space-y-1">
          <h1 className="text-[25px]">{title}</h1>
          {description && <p className="text-muted-foreground">{description}</p>}
        </div>
        {children}
      </div>
    </div>
  );
}
