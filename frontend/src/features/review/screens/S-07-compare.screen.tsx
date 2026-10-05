import type { ScreenModule } from "@/design/screen";
import { FIELDS } from "@/features/applications/fixtures";
import { CompareView } from "@/features/review/components/CompareView";

const REF = "SYN-APP-004";
const NAME = "Latha Sharma";

export const screen: ScreenModule["screen"] = {
  id: "S-07",
  name: "Compare application",
  feature: "review",
  job: "Shows each document field beside the application value, with the OCR box and a confidence badge.",
  states: {
    loading: () => (
      <CompareView reference={REF} name={NAME} status="needs_review" fields={[]} loading />
    ),
    empty: () => <CompareView reference={REF} name={NAME} status="missing_documents" fields={[]} />,
    "error: not_found": () => (
      <CompareView
        reference="Application not found"
        name=""
        status="needs_review"
        fields={[]}
        notice={{
          title: "That application does not exist.",
          body: "Go to the review queue.",
          action: "Go to the review queue",
        }}
      />
    ),
    "error: internal": () => (
      <CompareView
        reference={REF}
        name={NAME}
        status="needs_review"
        fields={[]}
        notice={{
          title: "The application did not load.",
          body: "Reload, or quote request 2e8a41d0 to the engineering team.",
          action: "Reload",
        }}
      />
    ),
    "error: image failed": () => (
      <CompareView reference={REF} name={NAME} status="needs_review" fields={FIELDS} imageFailed />
    ),
    success: () => (
      <CompareView reference={REF} name={NAME} status="needs_review" fields={FIELDS} />
    ),
    partial: () => (
      <CompareView
        reference={REF}
        name={NAME}
        status="needs_review"
        fields={FIELDS}
        partialNote="2 of 3 documents read. The 12th marksheet failed: upload a clearer photo."
      />
    ),
    "low confidence": () => (
      <CompareView
        reference={REF}
        name={NAME}
        status="needs_review"
        fields={FIELDS}
        initialSelected={4}
      />
    ),
    "no box": () => (
      <CompareView
        reference={REF}
        name={NAME}
        status="needs_review"
        fields={FIELDS}
        initialSelected={7}
      />
    ),
    stale: () => (
      <CompareView
        reference={REF}
        name={NAME}
        status="needs_review"
        fields={FIELDS}
        notice={{
          tone: "info",
          title: "This application changed.",
          body: "Reload fields.",
          action: "Reload",
        }}
      />
    ),
    offline: () => (
      <CompareView reference={REF} name={NAME} status="needs_review" fields={FIELDS} offline />
    ),
  },
};
