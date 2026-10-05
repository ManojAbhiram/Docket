# PRD: Docket (admissions document verification)

Source: spec.md (157 lines) and CONSTRAINTS.md (78 lines), both cited in place   Normalised: 2026-10-04
Owner: Manoj Abhiram (spec.md:L3)   Tracker epic: unconfirmed (BEARING_TRACKER=none)

Reading rule: CONSTRAINTS.md overrides spec.md where they disagree (CONSTRAINTS.md:L3). Where a statement below took the CONSTRAINTS.md wording, both sources are cited and the change is listed in docs/spec-changes.md.

## 1. Problem

inferred: Admissions staff would otherwise check scanned marksheets and ID proofs against each student record by hand at volume (spec.md:L9-L11 describe verifiers working only a flagged queue while the rest are auto-verified). The input states no problem section; see Could not extract.

## 2. Business objectives

| Id | Objective | Target (measurable) | Source |
| --- | --- | --- | --- |
| B1 | Verifiers work only the flagged applications; the rest are verified without hand checking | target: unconfirmed (spec.md:L11 says "say 12%" flagged of 5,000 applications, as an example) | spec.md:L11 |
| B2 | Every Verified application carries the extracted evidence and every verifier decision is logged | target: unconfirmed | spec.md:L9, spec.md:L74 |
| B3 | Extraction quality is measured per field before an engine is chosen | target: unconfirmed (no accuracy bar is given) | CONSTRAINTS.md:L41-L51 |

## 3. Non-goals

- DigiLocker (spec.md:L129).
- Fee payment (spec.md:L130).
- Transfer and category certificates (spec.md:L131); see Q-007 for the stretch item that touches this.
- Bulk upload over 100 files (spec.md:L132); see Q-008.
- Any paid API, paid hosting or account that needs a credit card (CONSTRAINTS.md:L7-L15).

## 4. Personas

| Persona | Group | Who they are | What they need | Source |
| --- | --- | --- | --- | --- |
| Admissions staff | 00 end user | Staff of the admissions office | Import applications, upload documents, see counts, export the verified list | spec.md:L29 |
| Verifier | 00 end user | Person who decides flagged applications | Work the flagged queue and approve, correct or reject with a reason | spec.md:L30 |
| Engineering team | 02 operator | inferred: the people who run evals, seeding and the gateway | Measure engines, seed synthetic data, keep CI free of live calls | spec.md:L100, CONSTRAINTS.md:L39 |

## 5. Requirement statements

One testable statement per id. Ids are never reused or renumbered.

| Id | Statement | Persona | Source | Flags |
| --- | --- | --- | --- | --- |
| REQ-001 | The system lets staff import student applications from a CSV file. | Admissions staff | spec.md:L36 | none |
| REQ-002 | The CSV import reads application id, name, father's name, date of birth, board, roll number, marks by subject and category. | Admissions staff | spec.md:L37 | none |
| REQ-003 | The system rejects a malformed CSV row and shows the reason for the rejection. | Admissions staff | spec.md:L141 | none |
| REQ-004 | The system lets staff upload scanned documents against an application. | Admissions staff | spec.md:L41 | none |
| REQ-005 | The system accepts uploads in JPG, PNG and PDF formats. | Admissions staff | spec.md:L42 | none |
| REQ-006 | The system rasterises the first page of an uploaded PDF locally. | Admissions staff | spec.md:L43 | none |
| REQ-007 | The system processes phone photos that are noisy, skewed or shadowed. | Admissions staff | spec.md:L44 | ambiguous: Q-001 |
| REQ-008 | The system makes exactly one gateway call per uploaded document. | Admissions staff | spec.md:L48, spec.md:L143, CONSTRAINTS.md:L66 | none |
| REQ-009 | The gateway call classifies each document as a 10th marksheet, a 12th marksheet or an ID proof. | Admissions staff | spec.md:L49 | none |
| REQ-010 | The gateway call returns the document's extracted fields as JSON, each with a confidence. | Admissions staff | spec.md:L49, CONSTRAINTS.md:L35 | none |
| REQ-011 | The system routes every low-confidence extracted field to Needs review. | Verifier | spec.md:L50, spec.md:L124 | ambiguous: Q-002 |
| REQ-012 | The system compares each extracted field with the corresponding application value. | Verifier | spec.md:L54 | none |
| REQ-013 | The system compares names by token-sorted similarity against a configured threshold. | Verifier | spec.md:L58, spec.md:L144 | ambiguous: Q-003 |
| REQ-014 | The system compares dates for exact match. | Verifier | spec.md:L59 | none |
| REQ-015 | The system compares roll numbers for exact match. | Verifier | spec.md:L60 | none |
| REQ-016 | The system compares marks for exact match. | Verifier | spec.md:L61 | none |
| REQ-017 | The system gives each application exactly one status: Verified, Needs review or Missing documents. | Admissions staff | spec.md:L65-L69, spec.md:L145 | ambiguous: Q-004 |
| REQ-018 | The system marks an application Verified automatically when all its fields match and stores the extracted evidence. | Admissions staff | spec.md:L9, spec.md:L11 | none |
| REQ-019 | The system does not mark an application Verified unless all its fields match or a verifier has decided. | Verifier | spec.md:L73, spec.md:L146 | none |
| REQ-020 | The system flags an application with a field mismatch for a verifier. | Verifier | spec.md:L9 | none |
| REQ-021 | The system lists the flagged applications to a verifier. | Verifier | spec.md:L11, spec.md:L30 | none |
| REQ-022 | The system shows, for each application, the document beside the application value, field by field. | Verifier | spec.md:L78, spec.md:L148 | none |
| REQ-023 | The system lets a verifier approve an application. | Verifier | spec.md:L82 | none |
| REQ-024 | The system lets a verifier correct an application. | Verifier | spec.md:L82 | ambiguous: Q-005 |
| REQ-025 | The system lets a verifier reject an application. | Verifier | spec.md:L82 | none |
| REQ-026 | The system requires a reason before it accepts a rejection. | Verifier | spec.md:L82 | none |
| REQ-027 | The system logs every decision with who made it, when, what was decided and the reason. | Verifier | spec.md:L74, spec.md:L82, spec.md:L147 | none |
| REQ-028 | The dashboard shows the count of applications by status. | Admissions staff | spec.md:L86 | none |
| REQ-029 | The system exports the verified list to CSV. | Admissions staff | spec.md:L87 | none |
| REQ-030 | The system routes all OCR and vision work through one gateway function. | Engineering team | CONSTRAINTS.md:L34 (replaces spec.md:L91) | none |
| REQ-031 | The gateway engine is selectable by configuration without changing callers. | Engineering team | CONSTRAINTS.md:L36 | none |
| REQ-032 | The gateway logs the engine, latency, outcome and token or unit count of every call, and records the cost as zero. | Engineering team | CONSTRAINTS.md:L37 (replaces spec.md:L94) | none |
| REQ-033 | The gateway refuses further calls once the configured call cap is reached. | Engineering team | CONSTRAINTS.md:L38 (replaces spec.md:L95) | ambiguous: Q-009 |
| REQ-034 | The test suite replays recorded gateway responses, and CI makes no live engine calls. | Engineering team | spec.md:L96, spec.md:L151, CONSTRAINTS.md:L39 | none |
| REQ-035 | The system selects its engine by scoring each free candidate on the same labelled synthetic set, by field type and by document classification, and records latency, hardware needed, the result and the runner-up in a decision record. | Engineering team | CONSTRAINTS.md:L43-L49 | none |
| REQ-036 | The system rejects any engine that cannot run for free end to end. | Engineering team | CONSTRAINTS.md:L51 | none |
| REQ-037 | The eval reports field-level extraction accuracy on 30 labelled synthetic documents. | Engineering team | spec.md:L100, spec.md:L152, CONSTRAINTS.md:L56 | none |
| REQ-038 | The eval compares the chosen engine with the runner-up on the same 10 documents. | Engineering team | spec.md:L101 as redefined by CONSTRAINTS.md:L55 | none |
| REQ-039 | The eval harness runs without any paid service. | Engineering team | CONSTRAINTS.md:L57 | none |
| REQ-040 | The seed produces 20 applications and 30 synthetic documents. | Engineering team | spec.md:L106, spec.md:L153 | none |
| REQ-041 | The seed renders documents from HTML to PNG with photo noise (blur, skew, shadow). | Engineering team | spec.md:L107, CONSTRAINTS.md:L20 | ambiguous: acceptance set in design |
| REQ-042 | The seed includes documents that deliberately mismatch their application. | Engineering team | spec.md:L108 | ambiguous: acceptance set in design |
| REQ-043 | The system uses only synthetic documents and applications, in development, tests, evals, demos and screenshots. | Engineering team | spec.md:L109, spec.md:L114, CONSTRAINTS.md:L19-L21 | none |
| REQ-044 | The system sends no real student data to any third-party service. | Engineering team | CONSTRAINTS.md:L22 | none |
| REQ-045 | The system supports a transfer certificate document type (stretch). | Admissions staff | spec.md:L136 | ambiguous: Q-007 |
| REQ-046 | The system shows field crops of a document (stretch). | Verifier | spec.md:L137 | ambiguous: acceptance set in design |

## 6. Constraints

- Postgres in Docker (spec.md:L21).
- Local PDF rasterising with pdf2image (spec.md:L22).
- "Nothing else" in the runtime (spec.md:L23); see Q-015 for how this meets a self-hosted engine.
- Total project cost is zero: no paid API, no credit card at any point, no prepaid or pay-as-you-go balance (CONSTRAINTS.md:L7-L11).
- Everything is open source or on a free tier that needs no card; hosting is free (CONSTRAINTS.md:L12-L13).
- A free tier that can silently convert to paid use is not allowed unless it cannot be billed without a card on file (CONSTRAINTS.md:L14).
- Any new dependency, service or model is checked against these rules before it is added (CONSTRAINTS.md:L15).
- Synthetic data only; never real student documents (spec.md:L109, CONSTRAINTS.md:L19-L22).
- brg_privacy is mandatory because of minors' data and category certificates (spec.md:L113).
- brg_llm_eval measures field-level extraction accuracy (spec.md:L102).
- The brg_patterns uploads pattern is loaded for the upload flow (spec.md:L118).
- Fallback for weak extraction: low-confidence fields go to Needs review instead of chasing accuracy (spec.md:L124, CONSTRAINTS.md:L77).

Withdrawn from spec.md by CONSTRAINTS.md:L26-L30 and therefore not constraints: OpenRouter, claude-haiku-4-5, max_tokens 600, the USD 8 cap and the USD 10 key cap. See docs/spec-changes.md.

## 7. Open questions

18 entries in docs/product/questions.md: 18 open (contradiction 4, gap 14, open-question 0), 18 need your confirmation (Q-001 to Q-018).

## 8. Could not extract

- Problem: not stated as a section in the input; inferred above. The product owner can supply it.
- Business objective targets: no accuracy bar, flagged-rate target or throughput target is called a target in the input.
- Tracker epic: no tracker is configured.

## 9. Glossary

| Term | Meaning | Source |
| --- | --- | --- |
| Verified | Status of an application whose fields all match, or on which a verifier has decided | spec.md:L67, spec.md:L73 |
| Needs review | Status of an application with a mismatch or a low-confidence field | spec.md:L68, spec.md:L124 |
| Missing documents | Status of an application that lacks documents | spec.md:L69 |
| Flagged queue | The applications a verifier works | spec.md:L11 |
| Gateway | The one function through which all OCR and vision work passes | CONSTRAINTS.md:L34 |
| Token-sorted similarity | The fuzzy comparison used for names | spec.md:L58 |
| Synthetic document | A made-up document rendered from HTML to PNG with photo noise | CONSTRAINTS.md:L20 |
