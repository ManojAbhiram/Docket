# Component contract: Docket

Each entry names the component in `frontend/src/components/ui` (shadcn, new-york) or the feature
component to add, its variants and its states. A need no variant covers becomes a variant here, not
a one-off class in a feature. Tokens: `docs/design/tokens.json`. Guide: `docs/design/DESIGN.md`.

## Button
- Component: `components/ui/button.tsx`
- Variants: primary (the accent, one per screen), secondary, ghost, destructive (reject)
- Sizes: default 36 px on desktop, large 48 px on phone and on S-03 and S-05
- States: rest, hover, active, focus-visible, disabled, loading
- Label: a verb and a noun, kept through the flow ("Import applications" then "Importing")

## Input, Textarea, Select
- Component: `components/ui/input.tsx`, `textarea.tsx`, `select.tsx`
- Variants: default
- States: rest, hover, focus-visible, filled, invalid, disabled
- Rules: a visible label above, never a placeholder alone. The border is `input` (3:1). An error sits
  under the field with its reason and keeps what was typed.

## Table
- Component: `components/ui/table.tsx`
- Variants: default (dense, 14 px), numeric columns right-aligned with tabular figures
- States: loading (skeleton rows), empty, populated, row hover, row selected, row focused
- Rules: flat, 1 px row borders, no shadow. The row is a link target at least 44 px tall on a phone.

## StatusBadge
- Component: `components/status-badge.tsx` (feature component, built on the badge)
- Variants: verified, needs_review, missing_documents, rejected
- States: static
- Rules: a word and a shape, never colour alone. Verified is a tick on success, Needs review a flag on
  warning, Missing documents a dash on info, Rejected a cross on danger.

## ConfidenceBadge
- Component: `components/confidence-badge.tsx`
- Variants: ok (at or above the cutoff), low (below it), none (no confidence returned)
- States: static
- Rules: the percentage in the badge, with the word "Low" when below the cutoff. Tabular figures.

## FieldRow
- Component: `components/field-row.tsx`
- Variants: match, mismatch, low_confidence, not_extracted, skipped
- States: rest, hover, selected, focus-visible
- Rules: application value, document value, a match mark with a word, a confidence badge. Selecting
  the row draws its OCR box on the image.

## DocumentImage
- Component: `components/document-image.tsx`
- Variants: with boxes, without boxes
- States: loading, loaded, error, zoomed
- Rules: the box is drawn from the field's x, y, width and height in pixels of the stored image,
  scaled with the image, in the accent colour with a 2 px outline; a mismatch box is danger.

## Dialog
- Component: `components/ui/dialog.tsx`
- Variants: default, decision
- States: closed, opening, open, submitting, error
- Rules: focus moves into the dialog, returns to the trigger on close, Esc and the Cancel button
  both close it. An overlay is the only place elevation 3 appears.

## FileDrop
- Component: `components/file-drop.tsx`
- Variants: default
- States: rest, drag-over, uploading, error
- Rules: 48 px "Choose files" button inside a drop area at least 96 px tall. Each file is its own row.

## Kbd
- Component: `components/ui/kbd.tsx`
- Variants: default
- States: static
- Rules: shows a shortcut key in the shortcuts dialog and beside a control that has one.

## Toast
- Component: `sonner` through `components/ui/sonner.tsx`
- Variants: success, error
- States: entering, visible, leaving
- Rules: a decision toast has no Undo, because the decision log is append-only.
