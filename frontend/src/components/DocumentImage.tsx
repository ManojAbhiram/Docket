import { Button } from "@/components/ui/button";
import type { FieldComparison } from "@/features/applications/types";

interface DocumentImageProps {
  /** Pixel size of the stored image, which the field boxes are measured in. */
  width: number;
  height: number;
  fields: FieldComparison[];
  /** The field whose box is outlined strongly. */
  selectedId?: number | undefined;
  /** The stored image, once the API serves it. Without it a sketch of the page is drawn. */
  src?: string;
  failed?: boolean;
}

const NEEDS_LOOK = new Set(["mismatch", "low_confidence", "not_extracted"]);

/** The document page with the OCR box of the selected field, and of every field that needs a look. */
export function DocumentImage({
  width,
  height,
  fields,
  selectedId,
  src,
  failed = false,
}: DocumentImageProps) {
  if (failed) {
    return (
      <div
        role="alert"
        className="flex aspect-[18/11] flex-col items-center justify-center gap-3 rounded-md border border-border bg-card p-6 text-center"
      >
        <p>The document image did not load.</p>
        <Button variant="outline" className="min-h-11 sm:min-h-9">
          Reload the image
        </Button>
      </div>
    );
  }
  const boxed = fields.filter((f) => f.box !== null);
  return (
    <figure className="overflow-hidden rounded-md border border-border bg-card">
      <svg
        viewBox={`0 0 ${String(width)} ${String(height)}`}
        role="img"
        aria-label="The document page. The selected field is outlined."
        className="block h-auto w-full"
      >
        <rect width={width} height={height} className="fill-card" />
        {src ? (
          <image href={src} width={width} height={height} />
        ) : (
          boxed.map((field) => {
            const [x, y, w, h] = field.box ?? [0, 0, 0, 0];
            return (
              <rect
                key={`sketch-${String(field.id)}`}
                x={x}
                y={y}
                width={w}
                height={h}
                rx={2}
                className="fill-muted"
              />
            );
          })
        )}
        {boxed.map((field) => {
          const [x, y, w, h] = field.box ?? [0, 0, 0, 0];
          const selected = field.id === selectedId;
          if (!selected && !NEEDS_LOOK.has(field.kind)) {
            return null;
          }
          return (
            <rect
              key={`box-${String(field.id)}`}
              data-box={field.id}
              x={x - 3}
              y={y - 3}
              width={w + 6}
              height={h + 6}
              rx={3}
              fill="none"
              strokeWidth={selected ? 3 : 2}
              strokeDasharray={selected ? undefined : "6 4"}
              className={selected ? "stroke-primary" : "stroke-destructive"}
            />
          );
        })}
      </svg>
      <figcaption className="border-t border-border px-4 py-2 text-sm text-muted-foreground">
        Outlined: the selected field. Dashed: fields that need a look.
      </figcaption>
    </figure>
  );
}
