import { useEffect, useRef } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import type { Box } from "@/features/applications/types";
import { CROP_ASPECT, cropRect } from "@/features/review/crop";
import type { ImageState } from "@/features/review/useImageSize";

const WIDTH = 160;
const HEIGHT = WIDTH / CROP_ASPECT;

interface FieldCropProps {
  /** The page image, as the compare screen loaded it. */
  source: ImageState;
  /** Where the field sits on the page, or null when the engine gave no position. */
  box: Box | null;
  /** The field's name, for a screen reader. */
  label: string;
}

/**
 * A small picture of the spot on the page where one value was read, drawn in the browser from the
 * page image the screen already holds, so a row shows its evidence beside its value. The slot keeps
 * its size in every state, so the table does not jump while the image loads.
 */
export function FieldCrop({ source, box, label }: FieldCropProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const image = source.status === "ready" ? source.image : null;
  const width = source.status === "ready" ? source.width : 0;
  const height = source.status === "ready" ? source.height : 0;

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext("2d");
    if (!element || !context || !image || !box) {
      return;
    }
    const scale = window.devicePixelRatio || 1;
    element.width = Math.round(WIDTH * scale);
    element.height = Math.round(HEIGHT * scale);
    const rect = cropRect(box, { width, height });
    context.drawImage(
      image,
      rect.x,
      rect.y,
      rect.width,
      rect.height,
      0,
      0,
      element.width,
      element.height,
    );
  }, [image, box, width, height]);

  const slot = "h-10 w-40 shrink-0 rounded-sm border border-border";
  if (source.status === "loading") {
    return <Skeleton data-testid="crop-slot" aria-busy="true" className={slot} />;
  }
  if (source.status === "failed") {
    return <Note>Image unavailable</Note>;
  }
  if (!box) {
    return <Note>No position</Note>;
  }
  return (
    <canvas
      ref={canvas}
      role="img"
      aria-label={`${label}, as read from the page`}
      className={`${slot} bg-card`}
      style={{ width: WIDTH, height: HEIGHT }}
    />
  );
}

function Note({ children }: { children: string }) {
  return (
    <span
      data-testid="crop-slot"
      className="flex h-10 w-40 shrink-0 items-center justify-center rounded-sm border border-dashed border-border px-2 text-center text-sm text-muted-foreground"
    >
      {children}
    </span>
  );
}
