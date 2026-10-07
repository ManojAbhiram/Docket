import { Check, Minus, TriangleAlert, X, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { FieldComparison, FieldKind } from "@/features/applications/types";
import { failedFirst } from "@/features/review/mapping";
import { cn } from "@/lib/utils";

const RESULT: Record<FieldKind, { word: string; icon: LucideIcon; tone: string }> = {
  match: { word: "Match", icon: Check, tone: "text-success" },
  mismatch: { word: "Mismatch", icon: X, tone: "text-destructive" },
  low_confidence: { word: "Check value", icon: TriangleAlert, tone: "text-warning" },
  not_extracted: { word: "Not found", icon: TriangleAlert, tone: "text-warning" },
  skipped: { word: "Skipped", icon: Minus, tone: "text-muted-foreground" },
};

/** The outcome of one comparison as a word and a shape, never colour alone. */
export function Result({ kind }: { kind: FieldKind }) {
  const { word, icon: Icon, tone } = RESULT[kind];
  return (
    <span className={cn("inline-flex items-center gap-1 font-semibold", tone)}>
      <Icon className="size-4" aria-hidden="true" />
      {word}
    </span>
  );
}

interface FieldsPanelProps {
  fields: FieldComparison[];
  selectedId: number | undefined;
  onSelect: (id: number) => void;
  /** The page image, drawn beside the fields. */
  image: ReactNode;
  /** A line under the image, for example that the selected field has no position. */
  imageNote?: ReactNode;
}

/** Each field beside the application's value, with the page image next to it. */
export function FieldsPanel({ fields, selectedId, onSelect, image, imageNote }: FieldsPanelProps) {
  const ordered = failedFirst(fields);
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="order-last space-y-4 lg:order-first lg:col-span-3">
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
                  data-state={field.id === selectedId ? "selected" : undefined}
                >
                  <TableCell>
                    <Button
                      variant="ghost"
                      className="min-h-9 justify-start px-2"
                      aria-pressed={field.id === selectedId}
                      onClick={() => {
                        onSelect(field.id);
                      }}
                    >
                      {field.label}
                    </Button>
                  </TableCell>
                  <TableCell className="font-mono break-words whitespace-normal">
                    {field.applicationValue}
                  </TableCell>
                  <TableCell className="font-mono break-words whitespace-normal">
                    {field.documentValue || "none"}
                  </TableCell>
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
                aria-pressed={field.id === selectedId}
                onClick={() => {
                  onSelect(field.id);
                }}
              >
                <span className="flex items-center justify-between gap-2 font-semibold">
                  {field.label}
                  <Result kind={field.kind} />
                </span>
                <span className="font-mono text-sm">Application: {field.applicationValue}</span>
                <span className="font-mono text-sm">Document: {field.documentValue || "none"}</span>
                <ConfidenceBadge confidence={field.confidence} />
              </Button>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-2 lg:sticky lg:top-4 lg:col-span-2 lg:self-start">
        {image}
        {imageNote}
      </div>
    </div>
  );
}
