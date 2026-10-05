import type { ScreenModule } from "@/design/screen";
import { DOCUMENTS, READING_DOCUMENT } from "@/features/applications/fixtures";
import { UploadView } from "@/features/intake/components/UploadView";

// Meera Nair: two of three documents read and one failed, as the applications list and the review
// queue show for the same record.
const REF = "SYN-APP-007";

export const screen: ScreenModule["screen"] = {
  id: "S-05",
  name: "Upload documents",
  feature: "intake",
  job: "Adds scans to one application and shows what the machine read from each.",
  states: {
    loading: () => <UploadView reference={REF} documents={[]} loading />,
    empty: () => <UploadView reference={REF} documents={[]} />,
    "error: payload_too_large": () => (
      <UploadView
        reference={REF}
        documents={[
          {
            id: "d-9",
            fileName: "scan-4.jpg",
            status: "failed",
            problem: "scan-4.jpg is over 8 MiB. Choose a smaller scan or photo.",
          },
        ]}
      />
    ),
    "error: unsupported_media_type": () => (
      <UploadView
        reference={REF}
        documents={[
          {
            id: "d-9",
            fileName: "report.docx",
            status: "failed",
            problem: "report.docx is not a JPG, PNG or PDF. Choose one of those.",
          },
        ]}
      />
    ),
    "error: validation_error": () => (
      <UploadView
        reference={REF}
        documents={[
          {
            id: "d-9",
            fileName: "panorama.png",
            status: "failed",
            problem: "panorama.png is too large in pixels. Reduce its size and upload it again.",
          },
        ]}
      />
    ),
    "error: not_found": () => (
      <UploadView
        reference={REF}
        documents={[]}
        readOnly
        notice={{
          title: "That application does not exist.",
          body: "Go to Applications.",
          action: "Go to Applications",
        }}
      />
    ),
    "error: forbidden": () => (
      <UploadView
        reference={REF}
        documents={DOCUMENTS}
        readOnly
        notice={{ title: "Only staff can upload documents." }}
      />
    ),
    "error: unauthorized": () => (
      <UploadView
        reference={REF}
        documents={[]}
        notice={{
          tone: "info",
          title: "You were signed out.",
          body: "Sign in, then choose the files again.",
          action: "Sign in",
        }}
      />
    ),
    "error: failed read": () => (
      <UploadView reference={REF} documents={DOCUMENTS.filter((d) => d.status === "failed")} />
    ),
    success: () => (
      <UploadView
        reference={REF}
        documents={[
          {
            id: "d-1",
            fileName: "marksheet-10th.jpg",
            status: "read",
            detectedType: "10th marksheet",
          },
          {
            id: "d-2",
            fileName: "marksheet-12th.png",
            status: "read",
            detectedType: "12th marksheet",
          },
          { id: "d-3", fileName: "id-card.pdf", status: "read", detectedType: "ID proof" },
        ]}
      />
    ),
    partial: () => <UploadView reference={REF} documents={[...DOCUMENTS, READING_DOCUMENT]} />,
    offline: () => <UploadView reference={REF} documents={DOCUMENTS} offline />,
    duplicate: () => (
      <UploadView
        reference={REF}
        documents={DOCUMENTS}
        notice={{
          tone: "info",
          title: "marksheet-10th.jpg is already uploaded.",
          body: "Nothing changed.",
        }}
      />
    ),
  },
};
