import { useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";

import { useMe } from "@/features/auth/hooks";
import { DecisionDialog } from "@/features/review/components/DecisionDialog";
import { ReviewView } from "@/features/review/components/ReviewView";
import { useApplication } from "@/features/review/hooks";
import { documentTitle, failedFirst, fieldLabel, toComparison } from "@/features/review/mapping";
import { countDecision } from "@/features/review/sitting";
import { ApiError } from "@/lib/api";

/** S-07 and S-08 with their data: one application, its documents, and the verifier's decision. */
export function ComparePage() {
  const { id } = useParams({ strict: false });
  const applicationId = id ?? "";
  const navigate = useNavigate();
  const me = useMe();
  const loaded = useApplication(applicationId);
  const [deciding, setDeciding] = useState(false);

  const application = loaded.data?.application;
  const etag = loaded.data?.etag ?? "";
  const error = loaded.error;
  const missing = error instanceof ApiError && error.status === 404;
  const canDecide =
    me.data?.role === "verifier" && application?.status === "needs_review" && !application.rejected;

  const correctable =
    application?.documents
      .filter((doc) => doc.is_current)
      .flatMap((doc) =>
        failedFirst(doc.fields.map(toComparison)).map((view) => {
          const original = doc.fields.find((field) => field.id === view.id);
          const label = original ? fieldLabel(original) : view.label;
          return {
            id: view.id,
            label: `${label} (${documentTitle(doc.detected_type)})`,
            value: view.documentValue,
          };
        }),
      ) ?? [];

  return (
    <>
      <ReviewView
        application={application}
        loading={loaded.isPending}
        canDecide={canDecide}
        onDecide={() => {
          setDeciding(true);
        }}
        onUpload={
          me.data?.role === "staff"
            ? () => {
                void navigate({ to: "/applications/$id/upload", params: { id: applicationId } });
              }
            : undefined
        }
        {...(error &&
          !application && {
            notice: missing
              ? {
                  title: "That application does not exist.",
                  body: "Go to the review queue.",
                  action: "Go to the review queue",
                }
              : {
                  title: "The application did not load.",
                  body: "Reload to try again.",
                  action: "Reload",
                },
          })}
        onNoticeAction={() => {
          if (missing) {
            void navigate({ to: "/queue" });
          } else {
            void loaded.refetch();
          }
        }}
      />
      {application && (canDecide || deciding) && (
        <DecisionDialog
          applicationId={application.id}
          reference={application.application_ref}
          etag={etag}
          fields={correctable}
          open={deciding}
          onClose={() => {
            setDeciding(false);
          }}
          onSaved={() => {
            countDecision();
            void navigate({ to: "/queue", search: { decided: true } });
          }}
          reload={async () => (await loaded.refetch()).data?.application.status}
        />
      )}
    </>
  );
}
