# Design review: Docket screens (round 1 of 1)

Target: `docs/design/screens/docket.md`, the nine screens S-01 to S-09 in the design gallery, direction
1-instrument-panel. **Method: source only.** No browser, screenshot, `pairs.py`, `evidence.py` or test ran
in the session that wrote this review, so every finding cites a file and line and no width or theme was
seen. Evidence: `source only (no browser)`. Colour: not measured by a script; the 31 colour pairs of
`frontend/src/design/contrast.test.ts` are the measurement to run. Repo check: not run.

**Verdict: not ready for a client look.** The approved faces (IBM Plex) are named in the CSS but not
installed, so every screen would render in the fallback fonts, which is not the look that was approved.
Nothing has been seen on screen. Install the faces, run the checks and take the screenshots first.

## First impression (from the source)

S-07 Compare application. Communicates: the document and the application side by side. Eye lands on: 1 the
reference and status badge in the header, 2 the "Decide" primary button, 3 the first (failed) field row.
The page's job is to judge a field, so the failed fields listed first and the dashed outline on the page
match it. S-02 Dashboard: three status tiles with a word and a shape each, then the role's primary action.

## Scores

| Category | Score | Weight | Evidence |
| --- | --- | --- | --- |
| hierarchy | 9 | 10% | one primary action per screen (`CompareView.tsx`, `QueueView.tsx`, `DashboardView.tsx`); squint test not run |
| typography | 6 | 15% | faces named, none loaded: `index.css` lines for `--font-sans`, `--font-display` (high, -3); table and badge text at 14 px (`ApplicationsView.tsx`, `StatusBadge.tsx`, medium, -1) |
| spacing | 9 | 10% | arbitrary values `text-[25px]`, `grid-cols-[9rem_1fr_1fr_auto_auto]`, `aspect-[18/11]` (`PageHeader.tsx`, `QueueView.tsx`, `DocumentImage.tsx`, medium, -1) |
| colour | 8 | 10% | `components/ui/button.tsx` uses `text-white`, `bg-primary/90` and `dark:bg-destructive/60`: composites not measured (medium, -1); the unmeasured pairs (medium, -1) |
| states | 9 | 10% | every flows state is a key of its screen; the hand-built queue and card rows have no hover state (`QueueView.tsx`, medium, -1) |
| responsive | 9 | 10% | table to card at `md` in `ApplicationsView.tsx` and `CompareView.tsx`; 375 px layout not seen (-1 unverified) |
| copy | 7 to 10 | 5% | S-05 showed one record as SYN-APP-004 with a failed document while S-06, S-07 show it fully read (high, -3). **Fixed in this round**, so 10 |
| accessibility | 9 | 10% | the three decision choices are `role="radio"` buttons with no arrow-key movement (`DecisionDialogView.tsx`, medium, -1) |
| motion | 9 | 5% | `transition-all` in `components/ui/button.tsx` line 7 (medium, -1); the reduced-motion rule is present (`index.css`) |
| consistency | 8 | 10% | hand-built bordered rows beside the library (`ApplicationsView.tsx` cards, `QueueView.tsx`, `UploadView.tsx`, `CompareView.tsx` field cards, medium, -1); `shadow-none` repeated on each `Card` (`DashboardView.tsx`, `ExportView.tsx`, medium, -1) |
| slop | 10 | 5% | no gradients, no icons in circles, no coloured left borders, status pills only |

Overall: 8.3 (B) before the fix, 8.5 (B) after it. The gate wants 8.0 and no category below 7: **typography is
6, so it does not pass.**

## Findings

| # | Category | Impact | Where | Change X to Y because Z |
| --- | --- | --- | --- | --- |
| 1 | typography | high | `frontend/src/index.css` (`--font-sans`, `--font-display`, `--font-mono`) | Install `@fontsource/ibm-plex-sans-condensed`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono` and import them in `main.tsx`, because the approved direction has never rendered; the CSP already allows self-hosted fonts. A dependency decision for the engineer |
| 2 | copy | high | `S-05-upload.screen.tsx` | Show SYN-APP-007 (two read, one failed) instead of SYN-APP-004, because the same record showed two different document states on two screens. **Applied** |
| 3 | consistency | medium | `ApplicationsView.tsx`, `QueueView.tsx`, `UploadView.tsx`, `CompareView.tsx` | Extract one `ListRow` (border, `bg-card`, padding, hover) because four screens hand-build the same row |
| 4 | consistency | medium | `DashboardView.tsx`, `ExportView.tsx` | Make `components/ui/card.tsx` flat (no shadow) once, because the design says a static block never carries a shadow and each instance repeats the override |
| 5 | accessibility | medium | `DecisionDialogView.tsx` | Give the radiogroup arrow-key movement (a roving tabindex) or use a real radio-group component, because `role="radio"` promises it |
| 6 | colour | medium | `components/ui/button.tsx`, `badge.tsx` | Replace `text-white`, `/90` hover fills and `dark:…/60` with tokens (`text-destructive-foreground`, a hover token) and measure each composite, because they are not on the contrast test. Not used by any screen yet |
| 7 | motion | medium | `components/ui/button.tsx` line 7 | `transition-all` to `transition-[color,background-color,box-shadow]`, because it can animate layout by accident |
| 8 | typography | medium | table cells and badges | 14 px data against the 16 px body floor is a deliberate choice in DESIGN.md section 3: confirm it with the product owner, or raise it |
| 9 | states | medium | `QueueView.tsx`, row | Add a hover fill (`bg-accent/…` as a token) because the list rows are pressable targets with no hover |
| 10 | spacing | polish | `PageHeader.tsx`, `QueueView.tsx`, `DocumentImage.tsx` | Move `25px` and the grid template into tokens or theme variables |
| 11 | motion | polish | `CountUp.tsx` | DESIGN.md and the direction README say 320 ms; the code reads `--duration-slow` (400 ms). Pick one |
| 12 | colour | polish | shadcn components | They draw a 3 px `ring-ring/50` beside the global 2 px outline, so a focused control shows two rings; keep one |

## Decisions for the owner

- Fonts: install the Plex faces (finding 1), or choose faces that are already bundled. Both change the look
  that was approved on the board, so this is the engineer's decision under AGENTS.md rule 7.
- Data type size: 14 px for table and badge text (finding 8), against the doctrine's 16 px body.

## Not run

`pairs.py`, `evidence.py`, `snapshot.mjs`, `gallery_check.py`, the frontend tests, the type check,
`make check`, and any browser look at 375, 768 and 1440 px in light and dark.

## Re-score

8.3 to 8.5 (+0.2) from fix 2, by my reading of the source.
