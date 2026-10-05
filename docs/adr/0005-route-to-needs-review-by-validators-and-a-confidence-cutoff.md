# ADR-0005: Route to Needs review by validators and a configured confidence cutoff

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: review routing (REQ-011, Q-002, Q-016)
- Reversibility: cheap: the cutoff is configuration; the rule that validators decide is a small module.

## Context

`spec.md` line 11 says verifiers work only the flagged queue, "say 12%", of 5,000 applications. That is an example, not a confirmed target (PRD B1 target unconfirmed). It applies to applications. About 3 documents per application means 12% of applications is about 4.2% of documents: 1 minus 0.88 to the power of one third.

Measured on the 30 synthetic documents (`evals/ocr/results/*.jsonl`), score = mean line confidence per document:

- Raw run: 11 of 30 documents contain a missed field (all in marks). Those average 0.987 against 0.992 for the 19 fully read. The 4 lowest scores (13.3%) include only 2 of the 11 misses; 4 of the 11 score 0.994 or more and look like correct reads.
- Preprocessed 640 px run (ADR-0001): all 30 read fully. The 4 lowest scores (cutoff 0.983, 13.3%) are all correct reads. Cutoffs 0.9804 flags 1 document (3.3%), 0.9806 flags 2 (6.7%). The same configuration gives identical scores on repeat, so the ranking is repeatable.
- The seed has 8 of 30 deliberate mismatches (27%), so it cannot calibrate a 12% total. `CONSTRAINTS.md` asks for per-field confidence; the numbers above are per document because no extractor exists.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Validators first plus a configured cutoff, initially 0.9804 (chosen) | on this data the score catches nothing (the flagged document was read correctly); the initial value is a placeholder until real scores exist | production scores exist and a percentile can be computed |
| Fixed cutoff 0.983 as measured | flags 4 of 30 documents (13.3%), about 35% of applications, nearly triple the target | the target were per document and scores were stable across batches |
| No confidence cutoff in v1 | drops the REQ-011 low-confidence rule and CONSTRAINTS.md per-field gating; misses at 0.994 and above are invisible to the score anyway | a better signal is the only gate wanted |

## Decision

We will send a document to Needs review when any field fails its format validator (ADR-0002), when a real mismatch is found, or when a field's confidence is below a configured cutoff, initially 0.9804 (provisional), because the engine score alone separates right from wrong too weakly to decide.

The cutoff is set by rule, not by number. For a target share T of applications flagged and k documents per application, the confidence-flagged share of documents is p = 1 minus (1 minus T')^(1/k), where T' is T minus the share already flagged by validators and mismatches. Today, with T = 12%, k = 3 and nothing else counted, p is 4.2%, which on these 30 documents is about 1 document: the 0.9804 figure. It is recomputed from the first real batch and per field once the extractor exists.

## Consequences

- Easier: the queue size is tunable without code; the rule survives a change of engine or preprocessing, which shifts the scores (raw and preprocessed runs differ).
- Harder: until real scores exist the number is a placeholder and flags documents that were read correctly. Accepted.
- Config name proposed: `NEEDS_REVIEW_CONFIDENCE`; target share `NEEDS_REVIEW_TARGET` (unconfirmed, awaiting the owner).
- Revisit when the first real batch exists, when per-field confidence exists, or when the flagged share of applications is more than 3 points from the target for a week.

## Commits us to

No new library.
