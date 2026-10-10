import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { applyChoice, readChoice, watchSystemTheme, type ThemeChoice } from "@/lib/theme";
import { cn } from "@/lib/utils";

const ORDER: ThemeChoice[] = ["system", "light", "dark"];
const LABEL: Record<ThemeChoice, string> = { system: "System", light: "Light", dark: "Dark" };
const ICON = { system: Monitor, light: Sun, dark: Moon } as const;

/** One button that cycles System, Light and Dark. It follows the OS while System is selected. */
export function ThemeToggle({ className }: { className?: string }) {
  const [choice, setChoice] = useState<ThemeChoice>(readChoice);
  useEffect(() => watchSystemTheme(), []);

  const next = ORDER[(ORDER.indexOf(choice) + 1) % ORDER.length] ?? "system";
  const Icon = ICON[choice];

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={cn("min-h-11 sm:min-h-8", className)}
      aria-label={`Theme: ${LABEL[choice]}. Switch to ${LABEL[next]}`}
      onClick={() => {
        applyChoice(next);
        setChoice(next);
      }}
    >
      <Icon aria-hidden="true" />
      <span>{LABEL[choice]}</span>
    </Button>
  );
}
