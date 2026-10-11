import { describe, expect, it } from "vitest";

import { field } from "./fixtures";
import { documentTitle, fieldKind, fieldLabel, provenanceWords, toComparison } from "./mapping";

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

describe("the date of birth", () => {
  it("is shown the way the document prints it, day first, on both sides", () => {
    const dob = field({ field_name: "dob", value: "10/12/2006", application_value: "2006-12-10" });

    expect(toComparison(dob).applicationValue).toBe("10/12/2006");
    expect(toComparison(dob).documentValue).toBe("10/12/2006");
  });

  it("is left as it is when the application value is not a plain date", () => {
    const odd = field({ field_name: "dob", application_value: "unknown" });

    expect(toComparison(odd).applicationValue).toBe("unknown");
  });

  it("does not touch another field that happens to look like a date", () => {
    const roll = field({ field_name: "roll_number", application_value: "2006-12-10" });

    expect(toComparison(roll).applicationValue).toBe("2006-12-10");
  });
});

describe("provenanceWords", () => {
  const read = { status: "read" as const, fallback_reason: null };

  it("says a Vision reading needs a person on every field", () => {
    expect(provenanceWords({ ...read, read_engine: "openrouter" })).toEqual([
      "Read by OpenRouter Vision. A person must check every field.",
    ]);
  });

  it("says a local reading was local", () => {
    expect(provenanceWords({ ...read, read_engine: "rapidocr" })).toEqual([
      "Read on this machine.",
    ]);
  });

  it("explains why Vision was asked for and not used", () => {
    expect(
      provenanceWords({
        ...read,
        read_engine: "rapidocr",
        fallback_reason: "vision_error",
      }),
    ).toEqual([
      "Read on this machine.",
      "Vision could not read the page, so it was read on this machine.",
    ]);
  });

  it("says nothing before a document is read", () => {
    expect(provenanceWords({ ...read, status: "uploaded", read_engine: null })).toEqual([]);
  });
});
