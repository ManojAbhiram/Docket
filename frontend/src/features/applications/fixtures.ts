import type {
  ApplicationSummary,
  DashboardCounts,
  FieldComparison,
  UploadedDocument,
} from "./types";

/** Times are shown in the office's zone, whatever the viewer's machine says. */
const formatter = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Kolkata",
});

export function formatTime(iso: string): string {
  return formatter.format(new Date(iso));
}

export const COUNTS: DashboardCounts = {
  verified: 3812,
  needsReview: 611,
  rejected: 37,
  missingDocuments: 577,
};

export function totalApplications(counts: DashboardCounts): number {
  return counts.verified + counts.needsReview + counts.missingDocuments;
}

export const APPLICATIONS: ApplicationSummary[] = [
  {
    id: "a-004",
    ref: "SYN-APP-004",
    name: "Latha Sharma",
    status: "needs_review",
    rejected: false,
    flag: "Name does not match",
    documentsRead: 3,
    documentsTotal: 3,
    updatedAt: "2026-10-05T04:12:41Z",
  },
  {
    id: "a-011",
    ref: "SYN-APP-011",
    name: "Ravi Menon",
    status: "needs_review",
    rejected: false,
    flag: "Low confidence on roll number",
    documentsRead: 2,
    documentsTotal: 3,
    updatedAt: "2026-10-05T04:30:02Z",
  },
  {
    id: "a-007",
    ref: "SYN-APP-007",
    name: "Meera Nair",
    status: "needs_review",
    rejected: false,
    flag: "A document could not be read",
    documentsRead: 2,
    documentsTotal: 3,
    updatedAt: "2026-10-05T05:02:10Z",
  },
  {
    id: "a-002",
    ref: "SYN-APP-002",
    name: "Arjun Rao",
    status: "verified",
    rejected: false,
    documentsRead: 3,
    documentsTotal: 3,
    updatedAt: "2026-10-05T03:48:00Z",
  },
  {
    id: "a-015",
    ref: "SYN-APP-015",
    name: "Farah Khan",
    status: "missing_documents",
    rejected: false,
    documentsRead: 1,
    documentsTotal: 3,
    updatedAt: "2026-10-04T11:20:00Z",
  },
  {
    id: "a-009",
    ref: "SYN-APP-009",
    name: "Dev Gupta",
    status: "needs_review",
    rejected: true,
    documentsRead: 3,
    documentsTotal: 3,
    updatedAt: "2026-10-04T09:05:00Z",
  },
];

export const QUEUE = APPLICATIONS.filter((a) => a.status === "needs_review" && !a.rejected);

/** The stored page image is 720 by 440 pixels; every box below is in those pixels. */
export const PAGE_SIZE = { width: 720, height: 440 } as const;

export const FIELDS: FieldComparison[] = [
  {
    id: 1,
    label: "Name",
    applicationValue: "Latha Sharma",
    documentValue: "Latha Sharmaa",
    confidence: 0.9712,
    kind: "mismatch",
    box: [220, 62, 150, 22],
  },
  {
    id: 2,
    label: "Father's name",
    applicationValue: "Salim Sharma",
    documentValue: "Salim Sharma",
    confidence: 0.9921,
    kind: "match",
    box: [220, 100, 140, 22],
  },
  {
    id: 3,
    label: "Date of birth",
    applicationValue: "10 Dec 2006",
    documentValue: "10/12/2006",
    confidence: 0.9954,
    kind: "match",
    box: [220, 138, 110, 22],
  },
  {
    id: 4,
    label: "Roll number",
    applicationValue: "SYN0945957",
    documentValue: "SYN0945951",
    confidence: 0.9533,
    kind: "low_confidence",
    box: [220, 176, 120, 22],
  },
  {
    id: 5,
    label: "Board",
    applicationValue: "CBSE",
    documentValue: "CBSE",
    confidence: 0.9988,
    kind: "match",
    box: [220, 214, 50, 22],
  },
  {
    id: 6,
    label: "Marks: English",
    applicationValue: "59",
    documentValue: "59",
    confidence: 0.9971,
    kind: "match",
    box: [330, 290, 30, 22],
  },
  {
    id: 7,
    label: "Marks: Mathematics",
    applicationValue: "87",
    documentValue: "",
    confidence: null,
    kind: "not_extracted",
    box: null,
  },
];

export const DOCUMENTS: UploadedDocument[] = [
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
  {
    id: "d-3",
    fileName: "id-card.pdf",
    status: "failed",
    problem: "Docket could not read id-card.pdf. Reprocess it, or upload a clearer photo.",
  },
];

/** A retake of the failed ID card, still being read: with DOCUMENTS it makes a partial list. */
export const READING_DOCUMENT: UploadedDocument = {
  id: "d-4",
  fileName: "id-card-retake.jpg",
  status: "processing",
};
