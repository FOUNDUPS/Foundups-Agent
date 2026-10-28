# EDUIT / Us Story Time — adaptive learning-content contract
Date: 2026-10-28. Status: VISION + SPECIFIED; not a shipped assessment or autonomous learning service.

## FoundUp: three inseparable dimensions
1. **Outcome:** EDUIT's educational singularity — accessible, repeatable learning through games that change their learning context, with evidence of learning rather than merely completion.
2. **Experience:** A participant plays an episode tile (video + game), meets a small number of learning objects, then completes a simple age-appropriate recognition/matching assessment and receives encouraging feedback/points.
3. **Self-improving production:** Existing FoundUps WRE/FAM/OpenClaw/Hermes infrastructure proposes, builds, reviews and improves content, game templates and learning-object selection. It operates separately from a child's session. No child interaction is an unreviewed RSI training input.

The Tool + The Content + The Experience is EDUIT's historical framing; the three dimensions above describe the operating FoundUp. EDUIT is one FoundUp; Storytime is a collection, and tiles/learning objects are content, not new FoundUps.

## Canonical Storytime tile contract — three required components
A **tile is a complete learning cycle**, not merely a video/game pair:
1. **WATCH — instructional video:** introduces the story, learning objective, cues and how to play. Its version and content must match the game.
2. **PLAY — interactive game:** lets the learner encounter and practice up to three reviewed learning objects per round; replay may load a different compatible approved pack.
3. **VERIFY — formative assessment:** after gameplay, three accessible, untimed picture/sound matching questions verify recognition of the round's actual objects, with feedback and separate learning points. This is not a high-stakes exam; errors never block replay.

A tile is only educationally complete when all three components are present, linked by tile/content revision and tested together. Existing video + game prototypes remain incomplete tiles until VERIFY ships. This three-part tile contract is distinct from the FoundUp's three operating dimensions above. Update all older "video + game" definitions, tile schemas, planners, Skillz, roadmap and acceptance criteria to reference WATCH → PLAY → VERIFY; do not mark the third component implemented until runtime evidence exists.

## Fundamental separation
**Stable playable mechanic != fixed lesson.** The same reviewed game can load a different approved three-object lesson on replay, without regenerating the game/video code. Gameplay events and lesson object IDs are mapped through a versioned content pack. The child-facing game cannot call an unbounded model or publish raw generated learning objects.

A replay should vary approved content where possible, not promise mathematically unique content with a finite catalog. Keep progression accessible; no penalization for repetition, disability, slow reaction, or limited language familiarity.

## Example: Little Shrew preschool round
Target audience example: ages 3–4, subject to child-development review. Select **three objects per round** from the existing cue pool (THUMP, SNIFF, CRUNCH, SQUISH), subject to actual episode compatibility. Example objects:
- THUMP: a dinosaur foot/stomp (sound → visible cause).
- SNIFF: a character smelling a plant (sound/action → visible cause).
- CRUNCH: a reviewed object/action from the actual episode, not a fabricated science claim.
- SQUISH: a fourth available sound/action concept in the existing game; depict a soft, cartoon compression or flattening under a descending shape, with no blood, gore, injury detail or frightening aftermath. For preschool learners, use playful squash-and-rebound imagery rather than graphic harm. Match the SQUISH word/sound to a clear visual cause.

Play the short rescue game with three clearly synchronized object cues. At completion, show one large, untimed picture-matching prompt per object, with two or three distinct visual choices and spoken/audio-accessible cues where reviewed. Example: “What made THUMP?” → dinosaur foot / plant / shrew nose. For SNIFF, match nose/smelling to the visible character action. For SQUISH, match a gently compressed cartoon character/object or squashing action to the cue, without blood or graphic violence. Avoid a trick question or asking children to infer an invisible cause. Reward a correct match once, offer a gentle retry and reveal the answer with sound/animation. A missed match never blocks Replay or Next.

The quiz is a **formative recognition check**, not a diagnostic test. Record game points and assessment points separately; no IQ, aptitude or age-percentile inference. Provide no-reading, keyboard, pointer and reduced-motion alternatives.

## Learning object and session contract — proposed `eduit.learning_object.v1`
Each reviewed object has stable `object_id`, `concept_id`, `age_band`, `locale`, `learning_objective`, `cue_id`, `sound_asset`, `visual_cause_asset`, `localized_prompt`, `choice_asset_ids`, `correct_choice_id`, `review_status`, `rights_provenance`, and `revision`. Sound-word translations are independently reviewed, not literal automatic substitutions.

A session binds `episode_id`, `tile_revision`, `content_pack_revision`, `locale`, `selected_object_ids` (maximum three for this prototype), `seed`, and `assessment_version`. Seeded deterministic selection enables tests and replay verification. Selection filters for reviewed assets, age band, locale coverage, scene/cue compatibility, distinct concepts, and prior-session variety where optional local state exists. If no valid fresh pack exists, reuse an approved pack honestly; never invent unreviewed content.

Flow: select reviewed pack → bind game cues → play → completion → show three matching prompts → award once-only points → feedback → replay with a different eligible pack. Film remains the reviewed episode revision; changing content must not imply that fixed video depicts a new cue it does not contain. Where the video cannot support the pack, use a compatible game-only variation or produce/review a new paired tile.

## Two separate improvement loops
**Learner adaptation (within a session/device):** adjust approved content, scaffolding and difficulty based on game-specific responses, preferably locally and optionally with parent-controlled local persistence. No raw child trace goes to WRE, AgentDB, analytics, model training or public leaderboards. With no stored history, choose deterministic safe variation without profiling.

**Production RSI (off-session):** use approved synthetic test cases, educator/editor corrections, verified accessibility checks, locale reviews and independently assessed artifact outcomes. Existing WRE PatternMemory retains developer lessons only after governed acceptance. Next *different* tile tests transfer; author cannot approve own output. Model-generated learning packs are drafts until rights, educational and language review.

## Existing owners and integration points
- EDUIT `README.md`, `INTERFACE.md`, `ROADMAP.md`, `docs/STORYTIME_RSI_SYSTEM_ARCHITECTURE.md`, `docs/TILE_PRODUCTION_RSI.md`.
- Browser mechanic: `public/eduit/storytime/engine.mjs`, `game.js`, `scene.mjs`; reuse rather than replacing.
- Story plan: `modules/foundups/kids_episodes/src/story_pipeline.py`; five-tile plan: `tile_batch.py`; fail-closed dispatch: `work_order_adapter.py`.
- Existing age/interaction review: `modules/foundups/eduit/skillz/interactive_experience_review/SKILLz.md`.
- Existing WRE admission, verification and memory, FAM tickets, AI Gateway, OpenClaw/Hermes, Mall product shell; do not duplicate their orchestration, catalog, memory, identity or payment planes.

## Required learning-content skill — specification, not yet installed
A dedicated `learning_content_review` Skillz should: receive audience, episode, locale and mechanic/cue contract; retrieve existing assets and objectives; propose at most three coherent learning objects; validate answerability and distinct visual distractors; verify locale/rights/science/age accessibility; freeze versioned content and deterministic test cases; return accepted draft or specific rejection. It must not execute provider effects, publish directly, generate child profiles or approve itself. Before creating the skill, inspect existing Kids Episodes/EDUIT skills for an equivalent owner and extend it if appropriate under WSP97.

## Acceptance / roadmap
P0 documentation: integrate this contract into EDUIT canonical entrypoints and current WSP97 context.
P0 deterministic prototype: implement content-pack schema/loader and three-object selection on existing game; test fresh/repeated seed, empty/invalid pack, cue/video mismatch, locale fallback and correct-answer integrity.
P0 assessment: three large picture matches, untimed, one-time points, retry/answer reveal, keyboard/touch and pause/reset. Test scoring separately from rescue score.
P1 content skill: existing-owner reuse audit, reviewed pack generation and independent educational/language/rights acceptance.
P1 transfer: next distinct tile with independent frozen tests and retained development correction; only then evaluate RSI gains.
P2 optional local parent view; no identifying child collection, account, paid generation or deployment by default.

## M2M handoff
Read current main, branch ownership, EDUIT README/INTERFACE/ROADMAP/ModLog, this contract, Storytime RSI architecture, tile acceptance, Kids Episodes owners and existing Skillz. Reconcile source before editing. Use WSP00/15/48/62/97; implement the smallest bounded existing-owner slice. Freeze synthetic lesson packs and negative cases before coding. Verify actual browser gameplay and independent educational/locale review where available. Update canonical docs, tests and ModLog; PR, exact-head CI, merge and exact-main CI are distinct gates. No live child data, new scheduler, invented authority, auto-publication or claim of autonomous RSI.

## Opening-story modal → instructional video transition (approved design, not yet shipped)
The WATCH component begins on first eligible visit with an accessible illustrated opening-story dialog, then collapses visually into the existing video panel and hands control to the existing instructional film. Preserve the current video-above-game layout and WATCH → PLAY → VERIFY contract. Do not create a fourth tile component or regenerate the film on each play.

- Reuse the Shorts-owned viewer/dialog, media lifecycle, and existing scene/asset/TTS pipeline. Do not introduce a competing player, modal framework, narration service or global scheduler.
- The 20–30-second opening uses five reviewed illustrated scenes: long ago (~150 Ma), small furry Jurassic mammal-like MAMMAs in sheltered burrows, three later mammal branches (MAMMA 🥚 monotremes, MAMMA 🦘 marsupials, MAMMA 🤰 placentals), a dinosaur THUMP, and a five-MAMMA rescue invitation. The three branches are relatives, not an egg→pouch→placental ladder. Do not claim every Jurassic mammal laid eggs or lived underground.
- Provide localized, human-reviewed narration/captions and explicit Play story / Skip story controls. Browser autoplay restrictions require an accessible start gesture or muted visual fallback; never force audible playback. Pause narration on tab hide, dialog dismissal, video start or navigation. Do not overlap narration and instructional film audio.
- On completion or Skip, animate the dialog rectangle into the existing video viewport where motion is permitted, then close/unmount the dialog and focus the existing video control. Under prefers-reduced-motion, use an instant cut. Never move the actual video element between DOM owners if that would disrupt playback.
- Auto-offer the intro only once per episode revision on that device; subsequent visits retain a visible 📖 Story replay control. Store only a local per-episode dismissed/completed flag, not child identity. Guest use and clearing local state must work. No modal on every game replay.
- If story images, localized narration or TTS are missing, fall back to the normal instructional video with no blank blocking overlay. Preserve game and VERIFY behavior, including separate scores.
- Acceptance: first visit, returning visit, replay, Skip, Escape/keyboard, touch, focus restoration, autoplay rejection, reduced motion, missing assets, locale fallback, tab hidden, narration/video exclusivity, video pause/resume and no child telemetry. Validate on mobile and desktop. Independent review of actual rendered output and WSP97/CI gates required before marking implemented.
