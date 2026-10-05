import { Check, Minus, TriangleAlert, X, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { DocumentImage } from "@/components/DocumentImage";
import { Kbd } from "@/components/Kbd";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ShortcutsDialog, type Shortcut } from "@/components/ShortcutsDialog";
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
import { PAGE_SIZE } from "@/features/applications/fixtures";
import type { FieldComparison, FieldKind } from "@/features/applications/types";
import { useHotkeys } from "@/lib/hotkeys";
import { cn } from "@/lib/utils";

const RESULT: Record<FieldKind, { word: string; icon: LucideIcon; tone: string }> = {
  match: { word: "Match", icon: Check, tone: "text-success" },
  mismatch: { word: "Mismatch", icon: X, tone: "text-destructive" },
  low_confidence: { word: "Check value", icon: TriangleAlert, tone: "text-warning" },
  not_extracted: { word: "Not found", icon: TriangleAlert, tone: "text-warning" },
  skipped: { word: "Skipped", icon: Minus, tone: "text-muted-foreground" },
};

const COMPARE_SHORTCUTS: Shortcut[] = [
  { keys: ["j", "k"], does: "Next and previous field" },
  { keys: ["d"], does: "Decide this application" },
  { keys: ["?"], does: "Show these shortcuts" },
];

function Result({ kind }: { kind: FieldKind }) {
  const { word, icon: Icon, tone } = RESULT[kind];
  return (
    <span className={cn("inline-flex items-center gap-1 font-semibold", tone)}>
      <Icon className="size-4" aria-hidden="true" />
      {word}
    </span>
  );
}

/** Fields that need a look first, then the rest in their original order. */
function failedFirst(fields: FieldComparison[]): FieldComparison[] {
  return [...fields].sort((a, b) => Number(a.kind === "match") - Number(b.kind === "match"));
}

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
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="order-last space-y-4 lg:order-first">
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Field</TableHead>
                    <TableHead scope="col">Application</TableHead>
                    <TableHead scope="col">Document</TableHead>
                    <TableHead scope="col">Result</TableHead>
                    <TableHead scope="col">Confidence</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ordered.map((field) => (
                    <TableRow
                      key={field.id}
                      data-state={field.id === selected ? "selected" : undefined}
                    >
                      <TableCell>
                        <Button
                          variant="ghost"
                          className="min-h-9 justify-start px-2"
                          aria-pressed={field.id === selected}
                          onClick={() => {
                            setSelected(field.id);
                          }}
                        >
                          {field.label}
                        </Button>
                      </TableCell>
                      <TableCell className="font-mono">{field.applicationValue}</TableCell>
                      <TableCell className="font-mono">{field.documentValue || "none"}</TableCell>
                      <TableCell>
                        <Result kind={field.kind} />
                      </TableCell>
                      <TableCell>
                        <ConfidenceBadge confidence={field.confidence} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <ul className="space-y-2 md:hidden">
              {ordered.map((field) => (
                <li key={field.id} className="rounded-md border border-border bg-card">
                  <Button
                    variant="ghost"
                    className="h-auto min-h-11 w-full flex-col items-stretch gap-2 p-4 text-left whitespace-normal"
                    aria-pressed={field.id === selected}
                    onClick={() => {
                      setSelected(field.id);
                    }}
                  >
                    <span className="flex items-center justify-between gap-2 font-semibold">
                      {field.label}
                      <Result kind={field.kind} />
                    </span>
                    <span className="font-mono text-sm">Application: {field.applicationValue}</span>
                    <span className="font-mono text-sm">
                      Document: {field.documentValue || "none"}
                    </span>
                    <ConfidenceBadge confidence={field.confidence} />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2 lg:sticky lg:top-4 lg:self-start">
            <DocumentImage
              width={PAGE_SIZE.width}
              height={PAGE_SIZE.height}
              fields={fields}
              selectedId={selected}
              failed={imageFailed}
            />
            {noBox && (
              <p role="status" className="text-muted-foreground">
                No position for this field. The full document is shown.
              </p>
            )}
          </div>
        </div>
      )}
      <ShortcutsDialog
        open={showShortcuts}
        onOpenChange={setShowShortcuts}
        shortcuts={COMPARE_SHORTCUTS}
      />
    </div>
  );
}
