# Test plan: Docket matching rules (US-00-004)

Backlog: `docs/product/backlog.md` as of 2026-10-05   Cases: docs/testing/test-cases.md
Version: v1   Author: unattributed

## 1. Headline

Scenarios: 7

test-cases: 5 ACs, 5 with cases, 26 live cases, 26 with oracles, 7 risks (high 2, medium 5, low 0), 0 threats traced from 0 threat models, 0 problems
test-types: unit 22, integration 4, e2e 0, manual 0; by machine 26 (automated 0, planned 26), by hand 0

## 2. Risk summary

| Risk | Story | What could go wrong | Level | Cases |
| --- | --- | --- | --- | --- |
| R-001 | US-00-004 | Another person's document is accepted as a match for an application, so a wrong applicant is verified | High | TC-0003, TC-0004, TC-0006 |
| R-005 | US-00-004 | A document from which nothing could be compared counts as a match, so an application is verified on no evidence | High | TC-0019, TC-0020, TC-0022 |

Medium: 5 (R-002, R-003, R-004, R-006, R-007, all US-00-004)   Low: 0

## 3. Scenarios

| Scenario | Story | Title | Proves that | Cases | Run by |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-004-1 | US-00-004 | Everything matches | a correct document is recognised as correct on every rule | TC-0001, TC-0011, TC-0015 | machine |
| TS-US-00-004-2 | US-00-004 | Harmless differences | harmless differences in print do not create work for a verifier | TC-0002, TC-0007, TC-0019, TC-0021 | machine |
| TS-US-00-004-3 | US-00-004 | A wrong value is caught | a wrong document is never accepted as right | TC-0003, TC-0006, TC-0008, TC-0012, TC-0016 | machine |
| TS-US-00-004-4 | US-00-004 | Boundary values | boundary values are decided the same way every time | TC-0004, TC-0005, TC-0009, TC-0010, TC-0013, TC-0014, TC-0017, TC-0018 | machine |
| TS-US-00-004-5 | US-00-004 | No evidence | an application cannot be verified on no evidence | TC-0020, TC-0022 | machine |
| TS-US-00-004-6 | US-00-004 | No personal data in logs | a child's personal data does not leak through logs | TC-0023, TC-0024 | machine |
| TS-US-00-004-7 | US-00-004 | Malformed input and repeatability | one bad document cannot block the queue | TC-0025, TC-0026 | machine |

## 4. Entry criteria

- The comparison module exists under `app/domain/` with a function per rule; today it does not (`app/domain/__init__.py` is empty). The author of the module confirms.
- `make check` passes on the branch before the new tests are added (the lead confirms).
- The decisions behind Q-003 (name threshold), Q-011 (date formats) and Q-017 (field map) are answered or the assumed readings in `docs/product/questions.md` are accepted (the product owner confirms).

## 5. Exit criteria

- Every P1 case passes (TC-0003, TC-0004, TC-0006, TC-0008, TC-0012, TC-0016, TC-0020, TC-0022, TC-0023, TC-0025).
- The gate `cases_check.py` exits 0 with `--plan` on this file.
- No open defect on a P1 case; a waiver names the product owner.
- Coverage of the comparison module is above the repository gate of 80 percent (`pyproject.toml` `fail_under`).

## 6. Environments

| Environment | Browsers and devices | Data and controls |
| --- | --- | --- |
| local and CI (`make test`, `make test-integration`) | none: the story has no screen | synthetic data only (`seed/`, `CONSTRAINTS.md` section 2); Postgres from `docker-compose.yml` for the four integration cases; log capture for TC-0023 and TC-0024 |

## 7. What QA raised while writing this

- [undefined] Q-003 gives no similarity threshold for names. TC-0001 to TC-0005 use values that are clearly equal or clearly different, so none sits near any threshold. A near-miss spelling (one letter changed) has no case until the threshold is set.
- [assumption] Dates are normalised to one format before an exact comparison (Q-011). TC-0007 assumes `04/03/2006` is day first and means 4 March 2006; the day-month order of other print formats is not covered.
- [assumption] TC-0014 assumes surrounding whitespace on a roll number is ignored. REQ-015 says only "exact". If exact means byte for byte, TC-0014 changes to a mismatch.
- [undefined] AC-US-00-004-3 does not say whether letter case matters in a roll number. No case asserts it; the roll numbers in the seed are all upper case.
- [undefined] A subject missing from a marksheet extraction is not covered by the PRD; TC-0018 assumes a mismatch, not a skipped field.
- [assumption] AC-US-00-004-5 says fields a document type does not carry are skipped, but the field map is open (Q-017). TC-0019 and TC-0021 take the map from the seed: an ID proof carries name and date of birth; a transfer certificate adds father's name.
- [risk] No comparison code exists, so every case is `planned` and none was run. The cases were written from the backlog, not from code.
- [risk] TC-0023 asserts the logs hold none of three values. A log line built from a whole object (for example a dict of the application) would leak them; the case catches only the three values it names.

## 8. How the gate is run

```
python3 "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/test-cases/scripts/cases_check.py" --story US-00-004 --plan docs/testing/test-plan.md
```

The case table passed this gate with 0 problems on 2026-10-05 (the two lines above). The `--steps` flag is left off because the story has no manual or e2e case, and the gate rejects an empty step table. The `--plan` check has not been run yet.
