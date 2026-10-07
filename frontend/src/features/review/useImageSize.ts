import { useEffect, useState } from "react";

type Outcome =
  | { key: string; status: "ready"; width: number; height: number; image: HTMLImageElement }
  | { key: string; status: "failed" };

export type ImageState =
  | { status: "loading" }
  | { status: "ready"; width: number; height: number; image: HTMLImageElement }
  | { status: "failed" };

/**
 * Loads a page image once to learn its pixel size, because the field boxes are measured in the
 * stored image's pixels, and keeps the loaded image so each field's crop is drawn from it without
 * another request (the page is served no-store). `retry` loads it again after a failure.
 */
export function useImageSize(src: string): { state: ImageState; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const key = `${src}#${String(attempt)}`;

  useEffect(() => {
    const image = new Image();
    image.onload = () => {
      setOutcome({
        key,
        status: "ready",
        width: image.naturalWidth,
        height: image.naturalHeight,
        image,
      });
    };
    image.onerror = () => {
      setOutcome({ key, status: "failed" });
    };
    image.src = src;
    return () => {
      image.onload = null;
      image.onerror = null;
    };
  }, [src, key]);

  const state: ImageState =
    outcome?.key === key
      ? outcome.status === "ready"
        ? { status: "ready", width: outcome.width, height: outcome.height, image: outcome.image }
        : { status: "failed" }
      : { status: "loading" };
  return {
    state,
    retry: () => {
      setAttempt((count) => count + 1);
    },
  };
}
