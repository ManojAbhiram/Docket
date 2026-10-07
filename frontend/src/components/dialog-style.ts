/**
 * The look and motion of a dialog's panel, passed as `className` to DialogContent (the generated
 * component under ui/ is not edited by hand). It opens with a fade, the zoom the component already
 * has and a short rise, and closes with the reverse, on the base duration and the enter easing.
 * Only transform and opacity move. Reduced motion ends both at once through the global rule.
 */
export const DIALOG_PANEL =
  "rounded-xl border shadow-(--shadow-3) duration-(--duration-base) ease-(--ease-enter) data-[state=open]:slide-in-from-bottom-2 data-[state=closed]:slide-out-to-bottom-2";
