# EDUIT interfaces

## Single teaching-word profile — 2026-11-02

`mountMoviePresentation` accepts `wordPlacement` (`below` or `scene`, default
`below`), `captionAvailable` (boolean), and `onChange(status)`. It returns
`setWordPlacement(value)`, `setCaptionAvailable(boolean)` and `status()` in
addition to existing lifecycle methods. Invalid values fail closed. Status
reports requested/effective placement, caption availability, expanded/ready/failed.
No arbitrary style/script URLs or model dispatch is accepted. Setters redraw the
retained movie frame without writing transport time or game state. Only a valid
revision2 cue sheet enables the separate word; absent captions, failed renderer
or compact/native playback retain the original picture word. The grown-up menu
pauses playback and persists the allowlisted choice locally under
`eduit.movie-word-placement.v1`; it does not resume automatically.
Director and storybook share exactly one revision-keyed narration module URL.
See [presentation contract](docs/SINGLE_WORD_PRESENTATION.md).

## Two-action story popup — 2026-11-02

Only `#storybook-play` and `#intro-close` are child actions:88px minimum targets,
64px glyphs and accessible Play/Pause/Resume/Close names. One Play runs every
page; Pause retains it, Resume repeats its phrase. Surface taps can start the
whole book; swipes/arrows no longer navigate or interrupt. Previous/Next/Watch
nodes are retired. `#intro-skip` stays hidden for unenhanced fallback compatibility.
Open focuses Play; X/Escape cancel without movie start. Existing play/pause/status
API and single completion handoff/browser-denial fallback stay intact.
Viewport updates still pause gameplay; video excludes only measured scrollbar
reflow with unchanged layout/height/offsets and matching changed client widths.
Unknown geometry, offsets and rotation keep prior pause rules.

## Sound cues / renderer generation — 2026-11-01

Revision2 stays25s/750frames with new authored demo holds and a rerendered MP4.
Action captions reserve time without overlapping the next cue; voice no longer
ducks Foley. `foleyVolume(cue)` restores each event's intended level and reset
clears retained sound/offset. Generation-addressed renderer copies and derived
same-origin imports replace the old fetched-source-only binding. Draw has no
static renderer fallback. [Exact contract and limits](docs/SOUND_CUE_REPAIR.md).

## Responsive movie picture — 2026-11-01

`mountMoviePresentation({video,panel,surface})` returns `setExpanded(boolean)`,
`ready()` and `dispose()`. Only expanded video gets recorded scene frames;
requestVideoFrameCallback supplies presented media time, with currentTime/rAF
fallback. Pause, seek, resize, repeat and foreground render the retained media
position. No play(), time assignment, game input or independent clock is used.
Collapsed/disposed/hidden views cancel frame work. Failure keeps native MP4.
`export_movie_presentation.mjs <asset-dir>` verifies existing film provenance,
all source hashes and actual MP4 bytes, derives750 frames through the existing
replay owner and proves canonical SVG equality before writing bounded sidecars.
The loader validates shape/cast/text/numbers and frame/movie/fetched-source
hashes. Fetched source hashes do not prove the identity of already executed
modules after an arbitrary mixed-version update; current renderer sources are
unchanged. Future renderer revisions need independently reviewed generation
binding. Manifest identity and installation scope remain unchanged.

## Word/picture activation and pictograms — 2026-11-01

The existing `.storybook-page` click starts all five pages from0 when paused.
Taps during playback do not interrupt it; the native primary button remains the
keyboard/screen-reader equivalent. Deliberate swipe/arrows pause for manual
preview; a cancelled pointer, drag or multitouch cannot become a start click.
An explicit primary Pause/Play resumes the retained page, repeating its phrase;
manual navigation and close/open clear that resume intent. Surface activation
always requests the whole story. Background/visibility changes still pause.

Stable button IDs retain accessible names; visible controls are ▶/Ⅱ, arrows,
⏭, × and 🎬. The gentle start hint points to ▶ rather than Next. Teaching words
remain large lesson content. The existing single video handoff remains; a denied
browser play exposes its existing explicit fallback. UI-TARS verify-only model
location, real CUA press and observed all-page/video outcome are separate proof.

## Preschool book presentation — 2026-11-01

Preschool-20 retains stable dialog/button IDs and story scheduler. The native
book fills available safe-area bounds. Primary labels are24px, teaching words
at least48px on short landscape phones/52px portrait and96px tablet. Last page
moves #storybook-watch into .intro-actions, hides redundant #intro-skip and keeps
#intro-close; accessible Play video name remains while visible text is ▶ Video.
Play story always restarts the full book; no autoplay/video/game clock changes.
Unavailable voice gets a separate landscape grid row, never over the words.
Manifest id/start_url/scope stay stable; no device-zoom guesses or frame busting.

## App menu and expanded scene — 2026-11-01

`#game-options` / `#video-options` open the same native `#options` dialog. Existing
wheel/language instances mount in #menu-character-panel/#menu-music-panel/
#menu-language-panel; section buttons #menu-characters/#menu-music/#menu-language.
`#close-options` Done and Escape return focus without resuming. Native dialog
focus containment; >=64px menu/choice/language targets; advanced controls remain
under #menu-advanced. No duplicate state, arbitrary media or new permissions.

`storytimeReview.setPresentation({expanded:boolean})` changes only framing.
`scenePresentation(width,height,expanded)` maps original960x540 coordinates into
an extended sky/soil viewBox. Art, hit targets and score share that mapping;
`freeze().svg` remains canonical960x540 for normalized feedback. Enter/exit,
marking and resume explicitly synchronize presentation. Whole-leg movement and
sky-open footprint use the same scene owner; no detached animated strip.

An observed cross-origin masked wrapper gets #open-full-app, a user-activated
_top link to the app's own current route. No automatic frame escape or open
redirect. Passing direct-origin checks does not certify eduit.org forwarding.


## Whole-story playback and film revision — 2026-11-01

`window.storytimeStorybook.play()` begins the whole story at plate0, or pauses
active playback. Opening alone never speaks. Skip/Close cancel without starting
video; completed playback closes once and starts the movie at0, with explicit
Play fallback on browser denial. Each new page visit's first video Play enters
the book unless explicitly dismissed. No child session records are transmitted.
`replay-timeline.json` revision same-engine-rescue-1 provides bounded event times
for movie action captions/voice; invalid/unavailable metadata leaves these off.
`storytime_replay.mjs` is offline input recording, not another game engine. Film
states use engine.advance/actorPose/gameWorld/scene. Runtime Foley references the
fixed15s game-foley.wav, not the replacement25s movie. Video remains original MAMMA
appearance, independent of cosmetic choices in the game. Re-render after source
changes; retain source/asset digests. Native device audio is a separate gate.


## Character/music sleeve — 2026-11-01

Existing `setAppearance` remains the only game-art mutation seam. Shorts-owned
`choice-wheel.mjs::mountChoiceWheel` handles allowlisted cosmetic choices;
`music-picker.mjs::mountMusicPicker` controls separate local background audio.
`window.storytimeMusic.status()` exposes selected/armed/pending/playing/message
for local review, not an analytics or dispatch API. Music Off defaults, explicit
Play only, quiet loop, no arbitrary source/child traces. Cue trace repair samples
live media time and labels callbacks versus acoustic evidence; original authored
offsets and English fallback remain. See choices contract and existing timing
review; full learning engine/worker admission are not implied.

> **Canonical 2026-10-28 handoff:** [Storytime conversation audit and Prometheus M2M handoff](docs/STORYTIME_RSI_CONVERSATION_AUDIT_AND_HANDOFF.md) is the current decision register. It supersedes conflicting historical statements below about video+game-only tiles, Earn Stars buttons, forced three-round quizzes, and autonomous runtime status. Existing site work is owned by a separate session; this PR documentation change must not overwrite that session's UI work.
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

### Fullscreen viewport contract — 2026-10-29
The viewer follows the visual viewport's dimensions and offsets at normal zoom,
including scroll, resize and foreground restoration. Changed bounds pause both
video and game; zoomed browser pages retain the layout viewport fallback. One
fullscreen CSS owner reserves one active control rail and a separately scaled
exit. Body-owned options/unlock share these viewport coordinates. Short landscape places the narrative beside the16:9 scene. No manifest,
install identity, game API or gesture interface changed.
