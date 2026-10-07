import type { Box } from "@/features/applications/types";

/** Width over height of the slot a crop is drawn into (160 by 40 px, docs/design/DESIGN.md). */
export const CROP_ASPECT = 4;

const MARGIN = 8;

export interface CropRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * The part of the page image to show for one field: the field's box centred, a margin around it,
 * widened or heightened to the slot's shape, and kept inside the page. Boxes are in the stored
 * image's pixels, so the result is too.
 */
export function cropRect(box: Box, page: { width: number; height: number }): CropRect {
  const [x, y, width, height] = box;
  const wanted = Math.max(width + 2 * MARGIN, CROP_ASPECT * (height + 2 * MARGIN));
  // Never larger than the page in either direction, and still the shape of the slot.
  const w = Math.min(wanted, page.width, page.height * CROP_ASPECT);
  const h = w / CROP_ASPECT;
  const left = Math.min(Math.max(x + width / 2 - w / 2, 0), page.width - w);
  const top = Math.min(Math.max(y + height / 2 - h / 2, 0), page.height - h);
  return { x: left, y: top, width: w, height: h };
}
