import { cn } from "@/lib/utils";

interface DocketLogoProps {
  /** `onDark` for the deep teal sidebar and panels, `onLight` for white surfaces. */
  tone?: "onDark" | "onLight";
  /** Shows the name beside the mark. */
  withName?: boolean;
  className?: string;
}

/**
 * The Docket mark: a case file with a check on its cover and a sheet behind it, the thing the
 * product hands back (a file that has been checked). Colours come from the theme tokens.
 */
export function DocketLogo({ tone = "onDark", withName = false, className }: DocketLogoProps) {
  const dark = tone === "onDark";
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg
        viewBox="0 0 40 40"
        role="img"
        aria-label="Docket logo"
        className="size-9 shrink-0"
        fill="none"
      >
        <rect
          x="12"
          y="5"
          width="20"
          height="24"
          rx="2.5"
          transform="rotate(8 22 17)"
          className={dark ? "fill-header-foreground/45" : "fill-primary/35"}
        />
        <path
          d="M5 14a3.5 3.5 0 0 1 3.5-3.5h8.2c.9 0 1.7.4 2.3 1l1.6 1.9c.4.5 1 .8 1.7.8h9.2A3.5 3.5 0 0 1 35 17.7V30.5A3.5 3.5 0 0 1 31.5 34h-23A3.5 3.5 0 0 1 5 30.5V14Z"
          className={dark ? "fill-header-foreground" : "fill-primary"}
        />
        <path
          d="m13.5 23.2 4.6 4.6 8.4-9.4"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={dark ? "stroke-header" : "stroke-primary-foreground"}
        />
      </svg>
      {withName && <span className="font-display text-xl font-semibold">Docket</span>}
    </span>
  );
}
