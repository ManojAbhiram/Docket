import { CircleAlert, Info } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface NoticeProps {
  tone?: "error" | "info";
  title: string;
  children?: ReactNode;
  /** The next step as a control, when there is one on this screen. */
  action?: ReactNode;
}

/**
 * A message that says what happened and what to do. An error is announced to assistive tech. It
 * carries a 4 px bar in the tone's colour and fades in; it never travels, so a notice that appears
 * during a fast review does not pull the eye.
 */
export function Notice({ tone = "error", title, children, action }: NoticeProps) {
  const Icon = tone === "error" ? CircleAlert : Info;
  return (
    <Alert
      variant={tone === "error" ? "destructive" : "default"}
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "enter-quiet border-l-4",
        tone === "error" ? "border-l-destructive" : "border-l-primary",
      )}
    >
      <Icon aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      {children && <AlertDescription>{children}</AlertDescription>}
      {action && <div className="col-start-2 pt-2">{action}</div>}
    </Alert>
  );
}

/** A notice as data, so a screen state can name its copy and its one next step. */
export interface NoticeSpec {
  tone?: "error" | "info";
  title: string;
  body?: string;
  /** The label of the control that takes the next step, for example "Reload". */
  action?: string;
}

export function NoticeBox({ spec }: { spec: NoticeSpec }) {
  return (
    <Notice
      tone={spec.tone ?? "error"}
      title={spec.title}
      action={
        spec.action ? (
          <Button type="button" variant="outline" size="sm" className="min-h-11 sm:min-h-8">
            {spec.action}
          </Button>
        ) : undefined
      }
    >
      {spec.body}
    </Notice>
  );
}
