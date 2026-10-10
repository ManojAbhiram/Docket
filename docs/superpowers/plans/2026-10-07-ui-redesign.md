# UI redesign, deep teal: plan

Task: NOTASK-9. Branch: `feature/NOTASK-9-UiRedesign`. Spec: piece 3 of
`docs/superpowers/specs/2026-10-07-docket-completion-design.md`.

Goal: the app looks and moves like a finished product. Solid teal tiles (`#0f766e`, `#134e4a`, amber
`#b45309` for needs review) on a cool light ground (`#f2f7f6`), white rows bordered `#d3e4e1`, calmer
motion, and a working dark theme. Frontend only. No new dependency: the IBM Plex faces are already
in `package.json` and imported in `src/main.tsx`.

## Rules kept

- Only `transform` and `opacity` move. Colour may fade; nothing changes size or position by layout.
- `prefers-reduced-motion` makes every animation instant: the global CSS rule plus
  `prefersReducedMotion()` for scripted motion.
- Compare view selection and the OCR box stay instant. The review queue and compare stay quiet.
- A poll or refresh never replays an entrance (`docs/design/motion.md`, rule 3).
- Text pairs 4.5:1, focus ring and field edges 3:1, both themes. 44 px touch targets, no horizontal
  page scroll at 400 px.

## Tasks

1. Plan (this file). Commit.
2. Tokens. Edit the palette in `scripts/make_tokens.py` to teal and regenerate
   `docs/design/tokens.json`, then write the same values into `frontend/src/index.css` (light and
   dark). Add roles for the tiles (`tile`, `tile-deep`, `tile-warn`, `tile-foreground`) and the
   header (`header`, `header-foreground`). Extend `src/design/contrast.test.ts` with the new pairs.
3. Motion layer. `src/lib/motion.ts`: `staggerStyle(index)` (capped) and the stagger constants.
   CSS in `index.css`: keyframes `docket-rise`, `docket-fade`, `docket-pop`, `docket-read-fill`;
   classes `.enter`, `.enter-quiet`, `.lift` (hover lift, shadow on a pseudo element so only opacity
   and transform change), `.route-enter`. Extend the reduced-motion rule. Tests in
   `src/lib/motion.test.ts` and a stylesheet contract test that fails if an animation or transition
   names a property other than transform, opacity or colour.
4. Shared components: `StatusBadge` (colour fade, pop on change only), `ListRow` (lift and
   entrance), `Notice`, `FileDrop` (drag state), new `ReadProgress`, new `AuthShell`, `PageHeader`,
   `Card`, `Button` and `Dialog` classes, and the shell in `app/RootLayout.tsx` (teal header, route
   transition, 44 px targets). Update tests whose assertions name old classes.
5. Screens, small commits: sign in; dashboard tiles with stagger, count-up and lift; applications;
   import; upload with progress fill; export; review queue and compare (quiet); decision dialog.
6. Docs: rewrite `docs/design/motion.md`, update `docs/design/DESIGN.md` and
   `docs/design/components.md` to match what was built.
7. Verify: `make check`, full vitest, accesslint audit on the running pages, browser look at 1280 px
   and 400 px in light and dark. Anything not run is written as "not run".
8. Report in `docs/progress/NOTASK-9.md` (Changed, Verified, Not done, Noticed). Commit.

## Out of scope

Backend (`app/`, `api/`, `evals/`, root `tests/`), new fonts or packages. A sign up screen is not on
this base commit (see the report); the shared `AuthShell` is built so it can adopt the look.
