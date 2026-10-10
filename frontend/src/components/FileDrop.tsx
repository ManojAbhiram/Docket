import { UploadCloud } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FileDropProps {
  id: string;
  label: string;
  /** What is accepted and how big, in one line, so a wrong file is not a surprise. */
  hint: string;
  accept: string;
  multiple?: boolean;
  disabled?: boolean;
  /** Called with the chosen or dropped files. Without it the picker is inert, as in the gallery. */
  onFiles?: (files: File[]) => void;
}

/**
 * A file picker in a drop area at least 96 px tall, with a 48 px control inside. Files can also be
 * dropped on the area; the area fills while a drag is over it. The control stays the way in for
 * keyboard and screen reader users.
 */
export function FileDrop({
  id,
  label,
  hint,
  accept,
  multiple = false,
  disabled = false,
  onFiles,
}: FileDropProps) {
  const [over, setOver] = useState(false);
  return (
    <div
      data-over={over ? "true" : undefined}
      className={cn(
        "min-h-24 space-y-3 rounded-lg border-2 border-dashed border-input bg-card p-6 transition-colors duration-(--duration-fast)",
        over && "border-primary bg-accent",
        disabled && "opacity-60",
      )}
      onDragOver={(event) => {
        if (!disabled) {
          event.preventDefault();
          setOver(true);
        }
      }}
      onDragLeave={() => {
        setOver(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        if (!disabled) {
          const files = Array.from(event.dataTransfer.files);
          onFiles?.(multiple ? files : files.slice(0, 1));
        }
      }}
    >
      <div className="flex items-center gap-2">
        <UploadCloud aria-hidden="true" className="size-5 text-primary" />
        <Label htmlFor={id}>{label}</Label>
      </div>
      <Input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={(event) => {
          onFiles?.(Array.from(event.target.files ?? []));
        }}
        className="h-12 py-2.5"
      />
      <p className="text-sm text-muted-foreground">{hint}</p>
    </div>
  );
}
