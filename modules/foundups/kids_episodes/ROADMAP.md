# Kids Episodes roadmap

## Product objective

Story or teaching intent → linked episode plan → original visuals/music → aligned captions → reviewed 15-second episodes → YouTube delivery → later objective-linked EDUIT activities/games. Maintain stable story and episode IDs, a character bible, educational progression and continuity across every output. The editor and FFmpeg renderer are production components, not the autonomous product itself.

## Current execution order — WSP 15, 012 production-first correction

Scores below are work-item judgments: Complexity + Importance + Deferability
(urgency) + Impact, each 1–5. LLME is not reassigned for these work items.
Priority is not a runtime authorization. Dependencies decide order within a band.

| Order | Work item | C/I/D/Impact | Total / band | Completion evidence |
|---|---|---|---|---|
| 1 | Finish current 15-second episode review and deliver via existing channel | 3/5/5/4 | 17 / P0 | Actual audio listening, final visual/educational review, verified channel and upload receipt |
| 2 | Capture and forward-test causal story-direction skill | 3/5/4/4 | 16 / P0 | Creator corrections become reusable rules; next actual episode is proposed to 012, revised from feedback and reviewed |
| 3 | Generate the next linked story using the existing rig/editor | 4/5/4/4 | 17 / P0 | Connected plan, original assets, rendered/reviewed next episode, continuity evidence |
| 4 | Deploy minimal EDUIT introduction and Story Time watch/play page | 3/4/3/4 | 14 / P1 | Hosted URL, TLS, playback/game checks; authenticated deployment binding |
| 5 | Integrate EDUIT-scoped discovery into the existing Mall | 4/3/2/3 | 12 / P2 | Registry/projection/return-path tests; no duplicate platform |
| 6 | Memory Horizon, unlocks and local parent reports | 3/2/1/3 | 9 / P3 | Separately bounded future work; no current tracking activation |

Current video: original code-generated animation, three five-second editorial
clips, exactly 15 seconds. Latest stomp/crunch/squish render exists locally;
actual listening and publication are not yet verified. Do not describe the older
private preview upload as delivery of this latest revision. Publish settings
still need the prior approval-review block resolved; do not silently bypass it.

Story direction is part of the existing production skill at
`modules/communication/youtube_shorts/skillz/kids_episode_production/`.
Use its correction-to-principle reference before the next production pass.
Paused items stay paused: no scheduled trend scout, new paid provider dependency,
full education Mall, new memory game or learner analytics in the video slice.

## 1. Local proof

Register this candidate under the existing YouTube work. Prove a real 15-second export from supplied assets, in draft/final presets and portrait/landscape, with burned captions and an SRT artifact. Validate invalid input handling, duration and decodable audio/video. Review a sample educational episode; a synthetic encoder fixture alone is not an educational-quality proof.

## 2. Story-to-sequence production workflow

Extend the existing editor and episode schema with a story input, sequence plan, shared characters and per-episode objectives/activities. Implement bounded generation steps and durable checkpoints so a failed shot resumes without duplicating completed episodes. Let the adult creator inspect the linked sequence, revise shots/captions/music, preview and export. Preserve one episode identity across revisions and record asset provenance. Reuse existing pfMALL identity/discovery if/when the editor becomes hosted; keep the discoverable-only information card distinct from an activated app.

## 3. Generation providers

Verify the current official provider interfaces, account access and permitted use. Support official Suno exports with plan/download/rights evidence; do not assume a third-party Suno API is official. Prioritize independently runnable open-model video generation. Qualify Wan2.2-TI2V-5B on a controlled GPU worker; keep OpenRouter for configured planning/storyboards and optional separately qualified hosted video. A hosted Wan model name does not establish open licensing. Google integrations remain optional legacy adapters, not a required production dependency. Generate original music and consistent characters, then measure actual outputs and align captions. Provider availability, paid calls and account activation are unverified until exercised with authorized credentials and bounded cost.

## 4. Research worker

Route a bounded recurring job through existing orchestration. Inspect a curated educational-channel set and bounded searches, timestamp public metrics and compare repeated observations. Analyze available video/music evidence for educational themes and activities. Keep quota/cost budgets, provenance, deduplication and a stop control. Avoid treating a generic popular chart as comprehensive children's trends. Retain suggestions for review; trending content is not permission to reuse assets.

## 5. Reviewed publication and learning

Pin the intended YouTube channel and use the existing publisher with made-for-kids declared. Review correctness, activity safety, intelligible music/voice, caption alignment and rights. Feed verified failures and successful patterns into existing WRE memory mechanisms; promote a revised skill only after an independent test and a later successful invocation. Do not describe a saved prompt as autonomous RSI.

## 6. EDUIT learning-game linkage

Reuse the existing `eduit` FoundUp identity and Play EDUIT context. Design activities that correspond to episode learning objectives and later resolve to verified EDUIT game capabilities. Games remain future work; no game engine, child profiles, adaptive-learning outcomes or public game URLs are claimed. Do not merge EDUIT with the unrelated live eSingularity campaign.

## Status and release gates

All stages beyond the bounded local implementation require separate evidence. Registration does not activate a daemon, provider account, public route, monetization or token. The [prototype gate](docs/intake/PROTOTYPE_GATE.md) owns promotion criteria. No completion percentage is asserted.

Little Shrew now supplies a source-grounded preset and shared vector storyboard. Next evidence: admitted generation consuming verified character references, original audio, and independent review of the actual nine-shot result. The source's missing Gemini image remains explicitly unreceived.

## Open-model execution plan — 2026-10-23

See the [repository and provider audit](../../communication/youtube_shorts/docs/OPEN_VIDEO_AUDIT.md). Keep the existing FFmpeg editor and story controller. Finish: worker hardware/workflow qualification, image-to-video callback and job recovery, non-Google planner/independent media review, explicit music/foley handling, then the existing first three Little Shrew shots and WRE runtime admission. ComfyUI is a candidate worker API; no worker is activated. Compare deterministic 2D rig animation if diffusion cannot preserve the simple characters.

## Local first-episode proof — 2026-10-25

First three beats now render using the shared deterministic 2D rig and original synthesized audio through the existing Shorts editor. See [production receipt and autonomy owners](../../communication/youtube_shorts/docs/KIDS_LOCAL_PRODUCTION.md). Independent frame/technical review completed; actual audio listening and full publication review remain unverified. General provider generation, durable provider polling, account/spend admission and runtime production binding remain open. The ChatGPT trend scout is disabled per 012; do not reactivate it.

## Working book and next-story test

012 selected **How a Shrew Became a Human** as a working book title. The next
episode of this same series is the practical test for the story-direction skill;
do not substitute an unrelated test story. First propose the continuation, then
retain creator corrections and inspect the resulting episode. Current proposal:
the survivor peers out from its intact root pocket into the changed world after
the stomp. This is a proposal, not an approved script or rendered episode.

Series framing follows successive generations and branching lineages; do not
present an individual shrew transforming into a human, or evolution as a planned
ladder. Exact ancestors, dates and transitions require evidence before teaching
them as fact. The title is a narrative framing, not a validated scientific claim.


## Five composite tiles: planning only — 2026-10-28
`src/tile_batch.py:prepare_tile_batch` creates an ordered five-tile build/review
DAG plus series-join review. `check_review_record` checks complete, artifact-bound
local evidence fields; it authenticates neither evidence nor independent actors.
See [EDUIT RSI contract](../eduit/docs/TILE_PRODUCTION_RSI.md) for criteria,
correction lineage, existing runtime owners and blocked integration gates.
No executor, queue, scheduler, promotion or new FoundUp registration is installed.
