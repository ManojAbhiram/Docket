import { useState } from "react";

/**
 * How many times `value` has changed since this component mounted. It is 0 on the first render and
 * stays 0 through re-renders with the same value, so a refresh that changes nothing animates
 * nothing. Used as a key and a flag: a status that really changed pops once (motion.md, rule 3).
 */
export function useChangeCount(value: string): number {
  const [last, setLast] = useState(value);
  const [changes, setChanges] = useState(0);
  if (last !== value) {
    setLast(value);
    setChanges(changes + 1);
  }
  return changes;
}
