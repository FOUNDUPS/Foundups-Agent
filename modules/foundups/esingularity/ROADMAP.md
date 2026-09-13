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

- [ ] Focus eSingularity.ai navigation on three to four primary tabs; determine labels/grouping in the active redesign, preserve JHR and participation access, and verify desktop/mobile consistency. Keep YUMORI.me's movement funnel intact.
- [x] Make the website skill resolve the target site, purpose, visitor goal and edit boundary before each change.
- [x] Add the FoundUp-owned [website operations skill](skills/website-update/SKILL.md), with history-backed shared-ticker checks and registry/agent discovery.
- [x] Add the reusable [ticker-update skill](../../../.agents/skills/esingularity-ticker/SKILL.md) with one dated field-status source and publication verification.
- [x] Add the canonical [grants/subsidies/PPP support registry](docs/GRANTS_AND_SUBSIDIES.md), reconcile it with the Drive grant-audit sheet, and require status labels that distinguish program existence from eligibility, application, selection, and award.
- [x] Send the first formal eligibility inquiry for the MOE/RCESPA regional-coexistence data-center decarbonization program, framed around a currently closed municipal onsen and a future lawful PPP/lease/SPC structure.
- [ ] Obtain written clarification from RCESPA on closed-facility status, applicant/operator/SPC structure, property/use-right timing, eligible heat-reuse equipment, stacking, and current-round timing.
- [ ] Feed only verified eligibility and eligible-cost calculations into the Phase 1 financial model; never book a statutory maximum cap or an unverified model placeholder as committed funding.
- [ ] Ask Fukui City to consider Cabinet Office PPP/PFI expert/one-stop support as part of an independent demolition-vs-reuse comparison.
- [x] Provide Japanese, English, and Portuguese states for the ten-slide presentation.
- [ ] Complete route-based Japanese, English, and Portuguese localization for every legacy page surface.
- [ ] Add confirmed community events through structured event data.
- [ ] Add a real member calendar only when authentication exists.
- [ ] Keep LINE as the primary participation conversion.

## Phase 4 — Exfoliation review

Evaluate a standalone `FOUNDUPS/eSingularity` repository only after contracts, tests, deployment, and contributor boundaries are independently stable. Until then, the canonical source remains in this monorepo.
