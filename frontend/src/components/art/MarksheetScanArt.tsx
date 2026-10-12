import { cn } from "@/lib/utils";

/** A marksheet being read: scan corners, a beam, and the fields found outlined. Decorative. */
export function MarksheetScanArt({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 170"
      aria-hidden="true"
      focusable="false"
      className={cn("h-auto w-full", className)}
      fill="none"
    >
      <rect
        x="62"
        y="12"
        width="116"
        height="146"
        rx="6"
        className="fill-card stroke-border"
        strokeWidth="2"
      />
      <rect x="76" y="26" width="88" height="7" rx="3.500" className="fill-foreground/75" />
      <rect x="76" y="40" width="60" height="4" rx="2" className="fill-muted-foreground/45" />
      <rect
        x="76"
        y="56"
        width="88"
        height="14"
        rx="3"
        className="fill-primary/10 stroke-primary"
        strokeWidth="1.600"
        strokeDasharray="4 3"
      />
      <rect x="82" y="61" width="40" height="4" rx="2" className="fill-foreground/60" />
      <rect
        x="76"
        y="76"
        width="88"
        height="14"
        rx="3"
        className="fill-primary/10 stroke-primary"
        strokeWidth="1.600"
        strokeDasharray="4 3"
      />
      <rect x="82" y="81" width="52" height="4" rx="2" className="fill-foreground/60" />
      <rect x="76" y="100" width="88" height="3" rx="1.500" className="fill-muted-foreground/35" />
      <rect x="76" y="110" width="88" height="3" rx="1.500" className="fill-muted-foreground/35" />
      <rect x="76" y="120" width="88" height="3" rx="1.500" className="fill-muted-foreground/35" />
      <rect x="76" y="130" width="64" height="3" rx="1.500" className="fill-muted-foreground/35" />
      <rect x="58" y="86" width="124" height="10" rx="5" className="fill-primary/30" />
      <path
        d="M44 40V24a8 8 0 0 1 8-8h16"
        className="stroke-primary"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M196 16h16a8 8 0 0 1 8 8v16"
        className="stroke-primary"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M44 130v16a8 8 0 0 0 8 8h16"
        className="stroke-primary"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M196 154h16a8 8 0 0 0 8-8v-16"
        className="stroke-primary"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}
