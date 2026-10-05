# ADR-0010: Re-encode uploaded images to strip metadata and cap size

- Status: Proposed (awaiting the engineer; not yet decided by a person)
- Date: 2026-10-05
- Task: US-02-002
- Deciders: none yet
- Area: object storage (uploads)
- Reversibility: one-way for stored documents: originals that were discarded cannot be recovered; only future uploads can change.

## Context

Phone photos carry EXIF data, including GPS position and device details, and the applicants are minors (`docs/privacy/DPIA-admissions-verification.md`). A PDF is stored as its first page (ADR-0007). The engine downsizes to 640 pixels (ADR-0001), so full resolution adds storage and no accuracy.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Decode and re-encode once on upload (proposed) | the original is lost, which AC-US-00-002-1 ("the file is stored") may not allow | minors' data and a small database |
| Store the original and strip on read | metadata stays at rest and the database grows | a case that needs the original |
| Strip metadata only, keep pixels | still stores large files | a large object store |

## Decision

We will decode every image on upload, drop all metadata by re-encoding, cap the longest side at 2,000 pixels (an assumption), and store JPEG quality 85 for photos and PNG for PNG, because it removes location data from minors' files and keeps the database small.

## Consequences

- Easier: no EXIF in the database or in any response.
- Harder: OpenCV, now a dev dependency, becomes a runtime dependency of the API image, and PDF rasterising needs `pdf2image` and the poppler system package. Both go through `dependency-audit`. The original bytes are not kept; this is the same open question as ADR-0007 for the product owner.
- Revisit if a story needs the original file.

## Commits us to

OpenCV (headless) as a runtime dependency, `pdf2image` with poppler. Outside the catalogue defaults: image and PDF handling has no default there.
