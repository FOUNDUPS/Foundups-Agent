# p.fMALL Navigation Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

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

### 4.2 Gesture Bindings (Fixed)

| Gesture | Mall Action | Status |
|---------|-------------|--------|
| swipe-up | Navigate: further/less relevant | FIXED |
| swipe-down | Navigate: nearer/more relevant | FIXED |
| swipe-left | Navigate: cluster shift left | FIXED |
| swipe-right | Navigate: cluster shift right | FIXED |
| tap | Inspect FoundUp (preview/focus) | FIXED |
| double-tap | Enter FoundUp | FIXED |
| long-press | Reserved (future: quick actions) | FIXED |
| pinch | Reserved (future: zoom) | FIXED |

### 4.3 Keyboard Bindings (Fixed)

| Key | Mall Action | Status |
|-----|-------------|--------|
| Arrow Up | Navigate: further | FIXED |
| Arrow Down | Navigate: nearer | FIXED |
| Arrow Left | Navigate: cluster left | FIXED |
| Arrow Right | Navigate: cluster right | FIXED |
| Enter | Enter focused FoundUp | FIXED |
| Escape | Reset view / close overlay | FIXED |

### 4.4 What Users Cannot Do

Users cannot:
- Remap swipe directions in the Mall
- Change what up/down/left/right mean
- Hide Mall navigation controls
- Move Mall anchor zones
- Enter "edit mode" for the Mall itself
- Reposition FoundUp cards manually

---

## 5. AI Projection vs User Navigation

### 5.1 Separation of Concerns

**User controls**: Navigation within the current projection
**AI controls**: The projection itself (sort, filter, arrangement)

This means:
- User swipes to move through the field
- AI changes what the field looks like
- Swipe grammar remains stable regardless of projection

### 5.2 Projection Commands (AI-Controlled)

AI can reproject the Mall based on:
- "show FoundUps near me"
- "show only food category"
- "show highest activity"
- "show things my agent recommends"
- "show by newest"
- "show by my network"

### 5.3 Invariant

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
| Enter FoundUp | Double-tap / Enter | Core navigation |
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
