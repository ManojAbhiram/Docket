import { useState } from "react";

import { DocumentImage } from "@/components/DocumentImage";
import { Kbd } from "@/components/Kbd";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ShortcutsDialog, type Shortcut } from "@/components/ShortcutsDialog";
import { StatusBadge, type StatusKind } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PAGE_SIZE } from "@/features/applications/fixtures";
import type { FieldComparison } from "@/features/applications/types";
import { FieldsPanel } from "@/features/review/components/FieldsPanel";
import { failedFirst } from "@/features/review/mapping";
import { useHotkeys } from "@/lib/hotkeys";

const COMPARE_SHORTCUTS: Shortcut[] = [
  { keys: ["j", "k"], does: "Next and previous field" },
  { keys: ["d"], does: "Decide this application" },
  { keys: ["?"], does: "Show these shortcuts" },
];

interface CompareViewProps {
  reference: string;
  name: string;
  status: StatusKind;
  fields: FieldComparison[];
  loading?: boolean;
  notice?: NoticeSpec;
  /** A line above the fields when not every document was read. */
  partialNote?: string;
  imageFailed?: boolean;
  offline?: boolean;
  initialSelected?: number;
  /** Opens the decision dialog (S-08). The `d` key and the Decide button both call it. */
  onDecide?: () => void;
}

/** S-07: each document field beside the application value, with the OCR box and a confidence badge. */
export function CompareView({
  reference,
  name,
  status,
  fields,
  loading = false,
  notice,
  partialNote,
  imageFailed = false,
  offline = false,
  initialSelected,
  onDecide,
}: CompareViewProps) {
  const ordered = failedFirst(fields);
  const [selected, setSelected] = useState<number | undefined>(initialSelected ?? ordered[0]?.id);
  const [showShortcuts, setShowShortcuts] = useState(false);

  const move = (step: number) => {
    const index = ordered.findIndex((f) => f.id === selected);
    const next = ordered[(index + step + ordered.length) % ordered.length];
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
      if (!loading && !offline) {
        onDecide?.();
      }
    },
    "?": () => {
      setShowShortcuts(true);
    },
  });

  const noBox = ordered.find((f) => f.id === selected)?.box === null;
  return (
    <div className="space-y-6">
      <PageHeader
        title={reference}
        description={name}
        actions={
          <>
            <StatusBadge status={status} />
            <Button
              className="min-h-11 sm:min-h-9"
              disabled={loading || offline}
              onClick={onDecide}
            >
              Decide <Kbd>d</Kbd>
            </Button>
          </>
        }
      />
      {offline && (
        <p role="status" className="text-muted-foreground">
          You are offline. Connect to decide.
        </p>
      )}
      {notice && <NoticeBox spec={notice} />}
      {partialNote && (
        <p role="status" className="text-warning">
          {partialNote}
        </p>
      )}
      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2" aria-busy="true">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      ) : fields.length === 0 ? (
        <div className="space-y-3 py-8">
          <p className="text-lg">No documents have been read yet.</p>
          <Button variant="outline" className="min-h-11 sm:min-h-9">
            Upload documents
          </Button>
        </div>
      ) : (
        <FieldsPanel
          fields={ordered}
          selectedId={selected}
          onSelect={setSelected}
          image={
            <DocumentImage
              width={PAGE_SIZE.width}
              height={PAGE_SIZE.height}
              fields={fields}
              selectedId={selected}
              failed={imageFailed}
            />
          }
          imageNote={
            noBox && (
              <p role="status" className="text-muted-foreground">
                No position for this field. The full document is shown.
              </p>
            )
          }
        />
      )}
      <ShortcutsDialog
        open={showShortcuts}
        onOpenChange={setShowShortcuts}
        shortcuts={COMPARE_SHORTCUTS}
      />
    </div>
  );
}
