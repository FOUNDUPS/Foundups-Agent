# EDUIT interfaces

Status: source contracts observed at main a6fed6dd8; episode integration SPECIFIED.
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
