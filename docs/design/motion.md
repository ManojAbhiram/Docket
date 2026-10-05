# Motion: Docket

Approach: minimal-functional with one intentional moment per page. Tokens: `docs/design/tokens.json`
(`motion.*`), bound in `frontend/src/index.css` as `--duration-*` and `--ease-*`. Only `transform` and
`opacity` move. Under `prefers-reduced-motion` every animation becomes a state change: the CSS rule in
`index.css` shortens all animations and transitions to 0.01 ms, and scripted motion reads
`prefersReducedMotion()` in `frontend/src/lib/motion.ts`.

## Rules

1. One orchestrated moment per page; everything else is a quiet state change.
2. Enter with the data. The dashboard count starts in the frame the real counts first render, never
   over placeholder tiles.
3. A poll or refresh never replays an entrance: the count animates from its last settled value, and
   only the first load counts up from zero.
4. The final figure is the formatter's output for the real value, not the last interpolated number.
5. No animation touches text while it is read, and no live region wraps an animated number.
6. Loops: none. Nothing autoplays.

## Applied in this product

| Where | Pattern | Duration and easing | Reduced-motion path | Test |
| --- | --- | --- | --- | --- |
| S-02 Dashboard tiles | count up once, from the last settled value on change | `--duration-slow` (400 ms), ease out (`countFrame`) | final figure at once, no frames | `src/lib/motion.test.ts`, `src/components/CountUp.test.tsx` |
| S-05 Upload document row | settles into place (4 px rise and fade) | `--duration-base` (240 ms), `--ease-enter` | the CSS rule ends the animation at once, the row is already in its end state | `src/design/screens.test.tsx` renders the rows; the animation itself is not run in jsdom |
| S-08 Decision dialog, shortcuts dialog | shadcn dialog open and close: fade and a small zoom | the component's own classes (`tw-animate-css`) | the same global rule | none; a component default |

## Not animated on purpose

- Row selection in the compare view and the queue, hover states and focus rings: instant, because
  these answer a key press or a pointer and delay would slow a verifier who is working fast.
- The OCR box on the document image: it moves to the next field instantly, so the verifier's eye
  does not follow a slide that says nothing the new position does not.
- Toasts and status changes: they appear and leave without motion; the text carries the meaning.

## Not run

The motion gate (`motion_check.py`), the frontend tests and any browser check have not been run, and
the animation has not been seen in a browser.
