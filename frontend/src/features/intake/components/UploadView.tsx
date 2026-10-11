import { ActionNotice } from "@/components/ActionNotice";
import { FileDrop } from "@/components/FileDrop";
import { ListRow } from "@/components/ListRow";
import type { NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ReadProgress, type ReadState } from "@/components/ReadProgress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentStatus, UploadedDocument } from "@/features/applications/types";
import type { ReadMode } from "@/features/intake/schemas";
import { useChangeCount } from "@/hooks/use-change-count";
import { cn } from "@/lib/utils";

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
  /** Vision can be chosen only when the server is set up for it. */
  visionAvailable?: boolean;
  mode?: ReadMode;
  onModeChange?: (mode: ReadMode) => void;
  onFiles?: (files: File[]) => void;
  onNoticeAction?: () => void;
}

/** A word in a pill that pops once when its state changes, and stays still on a refresh. */
function WordBadge({ word, state, bad }: { word: string; state: string; bad: boolean }) {
  const changes = useChangeCount(state);
  return (
    <Badge
      key={changes}
      variant="outline"
      className={cn(
        "py-1 text-sm",
        bad && "border-transparent bg-danger-subtle text-destructive",
        changes > 0 && "badge-changed",
      )}
    >
      {word}
    </Badge>
  );
}

function readState(status: DocumentStatus): ReadState {
  if (status === "failed") {
    return "failed";
  }
  return status === "read" ? "done" : "reading";
}

function summary(documents: UploadedDocument[]): string {
  const read = documents.filter((d) => d.status === "read").length;
  const reading = documents.filter(
    (d) => d.status === "processing" || d.status === "uploaded",
  ).length;
  const failed = documents.filter((d) => d.status === "failed").length;
  return `${read} read, ${reading} reading, ${failed} failed.`;
}

const MODES: { value: ReadMode; label: string; hint: string }[] = [
  { value: "free", label: "Read on this machine", hint: "Nothing leaves this machine." },
  {
    value: "vision",
    label: "Read with OpenRouter Vision",
    hint: "A model gives a second reading. A person checks every field.",
  },
];

/** Where the page goes, said before anything is sent. */
function ModeChoice({
  mode,
  onChange,
}: {
  mode: ReadMode;
  onChange?: ((mode: ReadMode) => void) | undefined;
}) {
  return (
    <fieldset className="space-y-3">
      <legend className="text-lg font-medium">How should the pages be read?</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {MODES.map((option) => (
          <div
            key={option.value}
            className={cn(
              "relative flex min-h-11 items-start gap-3 rounded-lg border bg-card p-4",
              mode === option.value ? "border-primary bg-accent" : "border-input",
            )}
          >
            <input
              id={`read-mode-${option.value}`}
              type="radio"
              name="read-mode"
              value={option.value}
              checked={mode === option.value}
              aria-describedby={`read-mode-${option.value}-hint`}
              onChange={() => {
                onChange?.(option.value);
              }}
              className="mt-1 size-4 accent-primary"
            />
            <div>
              <label
                htmlFor={`read-mode-${option.value}`}
                className="block cursor-pointer font-medium after:absolute after:inset-0"
              >
                {option.label}
              </label>
              <span
                id={`read-mode-${option.value}-hint`}
                className="block text-sm text-muted-foreground"
              >
                {option.hint}
              </span>
            </div>
          </div>
        ))}
      </div>
    </fieldset>
  );
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
  visionAvailable = false,
  mode = "free",
  onModeChange,
  onFiles,
  onNoticeAction,
}: UploadViewProps) {
  const sendsOut = visionAvailable && mode === "vision";
  const empty = !loading && !notice && documents.length === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title={`Documents for ${reference}`}
        description={
          sendsOut
            ? "Choose files to read with OpenRouter Vision."
            : "Read on this machine. Nothing is sent anywhere."
        }
      />
      {!readOnly && visionAvailable && <ModeChoice mode={mode} onChange={onModeChange} />}
      {!readOnly && sendsOut && (
        <p
          role="status"
          aria-label="Where the page goes"
          className="rounded-lg border border-warning bg-warning-subtle p-4 text-warning"
        >
          Each page image is sent to OpenRouter. Use synthetic documents only. If Vision cannot
          answer, the page is read on this machine instead.
        </p>
      )}
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
            {batch.map((item, index) => (
              <ListRow key={item.key} index={index} className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono">{item.name}</span>
                  <WordBadge
                    word={BATCH_WORDS[item.state]}
                    state={item.state}
                    bad={item.state === "refused"}
                  />
                </div>
                {item.state === "uploading" && (
                  <ReadProgress state="reading" label={`Uploading ${item.name}`} />
                )}
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
            {documents.map((document, index) => (
              <ListRow key={document.id} index={index} className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono">{document.fileName}</span>
                  <WordBadge
                    word={`${STATUS_WORDS[document.status]}${document.detectedType ? `: ${document.detectedType}` : ""}`}
                    state={document.status}
                    bad={document.status === "failed"}
                  />
                </div>
                <ReadProgress
                  state={readState(document.status)}
                  label={`${document.fileName}: ${STATUS_WORDS[document.status]}`}
                />
                {document.readBy && (
                  <p className="text-sm text-muted-foreground">{document.readBy}</p>
                )}
                {document.readNote && <p className="text-sm">{document.readNote}</p>}
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
