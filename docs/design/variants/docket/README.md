# Design directions: Docket (round 1)

Status: waiting for your choice. `chosen` in `approved.json` is null and no direction is the default.
Date: 2026-10-05. Author: draft, unreviewed.

## What was read

- Screens and copy: `docs/design/flows/docket/flows.md` (9 screens, S-01 to S-09, every state). Read.
- Users: `docs/product/PRD.md` personas through the flows: admissions staff (import, upload, export, dashboard) and verifiers (queue, compare, decide). Desktop and phone web.
- Design system: `DESIGN.md`, `docs/design/tokens.json`: absent. The only tokens are the shadcn neutral defaults in `frontend/src/index.css`. Nothing is frozen, so the directions vary colour, faces, type scale, layout, density and motion.
- Target: react-shadcn (`frontend/components.json`, style new-york, Tailwind v4, Fontsource not installed).
- Screens in the code: none. `frontend/src/app/` has no pages, so the directions cannot be rendered on real screens yet. Nothing was built, run or seen in a browser.

## Constraints found

| Constraint | Source |
| --- | --- |
| fonts must be self-hosted: `font-src 'self'`, no third-party font host | `frontend/nginx.conf` Content-Security-Policy |
| dark follows the `.dark` class or `data-theme="dark"` | `frontend/src/index.css` line 5 |
| motion opt-out for `prefers-reduced-motion` already exists | `frontend/src/index.css` lines 126 to 136 |
| no raw colour in a className, components read tokens by role | `frontend/src/index.css` line 7 |
| no dependency nobody asked for, propose it with the reason | `AGENTS.md` rule 7 |
| nothing from a real student appears on a screen, synthetic data only | `CONSTRAINTS.md`, DPIA |

## Audit of what the directions sit on

- Colours outside tokens: none found in `frontend/src` (no screens exist).
- Default tokens against the 4.5:1 and 3:1 rules, computed by hand from the oklch values, approximate:
  - `--muted-foreground` on `--muted` (light) is about 4.4:1, below 4.5:1.
  - `--ring` (light) is about 2.6:1 against white, below 3:1 for a focus indicator.
  - `--input` and `--border` (light, 0.922 lightness) are about 1.2:1 against white, far below 3:1 for field edges. Dark `--border` is 10% white and has the same problem.
  - The three directions set `--input` and `--ring` to pass 3:1 and keep `--border` for decorative separators only.
- Target sizes: shadcn new-york buttons and inputs are `h-9` (36 px), under the 44 px phone floor. Direction 2 sets 48 px. Directions 1 and 3 need the `design-system` step to set a 44 px minimum on phone.
- Fonts: nothing loads any face. The directions name Fontsource families that are not installed, so every screen renders the fallback stack until they are.
- Privacy: no screen exists to leak a name. The flows forbid showing a value in an import error, and the directions add no content.

## The three directions

### 1-instrument-panel

Serves the verifier at a desk all day (S-06, S-07, S-08). Weak for staff on a phone: dense rows need the status rail to collapse into a bottom bar and the targets raised to 44 px.

- Faces: IBM Plex Sans Condensed (display), IBM Plex Sans (body), IBM Plex Mono (figures, values). Proposed Fontsource packages, not installed.
- Palette (cool graphite): background `#f3f5f7` / dark `#0f1318`, card `#ffffff` / `#171d24`, text `#14181d` / `#e8ecf0`, one accent `#0b6fa4` / dark `#5bb4e5` (the job: the primary action and the current position), destructive `#b3261e` / `#f0857d`. Dark steps up in lightness for elevation and the accent is lighter and less saturated.
- Rhythm: dense rows, 4 px radius, tabular figures, a narrow status rail on the left, hairlines. Type scale ratio 1.25.
- Signature: the status rail, a 4 px column down each row coloured by status and always paired with the status word.
- Motion moment: the dashboard counts rise once from zero (320 ms, ease-out, transform and opacity only). Reduced motion shows the final numbers.

```
+------+-----------------------------------------------+
| rail | S-06  Review queue              14 to review  |
|  *   | SYN-APP-004  Latha Sharma   name mismatch  >  |
|  *   | SYN-APP-011  Ravi Menon     low confidence >  |
+------+-----------------------------------------------+
```

### 2-workshop

Serves the staff member doing intake at a desk or on a phone (S-03, S-05). Weak for the verifier: big margins mean more scrolling through a long field list.

- Faces: Bricolage Grotesque (display), Public Sans (body), IBM Plex Mono (data). Proposed, not installed.
- Palette (warm): background `#f4f1ec` / dark `#1b1814`, card `#fbf9f6` / `#26221c`, text `#231f1a` / `#f1ebe0`, ochre primary `#8f5b00` / dark `#e0a32e` (the job: the one action per band), steel `#3d5a73` / `#a9c1d6` for structure and focus.
- Rhythm: big margins, one object per band (the drop area, then the list, then the result), 14 px radius on the outer surface, 48 px controls. Ratio 1.333.
- Signature: each uploaded file is an object that settles into its band as it is stored, then its row changes from Uploaded to Reading to Read.
- Motion moment: the file row settles into place (480 ms, ease-out, transform and opacity). Reduced motion places it at once.

```
+------------------------------------------------------+
|  Upload documents                                    |
|                                                      |
|   +--------------------------------------------+     |
|   |  Drop files here          [ Choose files ] |     |
|   +--------------------------------------------+     |
|                                                      |
|   10th marksheet   Read on this machine   Read       |
+------------------------------------------------------+
```

### 3-ledger

Serves the admissions lead who reads the counts and exports the list, and anyone printing a page (S-02, S-04, S-09). Weak for the verifier on dense compare screens: a serif display face and ruled rows give less room for the OCR box and badge columns.

- Faces: Spectral (display), Work Sans (body), IBM Plex Mono (data). Proposed, not installed.
- Palette (neutral, one hue): background `#f2f2f0` / dark `#141614`, card `#ffffff` / `#1d201d`, text `#1a1c1a` / `#e9ebe7`, deep green `#1d5c3a` / dark `#7cc79b` (the job: the primary action and the current position), destructive `#9e2b25` / `#ee8c84`.
- Rhythm: ruled rows, right-aligned figures, 2 px radius, one measure of about 66 characters for prose. Ratio 1.25.
- Signature: the totals row, a heavier rule above the sum of Verified, Needs review and Missing documents.
- Motion moment: the total rule draws itself once (600 ms, ease in-out, a transform on a pseudo-element). Reduced motion draws it at once.

```
+------------------------------------------------------+
| Dashboard                                            |
| ---------------------------------------------------- |
| Verified                                      3,812  |
| Needs review                                    611  |
|   of which rejected                              37  |
| Missing documents                               577  |
| ==================================================== |
| Applications                                  5,000  |
+------------------------------------------------------+
```

## Distinctness and the generic default

- Distinctness: 3 of 3 pairs judged distinct (judged, not measured; retries: 0). Display family differs (condensed grotesque, display grotesque, serif), temperature differs (cool, warm, neutral with one hue), layout rhythm differs (dense rows with a rail, one object per band, ruled rows with right-aligned figures). Swapped-headline test: "Review queue" over a ruled serif ledger and "Upload documents" over a dense rail both look wrong.
- Generic default for this brief: a shadcn neutral dashboard, Inter, stat cards in a row, icons in circles, one blue. Lines that matched it were revised: no stat-card row (direction 3 uses a ledger, direction 1 a rail), no Inter, no icon circles. 3 lines revised.
- Hard rules checked by reading: no cream plus serif plus terracotta (direction 3 is grey paper with green), no near-black plus acid green, no purple gradient, no emoji, left-aligned, radius hierarchy per direction, dark steps up in lightness and the accent is desaturated.

## Contrast

Not checked by a script in this session. Hand computation from the hex values (approximate, relative luminance) puts every text pair in the three directions above 4.5:1 and every `--input` and `--ring` above 3:1 in both themes, but that is not a measurement. Run:

```
python3 docs/design/variants/docket/contrast.py
```

It reads the three CSS files and checks 16 text pairs at 4.5:1 and 4 edge pairs at 3:1 per theme. Paste its last line. A pair that fails is fixed in the CSS before you choose.

## How to view

The directions are theme files, not pages. `?variant=<name>` loads one on a dev server (dev only, not in the production bundle):

```
cd frontend && pnpm dev
http://localhost:5173/?variant=1-instrument-panel
http://localhost:5173/?variant=2-workshop
http://localhost:5173/?variant=3-ledger
```

There are no screens to look at yet. The three files change only the shadcn variables, so a screen built later in `screen-design` renders in each, and a dark theme is the `.dark` class or `data-theme="dark"` on any ancestor. Fonts: to see the real faces, install them as Fontsource packages (a dependency decision for you under AGENTS.md rule 7) and import them in `main.tsx`: `@fontsource/ibm-plex-sans-condensed`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`, `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/public-sans`, `@fontsource/spectral`, `@fontsource-variable/work-sans`.

## Recommendation

Recommended: 1-instrument-panel. The product's core job is the verifier comparing a value on a document with a value in an application, field by field, all day, and the hardest screen in the flows is S-07. Tabular figures, a status rail and dense rows serve that screen best. The intake screens (S-03, S-05) need the phone targets of direction 2, which can be taken as a remix: the 48 px controls and the one-object-per-band rhythm on S-03 and S-05 only. Say so in the remix field if you want that.

Tell me: the number you choose (1, 2 or 3), a rating from 1 to 5 for each, and any remix. I will repeat it back in one paragraph before writing it into `approved.json`, then run `design-system`.
