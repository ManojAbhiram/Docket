# Motion: Docket

Approach: calm and purposeful, in the deep teal direction. Entrances, counts, hover lift, progress,
status changes, route changes and dialogs move; the screens a verifier works fast stay quiet. Tokens:
`docs/design/tokens.json` (`motion.*`), bound in `frontend/src/index.css` as `--duration-*`,
`--ease-*`, `--stagger`, `--rise` and `--lift`. Only `transform` and `opacity` move; colour may fade.
Under `prefers-reduced-motion` every animation and transition ends at once (0.01 ms, no delay, no
hover travel), and scripted motion reads `prefersReducedMotion()` in `frontend/src/lib/motion.ts`.

## Rules

1. Only `transform` and `opacity` move. Layout properties never animate. A raised shadow is a
   pseudo element whose opacity fades, never a box-shadow transition.
2. Enter with the data. The dashboard count starts in the frame the real counts first render, never
   over placeholder tiles.
3. A poll or refresh never replays an entrance. Entrances run on mount, and rows and tiles are keyed
   by id, so a refresh that keeps them mounted plays nothing. The count animates from its last
   settled value. A status badge pops only when its status really changed (`useChangeCount`).
4. The final figure is the formatter's output for the real value, not the last interpolated number.
5. No animation touches text while it is read, and no live region wraps an animated number.
6. Nothing loops and nothing autoplays. The reading fill climbs once and waits.
7. Verifier screens are quiet: the review queue and the compare view use a fade only (`.enter-quiet`),
   no wave. Selection moves (`j`, `k`, click) and the OCR box change instantly.
8. Entrance animations use fill-mode `backwards`, so a finished animation never holds a hover transform.

## Applied in this product

| Where | Pattern | Class or code | Duration and easing | Reduced-motion path |
| --- | --- | --- | --- | --- |
| Route change (`RootLayout`) | page fades up 6 px, keyed by path | `.route-enter` | `--duration-base`, `--ease-enter` | ends at once |
| S-02 Dashboard tiles | staggered rise (40 ms per step, at most 8 steps), count up, hover lift | `.enter`, `staggerStyle(i)`, `CountUp`, `.lift` | 400 ms rise, 400 ms count, 150 ms lift | final figure and end state at once |
| S-04 Applications rows | staggered rise on table rows and phone cards | `.enter`, `ListRow index` | `--duration-slow` | at once |
| S-05 Upload rows | staggered rise; progress fill while a document is read, completes when read | `ReadProgress`, `.read-fill` | fill climbs to 90 percent over 12 s then waits; completes in `--duration-base` | fill shows its end state |
| Status badges (`StatusBadge`, upload badges) | pop (scale 0.9 to 1 with fade) when the status changes | `.badge-changed` | `--duration-base` | at once |
| S-01 Sign in | card rises once | `.enter` in `AuthShell` | `--duration-slow` | at once |
| S-09 Export card | rise and lift | `.enter`, `.lift` | as above | at once |
| Notices | fade in | `.enter-quiet` | `--duration-fast` | at once |
| S-06 Review queue rows | fade only, no wave | `.enter-quiet` | `--duration-fast` | at once |
| S-08 Decision dialog, shortcuts dialog | fade, small zoom and 8 px rise; reverse on close | `DIALOG_PANEL` | `--duration-base`, `--ease-enter` | at once |
| Buttons | 2 percent press | `button:active` | `--duration-fast` | none |

## Not animated on purpose

- Row selection in the compare view and the queue, hover fills on rows, focus rings: instant, because
  these answer a key press or a pointer and delay would slow a verifier who is working fast.
- The OCR box on the document image: it moves to the next field instantly.
- Toasts and status text carry their meaning in words.

## Tests

- `src/lib/motion.test.ts`: stagger steps and delay, including the reduced-motion path.
- `src/design/motion-contract.test.ts`: every keyframe moves only transform and opacity, transitions
  fade only colour, entrance classes fill backwards, and the reduced-motion rule ends animation,
  transition, delay and hover travel.
- `src/components/CountUp.test.tsx`, `StatusBadge.test.tsx`, `ReadProgress.test.tsx`.

## Not run

The animations have not been judged by eye beyond the browser check recorded in
`docs/progress/NOTASK-9.md`; jsdom does not run CSS animation.
