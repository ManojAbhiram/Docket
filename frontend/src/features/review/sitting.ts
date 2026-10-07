const KEY = "docket-decided";

/**
 * How many decisions this person has saved since they signed in, kept in the tab's session storage
 * so a reload keeps it. A browser that blocks storage counts nothing, which only hides a number.
 */
export function decidedThisSitting(): number {
  try {
    const stored = Number(window.sessionStorage.getItem(KEY));
    return Number.isInteger(stored) && stored > 0 ? stored : 0;
  } catch {
    return 0;
  }
}

/** Add one saved decision to the count. */
export function countDecision(): void {
  try {
    window.sessionStorage.setItem(KEY, String(decidedThisSitting() + 1));
  } catch {
    // Storage is blocked: the line simply stays without the count.
  }
}

/** Forget the count, when someone signs in or out. */
export function resetSitting(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // Nothing was stored, so nothing is left to forget.
  }
}
