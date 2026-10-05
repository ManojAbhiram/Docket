# ADR-0002: Extract fields with box rules and format validators

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: vision approach (field extraction)
- Reversibility: awkward: the extractor and its per-document-type rules are new code that tests and the review screen will depend on; replacing it with a model means rewriting the module and its cases.

## Context

The gateway must return a document type, fields as JSON and a per-field confidence (`CONSTRAINTS.md` section 3.1). No extractor exists. The benchmark only checks that a printed value appears somewhere in the OCR text (`evals/scoring.py`), an upper bound; it never assigned a value to a field. The engine (ADR-0001) returns text, boxes and scores per line (RapidOCR) and no fields. There are four document types in the seed (10th marksheet, 12th marksheet, ID proof, transfer certificate), one template each. The product fields and match rules are in `docs/product/PRD.md` (REQ-009 to REQ-016) and the field map is open (Q-017).

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Rules over OCR boxes plus format validators (chosen) | new code per document type and per board layout; real marksheets vary and cannot be tested on synthetic data | layouts are few and known; determinism and zero cost matter |
| Vision model returns JSON | 2.4 GB or more of local RAM, or a hosted key whose free tier allows training use and human review; output and confidence not deterministic | many unseen layouts and a host with RAM or an acceptable hosted terms |
| Rules first, model for flagged fields | two paths to build and test | rules fail on real layouts and the flagged queue is too large |

## Decision

We will pair each label with the value to its right using the OCR boxes, per document type, and validate every field with a format rule (a parseable date, a roll number matching the board pattern, five subjects, each mark 0 to 100), because it is deterministic, free and adds no RAM, and the validators are what decide Needs review (ADR-0005).

## Consequences

- Easier: every extraction is explainable and testable; confidence per field can be the minimum score of the lines it used, which `CONSTRAINTS.md` needs.
- Harder: each new board or layout needs rules; the first real marksheet may break them. Accepted: synthetic data cannot show this, and real data is banned (`CONSTRAINTS.md` section 2).
- To build: `app/domain/` extractor and validators under US-00-003; a scorer that checks the value at its field position, not anywhere on the page.
- Revisit if the rules miss more fields than the review queue can absorb on a layout set the owner supplies, or if more than a handful of layouts must be supported (reopens ADR-0003).

## Commits us to

No new library; Python standard library and the OCR output of ADR-0001.
