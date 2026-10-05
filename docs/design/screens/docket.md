# Screen designs: Docket (round 1)

Target: react-shadcn, screens as code. Each screen is a view in `frontend/src/features/<feature>/components/`
and a `screens/S-nn-*.screen.tsx` that renders every state from fixtures. Open them with
`cd frontend && pnpm dev`, then `http://localhost:5173/__design` (the index) or
`/__design/S-07?state=low%20confidence&theme=dark&chrome=0`. Direction: 1-instrument-panel (DESIGN.md),
light and dark, desktop and phone. Nothing here has been seen in a browser: no screenshot was taken.

Sources: flows `docs/design/flows/docket/flows.md` (v1, same day as the PRD), the contract
`api/openapi.yaml`, ADRs 0001 to 0011, tokens `frontend/src/index.css` (from `docs/design/tokens.json`).

## Screens

| Id | Screen | View | Phone arrangement | Shortcuts |
| --- | --- | --- | --- | --- |
| S-01 | Sign in | `auth/SignInView` | one column, 48 px primary button full width | Enter submits |
| S-02 | Dashboard | `reports/DashboardView` | three tiles stack, the role's primary action first | none |
| S-03 | Import applications | `intake/ImportView` | drop area, then the button, then the refused rows in a scrolling table | none |
| S-04 | Applications | `intake/ApplicationsView` | table becomes a card per application, two actions per card | none |
| S-05 | Upload documents | `intake/UploadView` | 48 px picker, then one card per document | none |
| S-06 | Review queue | `review/QueueView` | rows stack: ref and status, name, flag, then "Open" | `j` `k` move, `n` or "Review next" opens the oldest |
| S-07 | Compare application | `review/CompareView` | the document first with its outline, then one card per field, failed fields first | `j` `k` field, `d` decide, `?` shortcuts |
| S-08 | Decision dialog | `review/DecisionDialogView` | full-width dialog, the three choices stack | `a` `c` `r` choose, Esc closes |
| S-09 | Export verified list | `reports/ExportView` | the count above a full-width 48 px button | none |

Desktop: S-07 is two columns (fields left, the document sticky on the right); S-04 is a table; S-06 is a
ruled list with a selected row. Shortcuts never fire while a text field has focus and stop when a
modifier is held (`frontend/src/lib/hotkeys.ts`).

## States

Every state in the flows (section 2) is a key of its screen's `states`, with the flows' copy word for word
(`gallery_check.py` was not run, so this is by my reading). Beyond the flows: S-02 "success: verifier"
(the verifier's primary action is the queue), and S-08 "success" shows the dialog closed with the saved
line. Not drawn, because the flows mark them n/a: partial on S-01, S-08 and S-09.

## Gaps raised (each needs an owner)

1. **Confidence cutoff.** `ConfidenceBadge` compares with the provisional 0.9804 (ADR-0005). The API already
   returns `review_reason` on each field; the badge should read `review_reason === "low_confidence"` so the
   configured cutoff is the only source. Owner: backend lead rotation.
2. **Image size.** The OCR box is in pixels of the stored image, but the `Document` schema has no width or
   height, so the viewBox is a fixture constant (720 by 440). Add `width` and `height` to `Document`.
   Owner: backend lead rotation.
3. **Why flagged.** The queue row shows a reason ("Name does not match"), but the list response carries
   none. Add a short `flag` to the application list item. Owner: backend lead rotation.
4. **Stale decision.** The dialog's conflict state needs the ETag from `getApplication` kept by S-07 and sent
   as `If-Match`. Owner: frontend lead rotation.
5. **Reprocess.** S-05 shows "Reprocess" because `reprocessDocument` is in the contract; the route does not
   exist yet (story PS-12 in `docs/product/proposed-stories.md`). Owner: product owner.
6. **Shell navigation.** `RootLayout` has the product name and the theme toggle only. The destinations
   (Dashboard, Import, Applications, Review queue, Export) are plain text in the designs, not links, because
   the routes do not exist yet. Owner: frontend lead rotation.

## Not run

`gallery_check.py`, `contrast.py`, the motion gate, the frontend tests, the type check and the browser
screenshots. See `docs/design/DESIGN.md` section 9.
