# Coverage: PRD statements to stories

PRD: docs/product/PRD.md   Backlog: docs/product/backlog.md   Built: 2026-10-04

## Matrix

| REQ | Statement (short) | Judgement | Why | Covered by | AC ids |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Import applications from CSV | story | Staff can do something new: load applications | US-00-001 | AC-US-00-001-1 |
| REQ-002 | CSV columns | criterion-of US-00-001 | It lists what the import reads, not a separate action | US-00-001 | AC-US-00-001-1 |
| REQ-003 | Reject malformed rows with a reason | criterion-of US-00-001 | It is an error rule of the import | US-00-001 | AC-US-00-001-2, AC-US-00-001-3 |
| REQ-004 | Upload scanned documents | story | Staff can attach documents to an application | US-00-002 | AC-US-00-002-1, AC-US-00-002-4 |
| REQ-005 | Accept JPG, PNG, PDF | criterion-of US-00-002 | It limits which files the upload takes | US-00-002 | AC-US-00-002-1, AC-US-00-002-2 |
| REQ-006 | Rasterise first PDF page locally | criterion-of US-00-002 | It is how a PDF upload is handled | US-00-002 | AC-US-00-002-3 |
| REQ-007 | Process noisy phone photos | criterion-of US-00-003 | It qualifies how documents are read | US-00-003 | AC-US-00-003-5 |
| REQ-008 | One gateway call per document | criterion-of US-00-003 | It limits how reading is done | US-00-003 | AC-US-00-003-1 |
| REQ-009 | Classify document type | merged into US-00-003 (story) | Same reading step as extraction, one outcome | US-00-003 | AC-US-00-003-2 |
| REQ-010 | Fields as JSON with confidence | merged into US-00-003 (story) | The extraction is the core of the story | US-00-003 | AC-US-00-003-3 |
| REQ-011 | Low-confidence fields to Needs review | criterion-of US-00-003 | It is a routing rule for extracted fields | US-00-003 | AC-US-00-003-4 |
| REQ-012 | Compare each field with the application | story | The check that decides who needs a person | US-00-004 | AC-US-00-004-1, AC-US-00-004-5 |
| REQ-013 | Names by token-sorted similarity | criterion-of US-00-004 | A matching rule for one field type | US-00-004 | AC-US-00-004-1 |
| REQ-014 | Dates exact | criterion-of US-00-004 | A matching rule for one field type | US-00-004 | AC-US-00-004-2 |
| REQ-015 | Roll numbers exact | criterion-of US-00-004 | A matching rule for one field type | US-00-004 | AC-US-00-004-3 |
| REQ-016 | Marks exact | criterion-of US-00-004 | A matching rule for one field type | US-00-004 | AC-US-00-004-4 |
| REQ-017 | One of three statuses | story | Staff see a clear status for each application | US-00-005 | AC-US-00-005-1, AC-US-00-005-3, AC-US-00-005-5 |
| REQ-018 | Auto-Verified with evidence | criterion-of US-00-005 | It is one way the status is set | US-00-005 | AC-US-00-005-1 |
| REQ-019 | No Verified without match or decision | criterion-of US-00-005 | A guard on the status | US-00-005 | AC-US-00-005-4 |
| REQ-020 | Flag mismatches for a verifier | criterion-of US-00-005 | It is the other way the status is set | US-00-005 | AC-US-00-005-2 |
| REQ-021 | List flagged applications to a verifier | story | A verifier can open the queue | US-00-006 | AC-US-00-006-1 |
| REQ-022 | Document beside application value | criterion-of US-00-006 | It describes how a flagged item is shown | US-00-006 | AC-US-00-006-2, AC-US-00-006-3 |
| REQ-023 | Approve | story | A verifier can approve | US-00-007 | AC-US-00-007-1 |
| REQ-024 | Correct | criterion-of US-00-007 | One of the three decision actions of one story | US-00-007 | AC-US-00-007-2 |
| REQ-025 | Reject | criterion-of US-00-007 | One of the three decision actions of one story | US-00-007 | AC-US-00-007-4 |
| REQ-026 | Reason required for reject | criterion-of US-00-007 | A guard on reject | US-00-007 | AC-US-00-007-3 |
| REQ-027 | Log every decision | criterion-of US-00-007 | It applies to each decision action | US-00-007 | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-4, AC-US-00-007-5 |
| REQ-028 | Dashboard counts by status | story | Staff can see progress | US-00-008 | AC-US-00-008-1, AC-US-00-008-2 |
| REQ-029 | Export verified list | story | Staff can take the result away | US-00-009 | AC-US-00-009-1, AC-US-00-009-2 |
| REQ-030 | One gateway function | story | The team gets a single path for all engine calls | US-02-001 | AC-US-02-001-1 |
| REQ-031 | Engine selectable by configuration | criterion-of US-02-001 | A property of the gateway | US-02-001 | AC-US-02-001-2 |
| REQ-032 | Log each call, cost zero | criterion-of US-02-001 | A property of the gateway | US-02-001 | AC-US-02-001-3 |
| REQ-033 | Call cap | criterion-of US-02-001 | A property of the gateway | US-02-001 | AC-US-02-001-4 |
| REQ-034 | Replay recorded responses in tests | criterion-of US-02-001 | A test rule for the gateway | US-02-001 | AC-US-02-001-5 |
| REQ-035 | Select engine by scoring | story | The team can pick an engine from numbers | US-02-002 | AC-US-02-002-3, AC-US-02-002-4, AC-US-02-002-5, AC-US-02-002-6 |
| REQ-036 | Reject engines that cannot run free | criterion-of US-02-002 | A rule on which candidates qualify | US-02-002 | AC-US-02-002-1, AC-US-02-002-2 |
| REQ-037 | Field-level accuracy on 30 documents | story | The team gets the accuracy report | US-02-004 | AC-US-02-004-1 |
| REQ-038 | Chosen engine against runner-up on 10 | criterion-of US-02-004 | A second part of the same report | US-02-004 | AC-US-02-004-2 |
| REQ-039 | Eval harness runs free | non-functional | A cost quality carried by the eval story | US-02-004 | AC-US-02-004-3 |
| REQ-040 | Seed 20 applications and 30 documents | story | The team gets data to test with | US-02-003 | AC-US-02-003-1, AC-US-02-003-5 |
| REQ-041 | Render HTML to PNG with noise | criterion-of US-02-003 | It describes how seeded documents look | US-02-003 | AC-US-02-003-2 |
| REQ-042 | Deliberate mismatches | criterion-of US-02-003 | It describes some seeded documents | US-02-003 | AC-US-02-003-3 |
| REQ-043 | Synthetic data only | non-functional | A data quality carried by the seed story | US-02-003 | AC-US-02-003-4 |
| REQ-044 | No real student data to third parties | non-functional | A privacy quality carried by the stories that send documents to an engine | US-02-001, US-00-003 | AC-US-02-001-6, AC-US-00-003-6 |
| REQ-045 | Transfer certificate type (stretch) | out-of-scope | Q-007 decides it is out of scope until every other requirement is done | none | none |
| REQ-046 | Field crops (stretch) | story | A verifier gets a crop of each field | US-00-010 | AC-US-00-010-1, AC-US-00-010-2 |

## Gaps

| REQ | Why uncovered | Proposed action |
| --- | --- | --- |
| REQ-045 | Judged out of scope by Q-007 (assumed) | Confirm Q-007; if in scope, add a story after the core stories |

## Orphan stories

| Story | Reason it exists | Action |
| --- | --- | --- |
| US-00-011 inferred: | Sign-in is needed so the decision log can say who decided (Q-013) | accept as a REQ via prd / drop |

## Counts

Not run: the gate `coverage_check.py` could not be run because Bash is unavailable in this session. No counts or verdict are quoted.
