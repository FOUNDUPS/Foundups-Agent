# eSingularity TestModLog

## 2026-09-13 — Reusable field-status contract

- Replaced hard-coded September 10/City Hall event assertions with required status fields, ISO timestamp/JST validation and the shared href renderer check.
- Three existing JHR/field-status tests passed via direct invocation (pytest unavailable); 18 hostname-routing tests passed. The ticker skill passed quick validation. After restoring the homepage mount, the existing ticker integration test and focused frontend ESLint also passed.

## 2026-09-12 — Distinct-homepage regression contract

- Refreshed the existing YUMORI landing tests in place after the join-first PR #1653 page was restored; no duplicate test file was created.
- The content contract now requires the ordered WHY / WHAT / HOW movement funnel, five JOIN actions, the 1,000-person preparatory-committee target, JHR access, and community-compute framing.
- Removed stale assertions for the later long-form YUMORI iteration and stopped requiring live-field detail to be duplicated inside the movement page; the campaign ticker remains its canonical renderer.
- Paired this content suite with `test_domain_routing.mjs`: future acceptance requires both the correct page and the correct hostname selection.
- Fresh local evidence: 18 Node routing checks and eight dependency-free Python contract functions passed. Full `pytest` execution was unavailable in this environment; the broader direct runner still encounters the previously documented missing legacy `frontend/content/yumori-presentation.ts` reference.

## 2026-09-12 — Shared-host domain routing configuration

- Retrieved this inventory, tests README, and the existing `test_yumori_national_landing.py` before authoring tests. The Python suite covers movement content; the new dependency-free Node suite covers the distinct executable routing configuration without replacing that suite.
- Added `test_domain_routing.mjs`: before-files ordering, exact YUMORI.me and www host matches, eSingularity.ai/YUMORI.info/unknown-host exclusions, root-only internal rewrite, unchanged report/API/asset paths, and no query override or new redirect.
- Wired the Node command into the existing Validate eSingularity workflow after Node setup; retained all existing validation steps.
- Fresh local evidence: 18 configuration checks passed using Node v24.19.0 with `--experimental-strip-types`, against the reconciled production source plus the hostname-routing patch.
- This result is not a frontend build, HTTP/SPA test, DNS check or production deployment receipt. Those remain separate acceptance gates.

## 2026-09-11 — Full-screen real-building vision deck coverage

- Updated the existing presentation contract tests to treat `frontend/content/yumori-vision.ts` as the current real-building ten-slide semantic/evidence source.
- Added regression coverage for the optimized `public/vision/vision-sprite.jpg`, responsive sprite positioning, full-screen/deep-link behavior, keyboard Left/Right/Escape controls, touch swiping and reduced-motion handling.
- Added exact current slide-spine checks for option value, D-K, 24-hour onsen/wellness, AI rice field, COG DC heat reuse, 60 FoundUps plus B1 gym/rest/recovery, local problem-to-FoundUp, distributed Fukui prototype and closing choice.
- Added financial truth-boundary checks for reported demolition estimate vs. modeled five-year revenue and cumulative FCFE.
- Retained public-source checks on the landing page for Fukui AI/agriculture/satellite/manufacturing sources and the official D-K destination.

## 2026-09-06 — YUMORI presentation contract coverage

- Replaced corrupted legacy assertions with twelve UTF-8 contract tests for the current public architecture.
- Added exact ticker-notification and ten-slide Japanese canonical-source checks.
- Added complete English/Portuguese derivation, proposition, progressive-disclosure, floor-ladder, and COG DC ownership checks.
- Added economics label, autoplay/pause/touch, generated-asset, official-outreach-source, and `/future` route regressions.

## 2026-09-01 — Innovation Hub language and typography coverage

- Added regression checks for the Gather → Learn → Create → Launch floor progression.
- Added English-copy checks for the AI learning, creation, and launch floor descriptions.
- Added typography checks that highlighted campaign headings keep one consistent font voice.
- Added outcome-card checks, removed-choice-diagram coverage, and multilingual alt-text handling.
- Added a regression contract for the native six-step campaign coalition sequence and removal of the old stakeholder image.
- Added economic-impact checks that keep the direct-spending layer distinct, expose the 30-year method progressively, and exclude supplier, wage, job, and tax figures until official input-output analysis is complete.

## 2026-09-01 — Awara and D-K visual-reference coverage

- Added contract checks for the official Awara Yukemuri Yokocho and D-K gallery destinations.
- Added regression checks that the artist portrait remains a compact 52-pixel identity element and no longer dominates the night-experience card.
- Added translation checks for the Japanese-first reference links.

## 2026-09-01 — English economic-story regression coverage

- Added assertions for the complete English AI Rice Field explanation and use cases.
- Updated visitor-spending arithmetic to the official 2025 Fukui day-trip benchmark and added 30-year constant-attendance calculations.
- Added campaign-headline assertions to prevent the previous weak English story copy from returning.

## 2026-08-31 — Community-vision regression coverage

- Added checks for equivalent campaign hero copy across Japanese, English, and Portuguese.
- Added checks that 0102 MUSIC remains opt-in and pauses through viewport observation.
- Added checks for conditional concept labels, the generated concept asset, revised floor labels, and removal of landing sections 08–10.

## 2026-08-30 — Migration contract baseline

- Added identity, namespace, registry, hosting, route, and token-deferral checks.
- Added the shared FoundUp build-contract validator as a regression gate.
