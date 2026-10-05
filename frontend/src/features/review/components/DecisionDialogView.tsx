import { useState } from "react";

import { Kbd } from "@/components/Kbd";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useHotkeys } from "@/lib/hotkeys";

export type DecisionAction = "approve" | "correct" | "reject";

const CHOICES: { value: DecisionAction; label: string; key: string }[] = [
  { value: "approve", label: "Approve", key: "a" },
  { value: "correct", label: "Correct a value", key: "c" },
  { value: "reject", label: "Reject", key: "r" },
];

interface DecisionDialogViewProps {
  reference: string;
  /** The field being corrected, from the selection on S-07. */
  fieldLabel: string;
  initialAction?: DecisionAction;
  reason?: string;
  newValue?: string;
  /** Shown under the reason field, with the typed text kept. */
  reasonError?: string;
  busy?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  /** The dialog is controlled by the route; the gallery keeps it open. */
  open?: boolean;
  /** Called by Cancel, Esc and the close button. */
  onClose?: () => void;
}

/** S-08: approve, correct a value or reject, with the reason a rejection needs. Every decision is logged. */
export function DecisionDialogView({
  reference,
  fieldLabel,
  initialAction,
  reason = "",
  newValue = "",
  reasonError,
  busy = false,
  offline = false,
  notice,
  open = true,
  onClose,
}: DecisionDialogViewProps) {
  const [action, setAction] = useState<DecisionAction | undefined>(initialAction);
  useHotkeys(
    {
      a: () => {
        setAction("approve");
      },
      c: () => {
        setAction("correct");
      },
      r: () => {
        setAction("reject");
      },
    },
    open && !busy,
  );
  const blocked = busy || offline || action === undefined;
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onClose?.();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Decide {reference}</DialogTitle>
          <DialogDescription>
            Every decision is logged with who, when, what and why. A logged decision cannot be
            edited.
          </DialogDescription>
        </DialogHeader>
        {notice && <NoticeBox spec={notice} />}
        <div role="radiogroup" aria-label="Decision" className="grid gap-2 sm:grid-cols-3">
          {CHOICES.map((choice) => (
            <Button
              key={choice.value}
              type="button"
              role="radio"
              aria-checked={action === choice.value}
              variant={action === choice.value ? "default" : "outline"}
              className="min-h-11 justify-between"
              disabled={busy}
              onClick={() => {
                setAction(choice.value);
              }}
            >
              {choice.label}
              <Kbd>{choice.key}</Kbd>
            </Button>
          ))}
        </div>
        {action === "correct" && (
          <div className="space-y-2">
            <p className="text-muted-foreground">Field: {fieldLabel}</p>
            <Label htmlFor="new-value">New value</Label>
            <Input id="new-value" defaultValue={newValue} disabled={busy} />
          </div>
        )}
        {action === "reject" && (
          <div className="space-y-2">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              defaultValue={reason}
              disabled={busy}
              aria-invalid={reasonError ? true : undefined}
              aria-describedby={reasonError ? "reason-error" : undefined}
            />
            {reasonError && (
              <p id="reason-error" className="text-destructive">
                {reasonError}
              </p>
            )}
          </div>
        )}
        {offline && (
          <p role="status" className="text-muted-foreground">
            You are offline. Connect to save the decision.
          </p>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="min-h-11 sm:min-h-9"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button type="button" className="min-h-11 sm:min-h-9" disabled={blocked}>
            {busy ? "Saving decision" : "Save decision"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
