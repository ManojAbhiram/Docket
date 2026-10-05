# Constraints

These rules apply to the whole project and override `spec.md` wherever the two disagree.

## 1. Zero cost

Total project cost must be zero.

- No paid APIs.
- No credit card on any account, at any point.
- No OpenRouter credit or any other prepaid or pay-as-you-go balance.
- Everything is open source or on a free tier that needs no card.
- Hosting is free too. If a free tier asks for a card to sign up, it is not allowed.
- A free tier that can silently convert to paid use is not allowed unless it cannot be billed without a card on file.
- Any new dependency, service or model is checked against these rules before it is added.

## 2. Synthetic data only

- Never use real student documents, in development, tests, evals, demos or screenshots.
- All documents are synthetic, rendered from HTML to PNG with photo noise (blur, skew, shadow).
- All applications are synthetic. No real names, dates of birth, roll numbers or marks.
- Real student data must not be sent to any third-party service, free or not.

## 3. Replaced requirement: the model gateway

The following `spec.md` requirement is withdrawn:

> One vision call on OpenRouter using claude-haiku-4-5, max_tokens capped at 600, USD 8 spend cap.

It is replaced by an OCR/vision gateway whose engine is chosen by measured research.

### 3.1 Gateway

- All OCR and vision work goes through one gateway function. Nothing else in the codebase talks to an engine directly.
- The gateway takes a document image and returns a document type, extracted fields as JSON, and a per-field confidence.
- The engine behind the gateway is swappable by configuration, so the choice can change without touching callers.
- The gateway logs engine, latency, outcome and token or unit counts per call. Cost per call is always zero, and the log records that.
- The gateway enforces a call cap: it keeps a running count of calls and refuses further calls once the configured cap is reached. The cap protects free-tier quotas and compute limits, not money. The cap value is set by configuration and decided in the engine decision record.
- Tests replay recorded responses, so CI makes no live engine calls.

### 3.2 Engine selection

The engine is not fixed in advance. It is chosen from measurement.

1. Research candidates that satisfy section 1 (open source, self-hosted or free tier with no card).
2. Run each candidate on the same labelled synthetic set, with the same noise levels.
3. Score field-level extraction accuracy per field type (names, dates, roll numbers, marks), plus document classification accuracy.
4. Record latency per document and the hardware needed to run it.
5. Pick the engine with the best accuracy that runs within the free hosting limits. Write the result, the numbers and the runner-up into a decision record.

An engine that cannot be run for free, end to end, is disqualified however accurate it is.

### 3.3 Evals

- The "10-document comparison against a stronger model" in `spec.md` section 7 now means: compare the chosen engine against the runner-up on the same 10 documents.
- The 30-document labelled field-level accuracy eval stays as written.
- The eval harness must also run for free.

## 4. Sections of spec.md affected

| spec.md section | Effect |
|-----------------|--------|
| 1 Summary | "A vision model" becomes "an OCR/vision engine chosen per section 3.2" |
| 2 AI depth | Vision extraction stays; the engine is chosen by research |
| 3 Runtime | Stays, with hosting and every component also bound by section 1 |
| 5.3 Classification and extraction | "One vision call per document" becomes "one gateway call per document" |
| 6 LLM gateway | Replaced by section 3 of this file |
| 7 Evals | Stronger-model comparison redefined in section 3.3 |
| 11 Risks | The USD 10 cap risk is removed; the main risk is that free engines are less accurate on noisy phone photos |
| 14 criteria 3, 10, 12 | Criterion 3 reads "gateway call", criterion 10 is replaced by the logging rule in section 3.1, criterion 12 follows section 3.3 |

`spec.md` has not been edited. This file is the authority until it is brought in line.

## 5. Unchanged

- The verification flow, roles, matching rules, statuses and decision log.
- Fallback for weak extraction: route every low-confidence field to Needs review instead of chasing accuracy.
- Out of scope items and the privacy requirement.
