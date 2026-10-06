# ADR-0008: Receive uploads through the API with streaming size caps and a fixed set of types

- Status: Proposed (awaiting the engineer; derived from ADR-0007, not yet decided by a person)
- Date: 2026-10-05
- Task: US-02-002
- Deciders: none yet
- Area: object storage (uploads)
- Reversibility: cheap: one route and one limit; a later move to presigned uploads replaces the route and keeps the tables.

## Context

Staff upload scans and phone photos (US-00-002). ADR-0007 keeps the bytes in Postgres, so there is no object store to presign for, and the API must transform each file on the way in (a PDF becomes its first page, an image is re-encoded, see ADR-0010). The plan is in `docs/design/uploads-pattern.md`. The memory budget is 512 MB with the engine at about 509 MB peak (ADR-0001), so a buffered upload is a risk: an 8 MiB body read whole is 8 MiB, and several at once add up.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Through the API, streamed with a running byte count (proposed) | one process reads the body, so a slow client holds a connection | one office, a few concurrent uploads |
| Presigned direct-to-storage upload | needs an object store ADR-0007 did not choose, and the file arrives untransformed | a hosted production deployment with object storage |
| Read the whole body, then check the size | an oversized or hostile body is already in memory | never at this memory budget |

## Decision

We will receive each upload through `POST /api/applications/{id}/documents` as multipart, count bytes while streaming, refuse at 8 MiB with 413, and accept only JPEG, PNG and PDF where the declared type and the first bytes agree (415 otherwise), because nothing is stored until both checks pass and the limit does not depend on the client.

## Consequences

- Easier: one rule, enforced on the server and again by `chk_documents_size_range` and `chk_document_blobs_size_range`.
- Harder: `python-multipart` was proposed under rule 7 of AGENTS.md and approved on 2026-10-06 (pip-audit clean); it is now in `pyproject.toml`. The 8 MiB cap and the type list are assumptions for the product owner (data model section 12).
- Revisit when real documents are planned or object storage is chosen.

## Commits us to

`python-multipart` (a runtime dependency to be approved). No other new technology.
