# Docket design system

Version 2, 2026-10-07 (NOTASK-9). Direction: deep teal, on the structure of the approved instrument
panel. Tokens: `docs/design/tokens.json`, written by `scripts/make_tokens.py`. The CSS binding is
`frontend/src/index.css`, written by hand from the tokens in shadcn's names. Components:
`docs/design/components.md`. Motion: `docs/design/motion.md`. Themes: light and dark, section 7.

## 1. What the product is for

Admissions staff import applications and upload scans. A machine reads each document, and a
verifier decides the ones it could not settle. The memorable thing: **the document and the
application side by side, and the wrong field obvious in seconds.** Every choice below serves the
verifier at a desk all day, and the intake screens must still work on a phone.

## 2. Colour

Teal-tinted neutrals, one teal accent for the primary action and where you are, solid teal tiles on
the dashboard, and status colours that are never used alone: every status carries a word and a shape.

| Role | Light | Dark | Used for |
| --- | --- | --- | --- |
| bg | `#f2f7f6` | `#0b1514` | the page |
| surface | `#ffffff` | `#112321` | rows, tables, panels |
| overlay | `#ffffff` | `#234341` | dialogs, menus |
| text | `#0f1f1e` | `#e4efed` | body |
| text-muted | `#3f5a56` | `#9db8b4` | secondary text, labels |
| border | `#d3e4e1` | `#1f3a37` | row and panel borders (decorative) |
| border-strong | `#5a7773` | `#5a7773` | field edges, 3:1 |
| accent | `#0f766e` | `#2dd4bf` | primary button, link, focus ring |
| tile | `#0f766e` | `#115e59` | Verified tile |
| tile-deep | `#134e4a` | `#0d3b38` | Missing documents tile, sign in panel |
| tile-warn | `#b45309` | `#92400e` | Needs review tile |
| header | `#134e4a` | `#0d3b38` | the app bar |
| success | `#1e6b3a` | `#6fcf97` | Verified badge, Match |
| warning | `#8a5300` | `#f0b44c` | Needs review badge, Low confidence |
| danger | `#b3261e` | `#f0857d` | Mismatch, Rejected, destructive |
| info | `#3f5a56` | `#9db8b4` | Missing documents badge |

Text on a tile and on the header is white (light) or near white (dark header). Status meaning is
paired with a word and a shape (a tick, a flag, a cross, a dash). The dark theme steps surfaces up
in lightness and lightens the accent. `frontend/src/design/contrast.test.ts` reads `index.css` and
checks every text pair at 4.5:1 and the focus ring and field edges at 3:1, in both themes, including
the tile and header pairs.

## 3. Type

| Role | Face | Size | Weight | Use |
| --- | --- | --- | --- | --- |
| display, title | IBM Plex Sans Condensed | 25 and 20 px | 600 | headings, tile numbers |
| body | IBM Plex Sans | 16 px | 400 | reading text, form fields |
| label | IBM Plex Sans | 14 px | 600 | table headers, badges, buttons |
| code | IBM Plex Mono | 14 px | 400 | application refs, field values, ids |

Scale 1.25 (16, 20, 25), plus 14 for dense data. Two weights, 400 and 600. Figures use tabular
numerals wherever they align. Line height 1.5 for body, 1.15 for headings. The faces are Fontsource
packages already in `package.json` and imported in `src/main.tsx`, self-hosted (the CSP allows
`font-src 'self'`). The fallbacks (Arial Narrow, system-ui, ui-monospace) render until they load.

## 4. Space, shape, elevation

Space on 8, with one half step of 4: 4, 8, 16, 24, 32, 48, 64. Radius is a hierarchy: control 4 px,
container 8 px (`--radius`), tiles and dialogs 12 px. Elevation: 1 a tile at rest, 3 a tile or card
lifted by the pointer and a dialog. Rows, tables and the compare view are flat and separated by a
1 px border.

## 5. Motion

Calm and purposeful: tiles and rows enter in a short staggered wave, dashboard counts rise, cards and
tiles lift under the pointer, a reading document shows a progress fill, a status badge pops when it
changes, a new route fades up and a dialog opens with a fade and a short rise. Only `transform` and
`opacity` move. The review queue and compare screens stay quiet. Under `prefers-reduced-motion` every
animation is a state change. Full rules and the per-screen table: `docs/design/motion.md`.

## 6. Touch and keyboard

Controls reach 44 px on a phone (the intake screens use 48 px, taken from direction 2). A pointer
target is at least 24 px. Every control has a visible 2 px focus ring offset 2 px. Keyboard
shortcuts never fire while a text field has focus and are listed in the shortcuts dialog (`?`).

## 7. Themes

Light is the base. Dark is designed, not inverted. The switch is the `data-theme` attribute on
`<html>`, set before first paint by `/theme-init.js` from a stored choice (`docket-theme`: `light`,
`dark` or none for the system), so a dark user never sees a light flash. The CSS dark block is
`[data-theme="dark"]` (and `.dark`), and Tailwind's `dark:` variant matches the same selector. This
replaces the old setup in which the class and the variant could name different selectors.

## 8. What was decided here

- Three solid tiles carry the dashboard: teal for Verified, amber for Needs review, deep teal for
  Missing documents. Text on them is white.
- The app bar is deep teal; focus rings inside it are the header's light text colour.
- `info` stays a neutral for the Missing documents badge, so the accent keeps one job.
- No thick one-sided accent borders: a selected row is a fill and a drawn chevron.

## 9. Known gaps

- `design-lint` is not installed, so a stray hex or off-scale value is caught only in review.
- The variants under `frontend/src/design/variants/` are the old directions and keep their own colours.
