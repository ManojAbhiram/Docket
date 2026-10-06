import { useRef, useState } from "react";
import { toast } from "sonner";

import type { NoticeSpec } from "@/components/Notice";
import {
  DecisionDialogView,
  type CorrectableField,
  type DecisionDraft,
} from "@/features/review/components/DecisionDialogView";
import { decisionNotice } from "@/features/review/decisionNotice";
import { useDecide } from "@/features/review/hooks";
import type { DecisionInput } from "@/features/review/schemas";
import { ApiError } from "@/lib/api";

interface DecisionDialogProps {
  applicationId: string;
  reference: string;
  /** The version of the application the verifier is looking at. */
  etag: string;
  fields: CorrectableField[];
  open: boolean;
  onClose: () => void;
  /** Reload the application and say what status it has now. */
  reload: () => Promise<string | undefined>;
}

function inputFrom(draft: DecisionDraft): DecisionInput {
  if (draft.action === "correct" && draft.fieldId !== undefined) {
    return {
      action: "correct",
      extracted_field_id: draft.fieldId,
      new_value: draft.newValue,
    };
  }
  if (draft.action === "reject") {
    return { action: "reject", reason: draft.reason };
  }
  return { action: "approve" };
}

/** S-08 with its behaviour: send the decision with the version that was seen, then say what happened. */
export function DecisionDialog({
  applicationId,
  reference,
  etag,
  fields,
  open,
  onClose,
  reload,
}: DecisionDialogProps) {
  const decide = useDecide(applicationId);
  const sending = useRef(false);
  const [notice, setNotice] = useState<NoticeSpec | undefined>();

  const save = (draft: DecisionDraft) => {
    if (sending.current) {
      return;
    }
    sending.current = true;
    setNotice(undefined);
    decide.mutate(
      { input: inputFrom(draft), etag },
      {
        onSuccess: () => {
          toast.success("Decision saved");
          onClose();
        },
        onError: (error) => {
          void (async () => {
            const stale = error instanceof ApiError && error.status === 409;
            const status = stale ? await reload() : undefined;
            setNotice(decisionNotice(error, status));
          })();
        },
        onSettled: () => {
          sending.current = false;
        },
      },
    );
  };

  return (
    <DecisionDialogView
      reference={reference}
      fieldLabel=""
      fields={fields}
      busy={decide.isPending}
      open={open}
      returnFocusTo="decide-button"
      onClose={() => {
        setNotice(undefined);
        onClose();
      }}
      onSave={save}
      {...(notice && { notice })}
    />
  );
}
