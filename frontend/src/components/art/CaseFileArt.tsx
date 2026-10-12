import { cn } from "@/lib/utils";

/** A case file with papers rising out of it and a checked tab. Decorative. */
export function CaseFileArt({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 170"
      aria-hidden="true"
      focusable="false"
      className={cn("h-auto w-full", className)}
      fill="none"
    >
      <ellipse cx="120" cy="156" rx="86" ry="7" className="fill-foreground/10" />
      <path
        d="M30 52a8 8 0 0 1 8-8h50c3 0 5.700 1.300 7.500 3.500l6 7.500c1.600 2 4 3 6.500 3H202a8 8 0 0 1 8 8v78a8 8 0 0 1-8 8H38a8 8 0 0 1-8-8V52Z"
        className="fill-primary/25 stroke-primary"
        strokeWidth="2"
      />
      <g transform="rotate(-5 90 80)">
        <rect
          x="58"
          y="34"
          width="86"
          height="94"
          rx="5"
          className="fill-card stroke-border"
          strokeWidth="2"
        />
        <rect x="70" y="48" width="44" height="6" rx="3" className="fill-foreground/70" />
        <rect x="70" y="62" width="62" height="4" rx="2" className="fill-muted-foreground/50" />
        <rect x="70" y="72" width="54" height="4" rx="2" className="fill-muted-foreground/50" />
        <rect x="70" y="82" width="60" height="4" rx="2" className="fill-muted-foreground/50" />
        <rect
          x="70"
          y="96"
          width="36"
          height="14"
          rx="3"
          className="stroke-primary"
          strokeWidth="1.600"
          strokeDasharray="4 3"
        />
      </g>
      <g transform="rotate(6 150 80)">
        <rect
          x="108"
          y="30"
          width="86"
          height="98"
          rx="5"
          className="fill-card stroke-border"
          strokeWidth="2"
        />
        <rect x="120" y="44" width="52" height="6" rx="3" className="fill-foreground/70" />
        <rect x="120" y="58" width="62" height="4" rx="2" className="fill-muted-foreground/50" />
        <rect x="120" y="68" width="48" height="4" rx="2" className="fill-muted-foreground/50" />
        <rect x="120" y="78" width="58" height="4" rx="2" className="fill-muted-foreground/50" />
      </g>
      <path
        d="M30 78a8 8 0 0 1 8-8h164a8 8 0 0 1 8 8v52a8 8 0 0 1-8 8H38a8 8 0 0 1-8-8V78Z"
        className="fill-primary stroke-primary"
        strokeWidth="2"
      />
      <rect x="48" y="86" width="56" height="8" rx="4" className="fill-primary-foreground/80" />
      <rect
        x="48"
        y="100"
        width="38"
        height="5"
        rx="2.500"
        className="fill-primary-foreground/50"
      />
      <circle cx="176" cy="104" r="18" className="fill-primary-foreground" />
      <path
        d="m167 104 6.500 6.500L186 96.500"
        className="stroke-primary"
        strokeWidth="4.500"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
