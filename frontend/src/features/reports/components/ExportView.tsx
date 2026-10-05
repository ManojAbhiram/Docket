import { Download } from "lucide-react";

import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ExportViewProps {
  /** null while loading; 0 means there is nothing to export. */
  verifiedCount: number | null;
  busy?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** Set after a download: the file and its row count, in words. */
  done?: string;
}

const number = new Intl.NumberFormat("en-IN");

/** S-09: download the Verified applications as a CSV. */
export function ExportView({
  verifiedCount,
  busy = false,
  offline = false,
  notice,
  done,
}: ExportViewProps) {
  const empty = verifiedCount === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Export verified list"
        description="One row per Verified application: application id, name and decision."
      />
      {notice && <NoticeBox spec={notice} />}
      {done && (
        <p role="status" className="text-success">
          {done}
        </p>
      )}
      {empty ? (
        <div className="space-y-3 py-6">
          <p className="text-lg">No applications are Verified yet.</p>
          <Button variant="outline" className="min-h-11 sm:min-h-9">
            Back to dashboard
          </Button>
        </div>
      ) : (
        <Card className="shadow-none">
          <CardContent className="flex flex-wrap items-center justify-between gap-4">
            <p data-numeric>
              {verifiedCount === null
                ? "Counting Verified applications"
                : `${number.format(verifiedCount)} rows`}
            </p>
            <Button
              size="lg"
              className="min-h-12"
              disabled={busy || offline || verifiedCount === null}
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
