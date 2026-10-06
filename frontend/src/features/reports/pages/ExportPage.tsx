import { useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";

import type { VerifiedFile } from "../api";
import { ExportView } from "../components/ExportView";
import { useDashboard, useVerifiedExport } from "../hooks";
import { exportNotice } from "../notices";

const number = new Intl.NumberFormat("en-IN");

/** Hands the file to the browser through an object URL, and lets the URL go afterwards. */
function save(file: VerifiedFile): void {
  const url = URL.createObjectURL(file.blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.fileName;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 0);
}

/** The export: how many rows there are, and one button that downloads them. */
export function ExportPage() {
  const navigate = useNavigate();
  const counts = useDashboard();
  const exporter = useVerifiedExport();
  const [done, setDone] = useState<string>();
  const [foundEmpty, setFoundEmpty] = useState(false);
  const running = useRef(false);

  function download() {
    if (running.current) {
      return;
    }
    running.current = true;
    setDone(undefined);
    exporter.mutate(undefined, {
      onSuccess: (file) => {
        if (file.rows === 0) {
          setFoundEmpty(true);
          return;
        }
        setFoundEmpty(false);
        save(file);
        setDone(`Downloaded ${file.fileName} with ${number.format(file.rows)} rows.`);
      },
      onSettled: () => {
        running.current = false;
      },
    });
  }

  const known = counts.data?.verified;
  const verifiedCount = foundEmpty
    ? 0
    : counts.isPending
      ? null
      : counts.isError
        ? undefined
        : known;
  const notice = exporter.isError ? exportNotice(exporter.error) : undefined;

  return (
    <ExportView
      verifiedCount={verifiedCount}
      busy={exporter.isPending}
      {...(notice && { notice })}
      {...(done && { done })}
      onDownload={download}
      onAction={download}
      onNavigate={(to) => {
        void navigate({ to });
      }}
    />
  );
}
