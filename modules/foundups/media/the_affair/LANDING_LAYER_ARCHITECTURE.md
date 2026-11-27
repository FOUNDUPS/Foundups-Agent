# Landing Layer Architecture

## Purpose

The new landing sits in front of the existing Site experience. It does not replace, duplicate, or rewrite the deeper work already underway.

## Composition

The landing is assembled from independently editable layers:

1. **Responsive background plate** — one of seven phone plates or seven desktop plates. It contains the environment and the two adult performances only. Alice remains upper-left; Jensen remains upper-right; the center is kept clear.
2. **Center poster front** — one of seven scalable chapter images. It carries the period-specific Alice/memory at which adult Alice is looking.
3. **Live title and season copy** — HTML/CSS, never baked into either image layer.
4. **Prospectus back** — live HTML on the reverse of the center card.
5. **Ticket CTA** — a CSS-rendered movie ticket on the prospectus back, routed to the verified existing FoundUps member/login owner.

This produces fourteen responsive background plates plus seven reusable center images. Copy, sizing, flip behavior, and access routing can change without regenerating the expensive character artwork.

## Interaction contract

- First load: the title peels left-to-right from blur into focus once.
- Swipe or tap an edge: change active season and reset the center card to its front.
- Double-tap the center: flip front/back. Double-tap again: restore front.
- Focus center + `Enter`/`Space`: accessible flip equivalent.
- Desktop arrow keys: previous/next season.
- No persistent visible `1..7` selector.
- Prospectus back: documented-history framing, dramatized question, principal players, opening, finale, and ticket CTA only.
- Ticket CTA: navigation only; existing FoundUps owner performs login/access and must fail closed.

## Asset contract

```text
assets/landing/backgrounds/mobile/season-01..07.webp
assets/landing/backgrounds/desktop/season-01..07.webp
assets/landing/posters/season-01..07.webp
```

- Preserve adult anchors, scale, wardrobe, lighting, center safe zone, and color grade across all seven plates in each aspect ratio.
- Author expression and gaze according to `CHARACTER_GAZE_ARC.md`.
- Background plates contain no text, card, logo, ticket, or baked UI.
- Center posters contain no editable titles or body copy.
- Retain lossless private masters outside the public monorepo; deploy optimized derivatives through the private Site source.

## Render and continuity tests

- Phone: 390×844, 393×852, 430×932.
- Desktop: 1366×768, 1440×900, 1536×864.
- Produce contact sheets for all seven phone states and all seven desktop states.
- Overlay successive backgrounds and verify adult anchor drift remains visually negligible.
- Verify the center card never covers either adult face and the title never collides with the card.
- Verify front/back copy fits without scrolling at the three phone widths.
- Verify swipe, edge tap, flip, keyboard, reduced motion, and adjacent-image preload.

No deployment is accepted until the render matrix and contact sheets are reviewed.
