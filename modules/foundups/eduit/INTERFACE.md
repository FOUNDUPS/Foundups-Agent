# EDUIT interfaces
## EDUIT vision / Storytime Evolution map — 2026-10-28

[EDUIT Pain → Solution → Outcome and Storytime Evolution progression](docs/EDUIT_STORYTIME_VISION_AND_EVOLUTION_MAP.md) is the current specification for the three-question FoundUp vision, Storytime's place inside EDUIT, modular counting/word/language objects, replay, optional parent-controlled memory, About/How links and a proposed accessible Roadmap mind-map modal. All new runtime behavior remains unimplemented until independently verified. A complete tile is WATCH → PLAY → VERIFY, superseding older video + game descriptions.


## Adaptive learning content and formative assessment — 2026-10-28

[Adaptive learning-content contract](docs/ADAPTIVE_LEARNING_CONTENT.md) defines EDUIT's outcome/experience/production-RSI vision, reusable three-object content packs, post-game picture matching, separate learning points and off-session RSI. This is specified, not shipped. Reuse the existing game and review owners; do not collect child play traces for WRE learning.


## Cross-module RSI architecture — 2026-10-28

Read [Storytime RSI system architecture](docs/STORYTIME_RSI_SYSTEM_ARCHITECTURE.md) for canonical owners and the continuation sequence. This interface does not authorize new runtime admission, a second memory store, new orchestration, or child telemetry. A tile pairs video and game; the five-tile planner is not a production executor.


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


Status: source contracts observed at main a6fed6dd8; episode integration SPECIFIED.
Canonical product design: [Episode Mall architecture](docs/EPISODE_MALL_ARCHITECTURE.md).

## Existing local prototype

- `public/eduit/storytime/engine.mjs`: deterministic 15-second, five-character rescue game.
- `public/eduit/storytime/scene.mjs`: shared absolute-time scene/movie rendering.
- `build_site.py`: packages the existing static site, freshly generated media and
  Shorts-owned creator-review assets at `/review/`; refuses existing output.
- `render_story_preview.py`: three five-second clips, MP4/SRT, original audio and
  provenance through existing Shorts production. Local rendering is not review.
- Domain mappings and target bindings: [DEPLOYMENT.md](DEPLOYMENT.md).

## Proposed composite episode record

This is a design contract, not an accepted registry schema or current API.
Extend existing content/projection owners after schema review; do not mint a
FoundUp per episode or hand-edit generated catalog output.

| Field | Required meaning |
|---|---|
| FoundUp / collection / story / episode IDs | Stable existing parent identity plus content identities |
| Revision | Binds matching video, game, cue sheet and locale assets |
| Learning objective | One observable activity goal, distinct from reaction speed |
| Poster and video references | Reviewed assets/provenance, exactly 15 seconds for this series |
| Activity reference/version | Allowlisted existing activity adapter, never arbitrary executable code |
| Ordered next episode | Same collection, released/available; null means end |
| Locales | Available reviewed captions/instructions/word labels/audio variants |
| Cue sheet | Stable IDs, bounded event times, sound and localized word references |
| Creator and publication state | Creator-scoped draft/review/published/withdrawn references; visibility enforced by existing admission |
| Creation quota receipt | Server-owned job reservation/settlement reference; separate from viewing entitlement |
| Rating reference | Proposed episode feedback aggregate; owner and moderation unqualified |
| Access policy reference | Free or verified parent entitlement; no browser-authoritative boolean |

Activity lifecycle must support mount, explicit start, pause, reset, unmount and
bounded completion/error signals. These are required semantics, not shipped
method names. Scope context includes episode/revision/locale and allowed return
state, without child identity or raw play-history payloads to Red Dog.

## Shared ownership constraints

Reuse `public/member/INTERFACE.md`, fullscreen/navigation contracts, product state,
`gestureZone` and the existing Red Dog/account plane. The current video queue
is not a composite episode queue. Preserve other products' behavior.
PWA install/offline, public-product admission and authenticated conversation
transport each need separate evidence; none is implied by a working static page.


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

### Slow-rescue API additions
`initial({practice})`, `worldTime(state)`, `rescuePoints(arrival,practice)` and
`gameWorld(state,poses)` separate simulation/film clocks. State adds score,
awards, practice and outcome; actor wake profiles are explicit.
`storytimeReview.status()` adds score/practice; `reset()` clears round and pauses;
`setPractice(boolean)` resets to ready and pauses. Freeze includes game revision
and full scene/round state through existing viewer records. New feedback namespace
`slow-rescue-11` leaves old local notes untouched; clock validation permits up to
86400 active seconds for bounded untimed practice records. No storage/API upload
for score. No agent controller runtime is exposed yet.

### Information and responsive controls
The Shorts-owned viewer exposes About and How as native modal dialogs. Opening
pauses both media and game; closing preserves state and leaves explicit resume.
Full-screen makes page siblings inert. Controls use CSS viewport sizing rather
than canvas scaling: 64px at <=360px width or <=450px height, otherwise
clamp(72px,10vmin,88px). The same rule applies to play, switch, feedback and
expand controls. Actual physical touch delivery remains device acceptance.
The game/film API, score, scene revision and local feedback namespace are unchanged.
