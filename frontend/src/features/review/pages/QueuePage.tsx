import { useNavigate } from "@tanstack/react-router";

import { QueueView, type QueueRow } from "@/features/review/components/QueueView";
import { useQueue } from "@/features/review/hooks";
import { ApiError } from "@/lib/api";

/** S-06 with its data: the review queue, a page at a time. */
export function QueuePage() {
  const navigate = useNavigate();
  const queue = useQueue();
  const rows: QueueRow[] =
    queue.data?.pages.flatMap((page) =>
      page.data.map((item) => ({
        id: item.id,
        ref: item.application_ref,
        name: item.full_name,
        updatedAt: item.updated_at,
      })),
    ) ?? [];
  const offline = queue.error instanceof ApiError && queue.error.code === "network";

  return (
    <QueueView
      items={rows}
      loading={queue.isPending}
      loadingMore={queue.isFetchingNextPage}
      hasMore={queue.hasNextPage}
      offline={offline && rows.length > 0}
      {...(queue.isError &&
        rows.length === 0 && {
          notice: {
            title: "The queue did not load.",
            body: offline ? "Check your connection, then reload." : "Reload to try again.",
            action: "Reload",
          },
        })}
      onNoticeAction={() => {
        void queue.refetch();
      }}
      onLoadMore={() => {
        void queue.fetchNextPage();
      }}
      onOpen={(item) => {
        void navigate({ to: "/applications/$id", params: { id: item.id } });
      }}
      onDashboard={() => {
        void navigate({ to: "/dashboard" });
      }}
    />
  );
}
