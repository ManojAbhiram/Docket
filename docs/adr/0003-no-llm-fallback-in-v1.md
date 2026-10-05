# ADR-0003: No LLM fallback in v1

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: llm provider and models (optional fallback)
- Reversibility: cheap: the gateway is swappable by configuration (`CONSTRAINTS.md` section 3.1), so a fallback can be added behind it later without changing callers.

## Context

An optional model could re-read fields the rules (ADR-0002) cannot. Facts from `docs/research/free-hosting.md`, checked 2026-10-05:

- Gemini API free tier: free on Flash models, limits shown only in Google AI Studio, card requirement not found. Its terms allow training use and "human reviewers may read, annotate, and process your API input and output".
- Local Ollama vision models: granite3.2-vision 2.4 GB, qwen2.5vl 3B 3.2 GB (download sizes; no RAM figure on the model pages). Neither fits a 512 MB host beside the OCR engine.
- OpenRouter free models: 20 requests per minute and 50 per day; Hugging Face Inference Providers: $0.10 a month; Mistral and Cloudflare Workers AI limits for vision not confirmed.
- Nothing has failed that a fallback would fix: the rules are not built (ADR-0002), and the benchmark has no field-assignment errors to correct.
- Data is synthetic, so the hosted terms would be acceptable, but nothing needs the fallback yet.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| None in v1, keep the gateway swappable (chosen) | no recovery path if the rules fail on layouts we cannot test | the rules work on the layouts the owner supplies |
| Gemini free tier for flagged fields | training use and human review of inputs; limits unknown; card status unverified | rules fail on real layouts and the data is synthetic or consented |
| Local Ollama vision model | 2.4 GB or more; does not fit any free host with the engine | a local run with spare RAM and a field where the engine and rules fail |

## Decision

We will ship v1 with no LLM fallback and keep the gateway interface open to one, because no failure exists that it would fix and every option either costs RAM beyond the budget or sends page images to a third party.

## Consequences

- Easier: smaller scope, no third-party data flow, nothing to monitor for quota.
- Harder: a field the rules miss goes to Needs review and a person reads it. Accepted.
- Revisit when the extractor exists and a measured share of fields on layouts the owner supplies goes to review because of extraction failures, not because of true mismatches. Then reopen with the quota and terms checked again, since these figures are dated 2026-10-05.

## Commits us to

Nothing new.
