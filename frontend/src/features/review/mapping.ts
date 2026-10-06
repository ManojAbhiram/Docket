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

/** A field in the shape the comparison views take. */
export function toComparison(field: ReviewField): FieldComparison {
  return {
    id: field.id,
    label: fieldLabel(field),
    applicationValue: field.application_value ?? "none",
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
