import { Notice, type NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";

/** A notice whose one next step does something when a handler is given. */
export function ActionNotice({
  spec,
  onAction,
}: {
  spec: NoticeSpec;
  onAction?: (() => void) | undefined;
}) {
  return (
    <Notice
      tone={spec.tone ?? "error"}
      title={spec.title}
      action={
        spec.action ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-11 sm:min-h-8"
            onClick={onAction}
          >
            {spec.action}
          </Button>
        ) : undefined
      }
    >
      {spec.body}
    </Notice>
  );
}
