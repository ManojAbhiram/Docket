import { useState } from "react";

import { DocumentImage } from "@/components/DocumentImage";
import { Kbd } from "@/components/Kbd";
import type { NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ShortcutsDialog, type Shortcut } from "@/components/ShortcutsDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { documentImageUrl } from "@/features/review/api";
import { ActionNotice } from "@/features/review/components/ActionNotice";
import { FieldsPanel } from "@/features/review/components/FieldsPanel";
import {
  documentTitle,
  failedFirst,
  failureSentence,
  toComparison,
} from "@/features/review/mapping";
import type { ApplicationDetail, ReviewDocument } from "@/features/review/schemas";
import { useImageSize } from "@/features/review/useImageSize";
import { useHotkeys } from "@/lib/hotkeys";

const SHORTCUTS: Shortcut[] = [
  { keys: ["j", "k"], does: "Next and previous field" },
  { keys: ["d"], does: "Decide this application" },
  { keys: ["?"], does: "Show these shortcuts" },
];

interface ReviewViewProps {
  application?: ApplicationDetail | undefined;
  loading?: boolean;
  notice?: NoticeSpec;
  onNoticeAction?: () => void;
  /** The signed-in person may decide this application. */
  canDecide?: boolean;
  onDecide?: () => void;
  /** Staff can open the upload when nothing has been read. */
  onUpload?: (() => void) | undefined;
}

/** S-07 with real data: every current document with its fields beside the application's values. */
export function ReviewView({
  application,
  loading = false,
  notice,
  onNoticeAction,
  canDecide = false,
  onDecide,
  onUpload,
}: ReviewViewProps) {
  const current = application?.documents.filter((doc) => doc.is_current) ?? [];
  const earlier = application?.documents.filter((doc) => !doc.is_current) ?? [];
  const order = current.flatMap((doc) => failedFirst(doc.fields.map(toComparison)));
  const [selected, setSelected] = useState<number | undefined>();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const active = selected ?? order[0]?.id;

  const move = (step: number) => {
    const index = order.findIndex((field) => field.id === active);
    const next = order[(index + step + order.length) % order.length];
    if (next) {
      setSelected(next.id);
    }
  };
  useHotkeys({
    j: () => {
      move(1);
    },
    k: () => {
      move(-1);
    },
    d: () => {
      if (canDecide) {
        onDecide?.();
      }
    },
    "?": () => {
      setShowShortcuts(true);
    },
  });

  const nothingRead = application !== undefined && current.length === 0 && earlier.length === 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title={application?.application_ref ?? "Application not found"}
        description={application?.full_name}
        actions={
          application && (
            <>
              <StatusBadge status={application.rejected ? "rejected" : application.status} />
              {canDecide && (
                <Button id="decide-button" className="min-h-11 sm:min-h-9" onClick={onDecide}>
                  Decide <Kbd>d</Kbd>
                </Button>
              )}
            </>
          )
        }
      />
      {notice && <ActionNotice spec={notice} onAction={onNoticeAction} />}
      {loading && (
        <div className="grid gap-6 lg:grid-cols-2" aria-busy="true">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      )}
      {nothingRead && (
        <div className="space-y-3 py-8">
          <p className="text-lg">No documents have been read yet.</p>
          {onUpload && (
            <Button variant="outline" className="min-h-11 sm:min-h-9" onClick={onUpload}>
              Upload documents
            </Button>
          )}
        </div>
      )}
      {current.map((doc) => (
        <DocumentSection key={doc.id} doc={doc} selectedId={active} onSelect={setSelected} />
      ))}
      {earlier.length > 0 && (
        <details className="rounded-md border border-border bg-card p-4">
          <summary className="min-h-11 cursor-pointer font-semibold">
            Earlier uploads ({earlier.length})
          </summary>
          <div className="space-y-8 pt-4">
            {earlier.map((doc) => (
              <DocumentSection
                key={doc.id}
                doc={doc}
                selectedId={undefined}
                onSelect={setSelected}
              />
            ))}
          </div>
        </details>
      )}
      <ShortcutsDialog open={showShortcuts} onOpenChange={setShowShortcuts} shortcuts={SHORTCUTS} />
    </div>
  );
}

interface DocumentSectionProps {
  doc: ReviewDocument;
  selectedId: number | undefined;
  onSelect: (id: number) => void;
}

function DocumentSection({ doc, selectedId, onSelect }: DocumentSectionProps) {
  const title = documentTitle(doc.detected_type);
  const fields = doc.fields.map(toComparison);
  const picked = fields.find((field) => field.id === selectedId);
  return (
    <section aria-labelledby={`doc-${doc.id}`} className="space-y-3">
      <h2 id={`doc-${doc.id}`} className="text-lg font-semibold">
        {title}
      </h2>
      {doc.status === "failed" ? (
        <div className="space-y-1">
          <p>This document could not be read.</p>
          <p className="text-muted-foreground">{failureSentence(doc.failure_reason)}</p>
        </div>
      ) : doc.status === "uploaded" || doc.status === "processing" ? (
        <p className="text-muted-foreground">This document is still being read.</p>
      ) : doc.detected_type === "unknown" ? (
        <p>This document was not recognised as a marksheet or an ID proof.</p>
      ) : (
        <FieldsPanel
          fields={fields}
          selectedId={selectedId}
          onSelect={onSelect}
          image={<LiveImage documentId={doc.id} fields={fields} selectedId={selectedId} />}
          imageNote={
            picked?.box === null && (
              <p role="status" className="text-muted-foreground">
                No position for this field. The full document is shown.
              </p>
            )
          }
        />
      )}
    </section>
  );
}

interface LiveImageProps {
  documentId: string;
  fields: ReturnType<typeof toComparison>[];
  selectedId: number | undefined;
}

/** The stored page, measured first so the field boxes land where the text is. */
function LiveImage({ documentId, fields, selectedId }: LiveImageProps) {
  const src = documentImageUrl(documentId);
  const { state, retry } = useImageSize(src);
  if (state.status === "failed") {
    return (
      <div
        role="alert"
        className="flex aspect-[18/11] flex-col items-center justify-center gap-3 rounded-md border border-border bg-card p-6 text-center"
      >
        <p>The document image did not load.</p>
        <Button variant="outline" className="min-h-11 sm:min-h-9" onClick={retry}>
          Reload the image
        </Button>
      </div>
    );
  }
  if (state.status === "loading") {
    return <Skeleton className="aspect-[18/11]" aria-busy="true" />;
  }
  return (
    <DocumentImage
      width={state.width}
      height={state.height}
      fields={fields}
      selectedId={selectedId}
      src={src}
    />
  );
}
