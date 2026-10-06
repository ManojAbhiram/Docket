import type { ApplicationDetail, QueueItem, ReviewField } from "./schemas";

export const APPLICATION_ID = "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b";
export const DOCUMENT_ID = "0192b1c3-1a2b-7c4e-9a1b-2c3d4e5f6a7c";

export function field(overrides: Partial<ReviewField> = {}): ReviewField {
  return {
    id: 1,
    field_name: "name",
    subject: null,
    value: "Latha Sharma",
    application_value: "Latha Sharma",
    confidence: 0.99,
    box: [220, 60, 120, 22],
    match_result: "match",
    needs_review: false,
    review_reason: null,
    ...overrides,
  };
}

export function queueItem(overrides: Partial<QueueItem> = {}): QueueItem {
  return {
    id: APPLICATION_ID,
    application_ref: "SYN-APP-004",
    full_name: "Latha Sharma",
    status: "needs_review",
    rejected: false,
    updated_at: "2026-10-05T09:12:41Z",
    ...overrides,
  };
}

/** A flagged application with a mismatching name and a low-confidence board. */
export function detail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
  return {
    ...queueItem(),
    father_name: "Salim Sharma",
    date_of_birth: "2006-12-10",
    board: "CBSE",
    roll_number: "SYN0945957",
    marks: { English: 59 },
    category: "General",
    created_at: "2026-10-05T09:00:00Z",
    documents: [
      {
        id: DOCUMENT_ID,
        application_id: APPLICATION_ID,
        detected_type: "10th_marksheet",
        status: "read",
        failure_reason: null,
        is_current: true,
        created_at: "2026-10-05T09:05:00Z",
        fields: [
          field({
            id: 11,
            value: "Latha Sharmaa",
            match_result: "mismatch",
            needs_review: true,
            review_reason: "mismatch",
          }),
          field({
            id: 12,
            field_name: "board",
            value: "CBSE",
            application_value: "CBSE",
            confidence: 0.91,
            needs_review: true,
            review_reason: "low_confidence",
            box: [220, 180, 40, 22],
          }),
          field({
            id: 13,
            field_name: "roll_number",
            value: "SYN0945957",
            application_value: "SYN0945957",
            box: null,
          }),
        ],
      },
    ],
    ...overrides,
  };
}
