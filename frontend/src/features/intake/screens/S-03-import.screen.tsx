import type { ScreenModule } from "@/design/screen";
import { ImportView } from "@/features/intake/components/ImportView";

const FILE = "applications-october.csv";

export const screen: ScreenModule["screen"] = {
  id: "S-03",
  name: "Import applications",
  feature: "intake",
  job: "Loads applications from a CSV and says which rows were refused and why.",
  states: {
    loading: () => <ImportView fileName={FILE} busy />,
    empty: () => <ImportView />,
    "error: payload_too_large": () => (
      <ImportView
        fileName={FILE}
        notice={{
          title: "That file is too large.",
          body: "Split it into smaller files and import each.",
        }}
      />
    ),
    "error: unsupported_media_type": () => (
      <ImportView
        fileName="report.docx"
        notice={{ title: "That is not a CSV file.", body: "Choose a .csv file." }}
      />
    ),
    "error: validation_error": () => (
      <ImportView
        fileName={FILE}
        notice={{
          title: "The file is missing the column roll_number.",
          body: "Add it and import again.",
        }}
      />
    ),
    "error: forbidden": () => (
      <ImportView
        notice={{
          title: "Only staff can import applications.",
          action: "Go to the dashboard",
        }}
      />
    ),
    "error: idempotency_conflict": () => (
      <ImportView
        fileName={FILE}
        notice={{
          title: "This import was already sent with a different file.",
          body: "Choose the file again and import.",
        }}
      />
    ),
    "error: unavailable": () => (
      <ImportView
        fileName={FILE}
        notice={{
          title: "Docket cannot reach its database.",
          body: "Nothing was imported. Try again in a minute.",
        }}
      />
    ),
    success: () => <ImportView fileName={FILE} result={{ read: 20, created: 20, refused: [] }} />,
    partial: () => (
      <ImportView
        fileName={FILE}
        result={{
          read: 20,
          created: 19,
          refused: [{ row: 7, column: "date_of_birth", reason: "bad_date" }],
        }}
      />
    ),
    offline: () => <ImportView fileName={FILE} offline />,
  },
};
