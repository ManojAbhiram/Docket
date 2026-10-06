import { useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";

import type { NoticeSpec } from "@/components/Notice";
import type { UploadedDocument } from "@/features/applications/types";
import { UploadView } from "@/features/intake/components/UploadView";
import { useApplicationRef, useBatchUpload, useDocuments } from "@/features/intake/hooks";
import type { DocumentBody } from "@/features/intake/schemas";
import { ApiError } from "@/lib/api";

const MAX_BATCH = 100;

const TYPE_WORDS: Record<string, string> = {
  "10th_marksheet": "10th marksheet",
  "12th_marksheet": "12th marksheet",
  id_proof: "ID proof",
  transfer_certificate: "Transfer certificate",
  unknown: "Not recognised",
};

const FAILURE_WORDS: Record<string, string> = {
  timeout: "Reading took too long.",
  cap_reached: "The reading limit was reached.",
  engine_error: "The engine could not read the page.",
};

function shown(document: DocumentBody, position: number): UploadedDocument {
  const detected = document.detected_type ? TYPE_WORDS[document.detected_type] : undefined;
  const reason = document.failure_reason;
  return {
    id: document.id,
    fileName: `Document ${String(position + 1)}`,
    status: document.status,
    ...(detected && { detectedType: detected }),
    ...(document.status === "failed" && {
      problem: `${(reason && FAILURE_WORDS[reason]) ?? "Reading failed."} Upload the file again.`,
    }),
  };
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** S-05 with its behaviour: send scans one by one, then watch each one get read. */
export function UploadPage() {
  const { id } = useParams({ strict: false });
  const applicationId = id ?? "";
  const navigate = useNavigate();
  const application = useApplicationRef(applicationId);
  const documents = useDocuments(applicationId);
  const upload = useBatchUpload(applicationId);
  const [tooMany, setTooMany] = useState(false);

  const missing = isNotFound(application.error) || isNotFound(documents.error);
  let notice: NoticeSpec | undefined;
  if (missing) {
    notice = {
      title: "That application does not exist.",
      body: "Go to Applications.",
      action: "Go to Applications",
    };
  } else if (tooMany) {
    notice = {
      tone: "info",
      title: `Choose up to ${String(MAX_BATCH)} files at a time.`,
      body: "Upload the rest in another batch.",
    };
  } else if (application.isError || documents.isError) {
    notice = {
      title: "The documents did not load.",
      body: "Reload to try again.",
      action: "Reload",
    };
  }

  const known = new Set(documents.data?.data.map((d) => d.id));
  return (
    <UploadView
      reference={application.data?.application_ref ?? "this application"}
      documents={documents.data?.data.map(shown) ?? []}
      loading={documents.isPending && !missing}
      readOnly={missing}
      batch={upload.items}
      {...(notice && { notice })}
      onFiles={(files) => {
        setTooMany(files.length > MAX_BATCH);
        if (files.length <= MAX_BATCH) {
          void upload.start(files, known);
        }
      }}
      onNoticeAction={() => {
        if (missing) {
          void navigate({ to: "/applications" });
        } else {
          void application.refetch();
          void documents.refetch();
        }
      }}
    />
  );
}
