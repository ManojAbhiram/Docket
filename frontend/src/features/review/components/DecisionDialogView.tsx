import { RadioGroup as RadioGroupPrimitive } from "radix-ui";
import { useState } from "react";

import { ActionNotice } from "@/components/ActionNotice";
import { Kbd } from "@/components/Kbd";
import type { NoticeSpec } from "@/components/Notice";
import { Button, buttonVariants } from "@/components/ui/button";
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
import { cn } from "@/lib/utils";

export type DecisionAction = "approve" | "correct" | "reject";

const CHOICES: { value: DecisionAction; label: string; key: string }[] = [
  { value: "approve", label: "Approve", key: "a" },
  { value: "correct", label: "Correct a value", key: "c" },
  { value: "reject", label: "Reject", key: "r" },
];

/** A field a verifier may correct. */
export interface CorrectableField {
  id: number;
  label: string;
  value: string;
}

/** What the dialog hands back when the verifier saves. */
export interface DecisionDraft {
  action: DecisionAction;
  reason: string;
  newValue: string;
  fieldId: number | undefined;
}

interface DecisionDialogViewProps {
  reference: string;
  /** The field being corrected, from the selection on S-07. Used when no field list is given. */
  fieldLabel: string;
  /** The fields a correction can name, flagged ones first. */
  fields?: CorrectableField[];
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
  /** Called with the draft when it passes the checks the screen can make itself. */
  onSave?: (draft: DecisionDraft) => void;
  /** The id of the control that gets focus back when the dialog closes. */
  returnFocusTo?: string;
}

/** S-08: approve, correct a value or reject, with the reason a rejection needs. Every decision is logged. */
export function DecisionDialogView({
  reference,
  fieldLabel,
  fields,
  initialAction,
  reason = "",
  newValue = "",
  reasonError,
  busy = false,
  offline = false,
  notice,
  open = true,
  onClose,
  onSave,
  returnFocusTo,
}: DecisionDialogViewProps) {
  const [action, setAction] = useState<DecisionAction | undefined>(initialAction);
  const [reasonText, setReasonText] = useState(reason);
  const [valueText, setValueText] = useState(newValue);
  const [fieldId, setFieldId] = useState<number | undefined>(fields?.[0]?.id);
  const [problem, setProblem] = useState<{ field: "reason" | "value"; text: string } | undefined>();
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
  const reasonProblem = reasonError ?? (problem?.field === "reason" ? problem.text : undefined);
  const valueProblem = problem?.field === "value" ? problem.text : undefined;

  const save = () => {
    if (action === undefined) {
      return;
    }
    if (action === "reject" && reasonText.trim() === "") {
      setProblem({ field: "reason", text: "Give a reason for the rejection." });
      return;
    }
    if (action === "correct" && valueText.trim() === "") {
      setProblem({ field: "value", text: "Enter the new value." });
      return;
    }
    setProblem(undefined);
    onSave?.({ action, reason: reasonText.trim(), newValue: valueText.trim(), fieldId });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onClose?.();
        }
      }}
    >
      <DialogContent
        onCloseAutoFocus={(event) => {
          const target = returnFocusTo ? document.getElementById(returnFocusTo) : null;
          if (target) {
            event.preventDefault();
            target.focus();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>Decide {reference}</DialogTitle>
          <DialogDescription>
            Every decision is logged with who, when, what and why. A logged decision cannot be
            edited.
          </DialogDescription>
        </DialogHeader>
        {notice && <ActionNotice spec={notice} />}
        <RadioGroupPrimitive.Root
          aria-label="Decision"
          value={action ?? ""}
          disabled={busy}
          orientation="horizontal"
          className="grid gap-2 sm:grid-cols-3"
          onValueChange={(next) => {
            setAction(next as DecisionAction);
            setProblem(undefined);
          }}
        >
          {CHOICES.map((choice) => (
            <RadioGroupPrimitive.Item
              key={choice.value}
              value={choice.value}
              className={cn(
                buttonVariants({ variant: action === choice.value ? "default" : "outline" }),
                "min-h-11 justify-between",
              )}
            >
              {choice.label}
              <Kbd>{choice.key}</Kbd>
            </RadioGroupPrimitive.Item>
          ))}
        </RadioGroupPrimitive.Root>
        {action === "correct" && (
          <div className="space-y-2">
            {fields && fields.length > 0 ? (
              <>
                <Label htmlFor="correct-field">Field</Label>
                <select
                  id="correct-field"
                  className="min-h-11 w-full rounded-md border border-input bg-background px-3 text-base sm:min-h-9"
                  value={fieldId}
                  disabled={busy}
                  onChange={(event) => {
                    setFieldId(Number(event.target.value));
                  }}
                >
                  {fields.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}: {option.value || "none"}
                    </option>
                  ))}
                </select>
              </>
            ) : (
              <p className="text-muted-foreground">Field: {fieldLabel}</p>
            )}
            <Label htmlFor="new-value">New value</Label>
            <Input
              id="new-value"
              value={valueText}
              disabled={busy}
              aria-invalid={valueProblem ? true : undefined}
              aria-describedby={valueProblem ? "new-value-error" : undefined}
              onChange={(event) => {
                setValueText(event.target.value);
              }}
            />
            {valueProblem && (
              <p id="new-value-error" className="text-destructive">
                {valueProblem}
              </p>
            )}
          </div>
        )}
        {action === "reject" && (
          <div className="space-y-2">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              value={reasonText}
              disabled={busy}
              aria-invalid={reasonProblem ? true : undefined}
              aria-describedby={reasonProblem ? "reason-error" : undefined}
              onChange={(event) => {
                setReasonText(event.target.value);
              }}
            />
            {reasonProblem && (
              <p id="reason-error" className="text-destructive">
                {reasonProblem}
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
          <Button type="button" className="min-h-11 sm:min-h-9" disabled={blocked} onClick={save}>
            {busy ? "Saving decision" : "Save decision"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
