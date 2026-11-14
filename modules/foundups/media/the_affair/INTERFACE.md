# Interface

The Sprint 1 prototype is a static client-only interface.

## State

`activeChapter: 0..6`

## Inputs

- chapter button `1..7`;
- previous/next controls;
- horizontal or vertical swipe beyond the movement threshold;
- arrow keys;
- number keys `1..7`.

## Outputs

- one active background plate;
- chapter number, era, title, line, and evidence labels;
- `aria-current="step"` on the active chapter.

There is no API, identity, storage, payment, or write surface in Sprint 1.
