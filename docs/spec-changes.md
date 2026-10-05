# Spec changes from CONSTRAINTS.md

Date: 2026-10-04. CONSTRAINTS.md overrides spec.md (CONSTRAINTS.md:L3). spec.md itself is unchanged. This is the first PRD, so no REQ was withdrawn: each REQ was written in its final form and cites both documents. The Basis column of the PRD points here.

| # | spec.md says | CONSTRAINTS.md says | PRD effect |
| --- | --- | --- | --- |
| 1 | Vision model classifies and extracts (L9, L15) | An OCR/vision engine chosen by measurement (L30, L43-L51) | REQ-009, REQ-010 say "gateway call" and name no model; REQ-035 and REQ-036 are new |
| 2 | One vision call per document (L48, L143) | One gateway call per document (L66) | REQ-008 reworded |
| 3 | Extraction returns fields as JSON (L49) | Also a per-field confidence (L35) | REQ-010 adds the confidence |
| 4 | All model calls through one OpenRouter gateway function (L91) | One gateway function for all OCR and vision work (L34) | REQ-030 |
| 5 | Model claude-haiku-4-5 (L92) | Withdrawn (L26-L30); engine swappable by configuration (L36) | No model constraint; REQ-031 |
| 6 | max_tokens capped at 600 (L93) | Withdrawn (L26-L30) | No REQ |
| 7 | Gateway logs tokens and cost per call (L94) | Logs engine, latency, outcome and token or unit counts; cost always zero (L37) | REQ-032 |
| 8 | Gateway refuses calls once spend passes USD 8 (L95, L150) | Refuses calls once a configured call cap is reached; the cap protects quotas, not money (L38) | REQ-033, with Q-009 |
| 9 | Tests replay recorded responses (L96) | Same, no live engine calls in CI (L39) | REQ-034 |
| 10 | 10-document comparison against a stronger model (L101, L152) | Compare the chosen engine against the runner-up on the same 10 documents (L55) | REQ-038 |
| 11 | Eval harness unspecified | Eval harness runs for free (L57) | REQ-039 is new |
| 12 | Risk: Haiku misreads noisy photos; USD 10 key cap (L124-L125) | Cap risk removed; the risk is free engines being less accurate on noisy photos (CONSTRAINTS.md:L69) | USD risk not carried; the weak-extraction fallback kept as a constraint |
| 13 | Synthetic data only (L109, L114) | Also covers evals, demos, screenshots, and no real student data to third parties (L19-L22) | REQ-043, REQ-044 |
| 14 | OpenRouter key capped at USD 10 (spec.md:L125 still says this) | Zero cost, no card, free hosting (L7-L15) | Constraints in PRD section 6 |
| 15 | "Nothing else" in the runtime (L23) | Runtime stays, bound by the zero-cost rule (CONSTRAINTS.md:L65) | Constraint kept; tension logged as Q-015 |
| 17 | Fallback: lower the noise level in the synthetic set (L124) | Same noise levels for every candidate (L46); the fallback is neither kept nor withdrawn | Not carried into a REQ; recorded here so the drop is visible, see Q-016 |
| 16 | Acceptance criteria 3, 10, 12 (L143, L150, L152) | Criterion 3 reads "gateway call", 10 is replaced by the logging rule, 12 follows the evals section | Covered by REQ-008, REQ-032, REQ-033, REQ-037, REQ-038 |
