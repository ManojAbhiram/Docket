import { Download } from "lucide-react";

import { Notice, NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ExportViewProps {
  /** null while loading; 0 means there is nothing to export; undefined means it is not known. */
  verifiedCount: number | null | undefined;
  busy?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** Set after a download: the file and its row count, in words. */
  done?: string;
  /** Starts the download. Without it the screen is a picture, as in the design gallery. */
  onDownload?: () => void;
  /** Runs the notice's one action, for example Try again. */
  onAction?: () => void;
  /** Takes a link inside the app. Without it the link is an ordinary page load. */
  onNavigate?: (to: string) => void;
}

const number = new Intl.NumberFormat("en-IN");

/** S-09: download the Verified applications as a CSV. */
export function ExportView({
  verifiedCount,
  busy = false,
  offline = false,
  notice,
  done,
  onDownload,
  onAction,
  onNavigate,
}: ExportViewProps) {
  const empty = verifiedCount === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Export verified list"
        description="One row per Verified application: application id, name, date of birth, board, roll number, category and status."
      />
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
                disabled={busy}
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
      {done && (
        <p role="status" className="text-success">
          {done}
        </p>
      )}
      {empty ? (
        <div className="space-y-3 py-6">
          <p className="text-lg">No applications are Verified yet.</p>
          <Button asChild variant="outline" className="min-h-11 sm:min-h-9">
            <a
              href="/dashboard"
              onClick={(event) => {
                if (onNavigate) {
                  event.preventDefault();
                  onNavigate("/dashboard");
                }
              }}
            >
              Back to dashboard
            </a>
          </Button>
        </div>
      ) : (
        <Card className="shadow-none">
          <CardContent className="flex flex-wrap items-center justify-between gap-4">
            <p data-numeric>
              {verifiedCount === null && "Counting Verified applications"}
              {typeof verifiedCount === "number" && `${number.format(verifiedCount)} rows`}
              {verifiedCount === undefined && "The file holds every Verified application."}
            </p>
            <Button
              size="lg"
              className="min-h-12"
              disabled={busy || offline || verifiedCount === null}
              onClick={onDownload}
            >
              <Download aria-hidden="true" />
              {busy ? "Preparing the file" : "Download CSV"}
            </Button>
          </CardContent>
        </Card>
      )}
      {offline && (
        <p role="status" className="text-muted-foreground">
          You are offline. Connect to download.
        </p>
      )}
    </div>
  );
}
