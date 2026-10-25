# EDUIT interfaces

Status: standalone Story Time episode/PWA implemented; full Mall integration remains SPECIFIED.
Canonical product design: [Episode Mall architecture](docs/EPISODE_MALL_ARCHITECTURE.md).

## Existing local prototype

- `public/eduit/storytime/engine.mjs`: deterministic two-cue game and practice.
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

## Standalone Story Time PoC (2026-10-26)

Entry: `https://storytime.eduit.org/` redirects to `/storytime/`. `/about/`
retains EDUIT introduction; `/review/` mounts the existing Shorts review UI.
These are public static documents. There is no public rendering, shell,
provider API, voice dispatch, auth or interaction upload endpoint.

Local integration references (not registered catalog records):

| Reference | Value |
|---|---|
| foundupId / foundup_id | `eduit` |
| productionFoundupId / production_foundup_id | `kids_episodes` |
| publisherId / publisher_id | `us_story_time` (existing YouTube binding) |
| collectionId / collection_id | `storytime` |
| storyId / story_id | `little_shrew` |
| episodeId / episode_id | `little_shrew_poc_001` |
| locale | `en` |
| revision | Immutable content digest; visible in episode/review, `/revision.json` |

`game.js` exports frozen `episodeContext` and `storyTimeActivity`. This is a
local page adapter using fixed DOM IDs, not a remote dispatch API or completed
Mall product adapter. `activity.mjs` wraps the existing deterministic engine.

| Method | Semantics |
|---|---|
| mount() | Idempotent mounted state; never starts cues; disposed instances cannot remount |
| start() | Explicit transition from ready; pauses video before starting cues |
| pause() | Freezes active cue/animation and sound; preserves remaining cue time |
| resume() | Explicit continuation; pauses video, resets frame delta; hidden page cannot resume |
| reset() | Pauses media; returns same episode to idle, clears the attempt; no start |
| snapshot() | Frozen local state and refs; no persistence or network transmission |
| dispose() | Idempotent frame/listener/audio cleanup; prevents subsequent activity/completion |

Video play pauses the game. Play/Resume/Retry pause the video. Hidden pages and
expand/back transitions pause; return requires explicit Resume. Pointer clicks
and native keyboard buttons share the same handlers. Practice removes cue
limits; timeout and success both permit unlimited retry. Replay story only
restarts video. No Next destination exists; More stories coming is explicit.

A successful attempt dispatches non-bubbling `storytime:complete` on `#game-panel`
once, with frozen references above plus `status: completed`. No child identity,
tap history, timing profile or analytics payload. Retry/reset allows one result
for the next attempt. No completion after disposal. Current page has no network
or memory listener for this event.

The deployed return targets are fixed same-origin `/about/` and `/storytime/`,
plus explicit ordinary project/channel links. No return URL is accepted from
query parameters. Future Mall return must use its existing allowlisted return
owner and state contract. New origin means independent storage, service workers
and authentication; FoundUps login is not inherited. Future cross-origin
messaging must validate exact origin, source and payload.

Build `/revision.json` binds those same references to immutable asset paths.
The worker caches only the bounded episode/game shell; video/range requests
remain network-only. Updates wait for explicit Update & restart. See
[DEPLOYMENT](DEPLOYMENT.md) for origins, retention and rollback requirements.
