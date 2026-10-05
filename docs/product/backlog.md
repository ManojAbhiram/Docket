# Backlog: Docket

PRD: docs/product/PRD.md   Questions: docs/product/questions.md   Built: 2026-10-04

Code check: the repository holds only the scaffold (health endpoints, config, error handling, an empty `app/domain` and `app/db`). No domain rule from the PRD exists in code yet, so every rule below is new work and no statement contradicts code.

## Story index

| Story | Epic | Title | Persona | Priority | Points | Covers | Depends on |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-00-001 | EP-01 | Import applications from a CSV file | Admissions staff | Must | 5 | REQ-001, REQ-002, REQ-003 | none |
| US-00-002 | EP-01 | Upload scanned documents for an application | Admissions staff | Must | 5 | REQ-004, REQ-005, REQ-006 | US-00-001 |
| US-02-001 | EP-02 | Route all OCR and vision calls through one gateway | Engineering team | Must | 8 | REQ-030, REQ-031, REQ-032, REQ-033, REQ-034, REQ-044 | none |
| US-00-003 | EP-02 | Read the type and fields of an uploaded document | Admissions staff | Must | 8 | REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-044 | US-00-002, US-02-001 |
| US-00-004 | EP-02 | Compare extracted fields with the application | Verifier | Must | 5 | REQ-012, REQ-013, REQ-014, REQ-015, REQ-016 | US-00-003 |
| US-00-005 | EP-02 | Set each application's status automatically | Admissions staff | Must | 5 | REQ-017, REQ-018, REQ-019, REQ-020 | US-00-004 |
| US-00-011 | EP-03 | Sign in as staff or verifier | Admissions staff | Should | 5 | REQ-021, REQ-027 | none |
| US-00-006 | EP-03 | Review a flagged application side by side | Verifier | Must | 5 | REQ-021, REQ-022 | US-00-005, US-00-011 |
| US-00-007 | EP-03 | Decide a flagged application | Verifier | Must | 5 | REQ-023, REQ-024, REQ-025, REQ-026, REQ-027 | US-00-006 |
| US-00-010 | EP-03 | See field crops beside the values | Verifier | Could | 3 | REQ-046 | US-00-006 |
| US-00-008 | EP-04 | See counts of applications by status | Admissions staff | Must | 3 | REQ-028 | US-00-005 |
| US-00-009 | EP-04 | Export the verified list to CSV | Admissions staff | Must | 2 | REQ-029 | US-00-005 |
| US-02-003 | EP-05 | Seed synthetic applications and documents | Engineering team | Must | TBD | REQ-040, REQ-041, REQ-042, REQ-043 | none |
| US-02-002 | EP-05 | Choose the engine by measurement | Engineering team | Must | 2 | REQ-035, REQ-036 | US-02-001, US-02-003 |
| US-02-004 | EP-05 | Report extraction accuracy | Engineering team | Must | 1 | REQ-037, REQ-038, REQ-039 | US-02-002, US-02-003 |

## Hours by discipline

Not written: tasks were not requested, so there is no tasks.md and no gate "tasks:" line.

## EP-01 Get applications and documents in

Goal: staff have every application and its scanned documents in the system.
Covers: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006

### US-00-001 Import applications from a CSV file

Epic: EP-01   Priority: Must   Points: 5
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-001, REQ-002, REQ-003   Judgement: merged from REQ-001, REQ-002, REQ-003

**Narrative.** As admissions staff, I want to import applications from a CSV file, so that every application exists before its documents arrive.

**Why it matters.** B1: nothing can be compared or verified until the application record exists. All later stories wait on it.

**From the PRD.**
- REQ-001: "The system lets staff import student applications from a CSV file."
- REQ-002: "The CSV import reads application id, name, father's name, date of birth, board, roll number, marks by subject and category."
- REQ-003: "The system rejects a malformed CSV row and shows the reason for the rejection."

**Preconditions.**
- Staff are signed in (US-00-011).

**Acceptance criteria.**

- AC-US-00-001-1. Given a CSV with the eight listed columns and valid rows, when staff import it, then one application per row exists holding those values.
  Covers: REQ-001, REQ-002
- AC-US-00-001-2. Given a CSV row with a missing required value or an unreadable date, when staff import it, then that row is not created and its row number and reason are shown.
  Covers: REQ-003
- AC-US-00-001-3. Given a CSV with valid and malformed rows, when staff import it, then the valid rows are created and the malformed rows are listed with reasons.
  Covers: REQ-003

**Not in this story.**
- Bulk upload of documents over 100 files (PRD non-goal; Q-008).
- Handling of a duplicate application id (not stated in the PRD; raise before build).

**Depends on.**
- none

**Assumptions.**
- Sign-in exists for staff (Q-013).

**Tasks.** Not written.

### US-00-002 Upload scanned documents for an application

Epic: EP-01   Priority: Must   Points: 5
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-004, REQ-005, REQ-006   Judgement: merged from REQ-004, REQ-005, REQ-006

**Narrative.** As admissions staff, I want to upload scanned documents against an application, so that the system can read them.

**Why it matters.** B1: documents are the evidence the automatic check reads; without uploads no application can be auto-verified.

**From the PRD.**
- REQ-004: "The system lets staff upload scanned documents against an application."
- REQ-005: "The system accepts uploads in JPG, PNG and PDF formats."
- REQ-006: "The system rasterises the first page of an uploaded PDF locally."

**Preconditions.**
- The application exists (US-00-001).

**Acceptance criteria.**

- AC-US-00-002-1. Given an application, when staff upload a JPG, PNG or PDF file, then the file is stored against that application.
  Covers: REQ-004, REQ-005
- AC-US-00-002-2. Given a file of any other format, when staff upload it, then it is refused with a message that names the accepted formats.
  Covers: REQ-005
- AC-US-00-002-3. Given a PDF of several pages, when staff upload it, then only its first page is rasterised, on this machine, with no network call.
  Covers: REQ-006
- AC-US-00-002-4. Given a document type already uploaded for the application, when staff upload another of that type, then the newer one is used for matching and the older one is kept.
  Covers: REQ-004

**Not in this story.**
- Reading the document (US-00-003).
- Bulk upload over 100 files (PRD non-goal; Q-008).

**Depends on.**
- US-00-001: the application the file belongs to.

**Assumptions.**
- A re-upload replaces the earlier document for matching (Q-010).

**Tasks.** Not written.

## EP-02 Have documents read and decided automatically

Goal: an uploaded document is read once, compared with the application and the application gets a status, with no person involved when everything matches.
Covers: REQ-007 to REQ-020, REQ-030 to REQ-034, REQ-044

### US-02-001 Route all OCR and vision calls through one gateway

Epic: EP-02   Priority: Must   Points: 8
Persona: Engineering team, group 02   Ticket: unassigned
Covers: REQ-030, REQ-031, REQ-032, REQ-033, REQ-034, REQ-044   Judgement: merged from REQ-030, REQ-031, REQ-032, REQ-033, REQ-034; REQ-044 carried as non-functional

**Narrative.** As the engineering team, I want one gateway for every OCR and vision call, so that the engine can change and no call escapes logging, the cap or the replay tests.

**Why it matters.** B3: the engine is chosen by measurement and must be swappable; B2: every call is logged. Nothing that reads a document can ship before it.

**From the PRD.**
- REQ-030: "The system routes all OCR and vision work through one gateway function."
- REQ-031: "The gateway engine is selectable by configuration without changing callers."
- REQ-032: "The gateway logs the engine, latency, outcome and token or unit count of every call, and records the cost as zero."
- REQ-033: "The gateway refuses further calls once the configured call cap is reached."
- REQ-034: "The test suite replays recorded gateway responses, and CI makes no live engine calls."
- REQ-044: "The system sends no real student data to any third-party service."

**Preconditions.**
- none

**Acceptance criteria.**

- AC-US-02-001-1. Given the code base, when the architecture test runs, then it fails if any module outside the gateway imports an engine client.
  Covers: REQ-030
- AC-US-02-001-2. Given two engines configured in turn, when the same caller runs, then it returns the same result shape and no caller code changes.
  Covers: REQ-031
- AC-US-02-001-3. Given any call, when it finishes, then a log entry holds engine, latency, outcome, token or unit count and cost 0.
  Covers: REQ-032
- AC-US-02-001-4. Given the configured cap has been reached, when another call is made, then the gateway refuses it with a clear error and the document goes to Needs review.
  Covers: REQ-033
- AC-US-02-001-5. Given the test suite with the network disabled, when it runs, then every gateway test passes from recorded responses.
  Covers: REQ-034
- AC-US-02-001-6. Given the default configuration, when a document is processed, then the engine runs on this machine and no outbound request carries the document.
  Covers: REQ-044

**Not in this story.**
- Choosing the engine (US-02-002).
- Reading and classifying documents (US-00-003).
- The cap value and whether the count survives a restart (Q-009).

**Depends on.**
- none

**Assumptions.**
- The count persists across restarts (Q-009).
- The engine runs locally by default (Q-015, Q-018).

**Tasks.** Not written.

### US-00-003 Read the type and fields of an uploaded document

Epic: EP-02   Priority: Must   Points: 8
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-044   Judgement: merged from REQ-007, REQ-008, REQ-009, REQ-010, REQ-011; REQ-044 carried as non-functional

**Narrative.** As admissions staff, I want each uploaded document read automatically, so that nobody types its fields by hand.

**Why it matters.** B1: this removes the manual reading that verifiers would otherwise do. B2: the extracted fields are the stored evidence.

**From the PRD.**
- REQ-007: "The system processes phone photos that are noisy, skewed or shadowed."
- REQ-008: "The system makes exactly one gateway call per uploaded document."
- REQ-009: "The gateway call classifies each document as a 10th marksheet, a 12th marksheet or an ID proof."
- REQ-010: "The gateway call returns the document's extracted fields as JSON, each with a confidence."
- REQ-011: "The system routes every low-confidence extracted field to Needs review."
- REQ-044: "The system sends no real student data to any third-party service."

**Preconditions.**
- The document is stored (US-00-002) and the gateway exists (US-02-001).

**Acceptance criteria.**

- AC-US-00-003-1. Given an uploaded document, when it is processed, then exactly one gateway call is made for it.
  Covers: REQ-008
- AC-US-00-003-2. Given the call result, when it is stored, then the document type is a 10th marksheet, a 12th marksheet, an ID proof or unknown, and an unknown type sends the application to Needs review.
  Covers: REQ-009
- AC-US-00-003-3. Given the call result, when it is stored, then the fields are held as JSON and each field has a confidence.
  Covers: REQ-010
- AC-US-00-003-4. Given a field below the configured confidence threshold, when it is stored, then it is marked for Needs review.
  Covers: REQ-011
- AC-US-00-003-5. Given a synthetic phone photo with blur, skew and shadow, when it is processed, then processing completes and every field is either extracted or sent to Needs review, none silently dropped.
  Covers: REQ-007
- AC-US-00-003-6. Given a processed document, when the network is blocked in a test, then processing still completes, so no document left this machine.
  Covers: REQ-044

**Not in this story.**
- The comparison with the application (US-00-004).
- Choosing the engine (US-02-002).
- Cropping fields (US-00-010).

**Depends on.**
- US-00-002: the stored document.
- US-02-001: the gateway.

**Assumptions.**
- "Handled" means processed without failing, with weak fields to Needs review (Q-001).
- The threshold is configured and set from the eval (Q-002).
- The engine's confidence tracks correctness (Q-016); a spike decides this before build.

**Tasks.** Not written.

### US-00-004 Compare extracted fields with the application

Epic: EP-02   Priority: Must   Points: 5
Persona: Verifier, group 00   Ticket: unassigned
Covers: REQ-012, REQ-013, REQ-014, REQ-015, REQ-016   Judgement: merged from REQ-012, REQ-013, REQ-014, REQ-015, REQ-016

**Narrative.** As a verifier, I want each extracted field compared with the application, so that only real mismatches reach me.

**Why it matters.** B1: the comparison decides which applications need a person and which do not.

**From the PRD.**
- REQ-012: "The system compares each extracted field with the corresponding application value."
- REQ-013: "The system compares names by token-sorted similarity against a configured threshold."
- REQ-014: "The system compares dates for exact match."
- REQ-015: "The system compares roll numbers for exact match."
- REQ-016: "The system compares marks for exact match."

**Preconditions.**
- Fields are extracted (US-00-003).

**Acceptance criteria.**

- AC-US-00-004-1. Given a document name with the same words in another order, when compared, then it matches; given a different name, it does not match.
  Covers: REQ-012, REQ-013
- AC-US-00-004-2. Given dates that differ by one day, when compared, then they do not match; given the same date in different print formats, they match after normalising.
  Covers: REQ-014
- AC-US-00-004-3. Given roll numbers that differ by one character, when compared, then they do not match.
  Covers: REQ-015
- AC-US-00-004-4. Given marks that differ by one in any subject, when compared, then they do not match.
  Covers: REQ-016
- AC-US-00-004-5. Given a field that the document type does not carry, when compared, then it is skipped and not counted as a mismatch.
  Covers: REQ-012

**Not in this story.**
- Setting the status (US-00-005).
- The field map itself (Q-017, decided in design).

**Depends on.**
- US-00-003: the extracted fields.

**Assumptions.**
- The name threshold is configured and set from the eval (Q-003).
- Dates are normalised to one format first (Q-011).
- A field map says which document field meets which column (Q-017).

**Tasks.** Not written.

### US-00-005 Set each application's status automatically

Epic: EP-02   Priority: Must   Points: 5
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-017, REQ-018, REQ-019, REQ-020   Judgement: merged from REQ-017, REQ-018, REQ-019, REQ-020

**Narrative.** As admissions staff, I want every application to carry one clear status, so that I know what is done and what needs a person.

**Why it matters.** B1: matching applications are verified without a verifier. B2: the extracted evidence is stored with the Verified status.

**From the PRD.**
- REQ-017: "The system gives each application exactly one status: Verified, Needs review or Missing documents."
- REQ-018: "The system marks an application Verified automatically when all its fields match and stores the extracted evidence."
- REQ-019: "The system does not mark an application Verified unless all its fields match or a verifier has decided."
- REQ-020: "The system flags an application with a field mismatch for a verifier."

**Preconditions.**
- Comparisons exist (US-00-004).

**Acceptance criteria.**

- AC-US-00-005-1. Given every required document present and every compared field matching, when the last comparison finishes, then the status is Verified and the extracted fields are stored as evidence.
  Covers: REQ-017, REQ-018
- AC-US-00-005-2. Given a mismatch or a low-confidence field, when the comparison finishes, then the status is Needs review and the application is flagged.
  Covers: REQ-020
- AC-US-00-005-3. Given a required document type missing, when the status is set, then it is Missing documents.
  Covers: REQ-017
- AC-US-00-005-4. Given a mismatch and no verifier decision, when any caller, including a direct API call, asks for Verified, then the service refuses it.
  Covers: REQ-019
- AC-US-00-005-5. Given any application at any time, when its status is read, then it is exactly one of the three.
  Covers: REQ-017

**Not in this story.**
- A verifier's decision (US-00-007).
- Dashboard counts (US-00-008).

**Depends on.**
- US-00-004: the comparison results.

**Assumptions.**
- Required documents are a 10th marksheet, a 12th marksheet and an ID proof (Q-004).
- A field map decides which fields are compared (Q-017).

**Tasks.** Not written.

## EP-03 Decide flagged applications

Goal: a signed-in verifier works the flagged queue and each application ends with a logged decision.
Covers: REQ-021 to REQ-027, REQ-046

### US-00-011 Sign in as staff or verifier

Epic: EP-03   Priority: Should   Points: 5
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-021, REQ-027   Judgement: supports REQ-021 and REQ-027; no requirement names sign-in itself (Q-013)

**Narrative.** As a staff member or verifier, I want to sign in, so that my actions are mine and each role sees what it should.

**Why it matters.** B2: the decision log must say who decided, which needs a known user.

**From the PRD.**
- REQ-021: "The system lists the flagged applications to a verifier."
- REQ-027: "The system logs every decision with who made it, when, what was decided and the reason."
- The PRD names two roles and a log of "who" but no sign-in itself (see Q-013).

**Preconditions.**
- none

**Acceptance criteria.**

- AC-US-00-011-1. Given a seeded staff account, when the user signs in, then import, upload, dashboard and export are available.
  Covers: REQ-027
- AC-US-00-011-2. Given a seeded verifier account, when the user signs in, then the flagged queue and decisions are available.
  Covers: REQ-021, REQ-027
- AC-US-00-011-3. Given a verifier account, when it calls a staff-only action, then the service refuses it.
  Covers: REQ-021

**Not in this story.**
- Account management and password reset (not in the PRD; raise before build).

**Depends on.**
- none

**Assumptions.**
- Seeded role-based accounts (Q-013).

**Tasks.** Not written.

### US-00-006 Review a flagged application side by side

Epic: EP-03   Priority: Must   Points: 5
Persona: Verifier, group 00   Ticket: unassigned
Covers: REQ-021, REQ-022   Judgement: merged from REQ-021, REQ-022

**Narrative.** As a verifier, I want a queue of flagged applications and each field shown beside its document, so that I can judge a mismatch quickly.

**Why it matters.** B1: verifiers work only the flagged queue, not every application.

**From the PRD.**
- REQ-021: "The system lists the flagged applications to a verifier."
- REQ-022: "The system shows, for each application, the document beside the application value, field by field."

**Preconditions.**
- The verifier is signed in (US-00-011) and applications are flagged (US-00-005).

**Acceptance criteria.**

- AC-US-00-006-1. Given applications with all statuses, when a verifier opens the queue, then only the flagged applications are listed.
  Covers: REQ-021
- AC-US-00-006-2. Given a flagged application, when the verifier opens it, then each field shows the document and the application value side by side.
  Covers: REQ-022
- AC-US-00-006-3. Given a flagged application, when the verifier opens it, then the fields that failed are marked.
  Covers: REQ-022

**Not in this story.**
- The decision itself (US-00-007).
- Field crops (US-00-010).

**Depends on.**
- US-00-005: the flag.
- US-00-011: the signed-in verifier.

**Assumptions.**
- Only verifiers see the queue (Q-013).

**Tasks.** Not written.

### US-00-007 Decide a flagged application

Epic: EP-03   Priority: Must   Points: 5
Persona: Verifier, group 00   Ticket: unassigned
Covers: REQ-023, REQ-024, REQ-025, REQ-026, REQ-027   Judgement: merged from REQ-023, REQ-024, REQ-025, REQ-026, REQ-027

**Narrative.** As a verifier, I want to approve, correct or reject a flagged application, so that every application reaches a final, logged outcome.

**Why it matters.** B2: every decision is logged with who, when, what and why, so the outcome can be defended.

**From the PRD.**
- REQ-023: "The system lets a verifier approve an application."
- REQ-024: "The system lets a verifier correct an application."
- REQ-025: "The system lets a verifier reject an application."
- REQ-026: "The system requires a reason before it accepts a rejection."
- REQ-027: "The system logs every decision with who made it, when, what was decided and the reason."

**Preconditions.**
- A flagged application is open (US-00-006).

**Acceptance criteria.**

- AC-US-00-007-1. Given a flagged application, when the verifier approves it, then its status is Verified and the decision is logged.
  Covers: REQ-023, REQ-027
- AC-US-00-007-2. Given a flagged application, when the verifier corrects an extracted value, then the comparison runs again with the corrected value and the old and new values are logged.
  Covers: REQ-024, REQ-027
- AC-US-00-007-3. Given a rejection with no reason, when the verifier submits it, then the service refuses it.
  Covers: REQ-026
- AC-US-00-007-4. Given a rejection with a reason, when the verifier submits it, then the application is not Verified, leaves the flagged queue and the decision is logged.
  Covers: REQ-025, REQ-027
- AC-US-00-007-5. Given any decision, when the log is read, then the entry holds who, when, what was decided and the reason, and staff and verifiers can read it but not edit it.
  Covers: REQ-027

**Not in this story.**
- Listing and opening applications (US-00-006).

**Depends on.**
- US-00-006: the open application.

**Assumptions.**
- Correct edits the extracted value (Q-005).
- Reject keeps the status Needs review, adds a rejected decision flag and removes the application from the queue (Q-006).
- Staff and verifiers read the log (Q-012).

**Tasks.** Not written.

### US-00-010 See field crops beside the values

Epic: EP-03   Priority: Could   Points: 3
Persona: Verifier, group 00   Ticket: unassigned
Covers: REQ-046   Judgement: story (stretch)

**Narrative.** As a verifier, I want a crop of each field on the document, so that I do not search the whole page.

**Why it matters.** B1: faster review of flagged applications.

**From the PRD.**
- REQ-046: "The system shows field crops of a document (stretch)."

**Preconditions.**
- The engine returns where each field sits on the document.

**Acceptance criteria.**

- AC-US-00-010-1. Given an extracted field with a location, when the verifier opens a flagged application, then a crop of that field is shown beside its value.
  Covers: REQ-046
- AC-US-00-010-2. Given a field with no location, when the verifier opens the application, then the full document is shown and no crop.
  Covers: REQ-046

**Not in this story.**
- Everything else in the review screen (US-00-006).

**Depends on.**
- US-00-006: the review screen.

**Assumptions.**
- Acceptance is set in design (flag on REQ-046).

**Tasks.** Not written.

## EP-04 See and hand over the result

Goal: staff see where every application stands and take away the verified list.
Covers: REQ-028, REQ-029

### US-00-008 See counts of applications by status

Epic: EP-04   Priority: Must   Points: 3
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-028   Judgement: story

**Narrative.** As admissions staff, I want counts by status, so that I know how far the verification has got.

**Why it matters.** B1: the flagged count shows the verifier workload against the 12% example.

**From the PRD.**
- REQ-028: "The dashboard shows the count of applications by status."

**Preconditions.**
- Applications have statuses (US-00-005).

**Acceptance criteria.**

- AC-US-00-008-1. Given applications in all three statuses, when staff open the dashboard, then each status shows its count and the counts equal the stored records.
  Covers: REQ-028
- AC-US-00-008-2. Given a verifier approves an application, when the dashboard is opened again, then the Verified count is one higher and the Needs review count one lower.
  Covers: REQ-028

**Not in this story.**
- Any other chart or measure (not in the PRD).

**Depends on.**
- US-00-005: the statuses.

**Assumptions.**
- none

**Tasks.** Not written.

### US-00-009 Export the verified list to CSV

Epic: EP-04   Priority: Must   Points: 2
Persona: Admissions staff, group 00   Ticket: unassigned
Covers: REQ-029   Judgement: story

**Narrative.** As admissions staff, I want to export the verified list, so that I can pass it on.

**Why it matters.** B1: the verified list is the output of the whole process.

**From the PRD.**
- REQ-029: "The system exports the verified list to CSV."

**Preconditions.**
- Some applications are Verified.

**Acceptance criteria.**

- AC-US-00-009-1. Given Verified and other applications, when staff export, then the CSV holds one row for each Verified application and none for others.
  Covers: REQ-029
- AC-US-00-009-2. Given no Verified application, when staff export, then the CSV holds the header row only.
  Covers: REQ-029

**Not in this story.**
- Exporting other statuses (not in the PRD).

**Depends on.**
- US-00-005: the statuses.

**Assumptions.**
- Columns are application id, name and decision (Q-011).

**Tasks.** Not written.

## EP-05 Choose and prove the engine

Goal: the engine behind the gateway is chosen from measured results on synthetic data and its accuracy is reported.
Covers: REQ-035 to REQ-043

### US-02-003 Seed synthetic applications and documents

Epic: EP-05   Priority: Must   Points: TBD (estimate)
Persona: Engineering team, group 02   Ticket: unassigned
Covers: REQ-040, REQ-041, REQ-042, REQ-043   Judgement: merged from REQ-040, REQ-041, REQ-042, REQ-043

**Narrative.** As the engineering team, I want seeded synthetic applications and noisy documents, so that engines are tested without real student data.

**Why it matters.** B3: the engine is chosen and measured on this set; without it nothing can be scored.

**From the PRD.**
- REQ-040: "The seed produces 20 applications and 30 synthetic documents."
- REQ-041: "The seed renders documents from HTML to PNG with photo noise (blur, skew, shadow)."
- REQ-042: "The seed includes documents that deliberately mismatch their application."
- REQ-043: "The system uses only synthetic documents and applications, in development, tests, evals, demos and screenshots."

**Preconditions.**
- none

**Acceptance criteria.**

- AC-US-02-003-1. Given an empty database, when the seed runs, then 20 applications and 30 documents exist.
  Covers: REQ-040
- AC-US-02-003-2. Given a seeded document, when it is opened, then it is a PNG rendered from HTML with blur, skew and shadow applied.
  Covers: REQ-041
- AC-US-02-003-3. Given the seed, when its ground-truth file is read, then some documents are marked as mismatching their application and the field that differs is named.
  Covers: REQ-042
- AC-US-02-003-4. Given every seeded name, date, roll number and mark, when checked, then each was generated and none appears in a list of real data.
  Covers: REQ-043
- AC-US-02-003-5. Given each seeded document, when its label file is read, then every field value is recorded.
  Covers: REQ-040

**Not in this story.**
- Running any engine on the set (US-02-002).
- Reporting accuracy (US-02-004).

**Depends on.**
- none

**Assumptions.**
- The 30 seeded documents are the 30 eval documents (Q-014).
- Noise levels are set in design (flag on REQ-041).

**Tasks.** Not written.

### US-02-002 Choose the engine by measurement

Epic: EP-05   Priority: Must   Points: 2
Persona: Engineering team, group 02   Ticket: unassigned
Covers: REQ-035, REQ-036   Judgement: merged from REQ-035, REQ-036

**Narrative.** As the engineering team, I want the engine picked from measured results, so that the choice rests on numbers and costs nothing.

**Why it matters.** B3: this replaces the withdrawn OpenRouter model with an engine proven on the same data.

**From the PRD.**
- REQ-035: "The system selects its engine by scoring each free candidate on the same labelled synthetic set, by field type and by document classification, and records latency, hardware needed, the result and the runner-up in a decision record."
- REQ-036: "The system rejects any engine that cannot run for free end to end."

**Preconditions.**
- The gateway (US-02-001) and the seeded set (US-02-003) exist.

**Acceptance criteria.**

- AC-US-02-002-1. Given a candidate list, when it is reviewed, then each candidate is marked eligible or disqualified with the reason before it is run.
  Covers: REQ-036
- AC-US-02-002-2. Given an engine that cannot run free end to end, when candidates are scored, then it is excluded however accurate it is.
  Covers: REQ-036
- AC-US-02-002-3. Given the eligible candidates, when they run on the same labelled set at the same noise levels, then accuracy is recorded per field type (names, dates, roll numbers, marks) and for document classification.
  Covers: REQ-035
- AC-US-02-002-4. Given each candidate, when it runs, then latency per document and the hardware needed are recorded.
  Covers: REQ-035
- AC-US-02-002-5. Given the scores, when the decision record is written, then it names the chosen engine, the numbers and the runner-up.
  Covers: REQ-035
- AC-US-02-002-6. Given each candidate, when it runs, then the record states whether its per-field confidence separates correct from wrong fields.
  Covers: REQ-035

**Not in this story.**
- Reporting accuracy for the final product (US-02-004).
- Lowering the noise as a fallback (Q-016).

**Depends on.**
- US-02-001: the gateway.
- US-02-003: the seeded set.

**Assumptions.**
- The demo runs locally first (Q-018).
- The engine may need a runtime beyond Postgres and pdf2image (Q-015).

**Tasks.** Not written.

### US-02-004 Report extraction accuracy

Epic: EP-05   Priority: Must   Points: 1
Persona: Engineering team, group 02   Ticket: unassigned
Covers: REQ-037, REQ-038, REQ-039   Judgement: merged from REQ-037, REQ-038, REQ-039

**Narrative.** As the engineering team, I want an eval report, so that extraction quality is shown by field.

**Why it matters.** B3: the report is the measured evidence for the chosen engine.

**From the PRD.**
- REQ-037: "The eval reports field-level extraction accuracy on 30 labelled synthetic documents."
- REQ-038: "The eval compares the chosen engine with the runner-up on the same 10 documents."
- REQ-039: "The eval harness runs without any paid service."

**Preconditions.**
- The engine is chosen (US-02-002) and the set exists (US-02-003).

**Acceptance criteria.**

- AC-US-02-004-1. Given the 30 labelled documents, when the eval runs, then it reports accuracy for each field type.
  Covers: REQ-037
- AC-US-02-004-2. Given 10 of those documents, when the eval runs both engines, then it reports the chosen engine and the runner-up side by side.
  Covers: REQ-038
- AC-US-02-004-3. Given a clean checkout with only free tools, when the eval runs, then it completes with no paid service and no card.
  Covers: REQ-039

**Not in this story.**
- Choosing the engine (US-02-002).

**Depends on.**
- US-02-002: the chosen engine and runner-up.
- US-02-003: the labelled set.

**Assumptions.**
- The 10 documents are a subset of the 30 (Q-014).

**Tasks.** Not written.
