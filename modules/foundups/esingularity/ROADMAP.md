# Project eSingularity roadmap

## Permanent architecture guardrail

- [x] Keep one canonical monorepo frontend and one existing Sites deployment.
- [x] Keep `esingularity.ai/` focused on the Fukui eSingularity project/vision through `frontend/app/page.tsx`.
- [x] Keep `yumori.me/` and `www.yumori.me/` focused on the YUMORI movement and preparatory-committee join funnel through `frontend/app/yumori/page.tsx`.
- [x] Select the YUMORI root internally by hostname so YUMORI.me stays visible in the browser.
- [x] Protect the split with dependency-free routing tests and movement-page content tests.
- [x] Leave the external YUMORI.info → eSingularity.ai forwarding rule outside this frontend and unchanged.

These are continuing acceptance gates, not completed features that may later be removed. Every homepage redesign, merge reconciliation, and production publish must preserve both domain roles. Shared hosting must never become shared homepage content.

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
