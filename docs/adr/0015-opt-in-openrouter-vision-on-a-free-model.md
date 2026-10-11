# ADR-0015: Opt-in OpenRouter Vision on a free model

- Status: Accepted
- Date: 2026-10-11
- Task: NOTASK-15
- Deciders: Manoj Abhiram (chose the free-model scope in session)
- Area: document extraction, llm provider
- Reversibility: cheap; switch it off by leaving `OPENROUTER_API_KEY` empty. Migration 0003 only adds columns.

## Context

ADR-0003 shipped v1 with no LLM fallback and kept the gateway open to one. The owner now wants an
opt-in way to read a page with a vision model, next to the local RapidOCR. `CONSTRAINTS.md` still
holds: zero cost, no card, no OpenRouter credit, synthetic data only. The paid plan in
`docs/superpowers/plans/2026-10-10-dual-ocr.md` (USD 8 budget, holds, billing recovery) conflicts
with section 1 and is not built. OpenRouter lists free vision models (ids ending in `:free`) with a
published limit of 20 requests a minute and 50 a day.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Free model, opt-in per upload (chosen) | 50 requests a day, so it suits demos and a verifier's second look | a small team that wants a model's opinion on hard pages |
| Paid model with a USD 8 budget ledger | breaks section 1 and the `cost = 0` database check; three to four times the work | an owner who changes the zero-cost rule |
| Vision as the default reader | sends every page image to a third party and exhausts the free daily limit | never, under section 2 |

## Decision

We will add an opt-in Vision reader that calls one free OpenRouter vision model chosen by
`OPENROUTER_MODEL`, because it gives a second reading without breaking the zero-cost and
synthetic-data rules.

## Consequences

- Staff choose `free` (default) or `vision` on each upload. Vision needs a key and a model on the server, otherwise the upload is refused with 409 `vision_unavailable`.
- A model gives no score and no box, so every Vision field is stored with no confidence and marked for review: a person always decides.
- Vision is a first try. If it hits the cap, times out, errors or answers badly, the page is read by RapidOCR and the document keeps `fallback_reason`. An upload is never lost to the provider.
- The cap is 40 Vision calls in a rolling 24 hours, counted from `gateway_calls`, under the free 50 a day. Cost stays zero.
- The provider's own message is never stored or logged, because it can echo a value from the page.
- Page images leave the machine only in Vision mode. The upload screen says so, and data must be synthetic.
- `httpx` moves from the dev group to runtime dependencies. It was already locked.
- Revisit when the free limit blocks real use, or when the owner changes section 1 and wants the paid plan.

## Commits us to

`httpx` at runtime, an OpenRouter account with a free-tier key held only in the environment, and migration 0003.
