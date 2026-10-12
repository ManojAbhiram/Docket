import { cn } from "@/lib/utils";

/** A record with a Verified stamp pressed on it. Decorative. */
export function VerifiedStampArt({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 170"
      aria-hidden="true"
      focusable="false"
      className={cn("h-auto w-full", className)}
      fill="none"
    >
      <rect
        x="40"
        y="18"
        width="130"
        height="136"
        rx="6"
        className="fill-card stroke-border"
        strokeWidth="2"
      />
      <rect x="56" y="34" width="62" height="7" rx="3.500" className="fill-foreground/75" />
      <rect x="56" y="50" width="98" height="4" rx="2" className="fill-muted-foreground/45" />
      <rect x="56" y="62" width="84" height="4" rx="2" className="fill-muted-foreground/45" />
      <rect x="56" y="74" width="92" height="4" rx="2" className="fill-muted-foreground/45" />
      <rect x="56" y="86" width="70" height="4" rx="2" className="fill-muted-foreground/45" />
      <rect x="56" y="108" width="40" height="3" rx="1.500" className="fill-muted-foreground/30" />
      <rect x="56" y="118" width="54" height="3" rx="1.500" className="fill-muted-foreground/30" />
      <g transform="rotate(-10 156 112)">
        <circle cx="156" cy="112" r="40" className="stroke-primary" strokeWidth="4" />
        <circle
          cx="156"
          cy="112"
          r="32"
          className="stroke-primary"
          strokeWidth="1.600"
          strokeDasharray="3 4"
        />
        <path
          d="m138 113 12 12 24-27"
          className="stroke-primary"
          strokeWidth="8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}
