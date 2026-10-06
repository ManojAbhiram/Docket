import { vi } from "vitest";

/** jsdom has no matchMedia, which the toast container reads for the colour scheme. */
export function stubMatchMedia(): void {
  vi.stubGlobal("matchMedia", (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }));
}
