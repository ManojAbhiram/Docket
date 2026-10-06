import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

import { useMe } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api";

import { DashboardView } from "../components/DashboardView";
import { useDashboard } from "../hooks";
import { dashboardNotice } from "../notices";

const clock = new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" });

/** The dashboard: live counts, read again every 30 seconds while the tab is in front. */
export function DashboardPage() {
  const { data: me } = useMe();
  const navigate = useNavigate();
  const counts = useDashboard();
  const [announcement, setAnnouncement] = useState<string>();
  const firstRead = useRef(true);

  useEffect(() => {
    if (counts.dataUpdatedAt === 0) {
      return;
    }
    if (firstRead.current) {
      firstRead.current = false;
      return;
    }
    setAnnouncement(`Counts updated at ${clock.format(counts.dataUpdatedAt)}.`);
  }, [counts.dataUpdatedAt]);

  const failed = counts.error !== null;
  const offlineWithCounts =
    failed &&
    counts.data !== undefined &&
    counts.error instanceof ApiError &&
    counts.error.code === "network";
  const notice = failed && !offlineWithCounts ? dashboardNotice(counts.error) : undefined;

  return (
    <DashboardView
      audience={me?.role ?? "staff"}
      counts={counts.data ?? null}
      loading={counts.isPending}
      refreshing={counts.isFetching && !counts.isPending}
      {...(notice && { notice })}
      {...(offlineWithCounts && { asOf: clock.format(counts.dataUpdatedAt) })}
      {...(announcement && { announcement })}
      onRefresh={() => {
        void counts.refetch();
      }}
      onAction={() => {
        void counts.refetch();
      }}
      onNavigate={(to) => {
        void navigate({ to });
      }}
    />
  );
}
