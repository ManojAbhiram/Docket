# Docket design system

Version 1, 2026-10-05. Direction: `1-instrument-panel` (`docs/design/variants/docket/README.md`,
`approved.json`), applied on the instruction "does everything done" in place of a stated choice.
Tokens: `docs/design/tokens.json`, written by `scripts/make_tokens.py`. The CSS binding is
`frontend/src/index.css`, written by hand from the tokens in shadcn's names. Components:
`docs/design/components.md`. Screens: `docs/design/screens/docket.md`. Themes: light and dark,
section 7.

## 1. What the product is for

Admissions staff import applications and upload scans. A machine reads each document, and a
verifier decides the ones it could not settle. The memorable thing: **the document and the
application side by side, and the wrong field obvious in seconds.** Every choice below serves the
verifier at a desk all day, and the intake screens must still work on a phone.

## 2. Colour

Cool graphite neutrals (hue about 250, low chroma), one teal accent whose job is the primary action
and where you are, and four status colours that are never used alone: every status carries a word.

| Role | Light | Dark | Used for |
| --- | --- | --- | --- |
| bg | `#f3f5f7` | `#0f1318` | the page |
| surface | `#ffffff` | `#171d24` | tables, panels |
| surface-raised | `#ffffff` | `#1f2730` | a row on hover, a popover trigger |
| overlay | `#ffffff` | `#26323e` | dialogs, menus |
| text | `#14181d` | `#e6eaee` | body |
| text-muted | `#4a5560` | `#a3afbb` | secondary text, labels |
| border | `#d3d9df` | `#2a343f` | separators (decorative) |
| border-strong | `#7c8896` | `#6b7886` | field edges, 3:1 |
| accent | `#0f766e` | `#5eead4` | primary button, link, current item, focus ring |
| primary tile | `#115e59` | `#134e4a` | primary workflow tile; white text in light, off-white in dark |
| success | `#1e6b3a` | `#6fcf97` | Verified, Match |
| warning | `#8a5300` | `#f0b44c` | Needs review, Low confidence |
| danger | `#b3261e` | `#f0857d` | Mismatch, Rejected, destructive |
| info | `#4a5560` | `#a3afbb` | Missing documents |

Status meaning is paired with a word and a shape (a tick, a flag, a cross, a dash), never colour
alone. The dark theme steps surfaces up in lightness, uses off-white text and a lighter, less
saturated accent. Contrast, measured by `contrast.py` on `tokens.json` (not run in the session that
wrote this): text pairs 4.5:1, focus ring and field edges 3:1.

## 3. Type

| Role | Face | Size | Weight | Use |
| --- | --- | --- | --- | --- |
| display, title | IBM Plex Sans Condensed | 25 and 20 px | 600 | headings, tile numbers |
| body | IBM Plex Sans | 16 px | 400 | reading text, form fields |
| label | IBM Plex Sans | 14 px | 600 | table headers, badges, buttons |
| code | IBM Plex Mono | 14 px | 400 | application refs, field values, ids |

Scale 1.25 (16, 20, 25), plus 14 for dense data. Two weights, 400 and 600. Figures use tabular
numerals wherever they align. Line height 1.5 for body, 1.15 for headings. The faces are Fontsource
packages, self-hosted (the CSP allows `font-src 'self'`); they are proposed and not installed, so
the fallbacks (Arial Narrow, system-ui, ui-monospace) render until they are.

## 4. Space, shape, elevation

Space on 8, with one half step of 4: 4, 8, 16, 24, 32, 48, 64. Radius is a hierarchy: control 4 px,
container 6 px, overlay 8 px. Elevation: 0 flat, 1 a pressable at rest, 2 a pressable hovered, 3 an
overlay. **A static block never carries a shadow.** Tables, panels and the compare view are flat and
separated by a 1 px border.

## 5. Motion

One orchestrated moment per screen, 80 to 700 ms, transform and opacity only, ease-out entering and
ease-in leaving. The dashboard counts rise once; a document row settles when it is stored; a dialog
opens with a short fade and a 4 px rise. Under `prefers-reduced-motion` every animation becomes a
state change (the rule is in `frontend/src/index.css`). Motion is specified in
`docs/design/motion.md`.

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

## 8. What was decided here that the direction left open

- The four status colours and `info` as a neutral slate for Missing documents, so the accent blue
  keeps one job.
- The dark `popover` and overlay surfaces step up to `#26323e`.
- Table and badge text at 14 px: data, not body copy; contrast still 4.5:1.

## 9. Known gaps

- The faces are not installed (an AGENTS.md rule 7 decision for the engineer).
- `design-lint` is not installed, so a stray hex or off-scale value is caught only in review.
- The contrast measurement, the schema check and the generated system page have not been run.
