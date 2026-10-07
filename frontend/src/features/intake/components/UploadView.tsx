import { ActionNotice } from "@/components/ActionNotice";
import { FileDrop } from "@/components/FileDrop";
import { ListRow } from "@/components/ListRow";
import type { NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentStatus, UploadedDocument } from "@/features/applications/types";

const STATUS_WORDS: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  processing: "Reading",
  read: "Read",
  failed: "Failed",
};

export type BatchState = "waiting" | "uploading" | "stored" | "already" | "refused";

/** One file the person chose, and where it is in the one-by-one upload. */
export interface BatchItem {
  key: string;
  name: string;
  state: BatchState;
  /** Why the API refused it, in words. */
  problem?: string;
}

const BATCH_WORDS: Record<BatchState, string> = {
  waiting: "Waiting",
  uploading: "Uploading",
  stored: "Stored",
  already: "Already stored",
  refused: "Refused",
};

interface UploadViewProps {
  reference: string;
  documents: UploadedDocument[];
  loading?: boolean;
  /** Staff upload; a verifier sees the list only. */
  readOnly?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** Wiring from the page. Without it the controls are inert, as in the design gallery. */
  batch?: BatchItem[];
  onFiles?: (files: File[]) => void;
  onNoticeAction?: () => void;
}

function summary(documents: UploadedDocument[]): string {
  const read = documents.filter((d) => d.status === "read").length;
  const reading = documents.filter(
    (d) => d.status === "processing" || d.status === "uploaded",
  ).length;
  const failed = documents.filter((d) => d.status === "failed").length;
  return `${read} read, ${reading} reading, ${failed} failed.`;
}

/** S-05: add scans to one application and see what the machine read from each. */
export function UploadView({
  reference,
  documents,
  loading = false,
  readOnly = false,
  offline = false,
  notice,
  batch = [],
  onFiles,
  onNoticeAction,
}: UploadViewProps) {
  const empty = !loading && !notice && documents.length === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title={`Documents for ${reference}`}
        description="Read on this machine. Nothing is sent anywhere."
      />
      {notice && <ActionNotice spec={notice} onAction={onNoticeAction} />}
      {offline && (
        <p role="status" className="text-muted-foreground">
          You are offline. Connect to upload.
        </p>
      )}
      {!readOnly && (
        <FileDrop
          id="upload-files"
          label="Choose files"
          hint="JPG, PNG or PDF, up to 8 MiB each. A PDF is read from its first page."
          accept="image/jpeg,image/png,application/pdf"
          multiple
          disabled={offline}
          {...(onFiles && { onFiles })}
        />
      )}
      {batch.length > 0 && (
        <section aria-labelledby="batch-heading" className="space-y-3">
          <h2 id="batch-heading" className="text-xl">
            Files
          </h2>
          <ul className="space-y-2">
            {batch.map((item) => (
              <ListRow key={item.key} className="space-y-1 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono">{item.name}</span>
                  <Badge
                    variant="outline"
                    className={
                      item.state === "refused"
                        ? "border-transparent bg-danger-subtle text-sm text-destructive"
                        : "text-sm"
                    }
                  >
                    {BATCH_WORDS[item.state]}
                  </Badge>
                </div>
                {item.problem && <p role="alert">{item.problem}</p>}
              </ListRow>
            ))}
          </ul>
        </section>
      )}
      {loading && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2].map((slot) => (
            <Skeleton key={slot} className="h-12" />
          ))}
        </div>
      )}
      {empty && (
        <p className="text-lg">
          No documents yet. Upload a 10th marksheet, a 12th marksheet and an ID proof.
        </p>
      )}
      {documents.length > 0 && (
        <section aria-labelledby="documents-heading" className="space-y-3">
          <h2 id="documents-heading" className="text-xl">
            Documents
          </h2>
          <p role="status" data-numeric className="text-muted-foreground">
            {summary(documents)}
          </p>
          <ul className="space-y-2">
            {documents.map((document) => (
              <ListRow key={document.id} data-motion="settle" className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono">{document.fileName}</span>
                  <Badge
                    variant="outline"
                    className={
                      document.status === "failed"
                        ? "border-transparent bg-danger-subtle text-sm text-destructive"
                        : "text-sm"
                    }
                  >
                    {STATUS_WORDS[document.status]}
                    {document.detectedType ? `: ${document.detectedType}` : ""}
                  </Badge>
                </div>
                {document.problem && (
                  <div className="space-y-2">
                    <p>{document.problem}</p>
                    {document.status === "failed" && !readOnly && onFiles === undefined && (
                      <Button variant="outline" size="sm" className="min-h-11 sm:min-h-8">
                        Reprocess
                      </Button>
                    )}
                  </div>
                )}
              </ListRow>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
