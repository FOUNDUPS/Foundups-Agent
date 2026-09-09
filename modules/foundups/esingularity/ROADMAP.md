# Project eSingularity roadmap

## YUMORI.me Mosh Pit integration

The shared activity projection and expandable renderer candidate lives in
`modules/communication/moltbot_bridge`, with the registered Red Dog curation
Skillz alongside it. Reuse this for a stakeholder-gated project feed in the
existing frontend. The second local layer implements the gated reader at
`/f/esingularity_001/mosh-pit` and GET `/api/mosh-pit`; the canonical host remains
unconnected and no deployment is made. See `docs/MOSH_PIT_GATEWAY.md` for the
read-approval policy, upstream contract, limitations, and remaining write layer.
See `extensions/reddog/docs/MOSH_PIT_WAVE_MVP.md` for membership, write flow and
the open-source comparison. Keep private chronology out of public build assets.

## Phase 1 — Monorepo incubation (current)

- [x] Preserve the live Japanese-first campaign PWA.
- [x] Move canonical source under `modules/foundups/esingularity/frontend`.
- [x] Add FoundUp identity, manifest, registry, tests, and module documentation.
- [x] Add the Japanese-first ten-slide YUMORI presentation without redesigning the page shell.
- [x] Add one presentation notification to the existing campaign ticker.
- [x] Complete the first recursive mobile, accessibility, claim, and navigation audit.
- [ ] Replace generated concept visuals when approved project photography or render assets arrive.

## Phase 2 — Foundups discovery integration

- [x] Reserve `/f/esingularity_001` and `idb_esingularity_001`.
- [x] Add the registry entry and scope-free public catalog projection.
- [ ] Add campaign-specific portfolio media only after approval.
- [ ] Verify the Foundups.com landing and app handoff in production.

## Phase 3 — Campaign operations

- [x] Provide Japanese, English, and Portuguese states for the ten-slide presentation.
- [ ] Complete route-based Japanese, English, and Portuguese localization for every legacy page surface.
- [ ] Add confirmed community events through structured event data.
- [ ] Add a real member calendar only when authentication exists.
- [ ] Keep LINE as the primary participation conversion.

## Phase 4 — Exfoliation review

Evaluate a standalone `FOUNDUPS/eSingularity` repository only after contracts, tests, deployment, and contributor boundaries are independently stable. Until then, the canonical source remains in this monorepo.
