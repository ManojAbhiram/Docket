import { describe, expect, it } from "vitest";

import { field } from "./fixtures";
import { documentTitle, fieldKind, fieldLabel, toComparison } from "./mapping";

describe("fieldKind", () => {
  it("is a mismatch whenever the comparison said so", () => {
    expect(fieldKind(field({ match_result: "mismatch", review_reason: "mismatch" }))).toBe(
      "mismatch",
    );
  });

  it("keeps a mismatch even when the engine was also unsure", () => {
    expect(fieldKind(field({ match_result: "mismatch", review_reason: "low_confidence" }))).toBe(
      "mismatch",
    );
  });

  it("says not found for a field the engine did not read", () => {
    const missing = field({ value: "", match_result: "mismatch", review_reason: "not_extracted" });

    expect(fieldKind(missing)).toBe("not_extracted");
  });

  it("treats low confidence and a bad format as a value to check", () => {
    expect(fieldKind(field({ review_reason: "low_confidence", needs_review: true }))).toBe(
      "low_confidence",
    );
    expect(fieldKind(field({ review_reason: "format_invalid", needs_review: true }))).toBe(
      "low_confidence",
    );
  });

  it("is skipped when the field has nothing to compare with", () => {
    expect(fieldKind(field({ match_result: "skipped", application_value: null }))).toBe("skipped");
  });

  it("is a match otherwise, also before any comparison ran", () => {
    expect(fieldKind(field())).toBe("match");
    expect(fieldKind(field({ match_result: null }))).toBe("match");
  });
});

describe("fieldLabel and documentTitle", () => {
  it("names a field in plain words and a mark by its subject", () => {
    expect(fieldLabel(field({ field_name: "dob" }))).toBe("Date of birth");
    expect(fieldLabel(field({ field_name: "roll_number" }))).toBe("Roll number");
    expect(fieldLabel(field({ field_name: "marks", subject: "Mathematics" }))).toBe(
      "Marks: Mathematics",
    );
  });

  it("names a document by its type, or says it was not recognised", () => {
    expect(documentTitle("12th_marksheet")).toBe("12th marksheet");
    expect(documentTitle("id_proof")).toBe("ID proof");
    expect(documentTitle("unknown")).toBe("Document not recognised");
    expect(documentTitle(null)).toBe("Document not read yet");
  });
});

describe("toComparison", () => {
  it("lays a field out as the screens show it", () => {
    const view = toComparison(
      field({ id: 5, value: "X", application_value: null, confidence: null, box: null }),
    );

    expect(view).toMatchObject({
      id: 5,
      label: "Name",
      documentValue: "X",
      applicationValue: "none",
      confidence: null,
      box: null,
    });
  });

  it("passes a box through as four numbers", () => {
    expect(toComparison(field({ box: [1, 2, 3, 4] })).box).toEqual([1, 2, 3, 4]);
  });

  it("drops a box that is not four numbers", () => {
    expect(toComparison(field({ box: [1, 2] })).box).toBeNull();
  });
});
