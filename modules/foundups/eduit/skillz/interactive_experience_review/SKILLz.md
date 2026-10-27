---
name: interactive_experience_review
description: Audit and iteratively repair audience-specific games and web interfaces, including EDUIT Storytime timing, touch controls, learning cues, scoring and feedback. Use before implementation and after inspecting each changed output.
version: 0.2.0
intent_type: AUDIT
promotion_state: prototype
---

# Review an interactive experience

This is a reusable **candidate procedure**, first applied to EDUIT. It is not an
installed continuous worker, production-admitted Skillz, or proof of transfer to
other games. Keep each product's runtime and evidence in its existing module.

## Establish the contract

1. Retrieve AGENTS, WSP 00/97, the owning module README, INTERFACE, ROADMAP,
   ModLog and test inventory. Use the governed Holo owner; retain UNKNOWN
   freshness/index gaps when only lexical fallback is available. Check adjacent
   owners before inventing a shared engine, catalog, identity or scheduler.
2. Record the audience, intended action, input methods, target viewports,
   current revision and one observable success. For preschool use, distinguish
   learning the sequence from reading, reaction ability or developmental claims.
   Identify adult-only editing/options and the child-facing controls.
3. Separate immutable approved story/art from explicit new direction. A media
   export duration is not a game deadline. State which clocks change and trace
   their audio, cues, animation, scoring and pause dependencies. Preserve prior
   media identity when it is not rerendered.
4. Compare the smallest viable repair with the strongest alternative; record
   the chosen owner and WSP 15 allocation. Freeze acceptance cases before coding.
   Treat unfamiliar requirements as proposals, not already working features.

## Inspect in this order

| Pass | Required evidence |
|---|---|
| Causality and timing | A cue precedes the required action; travel and consequences are visible. All intended successes are achievable with the declared pace. Inspect anticipation, transition and ending, not only endpoints. |
| State and recovery | Pause, hidden page, resize, fullscreen, locale change and feedback do not consume play time, restart a round, lose drawings or alter awarded points. Reset semantics are explicit. |
| Learning correspondence | Bind each sound, readable word and visible cause. Move labels with their referent without covering faces, targets or exits. Check quiet visual playback and actual sound separately. |
| UI and accessibility | Measure rendered CSS bounds, not SVG/source sizes. Inspect phone/tablet portrait/landscape, installed entry where available, minimum supported viewport, focus, keyboard and mouse. Check tap overlap, safe areas, short landscape rails and glyph coverage. |
| Incentives and privacy | Award once for the intended completed action, never repeated input. Bound speed bonuses; preserve an untimed path. Keep learning success distinct from score. Do not infer aptitude or send child play records into agent memory. |
| Integration | Exercise actual root/inner launch, cache update, allowed messaging, share/cancel, child lock and teardown. Reuse existing Mall/Shorts owners; do not treat a local boolean as entitlement or account security. |

Use a deterministic first learning round when randomness would conceal the rule.
If variation is introduced, bind it to a reproducible seed and prove every
supported setup is solvable. A sleepy response must visibly acknowledge a tap;
retry/drowsing must not silently revoke an earned rescue. Test slow deliberate
input as well as the fastest successful route.

## Repair, rate and retain

- Run the closest existing tests, then inspect the actual affected preview.
  Extend existing test files for new edge cases. Do not use source assertions
  as evidence of visual readability, or simulated pointer events as native touch.
- Obtain an independent review of raw output/diff/test evidence. Keep author and
  reviewer identity separate. Repair observed defects and rerun the affected
  pass plus dependencies; do not expand unrelated suites without a reason.
- Grade each declared criterion independently: **1** blocked, **2** major defect,
  **3** usable with explicit gaps, **4** scoped checks pass with platform limits,
  **5** independently confirmed on every declared surface. Never average away a
  failed criterion or present this ordinal rubric as WSP 15 or learner progress.
- For 1–2, repair before accepting. For 3, distinguish an accessible defect from
  missing device evidence. For 4–5, stop polishing absent new evidence or scope.
- Retain `failure → cause hypothesis → repair → exact evidence → independent
  judgment → accepted/rejected candidate` in the product review receipt. Include
  source/media revisions, baseline comparison, limits and rollback reference.
  Keep future flood levels, replay exports and progression separate from shipped
  behavior until their own acceptance evidence exists.
- Update module docs/test history and link this candidate. Forward-test a useful
  rule on the **next actual episode or product task**, not an unrelated invented
  story. Do not claim generalization merely because another agent read it.
- Bundle one accepted milestone into its existing PR/deployment workflow; verify
  main and live result separately. Never activate WRE or publish media implicitly.

## Existing RSI boundary

Use [WRE](../../../../infrastructure/wre_core/README.md) and
[WSP 95](../../../../../WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md)
for future authenticated outcomes, candidate storage, independent evaluation and
promotion. `src/pattern_memory.py`, `src/pattern_ab_evidence.py` and
`src/skill_runtime_admission.py` remain those owners; do not add a second learning
database or promoter here. A module review receipt is development evidence, not
an authenticated runtime outcome. This prototype has no executor, production
registry entry, scheduled activation or automatic artifact-update authority.

For Storytime-specific staging and viewer invariants, read the existing
[production skill](../../../../communication/youtube_shorts/skillz/kids_episode_production/SKILLz.md)
and the current EDUIT review receipt. Apply the latest explicit creator direction
over historical timing defaults without rewriting unrelated approved details.

## Required correction and next-tile loop

Before every Storytime repair or new tile, load
[the tile-production contract](../../docs/TILE_PRODUCTION_RSI.md). Reuse its
criterion IDs and correction ledger; freeze acceptance before authoring. A tile
pairs matching video and game, not just an MP4. Use the Kids Episodes advisory
batch compiler for five-tile planning; never treat its digest as admission.
Inspect and independently review the next actual tile before propagating the
approach to four more. Record rule reuse or failure; update the regression and
receipt even when 012 did not report the defect. Do not modify the acceptance
oracle to rescue a failing candidate. This remains a prototype procedure, not
an active OpenClaw/Hermes worker or a promoted general game-development skill.

When adding a Python test, stage its owned path before running the existing
`modules/infrastructure/wre_core/scripts/generate_test_registry.py --write`,
then `--check`; review the exact generated delta before committing. CI exposed
this missing integration step during the five-tile contract milestone.
