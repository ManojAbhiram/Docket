import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { ImportView, type ImportResult } from "@/features/intake/components/ImportView";
import { useImport } from "@/features/intake/hooks";
import { importNotice } from "@/features/intake/notices";
import type { ImportResultBody } from "@/features/intake/schemas";

function toResult(body: ImportResultBody): ImportResult {
  return {
    read: body.rows_read,
    created: body.rows_created,
    refused: body.errors.map((e) => ({
      row: e.row_number,
      column: e.column_name,
      reason: e.reason_code,
    })),
  };
}

/** S-03 with its behaviour: choose a CSV, send it once, show what was created and refused. */
export function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const importer = useImport();
  const navigate = useNavigate();

  return (
    <ImportView
      {...(file && { fileName: file.name })}
      busy={importer.isPending}
      {...(importer.isError && { notice: importNotice(importer.error) })}
      {...(importer.data && { result: toResult(importer.data) })}
      onFile={(chosen) => {
        setFile(chosen);
        importer.reset();
      }}
      onImport={() => {
        if (file && !importer.isPending) {
          importer.mutate(file);
        }
      }}
      onViewApplications={() => {
        void navigate({ to: "/applications" });
      }}
    />
  );
}
