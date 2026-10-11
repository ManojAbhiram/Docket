import { FALLBACK_WORDS } from "@/features/applications/readWords";
import type { Box, FieldComparison, FieldKind } from "@/features/applications/types";

import type { ReviewDocument, ReviewField } from "./schemas";

const LABELS: Record<ReviewField["field_name"], string> = {
  name: "Name",
  father_name: "Father's name",
  dob: "Date of birth",
  board: "Board",
  roll_number: "Roll number",
  marks: "Marks",
  document_number: "Document number",
};

const TITLES: Record<NonNullable<ReviewDocument["detected_type"]>, string> = {
  "10th_marksheet": "10th marksheet",
  "12th_marksheet": "12th marksheet",
  id_proof: "ID proof",
  transfer_certificate: "Transfer certificate",
  unknown: "Document not recognised",
};

/** How a field reads on screen. A mismatch outranks everything: it is what the person decides on. */
export function fieldKind(field: ReviewField): FieldKind {
  if (field.review_reason === "not_extracted") {
    return "not_extracted";
  }
  if (field.match_result === "mismatch") {
    return "mismatch";
  }
  if (field.review_reason === "low_confidence" || field.review_reason === "format_invalid") {
    return "low_confidence";
  }
  if (field.match_result === "skipped") {
    return "skipped";
  }
  return "match";
}

export function fieldLabel(field: ReviewField): string {
  const label = LABELS[field.field_name];
  return field.subject ? `${label}: ${field.subject}` : label;
}

export function documentTitle(type: ReviewDocument["detected_type"]): string {
  return type === null ? "Document not read yet" : TITLES[type];
}

function asBox(box: number[] | null): Box | null {
  const [x, y, width, height] = box ?? [];
  if (
    box?.length !== 4 ||
    x === undefined ||
    y === undefined ||
    width === undefined ||
    height === undefined
  ) {
    return null;
  }
  return [x, y, width, height];
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** The application stores a date as 2006-12-10, the marksheets print it day first: 10/12/2006. */
function applicationText(field: ReviewField): string {
  const value = field.application_value ?? "none";
  const parts = field.field_name === "dob" ? ISO_DATE.exec(value) : null;
  return parts ? `${parts[3] ?? ""}/${parts[2] ?? ""}/${parts[1] ?? ""}` : value;
}

/** A field in the shape the comparison views take. */
export function toComparison(field: ReviewField): FieldComparison {
  return {
    id: field.id,
    label: fieldLabel(field),
    applicationValue: applicationText(field),
    documentValue: field.value,
    confidence: field.confidence,
    kind: fieldKind(field),
    box: asBox(field.box),
  };
}

/** Fields that need a look first, then the rest in their original order. */
export function failedFirst(fields: FieldComparison[]): FieldComparison[] {
  return [...fields].sort((a, b) => Number(a.kind === "match") - Number(b.kind === "match"));
}

const FAILURES: Record<string, string> = {
  cap_reached: "The engine's call limit was reached.",
  timeout: "Reading took too long.",
  engine_error: "The engine could not read the page.",
  interrupted: "Reading was interrupted.",
};

/** A failure reason code in plain words. The code itself never reaches the screen. */
export function failureSentence(reason: string | null): string {
  return (reason === null ? undefined : FAILURES[reason]) ?? "Reading failed.";
}

/** What read a document and, if Vision was asked for and not used, why. Empty until it is read. */
export function provenanceWords(
  doc: Pick<ReviewDocument, "status" | "read_engine" | "fallback_reason">,
): string[] {
  if (doc.status !== "read" || doc.read_engine === null) {
    return [];
  }
  const by =
    doc.read_engine === "openrouter"
      ? "Read by OpenRouter Vision. A person must check every field."
      : "Read on this machine.";
  const why = doc.fallback_reason === null ? undefined : FALLBACK_WORDS[doc.fallback_reason];
  return why === undefined ? [by] : [by, why];
}
