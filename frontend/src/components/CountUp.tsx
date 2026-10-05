import { useEffect, useRef, useState } from "react";

import { countFrame, prefersReducedMotion, tokenDuration } from "@/lib/motion";

interface CountUpProps {
  value: number;
  /** The product's formatter, applied to every frame, so grouping and digits never change. */
  format: (value: number) => string;
}

/** The count runs only when motion is allowed and the duration token is above zero. */
function animationMs(): number {
  return prefersReducedMotion() ? 0 : tokenDuration("--duration-slow");
}

/**
 * A number that counts up once when it first appears with real data, and from its last value when
 * it changes. With reduced motion, or a zero duration, the final figure is there at once. The text
 * holds the figure once and no live region wraps it, so a screen reader reads it once.
 */
export function CountUp({ value, format }: CountUpProps) {
  const [shown, setShown] = useState(0);
  const settled = useRef<number | null>(null);
  const animate = animationMs() > 0;

  useEffect(() => {
    const duration = animationMs();
    const from = settled.current;
    if (duration <= 0 || from === value) {
      return undefined;
    }
    const started = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = (now - started) / duration;
      setShown(countFrame(from, value, progress));
      if (progress >= 1) {
        settled.current = value;
        return;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [value]);

  return <span data-numeric>{format(animate ? shown : value)}</span>;
}
