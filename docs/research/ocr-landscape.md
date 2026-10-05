# OCR landscape for Docket: free, open source, 512 MB, noisy Indian document photos

Date: 2026-10-05   Timebox: 2 h (start time not recorded, see "Not run")   Stopped because: answered for the landscape; not answered for the 512 MB fit
Location: no throwaway code was written
Prior work: none in `docs/spikes/` or `docs/adr/`. Fits `CONSTRAINTS.md` section 3.2 step 1 (research candidates) and feeds Q-015, Q-016 and Q-018 in `docs/product/questions.md`.

## Question

Which free, open-source engines can read noisy phone photos and scans of Indian marksheets and ID proofs and run on CPU inside 512 MB of RAM, and which 4 to 6 should be measured first?

## Answered looks like

A shortlist of 4 to 6 candidates with a cited source per claim, and for each the evidence on licence, language coverage (English and Hindi), CPU memory and robustness. Not required: a measured RAM figure. That needs the engines running, which is the next step.

## Answer

Landscape: answered, shortlist of 5 below.
512 MB fit: **not answered.** No source states a peak RAM under 512 MB for any engine on CPU. The one published CPU figure, for PP-OCRv5 through PaddlePaddle, is far over budget (2,220 MB peak). RapidOCR and Tesseract are plausible but unmeasured.

Two facts shape everything else:

- **No candidate extracts named fields.** Every engine returns text, and most return boxes and scores. Name, father's name, date of birth, roll number, marks and document type must come from Docket's own layout and pattern rules. The Docling family outputs Markdown or JSON, but it is English-first and too heavy.
- **Hindi support sits in PP-OCRv5 models, not v6.** The newest PP-OCR generation does not cover Devanagari.

## How to read the evidence

Sources were fetched by a research agent and spot-checked by me. A claim marked **checked** was re-fetched or read by me. A claim marked **agent-fetched** was read by the agent only; its fetch tool summarises pages with a small model, so details may be off. A claim marked **unverified** has no fetched source. "Not stated" means the source gave no number.

## Operative inputs

- Memory budget: 512 MB, from the request. `CONSTRAINTS.md` gives no number. Whether the demo is local or hosted is open (Q-018), so 512 MB is treated as the hosting limit.
- Cost rule: zero cost, no card (`CONSTRAINTS.md:L7-L15`). All shortlisted engines are Apache-2.0, so the rule holds.
- Languages: English and Hindi (Devanagari), from the marksheet and ID proof types in `spec.md:L49`.
- Runtime: Python 3.14 in this repository (`pyproject.toml`). **Not checked:** whether ONNX Runtime, PaddlePaddle, PyTorch or the OCR wheels publish Python 3.14 builds. This could rule out candidates and is logged as DEBT-006.

## Candidates

| Candidate | Version, date | Licence | CPU RAM | Hindi / Devanagari | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| RapidOCR | 3.9.2, 2026-07-21 [PyPI](https://pypi.org/project/rapidocr/) | Apache-2.0 [PyPI](https://pypi.org/project/rapidocr/) | Not stated | v5 models only; v6 covers Chinese, Japanese, Latin [model list](https://rapidai.github.io/RapidOCRDocs/main/model_list/) (**checked**) | boxes, text, scores [usage](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) | 27.3 MB wheel, ONNX Runtime and OpenVINO [PyPI](https://pypi.org/project/rapidocr/). Models auto-download on first use [usage](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) |
| Tesseract 5.5.x, `tessdata_fast` | 5.5.3 on the releases page; date unverified [releases](https://github.com/tesseract-ocr/tesseract/releases) | Apache-2.0 [GitHub](https://github.com/tesseract-ocr/tesseract) | Not stated | `hin`, `san`, `mar`, `nep` share one Devanagari model, usable with `eng` [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) | Text. Word boxes and confidence: unverified | 76.8k stars, 437 open issues [GitHub](https://github.com/tesseract-ocr/tesseract). Needs preprocessing for photos (unverified) |
| PaddleOCR 3.7.0 | 2026-06-11 [PyPI](https://pypi.org/project/paddleocr/) | Apache-2.0 [PyPI](https://pypi.org/project/paddleocr/) | v5 mobile peak 2,220 MB, average 1,831 MB; v5 server peak 4,021 MB; 200 images, Xeon Gold 6271C [docs](http://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html) (**checked**) | v5 Devanagari recogniser: Hindi, Marathi, Nepali, Sanskrit, English; 84.96% line accuracy on Paddle's own 3,611-image set [HF](https://huggingface.co/PaddlePaddle/devanagari_PP-OCRv5_mobile_rec). v6 does not cover Devanagari [v6 docs](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv6/PP-OCRv6.html) | polygons, boxes, scores [docs](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html) | Optional document unwarping and orientation modules [docs](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html). Needs PaddlePaddle, install size not stated |
| docTR | 1.1.0, 2026-08-21 [PyPI](https://pypi.org/project/python-doctr/) | Apache-2.0 [PyPI](https://pypi.org/project/python-doctr/) | Not stated | Devanagari not mentioned in the README [GitHub](https://github.com/mindee/doctr) | word boxes, confidence [GitHub](https://github.com/mindee/doctr) | PyTorch dependency [GitHub](https://github.com/mindee/doctr) |
| EasyOCR 1.7.2 | 2024-09-24, no release since [GitHub](https://github.com/JaidedAI/EasyOCR) | Apache-2.0 | Not stated | Hindi listed among 80+ languages [GitHub](https://github.com/JaidedAI/EasyOCR) | boxes, confidence 0 to 1 [GitHub](https://github.com/JaidedAI/EasyOCR) | PyTorch; 476 open issues [GitHub](https://github.com/JaidedAI/EasyOCR) |
| Surya 0.22.1 | 2026-07-20 [PyPI](https://pypi.org/project/surya-ocr/) | Code Apache-2.0; weights under a modified AI Pubs Open Rail-M licence, free for research, personal use and organisations under USD 5M funding or revenue [GitHub](https://github.com/datalab-to/surya) | Not stated; 650M-parameter model [GitHub](https://github.com/datalab-to/surya) | 90+ languages incl. Hindi [GitHub](https://github.com/datalab-to/surya) | text, layout, tables, boxes [GitHub](https://github.com/datalab-to/surya) | Needs llama.cpp or vLLM [PyPI](https://pypi.org/project/surya-ocr/). Excluded: weights licence and size |
| Granite-Docling 258M | 2025-09-17 [HF](https://huggingface.co/ibm-granite/granite-docling-258M) | Apache-2.0 | Not stated | English, experimental Japanese, Arabic, Chinese; no Hindi [HF](https://huggingface.co/ibm-granite/granite-docling-258M) | Markdown, HTML, JSON | Excluded: no Hindi. SmolDocling-256M-preview is superseded and English only [HF](https://huggingface.co/ds4sd/SmolDocling-256M-preview) |
| PaddleOCR-VL-1.6 | 2026-05-28 [HF](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) | Apache-2.0 | Not stated; 1.0B parameters [HF](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) | The 1.6 card does not list Devanagari; the v1 card claims 109 languages [HF](https://huggingface.co/PaddlePaddle/PaddleOCR-VL) | Markdown, element layout | Excluded: size. Claims robustness to skew, warping, lighting, screen photography on its own benchmark [HF](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) |
| MinerU | 4.0 stable, date not stated [GitHub](https://github.com/opendatalab/MinerU) | Apache-2.0 with additional conditions [GitHub](https://github.com/opendatalab/MinerU) | 2 GB minimum on the basic tier [GitHub](https://github.com/opendatalab/MinerU) | English and Chinese documented | Markdown, JSON | Excluded: RAM |
| GOT-OCR-2.0-hf | 2024-09-03 [HF](https://huggingface.co/stepfun-ai/GOT-OCR-2.0-hf) | Apache-2.0 | About 1.2 GB for BF16 weights [HF](https://huggingface.co/stepfun-ai/GOT-OCR-2.0-hf) | "Multilingual", no list | text, Markdown | Excluded: RAM |
| olmOCR 0.4.0 | 2025-10-21 [GitHub](https://github.com/allenai/olmocr) | Apache-2.0 | At least 12 GB VRAM [GitHub](https://github.com/allenai/olmocr) | Not stated | Markdown | Excluded: needs a GPU |

Also read, all excluded for size (1B to 8.7B parameters) or missing CPU support:

- Florence-2-base, MIT, 0.23B parameters [HF](https://huggingface.co/microsoft/Florence-2-base)
- dots.ocr and dots.mocr, MIT, 3B parameters [GitHub](https://github.com/rednote-hilab/dots.ocr)
- DeepSeek-OCR, MIT, CUDA documented [GitHub](https://github.com/deepseek-ai/DeepSeek-OCR)
- LightOnOCR-2-1B, Apache-2.0, Hindi not listed [HF](https://huggingface.co/lightonai/LightOnOCR-2-1B)
- Nanonets-OCR2-3B, licence not stated on the card, parameter count given as both 3B and 4B [HF](https://huggingface.co/nanonets/Nanonets-OCR2-3B)
- Qwen3-VL-2B-Instruct, Apache-2.0, Hindi not confirmed [HF](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
- MiniCPM-V 4.5, Apache-2.0, 8.7B parameters [HF](https://huggingface.co/openbmb/MiniCPM-V-4_5)
- Docling, MIT [GitHub](https://github.com/docling-project/docling)

The "weights alone exceed 512 MB" reasoning for models of 1B parameters and up is my arithmetic from parameter counts (**unverified**; no source states it).

## Shortlist

Order is the order to measure in.

1. **RapidOCR with PP-OCRv5 Devanagari and English recognisers.** The Paddle models without the PaddlePaddle runtime. A 27 MB wheel with ONNX Runtime as the only heavy dependency gives it the best chance of fitting 512 MB, but no source states its RAM. Boxes and scores are returned.
2. **Tesseract 5.x with `tessdata_fast` `hin+eng`.** Native code, smallest expected footprint, Apache-2.0. RAM is not stated anywhere. The one Hindi comparison I read favours it (see Evidence on Hindi), and it is a useful second opinion against RapidOCR.
3. **PaddleOCR 3.x with PP-OCRv5 mobile models, as an accuracy baseline only.** It has the best-documented photo handling (unwarping, orientation) and a Devanagari recogniser, but its published CPU peak is 2,220 MB. Run it in a separate process on a bigger machine to see how much accuracy the 512 MB engines give up. It is not a deployment candidate.
4. **A PP-OCRv6 detector with a v5 Devanagari recogniser.** An untested hybrid: the v6 detector is smaller (4.4 MB tiny recogniser, 1.9 MB tiny detector per [docs](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html), agent-fetched) while the v5 recogniser keeps Hindi. Whether RapidOCR accepts the mix is **unverified**. Try it only if candidate 1 is over budget in detection.
5. **docTR.** Low priority. It gives word boxes and confidence, but Devanagari is not documented and PyTorch will be the largest dependency in the list. Measure it only if candidates 1 and 2 both fail on Hindi.

Not shortlisted: EasyOCR (no release since 2024-09, PyTorch, lowest Hindi score in the one study I read), every VLM and Docling-family model (size, no documented Hindi), Surya (weights licence and size).

## Evidence on Hindi

- Tesseract 93%, MMOCR 62%, Keras OCR 68%, PaddleOCR 56%, EasyOCR 56% on Hindi in Table I of [Open-Source OCR Libraries: A Comprehensive Study for Low Resource Language](https://aclanthology.org/2024.icon-1.48.pdf) (**checked**, read the PDF).
- Limits: the authors gathered their own images by hand and web scraping, the size is not stated, no PaddleOCR version is named (it predates the v5 Devanagari model), and the metric is called accuracy from WER and CER without a precise definition. It is general text, not photos or IDs. Treat it as a reason to include Tesseract, not as a ranking.
- Paddle's 84.96% line accuracy for the v5 Devanagari recogniser is its own figure on its own set [HF](https://huggingface.co/PaddlePaddle/devanagari_PP-OCRv5_mobile_rec), and a whole line counts as wrong if any character is wrong. The two numbers cannot be compared.
- No benchmark on Indian marksheets, Aadhaar or PAN photos was found.

## Risks

Each is logged in `docs/DEBT.md` as shown.

| Risk | Source | Debt row |
| --- | --- | --- |
| No engine has a published RAM figure under 512 MB, so the budget is unmet until measured | Candidates table | DEBT-001 |
| Hindi depends on the older PP-OCRv5 models; v6 dropped Devanagari. Pinning to v5 means maintenance and download risk | [model list](https://rapidai.github.io/RapidOCRDocs/main/model_list/) (**checked**) | DEBT-002 |
| OCR scores are not calibrated; REQ-011 sends low-confidence fields to Needs review, which only works if scores separate right from wrong (Q-016) | `docs/product/PRD.md` REQ-011 | DEBT-003 |
| RapidOCR downloads models from the network on first use (hosting source: [usage](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/), ModelScope per the agent, unverified). CI and offline runs need pre-downloaded models | [usage](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) | DEBT-004 |
| Hindi evidence is not on our task: no document-photo benchmark exists, and the one comparison is general text | Evidence on Hindi | DEBT-005 |
| Python 3.14 wheels for ONNX Runtime, PaddlePaddle, PyTorch and the OCR packages were not checked | Operative inputs | DEBT-006 |
| PaddleOCR issue #17955 reports about 43 GB RAM and an OOM kill on CPU with PaddleOCR 3.4.1 and PaddlePaddle 3.3.1 (Latin recogniser), closed without a visible fix in the fetched page [issue](https://github.com/PaddlePaddle/PaddleOCR/issues/17955) (agent-fetched) | Candidate 3 | Covered by candidate 3 being baseline only |
| RapidOCR 3.8.2 was yanked for a missing config file [PyPI](https://pypi.org/project/rapidocr/) (agent-fetched). Pin an exact version | Candidate 1 | Covered by pinning |

## Method for the next step (from the computer-vision skill)

- **Data:** synthetic only, as `CONSTRAINTS.md` section 2 requires. Do not collect real phone photos of marksheets, Aadhaar or PAN. The research agent suggested real photos; that is rejected here.
- **Split by document, not by image.** Every image of one synthetic student or document stays in one split. Do not tune the engine, confidence threshold and name threshold on the same 30 documents the accuracy is reported on (critic finding on Q-014).
- **Baseline:** Tesseract `hin+eng` with a fixed preprocessing recipe is the number to beat; if RapidOCR does not beat it on name and roll-number fields, take the simpler engine.
- **Metric:** exact match per field and per document type, as the skill says for documents. Not overall accuracy.
- **Confidence:** do not use scores as probabilities. For each engine, report how scores rank right against wrong fields (count of wrong values at high confidence, or AUROC).
- **Memory:** record peak RSS with `/usr/bin/time -v` for one document at the largest allowed image size, pinned to one core, and again after capping the image side before detection. A failed parse or engine error sends the document to review, never drops it (skill step 4).
- **Field rules:** layout and pattern checks per document type (date order, roll-number pattern) send a field to review regardless of confidence.

## Not run or not measured

- Peak RAM of every engine. No engine was installed or run: Bash is unavailable in this session (sandbox error, `apply-seccomp ... Permission denied`), so nothing was measured.
- The baseline `make check` required by the spike skill, the `.scratch/spike-ocr-landscape/` state file and the UTC start time were not run or recorded for the same reason. The 2 h timebox was not tracked on a clock.
- PaddlePaddle install size and RapidOCR model file sizes in MB.
- Whether a v6 detector works with a v5 recogniser in RapidOCR.
- Tesseract word confidence output and its latest release date.
- Last-commit dates for most repositories; the fetch tool showed counts, not dates.
- PP-StructureV3, small Qwen2.5-VL and Qwen3-VL-4B variants, and anything released in 2025 to 2026 that the agent did not search for.
- Python 3.14 compatibility of every package.

## Source conflicts

- RapidOCR release dates: PyPI says 2026-07-21; a GitHub releases summary printed 2024 dates. PyPI is trusted.
- PaddleOCR-VL size: README summary 0.9B, Hugging Face card 1.0B.
- Nanonets: the card gives both 3B and 4B.
- Tesseract: the front page said stable 5.0.0 (stale); the releases page said 5.5.3.
- MiniCPM-V 4.5: the card date does not match its arXiv identifier.
- Hindi: vendor blogs claim PaddleOCR is better on Indian languages; the one primary study I read says the opposite on its own data. Neither is our task.

## Recommendation

narrower spike: "On 30 synthetic marksheet and ID images with phone noise, does RapidOCR with PP-OCRv5 Devanagari plus English stay under 512 MB peak RSS at the largest accepted image size, and does it beat Tesseract `hin+eng` on exact-match name, date-of-birth, roll-number and marks fields?"

Reasoning: the landscape narrows the field to two engines that could fit the budget, and no source can settle the memory question without a run. The synthetic set is a dependency, so this spike follows US-02-003 (seed) and runs inside US-02-002 (choose the engine).

## Follow-up

- Task: "Measure RapidOCR and Tesseract on the synthetic set (RAM, per-field accuracy, confidence ranking)" (tracker: none; belongs in US-02-002)
- ADR needed: yes, after the measurement (`adr Choose the OCR engine`), recorded as Proposed until decided.

## Throwaway

No spike code was written and no `.scratch` directory was created.
