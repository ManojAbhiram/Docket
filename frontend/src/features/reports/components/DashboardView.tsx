import { CountUp } from "@/components/CountUp";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
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
}

const number = new Intl.NumberFormat("en-IN");

function Tile({
  label,
  value,
  detail,
  status,
}: {
  label: string;
  value: number;
  detail?: string;
  status: "verified" | "needs_review" | "missing_documents";
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
}: DashboardViewProps) {
  const total = counts ? totalApplications(counts) : 0;
  const primaryIsQueue = audience === "verifier";
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={counts && total > 0 ? `${number.format(total)} applications` : undefined}
        actions={
          <>
            <Button
              variant={primaryIsQueue ? "default" : "outline"}
              className="min-h-11 sm:min-h-9"
            >
              Review queue
            </Button>
            {audience === "staff" && (
              <>
                <Button className="min-h-11 sm:min-h-9">Import applications</Button>
                <Button variant="outline" className="min-h-11 sm:min-h-9">
                  Export verified list
                </Button>
              </>
            )}
          </>
        }
      />
      {asOf && (
        <p role="status" className="text-muted-foreground">
          Offline. Counts as of {asOf}.
        </p>
      )}
      {notice && <NoticeBox spec={notice} />}
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
          {audience === "staff" && (
            <Button className="min-h-11 sm:min-h-9">Import applications</Button>
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
