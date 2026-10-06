import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import { CountUp } from "@/components/CountUp";
import { Notice, NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { totalApplications } from "@/features/applications/fixtures";
import type { DashboardCounts } from "@/features/applications/types";

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
  children,
}: {
  to: string;
  onNavigate?: ((to: string) => void) | undefined;
  variant?: "default" | "outline" | "link";
  children: ReactNode;
}) {
  return (
    <Button asChild variant={variant} className="min-h-11 sm:min-h-9">
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

function Tile({
  label,
  value,
  detail,
  status,
  link,
}: {
  label: string;
  value: number;
  detail?: string;
  status: "verified" | "needs_review" | "missing_documents";
  link?: ReactNode;
}) {
  return (
    <Card className="shadow-none">
      <CardHeader>
        <CardTitle className="text-base font-semibold">
          <StatusBadge status={status} />
          <span className="sr-only"> {label}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="font-display text-[25px] font-semibold">
          <CountUp value={value} format={(amount) => number.format(amount)} />
        </p>
        <p className="text-sm text-muted-foreground">{detail ?? label}</p>
        {link}
      </CardContent>
    </Card>
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
            <Skeleton key={slot} className="h-28" />
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
          <Tile label="Verified" value={counts.verified} status="verified" />
          <Tile
            label="Needs review"
            value={counts.needsReview}
            detail={`of which ${number.format(counts.rejected)} rejected`}
            status="needs_review"
            link={
              <AppLink to={reviewTarget} variant="link" onNavigate={onNavigate}>
                {forVerifier ? "Open the queue" : "See applications"}
              </AppLink>
            }
          />
          <Tile
            label="Missing documents"
            value={counts.missingDocuments}
            status="missing_documents"
          />
        </div>
      )}
    </div>
  );
}
