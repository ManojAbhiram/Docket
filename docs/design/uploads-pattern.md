# Pattern plan: uploads (document scans and photos)

Pattern: `feature-patterns/references/uploads.md`. Stack: Python (FastAPI) with a React frontend. Existing hits for the reference's markers: 0 (read `app/`: no upload code, no presign, no scanner). Version v1, 2026-10-05, Proposed. Serves US-00-002, US-00-003, REQ-004 to REQ-006, ADR-0001, ADR-0007, `docs/security/threat-model-docket.md` T-10 to T-14.

No production code is written here. The plan feeds the upload story (US-00-002) and the "Upload hardening" story proposed by the threat model.

## Decisions

Decisions marked "from ADR" are settled by an accepted ADR. The others are my recommendations, recorded here as Proposed; none is recorded as decided because the user was not asked these in this conversation.

| Question | Choice | Reason |
| --- | --- | --- |
| Direct-to-storage or through the API? | Through the API (from ADR-0007: no object storage, bytes go to Postgres) | The reference prefers presigned uploads, but there is no object store to presign for, and the API must transform on the way in (a PDF becomes its first page, an image is normalised). It exceeds the reference's 5 MB guidance for this route, so the stream is read with a running byte count and refused at the cap, never buffered whole. One office means few concurrent uploads. |
| Size limit | 8 MiB per file, checked while streaming and again by `chk_documents_size_range` and `chk_document_blobs_size_range`; no per-user daily cap | The number is an assumption for the product owner (data model section 12). The cap lives on the server, never only in the client. A daily cap is not asked for by any story; the threat model's login and import hardening stories cover abuse. |
| Allowed types | JPEG, PNG and PDF, by declared type and by the first bytes of the file; both must agree | Matches AC-US-00-002-2. The sniff is a short server-side check on the leading bytes (`FF D8 FF`, `89 50 4E 47`, `%PDF-`), not a library, so no new dependency. A mismatch is refused, not quarantined, because nothing has been stored yet. |
| Virus scan | None in v1 | ClamAV needs a second container and over 1 GB of memory, which does not fit the 512 MB budget (ADR-0001, ADR-0004). The residual risk is a hostile file hitting a decoder (threat T-10), reduced by: magic bytes, size, pixel and page caps, a processing timeout, running one document at a time, never serving the stored bytes in any form but a re-encoded image with a fixed content type and `X-Content-Type-Options: nosniff`, and never executing anything from a file. Reopen for real data. |
| Image processing | On upload, one fixed form: decode, strip metadata, re-encode | Phone photos carry EXIF, including GPS position and device details, and these are minors. Re-encoding drops them. The image is stored at no more than 2,000 pixels on the longest side (assumption), as JPEG quality 85 for photos and PNG kept for PNG. A PDF is stored as its first page rasterised to JPEG at no more than 200 dpi (ADR-0007). The engine then downscales to 640 pixels (ADR-0001). Field crops (US-00-010) are computed on request, not stored. |
| Orphans and retention | No orphan files are possible: the document row and its bytes commit in one transaction. A sweeper marks a `processing` document older than 5 minutes as `failed` (reason `interrupted`) | Streaming into one transaction removes the "record without bytes" case. A crash during reading leaves a stuck `processing` row, which becomes a Needs review application. Retention of the documents themselves is UNDEFINED (data model section 8). |

## Data model

The tables already exist in `docs/design/schema.sql`: `documents` (metadata, status, current flag, sha256, size) and `document_blobs` (bytes). The reference's `files` and `file_derivatives` map to them as follows: `status` is `uploaded`, `processing`, `read` or `failed` instead of `pending`, `clean`, `infected`; there is no scan state and no derivatives table. A repeated upload of identical bytes for the same application is detected by `sha256` in the service (no unique index, because a deliberate re-upload after a replaced document is allowed).

## Endpoints

| Method and path | Auth | Does |
| --- | --- | --- |
| `POST /api/applications/{id}/documents` | session, staff role | multipart upload of one file; returns 202 with the document id, or 200 with the existing id when the same bytes are already stored for the application |
| `GET /api/applications/{id}/documents` | session | list an application's documents with type, status and failure reason |
| `GET /api/documents/{id}/image` | session | the stored image with a fixed content type, `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff` |

## Flow

1. The route reads the multipart body as a stream with a running byte count and stops at 8 MiB with 413. It reads the first bytes and compares them with the declared type (415 on a mismatch or an unsupported type).
2. Decode with limits before storing: an image over the pixel cap is refused with 422; a PDF is refused over the page cap (the first page only is rasterised) and the rasteriser runs with a time limit. Metadata is dropped by re-encoding.
3. One transaction inserts the `documents` row (`uploaded`) and its `document_blobs` row, and records `sha256` of the uploaded bytes and the size. The response is 202.
4. A single background loop claims `uploaded` documents with `FOR UPDATE SKIP LOCKED`, one at a time (this bounds memory, threat T-11), moves them to `processing`, calls the OCR gateway (ADR-0001, ADR-0002) and follows the processing rules in the data model (current document, status precedence, call log).
5. The result sets `read` or `failed`; the application status is recomputed in the same transaction.

The loop runs inside the API process because ADR-0004 gives one instance. A second consumer is not added: one document at a time is also the memory limit.

## Failure modes

| Fault | Handling |
| --- | --- |
| client disconnects mid-upload | nothing is committed; no row, no bytes |
| file over the size cap | 413 as soon as the running count passes 8 MiB; the rest is not read |
| declared type and first bytes disagree, or type unsupported | 415, nothing stored |
| decompression bomb or huge pixel size | refused before decoding fully; if it slips through, the processing timeout marks the document `failed` |
| decoder or rasteriser crashes or times out | document `failed` with a reason code, application becomes Needs review; the process is not the only copy of any state |
| process restarts during processing | the sweeper marks stale `processing` rows `failed` (`interrupted`); the staff member re-uploads |
| identical bytes uploaded twice for one application | 200 with the existing document id, no second row, unless the existing document is `failed`: failed documents are excluded from this check so a re-upload is processed (proposed, HLD section 16). Two identical concurrent uploads are made safe by the `idempotency_keys` primary key, not by the sha256 check alone |
| same type uploaded again (different bytes) | both kept; the newer one becomes current (data model processing rule 1) |
| database full or unavailable | upload returns 503; nothing is half stored because the two rows commit together |
| gateway cap reached | the document becomes `failed` with `cap_reached` and the application is Needs review (AC-US-02-001-4); it never stays `uploaded`, because the loop would claim it again and log a refused call without end. Raising the cap reprocesses nothing until a reprocess operation exists (HLD section 16) |

## Tests to write

- upload refuses a file over 8 MiB with 413 and stores nothing
- upload refuses a file whose first bytes do not match its declared type
- upload refuses an unsupported type such as a text file renamed `.png`
- upload refuses an image over the pixel cap and a PDF over the page cap
- upload of a JPEG with GPS EXIF stores an image with no EXIF
- upload of a multi-page PDF stores only the first page as JPEG within the size cap
- an interrupted upload (client closes mid-body) leaves no document row
- uploading the same bytes twice for one application returns the same id
- a newer upload of the same type becomes current and the older is kept
- a retried older upload does not displace a newer current document
- the image route returns 401 without a session and the fixed content type with one
- a `processing` document older than 5 minutes is marked `failed` by the sweeper
- the upload log lines hold no file name, no value and no byte content

## Per-stack pointers

- Python: FastAPI `UploadFile` reads a body through `python-multipart`, which is **not** in `pyproject.toml` and must be proposed with `dependency-audit` before use (it is a runtime dependency, small, open source). `pdf2image` plus the poppler system package for the PDF page (named in `spec.md:L22`, a new system dependency for the image). OpenCV (already a dev dependency) decodes and re-encodes images; it needs promotion to a runtime dependency for the service. A hand-written magic-byte check avoids `python-magic` and its libmagic dependency.
- React: `fetch` with a `FormData` body; no presigned URL. Show the 202 and poll the document list until `read` or `failed`.

## ADRs to record

- `adr "Receive uploads through the API with streaming size caps and a fixed set of types"` (Proposed, derived from ADR-0007)
- `adr "No malware scan in v1: mitigate with limits, re-encoding and fixed serving headers"` (Proposed, an accepted risk; reopen before real data)
- `adr "Re-encode uploaded images to strip metadata and cap size"` (Proposed)

## Open questions

- Is 8 MiB the right cap, and 2,000 pixels the right stored size? Owner: product owner, by 2026-10-31.
- Is it acceptable to discard the original PDF and keep only its first-page image (AC-US-00-002-1 says "the file is stored")? Owner: product owner, by 2026-10-31.
- Is a daily upload cap needed? No story asks for one. Owner: product owner.
