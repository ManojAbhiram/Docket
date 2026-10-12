# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Two signed-in roles, chosen at sign-up.
- **Staff** import applications from a CSV, upload each applicant's marksheets and ID proof, watch them being read, and export the verified list.
- **Verifiers** work the review queue: they open an application flagged as needing review, compare each value read from a document against the application's own value beside the page image, and approve, correct or reject.

## Product Purpose
Docket checks admission applications against the documents that support them. Each uploaded page is read, its type is detected (10th marksheet, 12th marksheet, ID proof, transfer certificate), its fields are compared with the application, and the application gets one of three statuses: Verified, Needs review, Missing documents. A person decides anything the machine cannot.

## Positioning
Documents are read on the server's own machine by default (RapidOCR). Sending page images to OpenRouter Vision is opt-in per upload and always announced. Every value a verifier sees is shown next to the application's value and the cropped region of the page it came from.

## Operating Context
Synthetic data only; no real student records (a banner says so on every page). Applications arrive as a CSV with application_id, name, father_name, date_of_birth, board, roll_number, marks_by_subject and category. Uploads are JPG, PNG or PDF, up to 8 MiB each. An application needs a read 10th marksheet, a read 12th marksheet and an ID proof to be Verified; a transfer certificate does not count.

## Capabilities and Constraints
- Routes today: sign in, sign up, applications list, import, upload per application, review queue, application review, dashboard, export.
- Existing design system: deep teal, tokens in `docs/design/tokens.json` and `frontend/src/index.css`, shadcn components including a sidebar, light and dark themes.
- Stack: React 19, TypeScript, Vite, TanStack Router and Query, Tailwind, shadcn/ui.
- Confirmed for this task (NOTASK-22): a sidebar navigation, a new Docket logo and related illustrations drawn as SVG (no image generator is available), plain task names for navigation, and an in-app Help Center for both roles.
- Undecided: a Help Center search box (not requested); real brand assets (none exist; the current mark is a placeholder circle in `public/favicon.svg`).

## Brand Commitments
The name is Docket. The current voice is plain and short: controls name their action, errors name the problem and the recovery. The deep teal palette is established.

## Evidence on Hand
No customers, testimonials, benchmarks or screenshots of real use exist, and none may be invented. Real product facts above come from the codebase and `docs/runbooks/deploy.md`.

## Product Principles
1. A person should never have to know a rule to understand a status: say what is missing and why.
2. The machine proposes; a person decides. Evidence (the page image and the value beside the application's value) is always on screen.
3. Say where data goes. Reading stays on the machine unless the person chooses otherwise.
4. Names say the task, not the module.

## Accessibility & Inclusion
Keyboard operation for every control, visible focus, text contrast of 4.5:1 or better in both themes (already enforced by tests in `frontend/src/design`).
