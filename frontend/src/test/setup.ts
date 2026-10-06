import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

import { server } from "./msw";

// jsdom has no ResizeObserver; Radix measures with it (radio group, checkbox,
// slider, switch), so a component test of a form would throw without it.
class ResizeObserverStub {
  observe(): undefined {
    return undefined;
  }
  unobserve(): undefined {
    return undefined;
  }
  disconnect(): undefined {
    return undefined;
  }
}
if (!("ResizeObserver" in globalThis)) {
  Object.defineProperty(globalThis, "ResizeObserver", {
    value: ResizeObserverStub,
    writable: true,
  });
}

// jsdom has no matchMedia; the toast container at the root of the layout reads it for the colour
// scheme. A plain stub that matches nothing, so every test can mount the whole app.
if (typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

// jsdom has no layout; the router's scroll restoration calls this on navigation.
Object.defineProperty(window, "scrollTo", { value: () => undefined, writable: true });

// MSW answers fetch for every test; an unhandled request is a failure, never
// a silent network call. Only src/lib/api.test.ts stubs fetch with
// vi.stubGlobal, to assert on the request the client builds; that bypasses it.
beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.unstubAllGlobals();
});

afterAll(() => {
  server.close();
});
