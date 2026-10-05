# ADR-0007: Store document images in Postgres behind a storage interface

- Status: Accepted
- Date: 2026-10-05
- Task: US-02-002
- Deciders: Manoj Abhiram (chose in session, recommended option)
- Area: database (file storage)
- Reversibility: awkward: bytes must be copied to the new store and a read path switched, but only `document_blobs` changes, not `documents` or any story.

## Context

Uploaded scans are the evidence for a Verified status (REQ-018) and are shown beside the application (US-00-006). The only store the project already runs is Postgres (`docker-compose.yml`). Facts:

- ADR-0004: free hosts have ephemeral disks, so files on a volume would be lost on a hosted deployment. Neon's free tier holds 1 GB.
- Size: the 30-document demo is about 5 MB. Real phone photos are 2 to 5 MB each (an estimate, not measured here), so 15,000 documents is on the order of 4.5 x 10^10 bytes.
- `docs/design/data-model.md`: `document_blobs` is one table with one row per document, apart from `documents`.
- The file cap is 8 MiB per upload (an assumption in `docs/design/data-model.md` section 12, unconfirmed).

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| `document_blobs` table in Postgres behind a storage interface (chosen) | does not scale past about 1 GB on the free host; backups and the working set grow with every image | the demo and a few hundred documents, on a host with no persistent disk |
| Files on a local volume | lost on an ephemeral free host, so it blocks the hosted variant | a local or self-hosted deployment at scale |
| S3-compatible object storage from the start | needs another service (local MinIO or a hosted tier whose card terms were not verified) and another credential | 15,000 real documents or a hosted production deployment |

## Decision

We will keep the page image of each document in a `document_blobs` table in Postgres, accessed only through a storage interface in the application, because it works locally and on an ephemeral-disk host with nothing new to run, and the interface lets a later move replace one table.

## Consequences

- Easier: one backup, one transaction for the document row and its bytes, no new service.
- Harder: the database grows by every image; only the demo size is supported on Neon Free. A PDF is stored as its first page rasterised to JPEG at no more than 200 dpi and the original is not kept (an assumption about AC-US-00-002-1).
- Revisit when real documents are about to be used, when the table passes 500 documents or 1 GB (the trigger is my estimate, not a measured limit), or when a hosted production deployment is planned. Then move to object storage behind the same interface.

## Commits us to

PostgreSQL `bytea` storage, no new library. A storage interface to be defined in `app/` (outside the standard stack: none).
