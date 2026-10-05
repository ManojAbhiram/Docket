# Admissions Document Verification (Education Document OCR and Student Record Matching)

Owner: Manoj Abhiram
Category: AI deep dive
Vertical: Universities / Admissions / Schools

## 1. Summary

Build an admissions document verification tool. Staff import student applications and upload scanned documents. A vision model classifies each document and extracts its fields. The system compares the extracted fields with the application record and flags mismatches for a human verifier. Applications that match fully are auto-marked Verified with the extracted evidence stored.

Use case: a university admissions office verifies 5,000 applications in July. Verifiers work only the flagged queue (about 12%); the rest are auto-verified.

## 2. AI depth

- Vision extraction (one call per document: classify and extract fields as JSON)
- Fuzzy matching (names)
- Extraction evals (field-level accuracy, model comparison)

## 3. Runtime and budget constraints

- Postgres in Docker.
- Local PDF rasterising (pdf2image).
- Nothing else.

## 4. Roles

| Role | Can do |
|------|--------|
| Admissions staff | Import applications from CSV, upload documents, view dashboard, export verified list |
| Verifier | Work the flagged queue: approve, correct or reject with a reason |

## 5. Functional requirements

### 5.1 Application import

- Staff import applications from CSV.
- Columns: application id, name, father's name, date of birth, board, roll number, marks by subject, category.

### 5.2 Document upload

- Staff upload scanned documents per application.
- Accepted formats: JPG, PNG, PDF.
- For PDF, the first page is rasterised locally (pdf2image).
- Phone photos are included (noisy, skewed, shadowed inputs must be handled).

### 5.3 Classification and extraction

- One vision call per document.
- The call classifies the document type (10th marksheet, 12th marksheet, ID proof) and extracts its fields as JSON.
- Every low-confidence field is routed to Needs review. Do not chase accuracy on noisy photos.

### 5.4 Matching

Each extracted field is compared with the application value:

| Field type | Rule |
|------------|------|
| Names | Fuzzy: token-sorted similarity with a threshold |
| Dates | Exact |
| Roll numbers | Exact |
| Marks | Exact |

### 5.5 Application status

Each application gets one of:

- Verified
- Needs review
- Missing documents

Rules:

- Nothing is marked Verified without either all fields matching or a verifier decision.
- Every decision is logged.

### 5.6 Per-field view

For each application, show the document beside the application value, field by field.

### 5.7 Verifier decisions

A verifier can approve, correct, or reject. Reject requires a reason. Every decision is logged (who, when, what, reason).

### 5.8 Dashboard and export

- Dashboard of counts by status.
- Export the verified list to CSV.

## 6. LLM gateway

- All model calls go through one gateway function on OpenRouter.
- Model: claude-haiku-4-5.
- max_tokens capped at 600.
- The gateway logs tokens and cost per call.
- The gateway refuses calls once the running total passes USD 8 (hard cap, leaving headroom under the USD 10 key limit).
- Tests replay recorded responses, so CI makes no live calls.

## 7. Evals

- Field-level extraction accuracy on 30 labelled synthetic documents.
- A 10-document comparison against a stronger model.
- Use `brg_llm_eval` to measure field-level extraction accuracy.

## 8. Seed data

- Seed 20 applications and 30 synthetic documents.
- Claude Code renders the documents from HTML to PNG with photo noise (blur, skew, shadow).
- Some documents are deliberately mismatched with their application.
- Never use real student documents, in the hackathon or anywhere else.

## 9. Privacy

- `brg_privacy` is mandatory (minors' data, category certificates).
- Synthetic data only for development, tests and demos.

## 10. Patterns

- `brg_patterns` has an uploads pattern worth loading for the upload flow.

## 11. Risks and fallbacks

| Risk | Fallback |
|------|----------|
| Haiku misreads noisy phone photos of marksheets | Lower the noise level in the synthetic set, and route every low-confidence field to Needs review instead of chasing accuracy |
| Vision spend exceeds the USD 10 key cap | Gateway hard stop at USD 8 running total; tests use recorded responses |

## 12. Out of scope

- DigiLocker
- Fee payment
- Transfer certificates and category certificates
- Bulk upload over 100 files

## 13. Stretch

- Transfer certificate document type.
- Field crops.

## 14. Acceptance criteria

1. CSV import creates applications with all listed columns; malformed rows are rejected with a visible reason.
2. JPG, PNG and PDF uploads are accepted; a PDF is rasterised locally to its first page.
3. Each uploaded document triggers exactly one gateway call and yields a document type plus fields as JSON.
4. Name comparison uses token-sorted similarity with a configured threshold; dates, roll numbers and marks use exact comparison.
5. Each application shows one of Verified, Needs review, Missing documents.
6. No application is Verified unless all fields match or a verifier decision exists.
7. A verifier can approve, correct or reject (reason required), and each decision appears in the decision log.
8. The per-field view shows the document beside the application value.
9. The dashboard shows counts by status; the verified list exports to CSV.
10. The gateway logs tokens and cost per call, caps max_tokens at 600, and refuses calls once the running total passes USD 8.
11. The test suite makes no live model calls (recorded responses only).
12. Eval report gives field-level accuracy on the 30 labelled synthetic documents and the 10-document stronger-model comparison.
13. Seed produces 20 applications and 30 synthetic documents, including deliberate mismatches, with no real student data.

## 15. Notes

- Good upsell later: DigiLocker and board-result verification.
