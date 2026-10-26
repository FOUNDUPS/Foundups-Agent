# EDUIT execution roadmap

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
