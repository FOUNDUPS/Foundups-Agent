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

### Shared responsive discovery (2026-10-18)

The default Mall uses vertical category groups with independently scrollable
horizontal tracks. Card width adapts to available viewport space; there is no
fixed count of visible rows and no six-tile cap. Resize/rotation uses CSS without
rebuilding the catalog. Explicit density controls still select the legacy grid;
**Adaptive category rows** returns to the shared browse mode. Pinch-out expands
one channel into its video field; pinch-in returns to the category rows.

Search Mall accepts short requests such as “show me videos on Fukui”, “show me
houses”, “show me cars” and “show me clothes”. It searches only loaded catalog
metadata and video metadata, with a small explicit English phrase/alias vocabulary.
Missing catalog content returns no results. It is not web search, a semantic model,
a voice service, a recommendation engine, or a new tenant app. Device keyboard
dictation can supply text; an authenticated future RedDog adapter can call the
same presentation API. No microphone or external AI endpoint is introduced.

Catalog entries remain the source of channel identity and capabilities. Native
cards, RedDog search and the bounded dispatcher share `mallTileField`; FoundUps
must supply catalog metadata and reuse this surface instead of copying it.
Categories are rendered from data, including future housing/product/creator entries.
Row offsets are saved locally alongside the existing outer scroll position.

### Mall Navigation
- swipe or scroll horizontally through FoundUps (desktop: mouse drag on carousel track)
- tap a tile to start lane autoplay through its video queue (Shorts-style)
- Enter FoundUp button to navigate to `/f/{foundup_id}` (tile or fullscreen)
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
- **Search Mall**: text input for local catalog discovery (topic, location, category, creator, video metadata)

### Other
- first-time visitors see a gesture discovery overlay (auto-dismisses, shown once)
- invite codes remain available from Red Dog plane
- collapsible guide topics explain the Mall, gestures, readiness states

### Shell-Local vs Resident RedDog/OpenClaw

| Feature | Current (Shell-Local) | Future (Resident RedDog/OpenClaw) |
|---------|----------------------|-------------------|
| Search Mall | Text input filters by creator name | AI-powered semantic search |
| Personal Mall | Filters by `creator === '012'` | Personalized recommendations |
| Projections | Client-side sort | AI-ranked projections |
| Density | Manual preset selection | AI-controlled adaptive density |

> **Note**: Search Mall text input is a dev/testing shim. A future authenticated
> RedDog thin-client adapter may use the principal-scoped OpenClaw execution
> layer. The current browser events and postMessage dispatcher are not a
> conversation transport and hold no model or work authority.

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

Catalog queries discover matching channels. Opening a matching channel retains its full video queue; the query does not filter individual videos within that queue.
