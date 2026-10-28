# EDUIT — Education Using Information Technology

## Adaptive learning content and formative assessment — 2026-10-28

[Adaptive learning-content contract](docs/ADAPTIVE_LEARNING_CONTENT.md) defines EDUIT's outcome/experience/production-RSI vision, reusable three-object content packs, post-game picture matching, separate learning points and off-session RSI. This is specified, not shipped. Reuse the existing game and review owners; do not collect child play traces for WRE learning.


## RSI architecture / new-session entrypoint — 2026-10-28

[Storytime RSI system architecture](docs/STORYTIME_RSI_SYSTEM_ARCHITECTURE.md) is the cross-module continuation map: eSingularity vision → EDUIT mission → Storytime tiles; WSP/WRE/FAM/HoloIndex/Kids Episodes/Mall ownership; current proof versus missing runtime authority. Use existing scaffolding, never a parallel engine. The [five-tile contract](docs/TILE_PRODUCTION_RSI.md) remains the acceptance oracle. First Little Shrew tile calibrates; the next actual tile must demonstrate retained improvement before autonomous RSI is claimed.


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


**FoundUp status:** local Story Time proof of concept implemented; domain deployment pending
**Product module:** Play EDUIT — adaptive learning through play  
**Historical educational vision:** eSingularity — learn anything, anytime, anywhere (LAAA)

EDUIT is the educational FoundUp and education-scoped sleeve of the existing Play FoundUps Mall. Its own identity does not imply a separate platform or duplicated shell. The existing `modules/foundups/esingularity/` application is a separate, live Fukui campaign and must not be modified by EDUIT work.

## Start here — current episode architecture

[Episode Mall architecture](docs/EPISODE_MALL_ARCHITECTURE.md) records 012’s
watch → play → Next direction, existing gestures, Red Dog, language cues and
parent-only membership proposal. Read [INTERFACE](INTERFACE.md),
[ROADMAP](ROADMAP.md) and [DEPLOYMENT](DEPLOYMENT.md) next.
EDUIT.org is intended to open the episode directly; this is specified, not deployed.

## Purpose and history

The 2007 EDUIT mission proposed freely accessible online education. The 2007 eSingularity initiative described **The Tool + The Content + The Experience**; the 2009 book and 2010 Malaysian prize proposal described adaptive games, learning-object assessment and identifying underserved talent. The 2023 EDUIT AI Teaching Touch Tablet and Baby0 discussions explored infant multilingual learning and explicitly proposed starting with an app. In the project's operator interpretation, Baby0 is an early conceptual ancestor of the OBAI/0102/Red Dog lineage; this is not a verified claim of uninterrupted software or model identity since 2001–2003. These are **historical proposals**, not evidence of measured outcomes.

[Historical lineage and primary sources](../../../docs/audits/pfmall_eduit/EDUIT_DISCOVERY_HISTORICAL_LINEAGE_2026-10-08.md)

## MVP: Play EDUIT

A browser-first, device-independent adaptive learning game. The initial product measures **game-specific learning progress**, not intelligence, diagnosis, or genius. Opportunity referrals and any profiling of minors require independent validation, parental/guardian consent, and human review. Do not collect child-identifying data for the initial synthetic demonstration.

## WSP 104 — Route namespace and tenant isolation

- Proposed `foundup_id`: `eduit` (requires registry reconciliation)
- Declared landing route: `/f/eduit`
- Declared app mount: `/f/eduit/app`
- Data namespace: `eduit`; no cross-tenant access to eSingularity or other FoundUps
- **Runtime:** local static proof of concept at `public/eduit`; no WSP 104 tenant route activation claimed

## AI hooks — contract only

| Hook | Status | Meaning |
|---|---|---|
| `get_status` | Planned | Report bounded operational status |
| `get_context` | Planned | Return consent-scoped game context |
| `navigate` | Planned | Navigate within EDUIT tenant routes |
| `launch_capability` | Planned | Launch a reviewed educational game |
| Shell handoff / return | Planned | Return safely to pfMALL |

## WSP 91 — DAEmon observability

No autonomous production worker exists. Planned outputs: health status, last action, error classification, recommended next action, queue/work state (N/A until worker exists), and telemetry under the `eduit` namespace. Never emit child identifiers or raw learner interaction data into telemetry.

## Autonomous operator continuity

0102 / Red Dog owns the next small verified implementation slices, WSP 97 closure and merge-to-main receipts. README and other module documentation are machine-operational context, not required reading for 012. Keep decisions, evidence, current state, and next steps inside the repository. No background execution is implied by this instruction.

## Earlier implementation slice (superseded by current roadmap)

1. Verify current FoundUp registry and schema; do not create a duplicate ID or public route.
2. Define a deterministic adaptive-difficulty game and synthetic tests.
3. Review accessibility, age-appropriate design, data minimization and consent.
4. Only then consider a public prototype. No DAO-driven model changes or child-data sharing in the MVP.

**Evidence status:** local landing, shared story/video scene and two-tap game implemented and tested. No validation study, child profiles, public deployment, autonomous worker or token. Registry production status remains unchanged.

## Linked educational media

[Kids Episodes](../kids_episodes/README.md) (`kids_episodes`) is the related story-to-linked-episodes FoundUp using existing YouTube production components. The local Story Time game now shares its scene with the episode video export. No autonomous story-production runtime is claimed. EDUIT retains its existing ID and independent scope.

## Story Time proof of concept

Source: `public/eduit/`. Read [deployment and local Codex handoff](DEPLOYMENT.md). Canonical planned domains are `eduit.org`, `ourstorytime.eduit.org`, and the redirect `eduit.foundups.com`. Kids Episodes remains `kids_episodes`; EDUIT remains `eduit`. No new FoundUp registration.

## Education Mall sleeve — operator direction

**Observed:** `public/member/INTERFACE.md` and `public/member/index.html` already
provide a registered product selection in the shared Mall shell. Move2Japan
reuses the tile field, controllers, gestures and product-scoped state. This is
the architectural precedent for EDUIT, not a second catalog application.

**Specified by 012:** EDUIT itself is discoverable as a FoundUp in the main Mall.
Inside EDUIT, discovery/search is restricted to educational content; unrelated
FoundUps results must not leak through global search, restored state or Red Dog
discovery. Some story records may be discoverable only within EDUIT's projection.
This projection boundary is distinct from authorization: hiding a public JSON
record is not access control. Reuse existing admission owners for protected data.

**Proposed, not implemented:** rows represent linked stories/epochs, horizontal
tiles their ordered playable episodes, and vertical travel moves through the
chronology. Divergent branches may follow a common ancestor. Completing a story
line could unlock the next level. Exact axes and progression rules remain open;
012 is exploring the idea, not authorizing a full progression system now.
Evolutionary ancestry and dates must be checked before becoming educational
claims; a fictional Little Shrew character is not proof of a specific ancestor.

**Earlier slice:** retained one Little Shrew game/video and an introduction
landing. The current architecture below supersedes introduction-first entry. Neither constitutes the integrated education Mall.
Do not build a duplicate PWA, generic catalog, learner account or unlock service
for this proof of concept. Future work should add a bounded EDUIT product adapter
to the existing shell, with tests that out-of-scope catalog items cannot appear.

**WSP 97 closure:** exact owner/adjacent product interfaces retrieved; existing
product reuse chosen over a new shell. Documentation/design change only for the
Mall sleeve. No production routing, PWA integration or unlock behavior claimed.

## Watch, play, progress — local parent report proposal

**012 proposal, not implemented:** a child watches the episode, plays its
corresponding game, then may repeat an optional faster challenge. The learning
objective is tied to the story: notice the cue, choose the appropriate action,
and complete the sequence. Speed is a separate challenge, not proof of learning.
Successful repetitions could gradually shorten the response window, within
reviewed limits; misses should ease the challenge or offer untimed practice.
Story access should not depend on reaction speed alone. Keep practice and an
accessible progression path available. Exact difficulty rules remain undecided.

**Observed now:** `public/eduit/storytime/engine.mjs` has two fixed four-second
cue windows and untimed practice. `game.js` pauses on hidden pages. There is no
adaptive speed, persistent progress store or parent report in this prototype.

**Proposed parent view:** describe a learning/progress curve, without assuming
it is a mathematical parabola. Show completed sequences, attempts, success rate,
challenge level and response-time trends compared with that child's own earlier
play. Separate first attempts from practiced attempts and compare like-for-like
game versions, difficulty, input method and device conditions. Show the number
of observations and insufficient-data states; do not infer a trend from one try.
Input timing includes rendering, device latency, anticipation and familiarity.
Use an actual monotonic timing measurement for future reporting, not the current
animation clock whose per-frame increment is capped. Paused/hidden attempts must
not produce misleading reaction-time results.

**Exploratory goal:** 012 is interested in whether unusual strengths, including
fast responses, might become visible to parents. No age percentile, 'gifted',
IQ, diagnostic or innate-ability label is justified by this game. Age-relative
comparisons would require separate suitable reference data and validation;
they are not part of this proof of concept. Do not gather birthdays or build a
cross-child dataset to support this speculative feature.

**Proposed data boundary:** optional progress remains in browser/device-local
storage, processed locally for the parent's view. No server upload, cross-family
comparison, advertising use, telemetry payload, agent memory ingestion or model
training from children's play. No account or identifying child details required.
Parent controls should enable/disable recording and clear all recorded progress;
any export must be an explicit parent action, never an automatic sync. Local
browser storage may be cleared and is shared by users of that browser profile;
it is not guaranteed backup or a private per-child identity boundary. Explain
that limitation and separate optional local player slots only if needed later.
The no-upload claim concerns play records, not ordinary hosting requests or an
external YouTube visit. Verify network behavior before making privacy claims.

**Integration/scope:** use EDUIT's adapter within the existing Mall and reuse its
appropriate storage infrastructure after checking ownership and isolation. Do
not mix child progress with account data or the global Mall's browsing history.
This turn preserves the design only: no tracker, database, speed ladder or
report UI is activated. A future bounded implementation needs synthetic tests
for timing, difficulty bounds, pause/resume, deletion and no-network leakage.

## Child FoundUps, discovery scope and return navigation

**012 direction:** the main Play FoundUps Mall shows EDUIT. EDUIT's education
Mall shows its own educational child FoundUps, such as Us Story Time and a
memory-game project once its existing identity is recovered. Educational child
FoundUps should not independently populate the general Mall. They remain part
of the same system; do not fork the platform or renumber existing canonical IDs.

**Observed gaps:** the canonical registry currently has `kids_episodes`, but no
`eduit` entry, despite EDUIT's module manifest. `public/member/mall-catalog.json`
puts Kids Episodes in `ai-education`. The registry schema has entity type,
public-surface and portfolio status, but no parent-FoundUp or education discovery
scope contract. A category alone cannot enforce the requested boundary. The
`parent_foundup_index` in the tile field relates an expanded video's UI position
to a tile, not durable registry ancestry. Simulator DAO parentage is also not the
production discovery owner. The public catalog projector reads the canonical
registry; do not hand-edit its output as a substitute for a registry contract.

**Proposed minimal contract, not activated:** retain canonical identity and
entity type; express parent relationship and allowed discovery surfaces as
separate, schema-validated metadata. EDUIT is visible in general discovery;
its educational children are visible in EDUIT discovery. Keep `ai-education` as
a descriptive category, not an authorization rule. Validate known parents,
no cycles/self-parenting and stable IDs. Existing unrelated FoundUps retain their
current behavior. Reconcile EDUIT's manifest into the canonical registry through
its existing intake owner before creating child entries. Resolve whether Our
Story Time is the public learning surface of `kids_episodes` or needs a distinct
identity; do not silently duplicate the production FoundUp to obtain a tile.

Both shared-Mall and public-directory projections, search/Red Dog discovery,
restored view state and suggestions need the same scope boundary. Scope-specific
projection must exclude unwanted records before presentation; hiding a tile with
CSS is insufficient. Protected records still use existing authorization. A
public educational game need not be inaccessible by direct URL merely because
it is excluded from general discovery.

**Navigation:** game → its parent education collection, preserving selected
story, row and scroll position; education collection → main Play FoundUps Mall.
Use existing product state/return owners, with bounded allowlisted destinations,
not arbitrary return URLs or browser history that may lead outside the system.
The proof of concept now has an explicit 'Back to EDUIT' link to the existing
introduction page. Returning to an actual restored education Mall awaits its
shared-shell product integration; no new route is claimed active.

**Memory-game recovery — verified:** the existing FoundUp is **Memory Horizon**,
canonical candidate ID `memory_horizon`, module `modules/foundups/memory_horizon/`.
Its documentation/manifest and registry candidate are on the existing branch
[`docs/memory-horizon-wsp109-intake-20260920`](https://github.com/FOUNDUPS/Foundups-Agent/tree/docs/memory-horizon-wsp109-intake-20260920/modules/foundups/memory_horizon),
not in the main-branch checkout inspected earlier. The branch README and onboarding
audit identify `SPECIFIED_NOT_IMPLEMENTED`: a branching adventure, unique events,
delayed recall probes and a retention timeline. Product POC issue
[#1821](https://github.com/FOUNDUPS/Foundups-Agent/issues/1821), RSI build experiment
#1825 and deferred assistive companion #1823 are linked in that source packet;
issue links do not prove completion. No runnable game or deployed tile was found
in the inspected module tree. Reconcile the existing branch/PR before importing
or extending it; preserve its ID and design work instead of registering a new
'Memory' FoundUp. 012's new direction places its educational game under EDUIT;
the separately proposed assistive companion is not automatically reassigned.
No clinical or recovery claim follows from the game. Keep personal family/medical
history out of public catalog copy and development receipts.

**Acceptance for a future integration slice:** one EDUIT entry in general Mall;
educational child tiles only within EDUIT; no duplicate IDs or state leakage;
exit restores the correct collection position; direct-entry exit has a safe
fallback; unknown product scopes fail closed. Current change documents this
contract and adds the explicit POC exit only; registry/projection migration and
Memory Horizon branch integration remain outstanding.


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
