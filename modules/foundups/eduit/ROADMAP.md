# EDUIT execution roadmap

## Phone storybook and narration correction — 2026-10-29

The existing PR #2256 now includes a follow-up phone-first correction: the first-visit storybook fills nearly the available portrait viewport, uses large short text and a taller picture, retains left/right swipe and Previous/Next, and explicit autoplay reads pages before handing off to the MP4. Browser playback restrictions can block automatic video sound, in which case the existing large Play control receives focus. Skip/Close do not auto-start video. The iPad retains its separate responsive layout. The upper fullscreen context on phones is bounded to avoid an oversized dirt strip; game physics, score, artwork scale and hit geometry remain unchanged. This is source implementation, not verified physical-device acceptance or a published Sites version. English browser TTS remains device-voice dependent; native iPad audible testing, all-locale audio and prerecorded production voices are separate acceptance gaps.


> **Canonical 2026-10-28 handoff:** [Storytime conversation audit and Prometheus M2M handoff](docs/STORYTIME_RSI_CONVERSATION_AUDIT_AND_HANDOFF.md) is the current decision register. It supersedes conflicting historical statements below about video+game-only tiles, Earn Stars buttons, forced three-round quizzes, and autonomous runtime status. Existing site work is owned by a separate session; this PR documentation change must not overwrite that session's UI work.
## EDUIT vision / Storytime Evolution map — 2026-10-28

[EDUIT Pain → Solution → Outcome and Storytime Evolution progression](docs/EDUIT_STORYTIME_VISION_AND_EVOLUTION_MAP.md) is the current specification for the three-question FoundUp vision, Storytime's place inside EDUIT, modular counting/word/language objects, replay, optional parent-controlled memory, About/How links and a proposed accessible Roadmap mind-map modal. All new runtime behavior remains unimplemented until independently verified. A complete tile is WATCH → PLAY → VERIFY, superseding older video + game descriptions.


## Adaptive learning content and formative assessment — 2026-10-28

[Adaptive learning-content contract](docs/ADAPTIVE_LEARNING_CONTENT.md) defines EDUIT's outcome/experience/production-RSI vision, reusable three-object content packs, post-game picture matching, separate learning points and off-session RSI. This is specified, not shipped. Reuse the existing game and review owners; do not collect child play traces for WRE learning.


## CI acceptance rule — 2026-10-28

Every Storytime/EDUIT RSI iteration follows the [mandatory post-merge CI acceptance gate](docs/TILE_PRODUCTION_RSI.md#mandatory-post-merge-ci-acceptance-gate-2026-10-28-correction). Squash merge is not completion: verify checks against the resulting main SHA, inspect failures, and retain corrections before claiming acceptance. Browser/audio/device and deployment gates remain separate.


## RSI integration gate / next-session execution — 2026-10-28

Read [Storytime RSI system architecture](docs/STORYTIME_RSI_SYSTEM_ARCHITECTURE.md) and [five-tile contract](docs/TILE_PRODUCTION_RSI.md). Preserve existing viewer repairs as independent UI priorities. RSI critical path: verify current WRE/FAM admission and authority → bind one real Little Shrew composite ticket with independent verifier and budget → inspect actual film/game output → retain a bounded correction in existing WRE memory → demonstrate transfer on the next *different* tile. No second orchestrator, memory, scheduler or auto-promotion. Current planning/checker is implemented; admitted end-to-end execution and transfer remain unproved.


## Five-tile RSI production contract — 2026-10-28

Read [TILE_PRODUCTION_RSI](docs/TILE_PRODUCTION_RSI.md) before the next tile or
repair. It maps creator corrections to fixed acceptance checks, existing
OpenClaw/Hermes/FAM/WRE owners, and next-real-tile transfer evidence. The pure
Kids Episodes planning/record checker is implemented; runtime admission, batch
execution and retained skill promotion remain unproved. No live UI changes.

## Current learning shell and evolution direction — 2026-10-28

[Learning, evolution and sharing roadmap](docs/EVOLUTION_PLAY_AND_SHARING_ROADMAP.md)
owns the latest direction: mechanical proof of concept, optional creature-AI
prototype, then parent-owned membership MVP. Five-mission sets, fictional trait
bonuses and reviewed replay-to-YouTube are planned, not live. Current score and
slow rescue remain unchanged. The viewer now adds Play/About/How, a channel link
above the local film, and viewport-sized controls. No YouTube iframe, upload,
account, model, fingerprint or child telemetry is introduced.


## Current slow-rescue direction — 2026-10-27

[SLOW_RESCUE_AND_AGENT_ROADMAP](docs/SLOW_RESCUE_AND_AGENT_ROADMAP.md) supersedes
the historical15-second game contracts below:60s active round,48s rescue window,
untimed practice, varied wake taps, progressive hazards and once-only arrival
points. The original15s film remains separate. The green vine is the destination.
Creature-agent traits, optional on-device models, honest AI status, flooding and
play-to-video are specified next prototypes, not active AI features.
Use [interactive experience review](skillz/interactive_experience_review/SKILLz.md)
for audience, lifecycle, UI and incentive audits; retain existing WRE ownership.


Current direction: [Episode Mall architecture](docs/EPISODE_MALL_ARCHITECTURE.md).
This supersedes the earlier introduction-first landing proposal. It preserves
Kids Episodes' production priority and the existing renderer/Mall ownership.

## Resume without reconstructing the conversation

1. Verify current main and PR state. PR #2215 merged the local review/game/video
   foundation; it did not deploy domains or integrate the shared Mall.
2. Read README, architecture, INTERFACE, DEPLOYMENT, then shared Mall/Red Dog
   contracts and Kids Episodes roadmap. Reconcile any later changes first.
3. Confirm canonical EDUIT registry status; preserve `eduit`/`kids_episodes` IDs.
4. Use governed Holo retrieval; UNKNOWN freshness must stay UNKNOWN. No child
   data belongs in agent memory. Link source decisions instead of duplicating them.

## Current next slice — supersedes the historical order below

First repair the existing viewer: stateful Play/Pause, in-panel fullscreen
whiteboard and draft retention, direct Video/Game switching, then snapshot/share,
Repeat video and child lock. Verify each bounded layer before adding the next.
Priority P0 for the broken feedback flow; P1 for repeat/lock after basic state
continuity. Ratings, Mall mounting and premium features stay deferred. This is
qualitative sequencing, not a newly calculated WSP15 score. No runtime changes
are included in this documentation milestone.

## Historical bounded implementation order — WSP 15

C/I/D/Impact are complexity, importance, urgency and impact (1–5 each).
Scores are planning judgments, not runtime admission or billing authority.

| Order | Slice | Score | Exit evidence |
|---|---|---|---|
| 1 | Finish current episode sound/educational review | 3/5/5/4=17 P0 | Actual listening and independent output review |
| 2 | Shared-Mall EDUIT episode adapter, video above game, arrows/Next/return | 4/5/5/4=18 P0 | One paired tile; no autoplay game; lifecycle, scope and navigation regression checks |
| 3 | Deploy the same POC to verified EDUIT hosting | 3/5/4/4=16 P0 | Authenticated binding, TLS and phone URL playback/game proof |
| 4 | Next actual linked episode | 4/5/4/4=17 P0 | Connected story, reviewed media/activity; real Next destination |
| 5 | Spanish/Japanese sound-word variants | 3/4/3/4=14 P1 | Natural language review, aligned assets and fallback checks |
| 6 | Parent-only library/premium creation, quota and rating-owner integration | 4/3/2/4=13 P1 | Existing payment-owner audit, real entitlement/cancel/restore and failure tests |
| 7 | Memory Horizon, optional local reports, wider progression | 3/2/1/3=9 P3 | Separate reviewed scopes; no present activation |

Dependencies override score order: do not ship a payment plan before a useful
released library, or promise a public link before hosting is verified. Do not
build the entire education catalog to deliver the first episode.

Current external blockers: authenticated Firebase/domain bindings unavailable
in the reviewed workspace. Shared-Mall episode adapter, child/parent boundary,
locale variants and paid entitlement are implementation gaps, not access excuses.

## Creator expansion after first playable proof

Premium Create a story uses the existing editor/controller with bounded credit
reservations. Persist private draft tiles, pair video with a reviewed activity
template, review and publish into EDUIT's shared catalog. Confirm entitlement,
quota/retry settlement and rating/moderation owners before coding. Public
multi-user editing, creation pricing and automatic publication are not live.


## Current rescue/viewer milestone

See [rescue game and review contract](docs/RESCUE_GAME_REVIEW.md) for the latest
accepted timeline, five-character rescue mechanics, child-first viewer, local
whiteboard, fullscreen gestures, priorities and deferred agent experiment.
This supersedes the earlier two-cue timeout/practice game description.


Current [touch/mouse and PWA audit](docs/TOUCH_MOUSE_PWA_AUDIT.md) records responsive
inputs, flag-only controls, standalone installation artifacts, source recovery,
Mall ownership and verification limits.


## Home Screen layout milestone — 2026-10-26

See [Home Screen repair](docs/HOME_SCREEN_LAYOUT_REPAIR.md) for the direct
root viewer, per-panel expand/collapse, pinch adapter, responsive viewport checks
and physical-device limits. Use `build_site.py --output-dir <new-dir> --storytime-root`
for standalone Storytime; shared Mall registration remains separately owned.


## Fullscreen child controls and feedback — 2026-10-26

[Episode tile controls](docs/EPISODE_TILE_CONTROLS.md) owns the latest specified
video/game switching, panel gestures, fullscreen freeze/mark/share, Repeat video,
child touch-lock and deferred rating direction. These are requirements, not
shipped capabilities. Existing source gaps and independent acceptance cases are
recorded there; keep the current scene/media and existing Mall/Shorts owners.


## Preschool viewer implementation — 2026-10-26

[Preschool review](docs/PRESCHOOL_VIEWER_REVIEW.md) records the current ages3–4
iteration: brighter panel controls, larger cue/count typography, fullscreen
freeze/mark/share, video/game switch, video repeat and child touch-lock. This
implements the bounded tile-control slice; native-device acceptance, authentic
Red Dog feedback transport and Mall ratings remain separate. Next priority is
physical-device acceptance of this episode before extending the story.

## Next implementation: three-round learning loop (2026-10-28)
See [adaptive learning contract](docs/ADAPTIVE_LEARNING_CONTENT.md). P0: three completed game rounds with approved varied lessons, then optional bottom-right Earn Stars opens picture matching, with Play Again available throughout. Keep game score distinct from verified learning points. First implementation deterministic and local; PWA/agent is not prerequisite. Requires actual game/UI/locale tests before release.

## EDUIT agentic learning game engine (2026-10-28)
See [EDUIT Agentic Learning Game Engine](docs/EDUIT_AGENTIC_LEARNING_GAME_ENGINE.md) for the sound → written word → spoken word timing contract, family casting with smaller Baby, reusable matching/tracing/counting modes, deterministic browser hooks, and 012 → 0102 → WSP97 RSI feedback loop. This is a design contract, not an implemented autonomous runtime. Replay awards play stars; no Earn Stars button.

## WSP15 prioritized execution cycles — canonical latest decision (2026-10-28)
**This supersedes earlier Earn Stars / three-round test-gate proposals above.** The only primary end-of-round action is pulsing **Play Again**; rescue earns stars. Three successful rounds may be counted, but no Earn Stars button or forced test. VERIFY is a learning capability to integrate later in a child-appropriate, optional interaction, not a permanent third panel. Reconcile older prose on subsequent cleanup rather than treating it as an active requirement.

| Priority | Cycle | Deliverable | Acceptance evidence |
|---|---|---|---|
| P0 / Sprint 0 | Release baseline and audit | Reconcile PR #2249, canonical game owner, About mind map, deployment workflow, and existing TTS/whiteboard skills | Exact branch/CI status, mobile screenshots, no duplicate architecture |
| P0 / Sprint 1 | **Multimodal cue timing** | THUMP Foley → visible THUMP → spoken THUMP, offsets in **milliseconds**, with locale/audio fallback | Measured onset/jitter, audible phone test, replay cancel, no overlapping speech |
| P0 / Sprint 2 | **Reliable game cycle** | Five rescues → foot THUMP → soil CRUNCH → foot lifts → Everyone Safe → thumb-side pulsing Replay, round counter, safe seeded placement variation | Deterministic end-to-end test, reduced-motion/mobile tests |
| P1 / Sprint 3 | **Modular content** | Reviewed sound/family/counting packs; rescued 1–5 with localized numeral/word/voice; smaller Baby; familiar + new replay objects | Fixture validation, no false family roles, all locales |
| P1 / Sprint 4 | **Integrated verification** | Age-appropriate matching/recognition with play-earned stars; optional later tracing through existing whiteboard owner | Real 3-year-old accessibility review, independent answer integrity, no forced quiz |
| P1 / Sprint 5 | **Journey UI and release** | Verify scrollable About mind map, first-visit story modal, bottom-right closes, PF Mall tile contract | Phone browser acceptance, exact-main CI, deployment smoke |
| P2 / Sprint 6 | **RSI transfer** | Turn corrections into skill/test receipts and prove transfer on second tile through existing FAM/WRE/WSP97 owners | Independent next-tile test; no child telemetry or unreviewed auto-publish |

**Why cue timing first:** It is a small cross-cutting engine primitive, unlocks five sound concepts and counting speech, and yields precise regression fixtures. The full test/assessment engine depends on stable content cues and completed game cycles; building it first would hard-code incorrect learning objects. Do not add an autonomous browser agent to ship the first tile. The 012↔0102 correction loop is documented RSI input; production autonomy is a later verified outcome. All PRs must pass CI and be squash-merged before claiming live deployment.

### Phone fullscreen acceptance — 2026-10-29
Bounded repair evidence: docs/PHONE_FULLSCREEN_REPAIR.md. Retain v12 negative
control and strengthened phone/tablet oracle on the next actual tile. Physical
Home Screen/pinch/upgrade acceptance and non-layout findings in issue2252 remain
open; the layout repair is not closure of narration/replay or autonomous RSI.
