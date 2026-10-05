import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FileDropProps {
  id: string;
  label: string;
  /** What is accepted and how big, in one line, so a wrong file is not a surprise. */
  hint: string;
  accept: string;
  multiple?: boolean;
  disabled?: boolean;
}

/** A file picker in a drop area at least 96 px tall, with a 48 px control inside. */
export function FileDrop({
  id,
  label,
  hint,
  accept,
  multiple = false,
  disabled = false,
}: FileDropProps) {
  return (
    <div className="min-h-24 space-y-3 rounded-md border border-dashed border-input p-6">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="h-12 py-2.5"
      />
      <p className="text-sm text-muted-foreground">{hint}</p>
    </div>
  );
}
