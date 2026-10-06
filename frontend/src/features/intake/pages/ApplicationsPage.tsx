import { Link } from "@tanstack/react-router";
import { useState } from "react";

import type { NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import { useMe } from "@/features/auth/hooks";
import {
  ApplicationsView,
  type ListedApplication,
  type StatusFilter,
} from "@/features/intake/components/ApplicationsView";
import { useApplications } from "@/features/intake/hooks";
import type { ApplicationBody } from "@/features/intake/schemas";
import { ApiError } from "@/lib/api";

function listed(body: ApplicationBody): ListedApplication {
  return {
    id: body.id,
    ref: body.application_ref,
    name: body.full_name,
    status: body.status,
    rejected: body.rejected,
    updatedAt: body.updated_at,
  };
}

function failure(error: unknown): NoticeSpec {
  if (error instanceof ApiError && error.code === "network") {
    return {
      tone: "info",
      title: "You are offline.",
      body: "Connect and try again.",
      action: "Try again",
    };
  }
  return {
    title: "The list did not load.",
    body: "Reload to try again.",
    action: "Reload",
  };
}

/** S-04 with its behaviour: the applications, filtered by status, twenty at a time. */
export function ApplicationsPage() {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const { data: me } = useMe();
  const query = useApplications(filter === "all" ? {} : { status: filter });
  const applications = query.data?.pages.flatMap((page) => page.data.map(listed)) ?? [];
  const staff = me?.role === "staff";

  return (
    <ApplicationsView
      applications={applications}
      filter={filter}
      loading={query.isPending}
      loadingMore={query.isFetchingNextPage}
      {...(query.isError && { notice: failure(query.error) })}
      {...(query.hasNextPage && {
        onLoadMore: () => {
          void query.fetchNextPage();
        },
      })}
      onFilter={setFilter}
      onNoticeAction={() => {
        void query.refetch();
      }}
      rowActions={(application) => (
        <>
          {staff && (
            <Button
              asChild
              size="sm"
              variant="outline"
              className="min-h-11 flex-1 md:min-h-8 md:flex-none"
            >
              <Link to="/applications/$id/upload" params={{ id: application.id }}>
                Add documents <span className="sr-only">for {application.ref}</span>
              </Link>
            </Button>
          )}
          <Button
            asChild
            size="sm"
            variant="ghost"
            className="min-h-11 flex-1 md:min-h-8 md:flex-none"
          >
            <Link to="/applications/$id" params={{ id: application.id }}>
              Open <span className="sr-only">{application.ref}</span>
            </Link>
          </Button>
        </>
      )}
      emptyAction={
        staff ? (
          <Button asChild className="min-h-11 sm:min-h-9">
            <Link to="/import">Import applications</Link>
          </Button>
        ) : (
          <p className="text-muted-foreground">Staff import applications from a CSV file.</p>
        )
      }
    />
  );
}
