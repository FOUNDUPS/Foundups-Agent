# p.fMALL Navigation Contract

**Version**: 2.0.0
**Date**: 2026-04-03
**Status**: Runtime Contract

---

## 1. Purpose

p.fMALL is an **AI interaction space** — a new way of interacting with AI and the world. Video is the default surface, but the paradigm extends to any content type: documents, community, FoundUps. The same interaction model (pinch, zoom, navigate) works everywhere, with AI mediating all engagement. Built for FoundUps first, with hooks into all content. Videos are the catalog layer — they tell each FoundUp's story.

This document defines the Mall as **fixed navigation infrastructure**.

The Mall is not a SoftProto customization surface.

The Mall is a discovery map. Users navigate it. They do not edit it.

SoftProto customization begins **inside FoundUp interiors**, not in the Mall shell.

---

## 2. Mall Anchor Model

The Mall has three fixed vertical zones:

```
+---------------------------+
|         TOP ANCHOR        |  <- Account / Profile / Self
|---------------------------|
|                           |
|       MIDDLE FIELD        |  <- Mall / FoundUps / Navigation Space
|                           |
|---------------------------|
|       BOTTOM ANCHOR       |  <- Red Dog / Digital Twin / Agent
+---------------------------+
```

### 2.1 Top Anchor

**Owner**: Account surface
**Contains**: Avatar trigger, user handle, account access
**Behavior**: Swipe-down from top opens account plane
**Fixed**: Yes - position and trigger are not user-configurable

### 2.2 Middle Field

**Owner**: Mall navigation
**Contains**: FoundUp cards, discovery space, navigation field
**Behavior**: 2D map navigation (see Section 4)
**Fixed**: Yes - navigation grammar is not user-configurable

### 2.3 Bottom Anchor

**Owner**: Red Dog / Concierge
**Contains**: Red Dog trigger, concierge panel
**Behavior**: Tap opens concierge panel
**Fixed**: Yes - position and trigger are not user-configurable

---

## 3. Mall vs FoundUp Interior

| Attribute | Mall | FoundUp Interior |
|-----------|------|------------------|
| Customizable layout | NO | YES (SoftProto) |
| Edit mode | NO | YES |
| Gesture override | NO | YES (object-scoped) |
| Module repositioning | NO | YES |
| AI projection | YES | YES |
| User navigation | YES | YES |
| Fixed grammar | YES | Partial (escape/close locked) |

**Rule**: The Mall is infrastructure. The FoundUp interior is user-owned space.

---

## 4. Mall Navigation Grammar

### 4.1 Axis Semantics

The Mall is a navigable discovery field, not a linear feed.

```
Y axis = distance / relevance gradient
         up = further / less relevant
         down = nearer / more relevant

X axis = category / cluster / similarity band
         left = shift to adjacent cluster
         right = shift to adjacent cluster
```

### 4.2 Gesture Bindings (Runtime)

| Gesture | Mall Action | Status |
|---------|-------------|--------|
| swipe | Navigate: snapped field motion (default) or glide (override) | RUNTIME |
| tap or click video tile | On wide desktop entry and in the HPC phone grid, open the shared player at the selected tile. Other category rows use their existing inline preview. A lane starts at its first clip. An expanded tile selects its own clip. | RUNTIME |
| tap or click non-video tile | Open the FoundUp quick view or the property listing detail. | RUNTIME |
| hover tile on desktop | Show available tile controls. | RUNTIME |
| Expand button | Open the shared full player for the selected video or lane. | RUNTIME |
| Enter button | Navigate to `/f/{foundup_id}` (WSP 104 canonical) | RUNTIME |
| pinch-out on an ordinary video lane | Expand the FoundUp into its video field. Desktop Ctrl+wheel up uses the same handler. | RUNTIME |
| pinch-in in the expanded field | Collapse back to the Mall. Desktop Ctrl+wheel down uses the same handler. | RUNTIME |
| long-press | Reserved (future: quick actions) | RESERVED |

### 4.3 Motion Modes (Runtime)

| Mode | Behavior | Status |
|------|----------|--------|
| Snap (default) | Discrete paging like iPhone home screens | RUNTIME |
| Glide | Fluid scroll for browsing (AI-tools override) | RUNTIME |

Set via `mallTileField.setMotionMode('snap')` or `mallTileField.setMotionMode('glide')`.

### 4.4 Keyboard Bindings (Fixed)

| Key | Mall Action | Status |
|-----|-------------|--------|
| Arrow Up | Navigate: further | FIXED |
| Arrow Down | Navigate: nearer | FIXED |
| Arrow Left | Navigate: cluster left | FIXED |
| Arrow Right | Navigate: cluster right | FIXED |
| Enter on a video tile | Match click on wide desktop and HPC phone entry. Other ordinary rows open the full player. | RUNTIME |
| Space on a tile | Use the tile's tap action. | RUNTIME |
| Escape | Close the active desktop poster player first. The next Escape can collapse the expanded lane. | FIXED |

### 4.5 What Users Cannot Do

Users cannot:
- Remap swipe directions in the Mall
- Change what up/down/left/right mean
- Hide Mall navigation controls
- Move Mall anchor zones
- Enter "edit mode" for the Mall itself
- Reposition FoundUp cards manually

### 4.6 Desktop poster browsing

The ordinary Mall checks member admission before mounting the member
catalog. `foundups.com/member/` remains an entry. The exact Play hostname
root forwards to its own `/member/` and permits the `/?signin=required`
return page. The shell loads lane and card
metadata and hands it to the shared field. On entry at 1024 CSS px or wider
with a fine primary pointer and hover, the default is the adaptive poster
grid. Touch and narrower entry use category rows. Saved layout takes
precedence, and the desktop grid retains its layout while resize adapts its
density. The state owner restores the selected layout and position.
[Member shell](../../../public/member/index.html) ·
[Tile field](../../../public/member/js/mall-tile-field.js) ·
[State restore](../../../public/member/js/mall-state-restore.js)

The grid can show video-backed FoundUps and cards for apps, repositories
and services. Non-video selection opens the existing quick view. Listings
use their detail view. Click, Enter or Space on a wide desktop video poster
enlarges its selected position and requests muted playback with the shared
player. The fullscreen button opens the full viewer. Expand from the inline
controls retains the same provider iframe. Hover reveals the action without
mounting media. Escape or Back returns focus and scroll to the poster.
After density reflow, dismissal restores the same tile in its new row.
WikiTube is the design reference for the full viewer and continuous queue.
The admitted browse dock searches the loaded Mall catalog. The full viewer
places its left-aligned queue search beneath the video and above the rail.
Search filters the active lane. Submit starts the first match when idle.
It leaves active playback alone.
[Catalog schema](PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md) ·
[Quick view](../../../public/member/js/mall-planes.js) ·
[Full player](PFMALL_FULLSCREEN_PLAYER_CONTRACT.md)

The gesture engine recognizes double-tap and double-click. The tile field
binds click, keyboard activation and pinch handlers. FLIP animates expansion
and collapse of a FoundUp video field. Save and Share use explicit player
controls. [Gesture engine](../../../public/member/js/gesture-engine.js) ·
[Tile interactions](../../../public/member/js/mall-tile-field.js)

Before this change, a controlled Windows Chromium 143 run at 1440 × 900 CSS px
showed the member shell opening in rows. Selecting the grid gave eight columns
and 15 cards. Hover mounted zero iframes. Clicking a video lane mounted one.
Enter opened the shared full player, Ctrl+wheel expanded and collapsed the
Move2Japan lane, and clicking AutoPost opened its quick view. This run used
the real shell and catalog with a provider fixture at source `4c1d1e7d`.

HPC uses a fixed scoped collection. Its wide fine-pointer view opens the
shared theater and its narrow or touch view opens the portrait grid.
Desktop verification and the remaining preview work are tracked in the
shared roadmap.
[HPC acceptance](../hpc/ROADMAP.md) ·
[Desktop poster browsing PoC](../pfmall/ROADMAP.md#desktop-poster-browsing-poc)

---

## 5. AI Projection vs User Navigation

### 5.1 Separation of Concerns

**User controls**: Navigation within the current projection
**AI controls**: The projection itself (sort, filter, arrangement)

This means:
- User swipes to move through the field
- AI changes what the field looks like
- Swipe grammar remains stable regardless of projection

### 5.2 Field Scope API (Runtime)

The Mall field scope filters the catalog before projection.

| API | Purpose | Status |
|-----|---------|--------|
| `setFieldScope({ type, query })` | Generic scope setter | RUNTIME |
| `projectPersonalMall()` | Filter to creator === '012' | RUNTIME |
| `searchByCreator(query)` | Case-insensitive substring on creator/entity | RUNTIME |
| `filterByCategory(category)` | Exact category match | RUNTIME |
| `filterByTag(tag)` | Exact tag match in tags array | RUNTIME |
| `clearFieldScope()` | Reset to full catalog | RUNTIME |
| `getFieldScope()` | Get current scope | RUNTIME |

Scope types:
- `personal` — `creator === '012'`
- `creator` — substring match on creator/entity
- `category` — exact match (case-insensitive)
- `tag` — exact match in tags array

### 5.3 Projection Commands (AI-Controlled)

AI can reproject the Mall based on:
- "show FoundUps near me"
- "show only food category"
- "show highest activity"
- "show things my agent recommends"
- "show by newest"
- "show by my network"

### 5.4 Invariant

**AI projection changes tile placement, not navigation grammar.**

If user swipes down, they always move toward "nearer/more relevant" in the current projection, regardless of what projection is active.

---

## 6. Protected Mall Anchors

### 6.1 Always Visible

| Element | Zone | Reason |
|---------|------|--------|
| Avatar trigger | Top | Account access |
| Red Dog trigger | Bottom | Concierge/help access |
| FoundUp field | Middle | Core Mall function |

### 6.2 Always Functional

| Action | Binding | Reason |
|--------|---------|--------|
| Open account | Swipe-down from top | User identity access |
| Open concierge | Tap Red Dog | Help/recovery path |
| Enter FoundUp | Enter button (tile or fullscreen) | Core navigation |
| Close overlay | Escape | Universal escape |

### 6.3 Cannot Be Hidden or Disabled

- Account avatar trigger
- Red Dog trigger
- Escape key binding
- Close buttons on overlays
- Sign out action (within account plane)

---

## 7. Account and Red Dog Treatment

### 7.1 Account Plane

**Status**: Anchored personal surface
**Position**: Slides down from top
**Customizable**: Partially, in later phases
**Phase 1**: Fixed layout, fixed controls

Contents (fixed in phase 1):
- Identity block (avatar, name, handle)
- FoundUps grid (tiles linking to entries)
- Invites drawer (collapsible)
- Options (sign out)

### 7.2 Red Dog Concierge

**Status**: Anchored agent surface
**Position**: Slides up from bottom-right trigger
**Customizable**: Partially, in later phases
**Phase 1**: Fixed layout, fixed content

Contents (fixed in phase 1):
- Concierge header
- Member info
- Current context
- Navigation guide
- Readiness guide
- Sign out

---

## 8. Overlay Behavior

When an overlay is open (FoundUp view, account plane, concierge):

| Gesture | Overlay Action | Status |
|---------|----------------|--------|
| swipe-up | Close overlay | LOCKED |
| Escape | Close overlay | LOCKED |
| Scrim tap | Close overlay | LOCKED |
| Close button | Close overlay | LOCKED |

**LOCKED** = Cannot be overridden by any scope, including FoundUp interiors.

---

## 9. Reset Behaviors

### 9.1 Mall-Level Resets

| Reset | Trigger | Effect |
|-------|---------|--------|
| Reset projection | AI command / voice | Return to default sort |
| Center on me | AI command / voice | Return to self-proximity view |
| Reset navigation | Escape (no overlay) | Return to home position |

### 9.2 URL Reset

```
/member/?reset=mall
```

Clears any cached Mall state and returns to default projection.

---

## 10. What This Contract Does NOT Cover

Out of scope for this document:
- FoundUp interior layout (see SoftProto guardrails)
- FoundUp interior gesture overrides (see SoftProto guardrails)
- Edit mode behavior (SoftProto only, not Mall)
- AI command layer implementation (SoftProto architecture)
- Persistence schema for user preferences (SoftProto architecture)

---

## 11. Summary

| Surface | Fixed | SoftProto-Enabled |
|---------|-------|-------------------|
| Gateway | YES | NO |
| Mall navigation | YES | NO |
| Mall anchors (top/bottom) | YES | NO |
| Account plane | YES (phase 1) | Later |
| Red Dog concierge | YES (phase 1) | Later |
| FoundUp interior | NO | YES |

**The Mall is a map. Maps have coordinates. Users navigate maps. They do not edit the map's coordinate system.**

---

*Contract complete. SoftProto begins inside FoundUp interiors, not in the Mall shell.*


## 12. Responsive category-row projection — 2026-10-18

The default browse projection is vertically stacked category groups with horizontal
tracks. Vertical movement visits another group; horizontal movement stays within
that group. Category sorting alone does not establish a relevance/distance score:
those earlier axis descriptions remain projection intent until such data exists.

Visible card count follows available space, not a fixed 3x2 grid or fixed number
of rows. Existing density presets select an explicit grid projection. Pinch-out
opens the selected FoundUp's videos; pinch-in returns to the rows. Independent
row offsets restore locally, using category keys and original catalog indexes.

All FoundUps reuse this grammar and the catalog search/presentation APIs. A future
housing projection may group by location through a separately declared adapter;
this slice groups by catalog category only. No unseen listings, location hierarchy,
personalized ranking or voice runtime is claimed.
