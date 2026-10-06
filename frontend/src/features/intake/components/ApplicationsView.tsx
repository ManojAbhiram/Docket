import type { ReactNode } from "react";

import type { NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge, type StatusKind } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatTime } from "@/features/applications/fixtures";
import type { ApplicationStatus, ApplicationSummary } from "@/features/applications/types";
import { ActionNotice } from "@/features/intake/components/ActionNotice";

export type StatusFilter = "all" | ApplicationStatus;

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "verified", label: "Verified" },
  { value: "needs_review", label: "Needs review" },
  { value: "missing_documents", label: "Missing documents" },
];

/** What the list needs of an application. The API list has no document counts, so they are optional. */
export type ListedApplication = Omit<ApplicationSummary, "documentsRead" | "documentsTotal"> &
  Partial<Pick<ApplicationSummary, "documentsRead" | "documentsTotal">>;

function statusOf(application: ListedApplication): StatusKind {
  return application.rejected ? "rejected" : application.status;
}

interface ApplicationsViewProps {
  applications: ListedApplication[];
  filter?: StatusFilter;
  /** The server's total, so a partial page can say "20 of 5,000". */
  total?: number;
  loading?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** Wiring from the page. Without it the controls are inert, as in the design gallery. */
  onFilter?: (filter: StatusFilter) => void;
  onNoticeAction?: () => void;
  onLoadMore?: () => void;
  loadingMore?: boolean;
  /** Replaces the row's buttons, for links. */
  rowActions?: (application: ListedApplication) => ReactNode;
  emptyAction?: ReactNode;
}

/** S-04: every application with its status, to find one and add its documents. */
export function ApplicationsView({
  applications,
  filter = "all",
  total,
  loading = false,
  offline = false,
  notice,
  onFilter,
  onNoticeAction,
  onLoadMore,
  loadingMore = false,
  rowActions,
  emptyAction,
}: ApplicationsViewProps) {
  const partial = total !== undefined && total > applications.length;
  const showCounts = applications.every((a) => a.documentsTotal !== undefined);
  const filteredEmpty = !loading && !notice && applications.length === 0 && filter !== "all";
  const empty = !loading && !notice && applications.length === 0 && filter === "all";
  return (
    <div className="space-y-6">
      <PageHeader
        title="Applications"
        description={
          total !== undefined
            ? `${new Intl.NumberFormat("en-IN").format(total)} applications`
            : undefined
        }
      />
      <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
        {FILTERS.map(({ value, label }) => (
          <Button
            key={value}
            type="button"
            variant={filter === value ? "default" : "outline"}
            aria-pressed={filter === value}
            className="min-h-11 sm:min-h-9"
            onClick={() => {
              onFilter?.(value);
            }}
          >
            {label}
          </Button>
        ))}
      </div>
      {offline && (
        <p role="status" className="text-muted-foreground">
          Offline. Showing what was loaded.
        </p>
      )}
      {notice && <ActionNotice spec={notice} onAction={onNoticeAction} />}
      {loading && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2, 3, 4, 5].map((slot) => (
            <Skeleton key={slot} className="h-11" />
          ))}
        </div>
      )}
      {empty && (
        <div className="space-y-3 py-8">
          <p className="text-lg">No applications yet.</p>
          {emptyAction ?? <Button className="min-h-11 sm:min-h-9">Import applications</Button>}
        </div>
      )}
      {filteredEmpty && (
        <div className="space-y-3 py-8">
          <p className="text-lg">
            No applications are {FILTERS.find((f) => f.value === filter)?.label}.
          </p>
          <Button
            variant="outline"
            className="min-h-11 sm:min-h-9"
            onClick={() => {
              onFilter?.("all");
            }}
          >
            Clear filter
          </Button>
        </div>
      )}
      {applications.length > 0 && (
        <>
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Application</TableHead>
                  <TableHead scope="col">Name</TableHead>
                  <TableHead scope="col">Status</TableHead>
                  {showCounts && (
                    <TableHead scope="col" className="text-right">
                      Documents read
                    </TableHead>
                  )}
                  <TableHead scope="col">Changed</TableHead>
                  <TableHead scope="col">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {applications.map((application) => (
                  <TableRow key={application.id}>
                    <TableCell className="font-mono">{application.ref}</TableCell>
                    <TableCell>{application.name}</TableCell>
                    <TableCell>
                      <StatusBadge status={statusOf(application)} />
                    </TableCell>
                    {showCounts && (
                      <TableCell data-numeric className="text-right">
                        {application.documentsRead} of {application.documentsTotal}
                      </TableCell>
                    )}
                    <TableCell>{formatTime(application.updatedAt)}</TableCell>
                    <TableCell className="space-x-2 text-right">
                      {rowActions ? (
                        rowActions(application)
                      ) : (
                        <>
                          <Button size="sm" variant="outline">
                            Add documents
                          </Button>
                          <Button size="sm" variant="ghost">
                            Open
                          </Button>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <ul className="space-y-2 md:hidden">
            {applications.map((application) => (
              <li
                key={application.id}
                className="space-y-2 rounded-md border border-border bg-card p-4"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono">{application.ref}</span>
                  <StatusBadge status={statusOf(application)} />
                </div>
                <p>{application.name}</p>
                {showCounts && (
                  <p data-numeric className="text-sm text-muted-foreground">
                    {application.documentsRead} of {application.documentsTotal} documents read
                  </p>
                )}
                <div className="flex gap-2">
                  {rowActions ? (
                    rowActions(application)
                  ) : (
                    <>
                      <Button variant="outline" className="min-h-11 flex-1">
                        Add documents
                      </Button>
                      <Button variant="ghost" className="min-h-11 flex-1">
                        Open
                      </Button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      {total !== undefined && partial && (
        <div className="flex flex-wrap items-center gap-3">
          <p data-numeric>
            {applications.length} of {new Intl.NumberFormat("en-IN").format(total)} shown.
          </p>
          <Button
            variant="outline"
            className="min-h-11 sm:min-h-9"
            disabled={offline || loadingMore}
            onClick={onLoadMore}
          >
            {loadingMore ? "Loading" : "Load more"}
          </Button>
        </div>
      )}
      {total === undefined && onLoadMore && (
        <div className="flex flex-wrap items-center gap-3">
          <p data-numeric>{applications.length} shown.</p>
          <Button
            variant="outline"
            className="min-h-11 sm:min-h-9"
            disabled={offline || loadingMore}
            onClick={onLoadMore}
          >
            {loadingMore ? "Loading" : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
