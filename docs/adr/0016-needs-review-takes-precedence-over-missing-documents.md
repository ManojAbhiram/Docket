# ADR-0016: Needs review takes precedence over Missing documents

- Status: Accepted
- Date: 2026-10-11
- Task: NOTASK-17
- Deciders: Manoj Abhiram (asked in session to close the acceptance audit gaps, recommended option)
- Area: application status rules
- Reversibility: cheap: one function (`app/domain/status.py`) and the tests that lock it.

## Context

AC-US-00-005-3 says an application with a required document type missing is Missing documents. The code and `tests/test_status_rules.py:test_needs_review_beats_missing_documents` return Needs review first when any document is flagged or mismatched, even if a required type is also missing. The acceptance audit found the two disagree.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Needs review first (chosen, current behavior) | a verifier may decide an application that is also incomplete, which is a small surprise | a verifier should see every flagged page at once, whatever else is missing |
| Missing documents first | a flagged page would stay invisible in the review queue until the last document arrives | the queue should hold only complete applications |

## Decision

We will keep Needs review ahead of Missing documents, because a mismatch or low-confidence field is something a person can act on now, while a missing document is something only the applicant can fix.

## Consequences

- Easier: the review queue shows every flagged application without waiting for uploads.
- Harder: the dashboard's Missing documents count excludes incomplete applications that are flagged.
- The backlog criterion AC-US-00-005-3 is reworded to say so. No code changes.

## Commits us to

The existing rule in `app/domain/status.py` and its test.
