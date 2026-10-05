import { afterEach, describe, expect, it, vi } from "vitest";

import {
  THEME_EVENT,
  THEME_STORAGE_KEY,
  applyChoice,
  readChoice,
  resolveTheme,
  type ResolvedTheme,
} from "./theme";

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("resolveTheme", () => {
  it("lets an explicit choice win over the system", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("follows the system when the choice is system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });
});

describe("applyChoice", () => {
  it("sets data-theme on the root element and remembers an explicit choice", () => {
    applyChoice("dark");

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("forgets the saved choice when it goes back to system", () => {
    applyChoice("dark");
    applyChoice("system");

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    expect(readChoice()).toBe("system");
  });

  it("tells a canvas or chart which theme was painted", () => {
    const seen: ResolvedTheme[] = [];
    window.addEventListener(THEME_EVENT, (event) => {
      seen.push((event as CustomEvent<ResolvedTheme>).detail);
    });

    applyChoice("light");

    expect(seen).toEqual(["light"]);
  });
});

describe("readChoice", () => {
  it("returns the saved light or dark choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    expect(readChoice()).toBe("light");
  });

  it("ignores a saved value it does not know", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "purple");

    expect(readChoice()).toBe("system");
  });

  it("still works when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(readChoice()).toBe("system");
  });
});
