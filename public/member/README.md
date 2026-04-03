# FoundUPS Member Mall

**Status**: Invite-gated p.fMALL shell live
**Location**: `public/member/`

## Overview

`/member/` is no longer a placeholder member shell.

It is now the admitted-user Mall experience that sits behind the existing FoundUPS invite gateway:
- Clerk session check
- invite validation
- username claim
- then swipe into the Mall

The gateway is preserved. The change is the admitted state.

## Runtime Shape

```text
public/member/
|- index.html
|- foundup.html
|- css/member.css
|- css/account-concierge.css
|- css/mall-planes.css
|- css/mall-tile-field.css
|- js/gesture-engine.js
|- js/mall-planes.js
|- js/mall-tile-field.js
|- js/gesture-hints.js
|- js/account-concierge.js      <- Unified Red Dog plane (window.redDog)
|- js/red-dog-concierge.js      <- Legacy FAQ topics (deprecated)
|- mall-video-catalog.json      <- Video Mall data source
|- mall-catalog.json            <- Legacy FoundUp catalog (non-video)
|- tests/
|- README.md
|- INTERFACE.md
|- ModLog.md
```

### Primary Runtime Files

| File | Role |
|------|------|
| `account-concierge.js` | Unified Red Dog plane. Exposes `window.redDog` API. |
| `mall-tile-field.js` | Video Mall tile grid. Exposes `window.mallTileField` API. |
| `mall-planes.js` | FoundUp view planes. Exposes `window.mallPlanes` API. |
| `gesture-engine.js` | Touch/mouse gesture detection. |
| `red-dog-concierge.js` | Legacy FAQ topics. Will be removed when OpenClaw lands. |

## Current UX

### Mall Navigation
- swipe or scroll horizontally through FoundUps (desktop: mouse drag on carousel track)
- tap a tile to play/pause video in Mall context
- double-tap a tile to enter FoundUp view directly
- pinch-out on tile to expand into FoundUp's video field
- pinch-in (expanded) to collapse back to Mall

### FoundUp View
- swipe up to close, swipe left/right to navigate between FoundUps
- double-tap/click to save locally (heart indicator, localStorage)
- "Full details" link navigates to dedicated entry page (`foundup.html?id={id}`)

### Red Dog Unified Plane
- swipe down from top or tap avatar to open Red Dog plane
- Red Dog plane combines: identity, AI tools, channels, context briefing
- **AI Tools**: projection sort, density presets, motion mode
- **Channels**: "Populate My Mall", "Personal Mall", "Search Mall"
- **Search Mall**: text input for creator search (shell-local, dev/testing shim)

### Other
- first-time visitors see a gesture discovery overlay (auto-dismisses, shown once)
- invite codes remain available from Red Dog plane
- collapsible guide topics explain the Mall, gestures, readiness states

### Shell-Local vs OpenClaw

| Feature | Current (Shell-Local) | Future (OpenClaw) |
|---------|----------------------|-------------------|
| Search Mall | Text input filters by creator name | AI-powered semantic search |
| Personal Mall | Filters by `creator === '012'` | Personalized recommendations |
| Projections | Client-side sort | AI-ranked projections |
| Density | Manual preset selection | AI-controlled adaptive density |

> **Note**: Search Mall text input is a dev/testing shim. It will be replaced by OpenClaw-powered search when the gateway is ready.

## Out of Scope

- direct tenant execution
- wallet flows
- `/f/{foundup_id}` domain routing
- restoring the legacy member shell

## Source Of Truth

### Video Mall Catalog (Primary)

`mall-video-catalog.json` is the **primary data source** for the Video Mall.

Schema: `modules/foundups/docs/PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`

This catalog powers:
- Video Mall tile field (`mall-tile-field.js`)
- Creator search / field scope filtering
- Video queue for fullscreen player

### Legacy FoundUp Catalog

`mall-catalog.json` is a **legacy artifact** for non-video FoundUp cards.

Canonical source: `modules/foundups/pfmall/` (manifests + presentation overrides).

Regenerate:
```bash
python -m modules.foundups.pfmall.member_catalog_export
```

Do not hand-edit either catalog — edit source manifests, then regenerate.

---

*Last Updated: 2026-04-03*
