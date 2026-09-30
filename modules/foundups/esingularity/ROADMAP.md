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

- [x] Centralize approved YUMORI.me / guardian / JHR branding in the shared website skill, with eSingularity and YUMORI.me entrypoints plus ticker/report cross-references. This records the language contract; it does not publish or certify live compliance.
- [ ] Focus eSingularity.ai navigation on three to four primary tabs; determine labels/grouping in the active redesign, preserve JHR and participation access, and verify desktop/mobile consistency. Keep YUMORI.me's movement funnel intact.
- [x] Make the website skill resolve the target site, purpose, visitor goal and edit boundary before each change.
- [x] Add the FoundUp-owned [website operations skill](skills/website-update/SKILL.md), with history-backed shared-ticker checks and registry/agent discovery.
- [x] Add the reusable [ticker-update skill](../../../.agents/skills/esingularity-ticker/SKILL.md) with one dated field-status source and publication verification.
- [x] Add the WRE-registered [YUMORI Moshpit Skillz](skillz/yumori_moshpit/SKILLz.md) so Red Dog/0102 consistently separate campaign history from agent-learning telemetry and preserve reverse-chronological JST ordering.
- [x] Add the WRE-registered [YUMORI.me correspondence parent](skillz/yumori_contact_ledger/SKILLz.md) for live Gmail/CRM reconciliation, routing consent, 0102 proxy voice, receipts and recursive operator learning without a parallel contact database.
- [x] Add the WRE-registered [YUMORI Work orchestrator](skillz/yumori_work_orchestrator/SKILLz.md) so 012/Red Dog planning is reconciled against live state, WSP 15-ranked, split into 012 physical actions vs machine work, and handed to the existing governed Work chain. Capital discovery reuses CONTACTS `Capital Targets` / `Capital People` and verified first-degree LinkedIn/Gmail evidence rather than creating another investor database.
- [x] Add the canonical [grants/subsidies/PPP support registry](docs/GRANTS_AND_SUBSIDIES.md), reconcile it with the Drive grant-audit sheet, and require status labels that distinguish program existence from eligibility, application, selection, and award.
- [x] Send the first formal eligibility inquiry for the MOE/RCESPA regional-coexistence data-center decarbonization program, framed around a currently closed municipal onsen and a future lawful PPP/lease/SPC structure.
- [ ] Obtain written clarification from RCESPA on closed-facility status, applicant/operator/SPC structure, property/use-right timing, eligible heat-reuse equipment, stacking, and current-round timing.
- [ ] Feed only verified eligibility and eligible-cost calculations into the Phase 1 financial model; never book a statutory maximum cap or an unverified model placeholder as committed funding.
- [x] Add a canonical candidate-site registry and separate FIN workbook tabs for Site 1 — Sukatto, Site 2 — Shimousaka, and Site 3 — Hanyu.
- [x] Add the repository-owned demand-led YUMORI economic model, 24-offer service catalog, formula-driven Demand & Capacity / Node Sizing workbook projection, demand-capped heat calculation, and sourced JHR infrastructure-flow ledger.
- [ ] Obtain utility and fiber responses for each candidate site; for Hanyu submit demand-derived initial and expansion load cases from the canonical economic model. Do not promote any fixed kW/MW into the functional model before demand, engineering and utility evidence support it.
- [x] Correct the Fukui policy boundary after METI's 2026-09-11 first-tranche decision: Fukui Prefecture (Fukui City / Obama City) is now a formally designated **decarbonized-power-utilization GX Strategic Region**, not merely a first-stage candidate and not a data-center-cluster designation.
- [ ] Add a GX-policy alignment agenda item to the Hanyu/Shimousaka prior consultation: ask Education Policy / Facilities Utilization to coordinate with Fukui City Enterprise Location Promotion on whether adaptive-reuse compute nodes can complement the City's designated GX industrial-location strategy.
- [ ] Open a bounded eligibility consultation with Fukui Prefecture Growth Industry Location Division on the ¥10B building-constructed AI data-center incentive and with Fukui City Enterprise Location Promotion on the municipal cap/stacking rule. Current Hanyu phase is below the threshold; do not claim eligibility.
- [ ] Open a bounded eligibility consultation with the GX Regional Co-Creation Subsidy office for the DC equipment-investment track before the second call: verify whether an eligible PPP/reuse site in Fukui City can qualify outside the named prefectural GX industrial-park parcel and what power-source / host-region contribution evidence is required.

- [ ] Ask Fukui City to consider Cabinet Office PPP/PFI expert/one-stop support as part of an independent demolition-vs-reuse comparison.
- [x] Provide Japanese, English, and Portuguese states for the ten-slide presentation.
- [ ] Complete route-based Japanese, English, and Portuguese localization for every legacy page surface.
- [ ] Add confirmed community events through structured event data.
- [ ] Add a real member calendar only when authentication exists.
- [ ] Keep LINE as the primary participation conversion.

## Phase 4 — Exfoliation review

Evaluate a standalone `FOUNDUPS/eSingularity` repository only after contracts, tests, deployment, and contributor boundaries are independently stable. Until then, the canonical source remains in this monorepo.


## Drive knowledge boundary — current project vs historical eSingularity

Current Fukui work uses the **YUMORI × eSingularity.ai × AI Koban** project family. Mutable correspondence/editorial/partner drafts live under the Drive container `CURRENT — YUMORI × eSingularity.ai × AI Koban — Working Documents` using semantic folder prefixes. Numeric prefixes remain reserved for the canonical project-document spine in [DRIVE_DOCUMENT_INDEX.md](docs/DRIVE_DOCUMENT_INDEX.md).

Historical Educational Singularity / eSingularity material (including 2007–2010-era work) is long-term provenance, not current Fukui authority. Agents must not mix it into current retrieval solely because the `eSingularity` term matches; promotion into current work requires an explicit current citation/verification path.

## Three-site capital-allocation rebaseline — 2026-09-29

- [x] Retain canonical Site 3/2/1 identities with Priority 1 Hanyu, Priority 2 Shimousaka, Priority 3 optional Sukatto.
- [x] Extend the canonical model and existing 18-tab FIN workbook with independent costs, three Hanyu cash scenarios, investor/retained-cash separation and a self-funding test.
- [x] Rebaseline native Doc 05's opening/decisions and align 07 while preserving six photos.
- [ ] Gate 1: utility/fiber/building/demand/CapEx/finance/legal evidence for a minimum viable Hanyu node.
- [ ] Gate 2: additional actual or contracted demand, independent site engineering and acceptable finance metrics for Hanyu expansion / Shimousaka.
- [ ] Gate 3: lawful City route, rights, rehabilitation/asbestos/MEP and thermal economics for optional Sukatto.
- [ ] Obtain site quotes and financing terms; replace 51 missing capital inputs and 55 annual cash inputs per scenario before interpreting numerical portfolio feasibility.
- [ ] Confirm asset-specific City filing units and each grant's applicant/site/equipment application unit. No automatic single three-site filing or award.

## 2026-09-29 — Costed portfolio planning

- [x] Populate independent low/base/high CapEx and demand-led downside/base/upside financial scenarios; publish formulas to existing FIN.
- [ ] Replace MODEL ONLY scope quantities and rates with surveys/vendor/utility evidence.
- [ ] Obtain customer orders, carrier route, City use terms and finance/tax review; then select a deployable minimum phase.
- [ ] Resolve dated drawdowns, VAT bridge, refurbishment scope and actual commissioning sequence. No deployment gate is passed by entering planning estimates.
