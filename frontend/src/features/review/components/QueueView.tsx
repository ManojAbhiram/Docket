import { useState } from "react";

import { Kbd } from "@/components/Kbd";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTime } from "@/features/applications/fixtures";
import type { ApplicationSummary } from "@/features/applications/types";
import { useHotkeys } from "@/lib/hotkeys";
import { cn } from "@/lib/utils";

interface QueueViewProps {
  items: ApplicationSummary[];
  /** The server's total, so a partial page can say "20 of 611". */
  total?: number;
  loading?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** Opens one application on S-07. "Review next" and the `n` key open the oldest. */
  onOpen?: (item: ApplicationSummary) => void;
}

/** S-06: the flagged applications a verifier still has to decide, oldest first. */
export function QueueView({
  items,
  total,
  loading = false,
  offline = false,
  notice,
  onOpen,
}: QueueViewProps) {
  const [selected, setSelected] = useState(0);
  const reviewNext = () => {
    const oldest = items[0];
    if (oldest && !offline) {
      onOpen?.(oldest);
    }
  };
  useHotkeys({
    n: reviewNext,
    j: () => {
      setSelected((current) => Math.min(current + 1, items.length - 1));
    },
    k: () => {
      setSelected((current) => Math.max(current - 1, 0));
    },
  });
  const count = total ?? items.length;
  const empty = !loading && !notice && items.length === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Review queue"
        description={!loading && items.length > 0 ? `${count} to review` : undefined}
        actions={
          <Button
            className="min-h-11 sm:min-h-9"
            disabled={items.length === 0 || offline}
            onClick={reviewNext}
          >
            Review next <Kbd>n</Kbd>
          </Button>
        }
      />
      {offline && (
        <p role="status" className="text-muted-foreground">
          Offline. Showing what was loaded.
        </p>
      )}
      {notice && <NoticeBox spec={notice} />}
      {loading && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2, 3, 4, 5].map((slot) => (
            <Skeleton key={slot} className="h-14" />
          ))}
        </div>
      )}
      {empty && (
        <div className="space-y-3 py-8">
          <p className="text-lg">Nothing needs review.</p>
          <Button variant="outline" className="min-h-11 sm:min-h-9">
            Go to the dashboard
          </Button>
        </div>
      )}
      {items.length > 0 && (
        <ul className="divide-y divide-border rounded-md border border-border bg-card">
          {items.map((item, index) => (
            <li
              key={item.id}
              aria-current={index === selected ? "true" : undefined}
              className={cn(
                "grid min-h-14 items-center gap-x-4 gap-y-1 px-4 py-3 md:grid-cols-[9rem_1fr_1fr_auto_auto]",
                index === selected && "bg-accent",
              )}
            >
              <span className="font-mono">{item.ref}</span>
              <span>{item.name}</span>
              <span className="text-muted-foreground">{item.flag}</span>
              <span className="text-sm text-muted-foreground">{formatTime(item.updatedAt)}</span>
              <span className="flex items-center gap-2">
                <StatusBadge status="needs_review" />
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-11 sm:min-h-8"
                  onClick={() => {
                    onOpen?.(item);
                  }}
                >
                  Open
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {total !== undefined && total > items.length && (
        <div className="flex flex-wrap items-center gap-3">
          <p data-numeric>
            {items.length} of {total} shown.
          </p>
          <Button variant="outline" className="min-h-11 sm:min-h-9" disabled={offline}>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
