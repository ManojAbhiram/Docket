import { Check, Flag, Minus, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import { CountUp } from "@/components/CountUp";
import { Notice, NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { totalApplications } from "@/features/applications/fixtures";
import type { DashboardCounts } from "@/features/applications/types";
import { staggerStyle } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface DashboardViewProps {
  /** Who is looking: staff import and export, a verifier works the queue. */
  audience: "staff" | "verifier";
  /** null while loading or when the counts did not load. */
  counts: DashboardCounts | null;
  loading?: boolean;
  notice?: NoticeSpec;
  /** Set when offline: the time the counts were read, in words. */
  asOf?: string;
  /** Reads the counts again. Without it the screen has no refresh button. */
  onRefresh?: () => void;
  refreshing?: boolean;
  /** Runs the notice's one action, for example Reload. */
  onAction?: () => void;
  /** Takes a link inside the app. Without it the links are ordinary page loads. */
  onNavigate?: (to: string) => void;
  /** A polite sentence for assistive technology when the counts changed by themselves. */
  announcement?: string;
}

const number = new Intl.NumberFormat("en-IN");

/** A real link, so it opens in a new tab and works from the keyboard, that stays in the app. */
function AppLink({
  to,
  onNavigate,
  variant = "outline",
  className,
  children,
}: {
  to: string;
  onNavigate?: ((to: string) => void) | undefined;
  variant?: "default" | "outline" | "link";
  className?: string;
  children: ReactNode;
}) {
  return (
    <Button asChild variant={variant} className={cn("min-h-11 sm:min-h-9", className)}>
      <a
        href={to}
        onClick={(event) => {
          if (onNavigate && !event.metaKey && !event.ctrlKey && !event.shiftKey) {
            event.preventDefault();
            onNavigate(to);
          }
        }}
      >
        {children}
      </a>
    </Button>
  );
}

const TILES = {
  verified: { tone: "bg-tile", icon: Check },
  needs_review: { tone: "bg-tile-warn", icon: Flag },
  missing_documents: { tone: "bg-tile-deep", icon: Minus },
} as const;

/** A solid tile: the status as a word and a shape on a deep colour, then the count. */
function Tile({
  label,
  value,
  detail,
  status,
  index,
  link,
}: {
  label: string;
  value: number;
  detail?: string;
  status: keyof typeof TILES;
  index: number;
  link?: ReactNode;
}) {
  const { tone, icon: Icon } = TILES[status];
  return (
    <div
      style={staggerStyle(index)}
      className={cn(
        "enter lift flex flex-col gap-1 rounded-xl p-5 text-tile-foreground shadow-(--shadow-1)",
        tone,
      )}
    >
      <p className="flex items-center gap-2 text-base font-semibold">
        <Icon aria-hidden="true" className="size-4" />
        {label}
      </p>
      <p className="font-display text-[44px] leading-none font-semibold">
        <CountUp value={value} format={(amount) => number.format(amount)} />
      </p>
      <p className="text-sm">{detail ?? "applications"}</p>
      {link}
    </div>
  );
}

/** S-02: how many applications are Verified, Needs review and Missing documents, and the next job. */
export function DashboardView({
  audience,
  counts,
  loading = false,
  notice,
  asOf,
  onRefresh,
  refreshing = false,
  onAction,
  onNavigate,
  announcement,
}: DashboardViewProps) {
  const total = counts ? totalApplications(counts) : 0;
  const forVerifier = audience === "verifier";
  const reviewTarget = forVerifier ? "/queue" : "/applications";
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={counts && total > 0 ? `${number.format(total)} applications` : undefined}
        actions={
          <>
            {onRefresh && (
              <Button
                variant="outline"
                className="min-h-11 sm:min-h-9"
                disabled={refreshing}
                onClick={onRefresh}
              >
                <RefreshCw aria-hidden="true" className={refreshing ? "animate-spin" : undefined} />
                {refreshing ? "Refreshing" : "Refresh"}
              </Button>
            )}
            {forVerifier && (
              <AppLink to="/queue" variant="default" onNavigate={onNavigate}>
                Review queue
              </AppLink>
            )}
            {!forVerifier && (
              <>
                <AppLink to="/import" variant="default" onNavigate={onNavigate}>
                  Import applications
                </AppLink>
                <AppLink to="/export" onNavigate={onNavigate}>
                  Export verified list
                </AppLink>
              </>
            )}
          </>
        }
      />
      {announcement && (
        <p role="status" className="sr-only">
          {announcement}
        </p>
      )}
      {asOf && (
        <p role="status" className="text-muted-foreground">
          Offline. Counts as of {asOf}.
        </p>
      )}
      {notice &&
        (onAction && notice.action ? (
          <Notice
            tone={notice.tone ?? "error"}
            title={notice.title}
            action={
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-11 sm:min-h-8"
                onClick={onAction}
              >
                {notice.action}
              </Button>
            }
          >
            {notice.body}
          </Notice>
        ) : (
          <NoticeBox spec={notice} />
        ))}
      {loading && (
        <div className="grid gap-4 sm:grid-cols-3" aria-busy="true">
          {[0, 1, 2].map((slot) => (
            <Skeleton key={slot} className="h-40 rounded-xl" />
          ))}
        </div>
      )}
      {counts && total === 0 && (
        <div className="space-y-3 py-8">
          <p className="text-lg">No applications yet.</p>
          {!forVerifier && (
            <AppLink to="/import" variant="default" onNavigate={onNavigate}>
              Import applications
            </AppLink>
          )}
        </div>
      )}
      {counts && total > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Tile label="Verified" value={counts.verified} status="verified" index={0} />
          <Tile
            label="Needs review"
            value={counts.needsReview}
            detail={`of which ${number.format(counts.rejected)} rejected`}
            status="needs_review"
            index={1}
            link={
              <AppLink
                to={reviewTarget}
                variant="link"
                className="-ml-4 w-fit text-tile-foreground underline"
                onNavigate={onNavigate}
              >
                {forVerifier ? "Open the queue" : "See applications"}
              </AppLink>
            }
          />
          <Tile
            label="Missing documents"
            value={counts.missingDocuments}
            status="missing_documents"
            index={2}
          />
        </div>
      )}
    </div>
  );
}
