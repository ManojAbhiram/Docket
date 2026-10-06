import { z } from "zod";

export const statusSchema = z.enum(["verified", "needs_review", "missing_documents"]);
export type Status = z.infer<typeof statusSchema>;

export const reasonCodeSchema = z.enum([
  "missing_value",
  "bad_date",
  "bad_marks",
  "duplicate_application_ref",
  "too_long",
  "out_of_range",
  "malformed_row",
]);

/** One refused CSV row: its number, its column and a reason code. Never the value. */
export const importRowErrorSchema = z.object({
  row_number: z.number().int(),
  column_name: z.string().nullable(),
  reason_code: reasonCodeSchema,
});

export const importResultSchema = z.object({
  id: z.string(),
  rows_read: z.number().int(),
  rows_created: z.number().int(),
  rows_rejected: z.number().int(),
  errors: z.array(importRowErrorSchema),
});
export type ImportResultBody = z.infer<typeof importResultSchema>;

export const pageSchema = z.object({
  next_cursor: z.string().nullable(),
  has_more: z.boolean(),
});

export const applicationSchema = z.object({
  id: z.string(),
  application_ref: z.string(),
  full_name: z.string(),
  status: statusSchema,
  rejected: z.boolean(),
  updated_at: z.string(),
});
export type ApplicationBody = z.infer<typeof applicationSchema>;

export const applicationListSchema = z.object({
  data: z.array(applicationSchema),
  page: pageSchema,
});

export const documentStatusSchema = z.enum(["uploaded", "processing", "read", "failed"]);

export const documentTypeSchema = z.enum([
  "10th_marksheet",
  "12th_marksheet",
  "id_proof",
  "transfer_certificate",
  "unknown",
]);

export const documentSchema = z.object({
  id: z.string(),
  application_id: z.string(),
  detected_type: documentTypeSchema.nullable(),
  status: documentStatusSchema,
  failure_reason: z.string().nullable(),
  is_current: z.boolean(),
  created_at: z.string(),
});
export type DocumentBody = z.infer<typeof documentSchema>;

export const documentListSchema = z.object({
  data: z.array(documentSchema),
  page: pageSchema,
});
