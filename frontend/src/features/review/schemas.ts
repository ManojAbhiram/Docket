import { z } from "zod";

const statusSchema = z.enum(["verified", "needs_review", "missing_documents"]);

/** One row of the review queue (api/openapi.yaml: Application). */
export const queueItemSchema = z.object({
  id: z.string(),
  application_ref: z.string(),
  full_name: z.string(),
  status: statusSchema,
  rejected: z.boolean(),
  updated_at: z.string(),
  /** Why it is flagged, in a few words. Null when not flagged. */
  flag_reason: z.string().nullish(),
});
export type QueueItem = z.infer<typeof queueItemSchema>;

export const queuePageSchema = z.object({
  data: z.array(queueItemSchema),
  page: z.object({ next_cursor: z.string().nullable(), has_more: z.boolean() }),
});
export type QueuePage = z.infer<typeof queuePageSchema>;

const reviewFieldSchema = z.object({
  id: z.number(),
  field_name: z.enum([
    "name",
    "father_name",
    "dob",
    "board",
    "roll_number",
    "marks",
    "document_number",
  ]),
  subject: z.string().nullable(),
  value: z.string(),
  application_value: z.string().nullable(),
  confidence: z.number().nullable(),
  box: z.array(z.number()).nullable(),
  match_result: z.enum(["match", "mismatch", "skipped"]).nullable(),
  needs_review: z.boolean(),
  review_reason: z
    .enum(["low_confidence", "format_invalid", "mismatch", "not_extracted"])
    .nullable(),
});
export type ReviewField = z.infer<typeof reviewFieldSchema>;

const reviewDocumentSchema = z.object({
  id: z.string(),
  application_id: z.string(),
  detected_type: z
    .enum(["10th_marksheet", "12th_marksheet", "id_proof", "transfer_certificate", "unknown"])
    .nullable(),
  status: z.enum(["uploaded", "processing", "read", "failed"]),
  failure_reason: z.string().nullable(),
  is_current: z.boolean(),
  created_at: z.string(),
  fields: z.array(reviewFieldSchema),
});
export type ReviewDocument = z.infer<typeof reviewDocumentSchema>;

/** An application with its documents and, per field, the value beside the application's own. */
export const applicationDetailSchema = queueItemSchema.extend({
  father_name: z.string(),
  date_of_birth: z.string(),
  board: z.string(),
  roll_number: z.string(),
  marks: z.record(z.string(), z.number()),
  category: z.string(),
  created_at: z.string(),
  documents: z.array(reviewDocumentSchema),
});
export type ApplicationDetail = z.infer<typeof applicationDetailSchema>;

export const decisionSchema = z.object({
  id: z.string(),
  application_id: z.string(),
  action: z.enum(["approve", "correct", "reject"]),
  reason: z.string().nullable(),
  extracted_field_id: z.number().nullable(),
  decided_by: z.string(),
  created_at: z.string(),
  application_status: statusSchema.nullable(),
});
export type Decision = z.infer<typeof decisionSchema>;

export interface DecisionInput {
  action: "approve" | "correct" | "reject";
  reason?: string;
  extracted_field_id?: number;
  new_value?: string;
}
