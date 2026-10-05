import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useHotkeys, type HotkeyMap } from "./hotkeys";

function Probe({ map }: { map: HotkeyMap }) {
  useHotkeys(map);
  return <input aria-label="Reason" />;
}

describe("useHotkeys", () => {
  it("runs the action for a key pressed on the page", async () => {
    const next = vi.fn();
    render(<Probe map={{ j: next }} />);

    await userEvent.keyboard("j");

    expect(next).toHaveBeenCalledOnce();
  });

  it("does nothing while the user is typing in a field", async () => {
    const next = vi.fn();
    render(<Probe map={{ j: next }} />);
    await userEvent.click(screen.getByLabelText("Reason"));

    await userEvent.keyboard("j");

    expect(next).not.toHaveBeenCalled();
  });

  it("does nothing when a modifier key is held", async () => {
    const next = vi.fn();
    render(<Probe map={{ j: next }} />);

    await userEvent.keyboard("{Control>}j{/Control}");

    expect(next).not.toHaveBeenCalled();
  });
});
