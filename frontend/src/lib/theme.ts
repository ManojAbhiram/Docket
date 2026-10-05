export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "docket-theme";
export const THEME_EVENT = "docket:theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** The theme to paint: an explicit choice wins, "system" follows the OS. */
export function resolveTheme(choice: ThemeChoice, systemPrefersDark: boolean): ResolvedTheme {
  if (choice === "system") {
    return systemPrefersDark ? "dark" : "light";
  }
  return choice;
}

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** The saved choice. Storage can throw (private windows, blocked site data): then "system". */
export function readChoice(): ThemeChoice {
  try {
    const saved = storage()?.getItem(THEME_STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches;
}

/** Paint the theme, remember the choice, and tell anything that draws its own colours. */
export function applyChoice(choice: ThemeChoice): ResolvedTheme {
  const resolved = resolveTheme(choice, systemPrefersDark());
  document.documentElement.setAttribute("data-theme", resolved);
  try {
    if (choice === "system") {
      storage()?.removeItem(THEME_STORAGE_KEY);
    } else {
      storage()?.setItem(THEME_STORAGE_KEY, choice);
    }
  } catch {
    // Storage is blocked: the choice lasts until the page reloads.
  }
  window.dispatchEvent(new CustomEvent<ResolvedTheme>(THEME_EVENT, { detail: resolved }));
  return resolved;
}

/** While "system" is selected, follow the OS when it changes. Returns the unsubscribe. */
export function watchSystemTheme(): () => void {
  if (typeof window.matchMedia !== "function") {
    return () => undefined;
  }
  const query = window.matchMedia(DARK_QUERY);
  const onChange = () => {
    if (readChoice() === "system") {
      applyChoice("system");
    }
  };
  query.addEventListener("change", onChange);
  return () => {
    query.removeEventListener("change", onChange);
  };
}
