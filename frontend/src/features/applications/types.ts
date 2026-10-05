export type ApplicationStatus = "verified" | "needs_review" | "missing_documents";

export interface ApplicationSummary {
  id: string;
  ref: string;
  name: string;
  status: ApplicationStatus;
  rejected: boolean;
  /** Why it is flagged, shown in the review queue. */
  flag?: string;
  documentsRead: number;
  documentsTotal: number;
  updatedAt: string;
}

export interface DashboardCounts {
  verified: number;
  needsReview: number;
  rejected: number;
  missingDocuments: number;
}

export type FieldKind = "match" | "mismatch" | "low_confidence" | "not_extracted" | "skipped";

/** The box is x, y, width and height in pixels of the stored image. */
export type Box = readonly [number, number, number, number];

export interface FieldComparison {
  id: number;
  label: string;
  applicationValue: string;
  documentValue: string;
  confidence: number | null;
  kind: FieldKind;
  box: Box | null;
}

export type DocumentStatus = "uploaded" | "processing" | "read" | "failed";

export interface UploadedDocument {
  id: string;
  fileName: string;
  status: DocumentStatus;
  /** The type the engine found, in words, once read. */
  detectedType?: string;
  /** Set when the file is refused or the read failed, in the flows' copy. */
  problem?: string;
}
