# Progress: NOTASK-30 ReprocessFailedDocument

- Task: NOTASK-30
- Title: ReprocessFailedDocument
- Branch: feature/NOTASK-30-ReprocessFailedDocument
- Status: in review
- Owner: Manoj Abhiram
- Started: 2026-10-16
- Updated: 2026-10-16
- Acceptance criteria: 4

## Next
- engineer pushes the branch

## Done
- POST /api/documents/{id}/reprocess (staff, CSRF, 202 DocumentOut, 409 document_not_failed), one transaction with status recompute
- Late result fence: complete and fail check the claim's updated_at
- Reprocess button wired on the upload screen, failed copy fixed
- OpenAPI, HLD section 16, uploads-pattern and PS-12 updated; duplicate-upload (sha256) rule unchanged and pinned by a test

## Blockers
- none

## Decisions
- Fence with claimed_at; keep sha256 dedup; keep created_at and requested_mode; no Idempotency-Key, no migration; staff only

## Links
- MR: none
- Ticket: none
