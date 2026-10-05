# Test scenarios

Source: `docs/product/backlog.md` as of 2026-10-05. One block per story. Written by
`test-cases`; change the backlog, not this file, to change a scenario.
Each row names the cases in `test-cases.md` that cover it. Scope of this run: US-00-004 only.

## US-00-004: Compare extracted fields with the application

Requirements: REQ-012, REQ-013, REQ-014, REQ-015, REQ-016
Acceptance criteria: AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4, AC-US-00-004-5

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-004-1 | Happy | An identical name, date, roll number and set of marks all match | a correct document is recognised as correct on every rule | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0001, TC-0011, TC-0015 |
| TS-US-00-004-2 | Alternate | The same name in the other order, the same date in another print format, and an ID proof without marks all still match | harmless differences in print do not create work for a verifier | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-5 | TC-0002, TC-0007, TC-0019, TC-0021 |
| TS-US-00-004-3 | Error | A different given name, a date one day off, a roll number off by one digit and a mark off by one each mismatch | a wrong document is never accepted as right | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0003, TC-0008, TC-0012, TC-0016, TC-0006 |
| TS-US-00-004-4 | Edge | Empty name, single-word name, leap day, impossible date, letter O for zero, trailing space, marks 0 and 100, missing subject | boundary values are decided the same way every time | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3, AC-US-00-004-4 | TC-0004, TC-0005, TC-0009, TC-0010, TC-0013, TC-0014, TC-0017, TC-0018 |
| TS-US-00-004-5 | Error | A document from which nothing could be compared is not a match | an application cannot be verified on no evidence | AC-US-00-004-5 | TC-0020, TC-0022 |
| TS-US-00-004-6 | Security | Comparing a document writes no name, date of birth or roll number to the logs | a child's personal data does not leak through logs | AC-US-00-004-1, AC-US-00-004-2, AC-US-00-004-3 | TC-0023, TC-0024 |
| TS-US-00-004-7 | Edge | Malformed or hostile values never crash the comparison, and the same input always gives the same result | one bad document cannot block the queue | AC-US-00-004-2 | TC-0025, TC-0026 |

Not applicable: Performance: the PRD gives no speed target for matching (the comparison is local string work); Accessibility: the story has no screen.
Invariants: a comparison never raises on malformed input (TC-0025); the same input gives the same result twice (TC-0026).

## Needs rewording

Criteria with no testable expected result. Each one counts as uncovered
until the backlog is fixed.

- none
