import { Notice, NoticeBox, type NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";

interface ActionNoticeProps {
  spec: NoticeSpec;
  /** Runs when the notice's one action is pressed. Without it the gallery's inert notice is shown. */
  onAction?: (() => void) | undefined;
}

/** A notice whose action does something: reload the data, or go back to the queue. */
export function ActionNotice({ spec, onAction }: ActionNoticeProps) {
  if (!onAction || !spec.action) {
    return <NoticeBox spec={spec} />;
  }
  return (
    <Notice
      tone={spec.tone ?? "error"}
      title={spec.title}
      action={
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-h-11 sm:min-h-8"
          onClick={onAction}
        >
          {spec.action}
        </Button>
      }
    >
      {spec.body}
    </Notice>
  );
}
