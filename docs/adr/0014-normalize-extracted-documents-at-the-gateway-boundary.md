# ADR-0014: Normalize extracted documents at the gateway boundary

- Status: Accepted
- Date: 2026-10-10
- Task: NOTASK-11
- Deciders: Manoj Abhiram (engineering decision D3, option 3A)
- Area: document extraction contract
- Reversibility: awkward; reader protocols, worker mocks and persistence callers move together.

## Context

The approved dual-engine plan needs both readers to return the same classified fields. Previously the gateway returned OCR words and the worker classified and extracted them. A Vision result is already structured; pretending it is OCR words would invent scores and boxes. ProcessedDocument belonged to the worker even though persistence also imported it. The lower-level OCR engine interface and killable child remain useful for RapidOCR and recorded evaluations.

## Options considered

### Option A: shared structured result at the gateway boundary (chosen)

Own ProcessedDocument in an independent domain module. Normalize Free OCR inside GatewayReader and pass the result unchanged through the worker to persistence. This updates authored protocols and mocks together, and leaves the low-level Engine/OcrResult interface intact.

### Option B: separate extraction paths in the worker

Keep OCR words as the worker input and add a separate Vision branch or fabricated word adapter. This duplicates downstream extraction responsibility or implies unsupported OCR evidence for Vision. It would suit independent products with genuinely different persistence contracts, which this plan does not select.

## Decision

We will use a shared structured extraction result at the gateway boundary, because both engines must feed the same worker, evidence comparison and persistence contract without fabricated OCR scores or boxes.

## Consequences

- Classification and extraction happen once for Free OCR, with the supplied confidence cutoff.
- The worker preserves the normalized document and continues to own queue/error/stale-result ordering.
- Low-level OCR words, free call logging, call refusal and child cleanup retain their existing contracts.
- Requested mode, actual engine, missing-evidence safety and Vision review eligibility are later parts of T10. This first change adds no provider request or paid eligibility.
- Revisit if another document reader needs a different evidence contract rather than this shared result.

## Commits us to

Existing Python domain dataclasses and the current gateway/worker/persistence components. No new dependency.
