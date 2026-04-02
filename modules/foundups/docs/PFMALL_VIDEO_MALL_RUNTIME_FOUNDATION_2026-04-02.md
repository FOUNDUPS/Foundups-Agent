# p.fMALL Video Mall Runtime Foundation

**Version**: 1.0.0  
**Date**: 2026-04-03  
**Status**: Runtime foundation (phase 1 landed)  
**Owner**: 0102

---

## 1. Purpose

Define the next correct product layer for the admitted FoundUps suite:

- `/` = gated front door
- `/member/` = admitted Mall
- Mall = low-chrome, gesture-zoned, video-first discovery field
- each tile = a FoundUp backed by a queue of videos
- tap = play
- double-tap = go through the door into the FoundUp
- top zone = account/profile/self
- bottom zone = Red Dog / digital twin / AI tools
- middle zone = the Mall field itself
- later, `SoftProto` = movable/reconfigurable interface zones and controls
- later, `/f/{id}` = true external FoundUp route family

This document exists to correct the earlier framing:

The Mall is not just a discovery plane.  
The Mall is a **video engagement space**.

The FoundUp interior is not just an entry shell.  
It is a future **living agent world** centered on a visible FoundUp Core.

---

## 2. Relationship To Existing Contracts

This note does not replace the current active contracts.

It sits beside them:

- `PFMALL_MALL_NAVIGATION_CONTRACT.md`
  - current fixed Mall shell grammar
  - current live runtime truth
- `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`
  - current route family and shell-to-FoundUp boundary
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
  - current Red Dog identity truth
- `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
  - future configurable interface/runtime layer

Status (2026-04-03):

- `PFMALL_MALL_NAVIGATION_CONTRACT.md` is now v2.0.0 Runtime Contract
- tap = play/pause, double-tap = enter, pinch-out/in, Snap/Glide — all landed
- this document and the navigation contract are now aligned

---

## 3. Current Repo Truth

### 3.1 Runtime (Landed)

- gateway
- admitted Mall shell
- top / middle / bottom anchor structure
- Red Dog shell presence
- account / concierge plane
- transitional FoundUp entry shell
- `/f/{id}` bridge structure
- localhost Mall dev harness
- stable shell and tests
- **video-backed tile field** (`mall-tile-field.js`)
- **tap = play/pause** in Mall context
- **double-tap = enter FoundUp**
- **pinch-out = expand FoundUp into video field**
- **pinch-in = collapse back to Mall**
- **Snap motion mode** (default discrete paging)
- **Glide motion mode** (fluid scroll override)
- **Density presets** (2x3, 3x4, 3x5, 5x8 — AI-controlled)
- **Field scope APIs** (`setFieldScope`, `projectPersonalMall`, `searchByCreator`, `filterByCategory`, `filterByTag`)
- **Search Mall concierge wiring** (search input UI, wired to field scope)
- **Manifest projection** (tags, category filter)
- **Fullscreen player** shell

### 3.2 Future (Not Yet Real)

- true AI-driven field repopulation
- real FoundUp interior as a living agent world
- actual `SoftProto` runtime for movable UI / configurable zones
- save / share / follow persistence
- tokenomic execution
- live cross-platform ingestion

Current insertion points that already exist:

- `public/member/index.html`
  - admitted Mall shell and anchor zones
- `public/member/js/mall-tile-field.js`
  - tile interaction and projection shell
- `public/member/js/mall-planes.js`
  - preview / handoff plane
- `public/member/js/gesture-engine.js`
  - shared swipe / tap / double-tap gesture detection
- `public/member/js/account-concierge.js`
  - Red Dog shell-side agent surface
- `public/member/foundup.html`
  - transitional FoundUp entry shell
- `public/f/index.html`
  - route bridge into transitional entry

---

## 4. End-State Product Model

### 4.1 Mall

The Mall should become:

- a phone-first visual browsing surface
- a field of square video-backed FoundUp tiles
- a low-chrome interaction space
- a constrained, topic-stable browsing environment
- an AI-addressable discovery plane

### 4.1.1 Default vs General Rule

The Mall must support two truths at once:

- default product posture = startup discovery
- default media unit = video

That means the first strong runtime should feel like:

- startup FoundUps by default
- video-backed browsing by default

But the Mall itself must remain a general discovery field.

It should later be able to project:

- startup FoundUps
- creators
- channels
- LinkedIn account lanes
- X account lanes
- geo-based lanes
- category collections
- other indexed objects

Rule:

- the field grammar stays stable
- the projection changes
- Red Dog / the agent is what changes the projection

So the product default is not "anything."

The product default is:

- startup FoundUps
- shown through videos

But the architecture must not hardwire the Mall to startups forever.

### 4.2 FoundUp Tile

Each tile should represent:

- one FoundUp
- one constrained queue/series of videos
- one creator/team/channel/profile/entity lane

A tile is not just a card.

It is a media-backed entry point into a FoundUp topic lane.

### 4.3 FoundUp Identity Rule

Original FoundUps definition:

- a `FoundUp` is a founder with an idea

In the Mall/video runtime, that means a FoundUp can be represented through a
specific media/account lane owned by that founder or entity.

Examples:

- Move to Japan videos = one FoundUp
- AntifaFM videos = one FoundUp
- a LinkedIn account or sub-account = one FoundUp
- an X account = one FoundUp

Important:

- one person/entity may expose multiple FoundUps
- one content account does not need to stand for the whole person
- each FoundUp should stay idea/lane-scoped rather than collapsing all output
  from one person into one giant profile tile

That keeps the Mall aligned with the original product model:

- the Mall indexes founders/ideas through visible media lanes
- the field is made of FoundUps, not generic social accounts

### 4.4 FoundUp Interior

Double-tap should eventually enter a real FoundUp interior, not a dead dashboard.

The interior should become a living system where the user can:

- watch work happening
- inspect state
- assign compute
- inspect eligible task surfaces
- later descend into tasks, code, and agent collaboration

Working planning name:

- `FoundUp Core`

No more naming should be invented in this slice unless runtime implementation forces it.

---

## 5. Zone Model

### 5.1 Top Zone

Purpose:

- profile
- account
- preferences
- personal context

Interactions:

- tap = open profile/account
- swipe-down = open top plane
- swipe-up = close top plane

### 5.2 Middle Zone

Purpose:

- Mall field
- FoundUp tiles
- video browsing
- playback entry

Interactions:

- swipe in field = move through Mall grid / projection
- tap tile = play/pause current or top video in Mall context
- double-tap tile = enter FoundUp
- corner expand control = fullscreen current video
- pinch-out on FoundUp tile = expand that FoundUp into its video field
- pinch-in on expanded video field = collapse videos back into the parent FoundUp

### 5.2.1 Field Motion Mode

The middle field should support two motion modes:

- `Snap` = default
- `Glide` = temporary fluid override

`Snap` means:

- left/right behaves like iPhone screen-to-screen paging
- up/down moves in discrete depth/history/relevance steps
- the field feels structured and magnetic

`Glide` means:

- the same swipe directions keep the same meaning
- movement becomes fluid rather than page-snapped
- the user can roam the current projection more freely

Rule:

- motion mode changes how the field moves
- motion mode does not change what directions mean
- `Snap` is the product default
- `Glide` is a temporary Red Dog / AI-tools override

### 5.2.2 Middle-Field Density

The middle field should support AI-controlled density presets.

Examples:

- `2 x 3`
- `3 x 4`
- `3 x 5`
- `5 x 8`

Rule:

- top zone and bottom zone stay protected
- density changes only affect the middle field
- Red Dog / the agent can change density as part of projection
- the user may choose or save a preferred preset through Red Dog tools
- density is a projection/view concern, not a user-editable layout system

This should feel closer to a smart media browser than a fixed dashboard grid.

### 5.3 Bottom Zone

Purpose:

- Red Dog
- user digital twin
- AI management tools

Interactions:

- tap = open Red Dog interaction plane
- hold = talk
- swipe-up = open bottom AI tools plane
- swipe-down = close bottom AI tools plane

### 5.3.1 Bottom AI Density Control

Density control belongs in the bottom AI tools plane.

That is the right placement because:

- density is part of Mall projection/view logic
- Red Dog is the projection-control surface
- the Mall should stay low-chrome until the user asks for tools

Recommended model:

- swipe-up on Red Dog opens AI tools
- motion mode control appears there
- density presets appear there as quick controls
- the user can store a preferred preset
- Red Dog can also set density through AI commands

Motion mode options:

- `Snap`
- `Glide`

Behavior:

- `Snap` is the default
- the user can switch to `Glide` inside the bottom AI tools plane
- when the user returns to `Snap`, the Mall settles to the nearest valid page /
  cluster position

Optional compact affordance:

- while AI tools are open, a small side bar or scrub control may appear for
  fast density changes
- while AI tools are open, a compact motion-mode control may also appear there
- it should be temporary, not permanent shell chrome
- once the user chooses a preset, that preset remains active until changed

Examples:

- `2 x 3`
- `3 x 4`
- `3 x 5`
- `5 x 8`

---

## 6. Gesture Scope Model

Gesture meaning must stay stable by scope.

### 6.1 FoundUp Field Scope

FoundUp field semantics:

- swipe-up / swipe-down = move through depth / distance / relevance
- swipe-left / swipe-right = shift across adjacent clusters / categories / contextual planes
- default motion = snapped paging
- optional AI-tools override = fluid glide through the same projected field
- tap tile = play/pause current or top video in that FoundUp
- double-tap tile = enter FoundUp
- corner expand control = fullscreen current video
- pinch-out on FoundUp tile = expand that FoundUp into all of its videos

### 6.2 Expanded FoundUp Video Field

When a FoundUp expands, the middle field is repopulated with that FoundUp's
videos.

Expanded video-field semantics:

- each tile = one video from the current FoundUp queue
- tap video tile = play/pause that specific video
- corner expand control = fullscreen that specific video
- double-tap video tile = enter the parent FoundUp at that context
- pinch-in = collapse all videos back into the parent FoundUp
- the queue remains constrained to that FoundUp unless Red Dog widens scope

### 6.3 Fullscreen Video Scope

Fullscreen is not a new feed.

It is a larger view of the same FoundUp-constrained queue.

Fullscreen semantics:

- swipe-up = next video in the same FoundUp queue
- swipe-down = exit fullscreen / return to the previous Mall state
- swipe-left = save hook
- swipe-right = dismiss / delete hook placeholder
- pinch-in = return from fullscreen
- tap = show/hide fullscreen chrome

### 6.4 Fullscreen Queue Rail

Fullscreen should support a temporary queue rail, not a permanent cluttered
chrome block.

Structure:

- top bar = back, share, like/save, info, hide/delete, more
- center = active video
- bottom rail = upcoming/adjacent videos from the same FoundUp queue

Behavior:

- bottom rail is hidden by default
- swipe-up from the bottom edge reveals the rail
- user can thumb-scrub or tap a video in the rail
- selecting a rail item should autoplay that item
- after inactivity, the rail auto-hides

This is a queue browser, not a global feed takeover.

Rules:

- no topic drift
- no random autoplay derailment
- no cross-FoundUp jump unless explicitly commanded

### 6.5 Runtime Status

**RESOLVED** as of 2026-04-03.

Current runtime (landed):

- tap = play/pause
- double-tap = enter
- pinch-out = expand FoundUp into video field
- pinch-in = collapse back to Mall
- Snap = default motion mode
- Glide = temporary AI-tools override

The semantic migration from `tap = inspect` to `tap = play` is complete.

---

## 7. Object / Scope Inventory

Using the current Tesseract interaction structure:

```text
app.member
  └─ plane.mall
      ├─ module.topBar
      │   └─ object.userIcon
      ├─ module.tileField
      │   └─ object.foundupTile[*]
      ├─ module.videoPlayer
      │   └─ object.activeVideo
      └─ module.redDog
          └─ object.redDogAnchor
```

Current repo status by scope:

- `module.topBar`
  - real
- `module.tileField`
  - real
- `module.redDog`
  - real
- `module.videoPlayer`
  - not yet real
- `plane.foundupInterior`
  - not yet real

Future requirement for every scope:

- default behavior
- local override
- AI addressability
- later `SoftProto` customization where allowed

---

## 8. Video-Backed FoundUp Data Model

The current Mall catalog is metadata-only.

The first video-backed runtime should extend the FoundUp shell data with a queue model.

Minimum record shape:

```json
{
  "foundup_id": "move2japan",
  "title": "Move to Japan",
  "creator": "012",
  "source_type": "youtube_channel",
  "category": "travel",
  "tags": ["japan", "relocation", "life"],
  "geo": "Fukui",
  "status": "active",
  "video_count": 12,
  "poster_url": "/media/posters/move2japan.jpg",
  "videos": [
    {
      "video_id": "v001",
      "title": "Episode 1",
      "thumbnail_url": "/media/thumbs/move2japan-001.jpg",
      "poster_url": "/media/posters/move2japan-001.jpg",
      "embed_url": "https://www.youtube.com/embed/...",
      "source_url": "https://www.youtube.com/watch?v=...",
      "timestamp": "2026-04-01T00:00:00Z",
      "duration_seconds": 54
    }
  ]
}
```

Required phase-1 fields:

- `foundup_id`
- `title`
- `creator/entity`
- `source_type`
- `tags/category`
- `geo` if available
- `video_count`
- `videos[]`
- `poster/thumbnail`
- `source_url` or `embed_url`
- `timestamp`
- `status`

Fields that can remain stubbed in phase 1:

- relevance score
- affinity score
- tokenomic yield
- follow/join metrics
- agent workload state

---

## 9. Demo Content Population Strategy

Use real 012 content where possible, but do not begin with live ingestion complexity.

### 9.1 Safest Prototype Path

Use a shell-owned manifest/static dataset first.

That dataset should be curated from real 012 assets, such as:

- Move to Japan
- AntifaFM
- FoundUps
- UndaoDu
- selected LinkedIn account/sub-account FoundUps
- selected X account FoundUps
- other known 012 lanes that already have stable media assets

The rule is:

- each channel/account/profile lane becomes its own FoundUp when it maps to a
  distinct founder+idea lane
- do not flatten all 012 presence into one creator record

### 9.2 Existing Hook Surfaces

Existing repo surfaces that indicate usable content hooks already exist:

- `docs/audits/VIDEO_INDEXING_ECOSYSTEM_AUDIT_20260116.md`
  - confirms a stable video indexing ecosystem exists elsewhere in the repo
- `modules/foundups/pfmall/member_catalog_export.py`
  - existing shell-side export path for Mall catalog data
- `modules/communication/moltbot_bridge/src/pfmall_catalog.py`
  - shell-side catalog loading path
- current `public/member/mall-catalog.json`
  - existing shell-owned demo catalog pattern

### 9.3 Rule For Phase 1

Do:

- use real 012 video/content references
- export or hand-curate a stable manifest
- keep the first video Mall shell-owned

Do not:

- start with live YouTube API ingestion
- start with LinkedIn scraping/runtime dependency
- start with cross-platform sync
- start with multi-tenant external feed federation

---

## 10. FoundUp Interior Direction

Double-tap should continue to mean:

- go through the door into the FoundUp

But the long-term target is not a static entry sheet.

The target is a living FoundUp interior centered on the FoundUp Core:

- visible activity system
- current state / stage
- agent work visibility
- user-level task assignment entry
- future drill-down into task/code/agent collaboration

For now:

- `public/member/foundup.html` stays transitional
- do not pretend the real living core already exists

---

## 11. Red Dog / 0102 Addendum

Red Dog is not decoration.

Red Dog is the user's persistent `0102` agent surface across the admitted suite.

### 11.1 Identity

- Red Dog = the user's digital twin / best-friend agent
- OpenClaw = Red Dog's action/body layer
- wardrobe / skills wardrobe = role and mode system

Red Dog may later shift stance by context:

- companion
- concierge
- patrol / guard dog
- builder / worker
- researcher
- inbox / task helper

### 11.2 Core Rule

Every meaningful surface must have AI hooks.

That includes:

- Mall field
- video/player layer
- FoundUp entry layer
- FoundUp interior
- account/concierge plane
- top/bottom option planes
- future `SoftProto` controls

### 11.3 Required Hook Families

Even when not fully active yet, the hook paths should exist conceptually.

Examples:

- `search_foundups_by_category`
- `search_foundups_by_creator`
- `search_foundups_by_geo`
- `sort_current_projection`
- `project_default_startups`
- `project_default_videos`
- `project_by_creator`
- `project_by_geo`
- `project_by_category`
- `show_related_foundups`
- `open_foundup`
- `open_profile_plane`
- `open_ai_tools_plane`
- `assign_compute_to_foundup`
- `save_video`
- `share_video`
- `follow_foundup`
- `grab_all_my_linked_profiles`
- `populate_my_mall`

### 11.4 Account / User Future

The account/concierge plane must remain compatible with future user-level AI population actions such as:

- "grab all my stuff"
- "fill in my profiles"
- "connect my accounts"
- "show everything I'm working on"

For this phase:

- preserve shell-owned truthful hooks only
- do not fake autonomy that does not exist yet

### 11.5 Search / Projection Rule

Red Dog should be able to search and reproject the Mall through structured hooks.

Primary early axis:

- category

Examples:

- show startup FoundUps
- show restaurants
- show Move to Japan related FoundUps
- show FoundUps in Fukui
- show everything for UndaoDu

Current planning rule:

- default category posture = startups
- default media posture = videos

But the search/projection system must remain broad enough to sort or project any
indexed object family later.

Do not rebuild the Mall grammar for each content type.

Change the projection, not the field logic.

---

## 12. Implementation Status

### Phase 1 — LANDED (2026-04-03)

| Item | Status |
|------|--------|
| video-backed FoundUp manifest | ✓ RUNTIME |
| queue counts on Mall tiles | ✓ RUNTIME |
| tile poster/thumbnail media layer | ✓ RUNTIME |
| snapped field motion (Snap default) | ✓ RUNTIME |
| Glide override in Red Dog AI tools | ✓ RUNTIME |
| Mall-local active video runtime | ✓ RUNTIME |
| expanded FoundUp video-field mode | ✓ RUNTIME |
| explicit fullscreen entry control | ✓ RUNTIME |
| AI-controlled density presets | ✓ RUNTIME |
| local active-video gesture scope | ✓ RUNTIME |
| fullscreen video mode | ✓ RUNTIME |
| Red Dog shell hook for category projection | ✓ RUNTIME |
| Field scope APIs (`setFieldScope`, `searchByCreator`, etc.) | ✓ RUNTIME |
| Search Mall concierge wiring | ✓ RUNTIME |

### Phase 1 — Stubbed (Not Blocking)

| Item | Status |
|------|--------|
| save / share / follow persistence | STUB |
| AI field repopulation execution | STUB |
| tokenomic execution | STUB |
| FoundUp interior core runtime | STUB |
| live cross-platform ingestion | STUB |

### Next Phases

| Phase | Focus |
|-------|-------|
| Phase 2 | Red Dog true field reprojection by creator/geo/category/query |
| Phase 3 | Real FoundUp living core |
| Phase 4 | First bounded `SoftProto` runtime spike |

---

## 13. Execution Order

### Completed

1. ✓ Build the Mall as a real video-backed system (Phase 1 landed 2026-04-03)

### Next

2. Make Red Dog reproject the field by creator / geo / category / query
3. Turn the FoundUp interior into the first real living core
4. Only then do the first bounded `SoftProto` runtime spike

Bottom line:

The video Mall is real.  
The first real customizable room is not next.  
Next is true AI-driven field repopulation.
