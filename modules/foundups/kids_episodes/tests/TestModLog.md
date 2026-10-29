# Kids Episodes TestModLog

## 2026-10-23 — Story production contract

- Source planner/controller: 30 no-network tests passed.
- Raw story remains unchanged; explicit term corrections are annotations.
- Source spans cover the complete story, episode continuity states join, generation lengths are provider capabilities and edit lengths total 15 seconds.
- Inputs, execution-binding digest and asset hashes bind checkpoints; uncertain effects cannot be automatically replayed.
- Fresh independent review required on resume; author/reviewer labels must differ but are not authenticated authority by themselves.
- Final assembled film requires an additional exact-artifact review including joins; absence retains `assembled_unreviewed`.
- Actual scratch integration produced 30.000000 seconds and 900 video frames from two episodes via real FFmpeg renderer/assembler. Admission and semantic review were test doubles, not live proof.

Independent review hardening: post-review asset rehashes reject changed media/captions; source/audience context reaches reviewers; input corrections validate before paid planning; exclusive random checkpoint temporary files prevent predictable-symlink writes; checkpoint read symlinks are rejected. Regression tests cover each finding.

Global acceptance rechecks all episode source/audio/render/caption assets and final assembly before returning; later reviewer or assembler mutation of earlier accepted media is rejected.

Final selected regression suite: 217 passed, including registry/schema, OpenClaw route, real WRE loader, provider contracts and FFmpeg integration. Planner caption schema is bounded to the renderer maximum of 30; reviewer explicitly checks raw source fidelity and supplied audience/corrections.

## 2026-10-23 — Little Shrew preset

85 module tests passed, including 12 new preset cases for canonical controller compatibility, nine-beat coverage, joined states, provider-duration rejection, design reference hashes and shared rig consistency. SVG render inspection caught missing legacy xlink references; added compatibility attributes and checked the corrected storyboard. These checks validate a design preset, not actual generated video or audio. Existing pytest configuration emits two warnings because the local interpreter lacks pytest-asyncio; no tests in this selection require it.


## 2026-10-28 — Batch RSI planning boundary
Four stdlib unittest methods pass with per-criterion failure subtests; existing
18 EDUIT Node tests pass. No runtime, visual/audio or forward-transfer proof.
Run `python -B -m unittest modules.foundups.kids_episodes.tests.test_tile_batch -v`.
The existing Kids Episodes workflow collects this suite through pytest; local
pytest was unavailable, not reported as passed. See TILE_PRODUCTION_RSI in EDUIT.

Hosted first attempt: Kids Episodes passed; general CI stopped at stale canonical
test registry. Regenerated using the existing owner: one new unit-test entry,
1774→1775 total, quarantine count273 unchanged; --check now passes locally.
This integration failure remains recorded and the review procedure now requires
staging/regenerating/checking the registry when adding Python tests.
