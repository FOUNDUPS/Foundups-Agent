# Interface

The Sprint 1 prototype is a static client-only interface.

## State

`activeChapter: 0..6`

## Inputs

- horizontal or vertical swipe beyond the movement threshold;
- tap left/right edge for previous/next;
- double-tap the center poster to flip front/back;
- arrow keys;
- `Enter`/`Space` on the focused center card to flip front/back;
- movie-ticket CTA.

## Outputs

- one art-directed background plate selected from the phone/desktop set;
- one active scalable center-poster image;
- live title, chapter number, season title, and fictionalized-concept disclosure;
- ephemeral front/back state for the active center card;
- live HTML prospectus back with documented-history framing, dramatized question, principal players, and opening/finale pitch;
- an accessible current-state announcement without a persistent visible `1..7` selector;
- navigation to the existing FoundUps member/login owner when the ticket CTA is activated.

There is no new API, identity, storage, payment, entitlement, or write surface in Sprint 1. Flip state is ephemeral client state. The ticket CTA is navigation only and grants no access.
