# SoftProto FoundUp Interior Guardrail Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines what SoftProto customization is **allowed** inside a FoundUp interior.

It complements the Mall Navigation Contract, which locks the Mall as fixed infrastructure.

**Boundary rule**:
- Mall = fixed navigation infrastructure (see `PFMALL_MALL_NAVIGATION_CONTRACT.md`)
- FoundUp interior = SoftProto-enabled customization surface (this document)

---

## 2. Scope Hierarchy

Inside a FoundUp interior, the following scope hierarchy applies:

```
FoundUp (interior root)
  -> Plane (main view, detail view, tool view)
    -> Module (mic, search, widget, control)
      -> Submodule (input field, results list, settings panel)
        -> Object (button, card, video, canvas)
```

Each level can:
- Inherit gestures/layout from parent
- Override gestures/layout locally
- Expose its own customization surface

---

## 3. What Is Configurable

### 3.1 Layout

| Element | Configurable | Bounds |
|---------|--------------|--------|
| Module position | YES | Within FoundUp viewport |
| Module visibility | YES | Protected modules exempt |
| Module size | YES | Min/max constraints |
| Module z-index | YES | Within layer rules |
| Grid snap | YES | On/off toggle |
| Grid size | YES | 4-32px range |

### 3.2 Gestures (Object-Scoped)

| Gesture | Configurable | Scope |
|---------|--------------|-------|
| swipe-up | YES | Object, Submodule, Module |
| swipe-down | YES | Object, Submodule, Module |
| swipe-left | YES | Object, Submodule, Module |
| swipe-right | YES | Object, Submodule, Module |
| tap | YES | Object, Submodule, Module |
| double-tap | YES | Object, Submodule, Module |
| long-press | YES | Object, Submodule, Module |

**Exception**: Overlay close gestures remain LOCKED (see Section 4).

### 3.3 Modules

Users can:
- Add custom modules from the registry
- Remove non-protected modules
- Reorder modules in layout
- Resize modules within bounds
- Configure module-specific settings

### 3.4 AI Commands

AI can mutate the same state as user edits:
- `moveModule(id, position)`
- `showModule(id)`
- `hideModule(id)` (non-protected only)
- `resizeModule(id, size)`
- `updateGesture(scope, gesture, action)` (non-LOCKED only)
- `resetLayout()`
- `resetGestures()`

---

## 4. What Remains LOCKED

### 4.1 LOCKED Gestures (Cannot Override)

| Gesture | Context | Action | Reason |
|---------|---------|--------|--------|
| Escape | Anywhere | Exit edit mode / close overlay | Universal escape |
| swipe-up | Overlay open | Close overlay | Universal close |
| scrim tap | Overlay open | Close overlay | Universal close |
| close button | Overlay present | Close overlay | Navigation safety |

These are LOCKED at FoundUp interior root level and cannot be overridden by any child scope.

### 4.2 Protected Modules (Cannot Hide/Remove)

| Module | Reason |
|--------|--------|
| Exit/Back control | Must always return to Mall |
| FoundUp identity header | User must know which FoundUp they're in |
| Edit mode exit button | Must always be able to exit edit mode |

### 4.3 Protected Actions (Cannot Disable)

| Action | Reason |
|--------|--------|
| Return to Mall | Navigation escape |
| Exit edit mode | Prevent edit-mode trap |
| Reset to defaults | Recovery path |

---

## 5. Edit Mode Rules

### 5.1 Entering Edit Mode

Edit mode is entered via:
- Explicit "Edit Layout" action
- AI command `enterEditMode()`
- Long-press on empty area (optional, configurable)

### 5.2 Edit Mode Behavior

When `editMode === true`:

| Action | Status |
|--------|--------|
| Drag modules | ENABLED |
| Resize modules | ENABLED |
| Select modules | ENABLED |
| Module tap (normal action) | SUPPRESSED |
| Swipe navigation | SUPPRESSED |
| Double-tap actions | SUPPRESSED |
| Escape key | ENABLED (exits edit mode) |
| Done/Save button | ENABLED |
| Reset button | ENABLED |

### 5.3 Exiting Edit Mode

Edit mode exits via:
- Escape key (always works)
- "Done" / "Save" button
- AI command `exitEditMode()`
- Page navigation (auto-exit)
- Timeout (5 minutes inactivity)
- Visibility change (tab hidden)

### 5.4 Edit Mode Persistence

- Layout changes persist on "Done/Save"
- Escape without save discards changes
- Auto-exit saves current state

---

## 6. Override Boundaries

### 6.1 Scope Resolution

When a gesture fires inside a FoundUp interior:

```
1. Check if gesture is LOCKED at FoundUp root
   -> If LOCKED: execute root action, stop

2. Check if editMode is active
   -> If edit mode: apply edit mode rules, stop

3. Check current target for local binding
   -> If local binding: execute local action, stop

4. Walk up scope tree (object -> submodule -> module -> plane -> root)
   -> First binding found: execute action, stop

5. No binding found: no-op
```

### 6.2 Inheritance vs Override

| Parent Scope | Child Scope | Behavior |
|--------------|-------------|----------|
| Has binding | No binding | Child inherits parent |
| Has binding | Has binding | Child overrides parent |
| No binding | Has binding | Child binding applies |
| No binding | No binding | No action |

### 6.3 Override Examples

**Example 1**: Video player with custom swipe
```
FoundUp root: swipe-up = scroll up
Video object: swipe-up = show controls
Result: swipe on video shows controls; swipe elsewhere scrolls
```

**Example 2**: Search module with custom double-tap
```
FoundUp root: double-tap = (no default)
Search module: double-tap = clear input
Result: double-tap on search clears; double-tap elsewhere is no-op
```

---

## 7. Reset and Recovery

### 7.1 Required Reset Paths

| Reset Type | Scope | Effect |
|------------|-------|--------|
| Reset Layout | FoundUp | Restores default module positions |
| Reset Gestures | FoundUp | Restores default gesture bindings |
| Reset All | FoundUp | Full preference reset |
| Factory Reset | System | Clears all local storage |

### 7.2 Reset Accessibility

Reset must be accessible from:
- Edit mode toolbar
- FoundUp settings/options
- Red Dog concierge (recovery path)
- URL parameter (`?reset=foundup`)

### 7.3 Corruption Recovery

If preferences fail to load:
1. Detect corruption type
2. Log error
3. Fall back to defaults
4. Optionally notify user
5. Never block FoundUp load

---

## 8. AI/User Command Layer

### 8.1 Unified Command Principle

AI and user edits must use the same command layer:

```typescript
// Both AI and UI use these same commands:
dispatch({ type: 'MOVE_MODULE', id: 'mic', position: { x: 100, y: 50 } });
dispatch({ type: 'UPDATE_GESTURE', scope: 'video', gesture: 'swipeUp', action: 'showControls' });
dispatch({ type: 'ENTER_EDIT_MODE' });
dispatch({ type: 'EXIT_EDIT_MODE' });
```

**Rule**: No direct state mutation. All changes go through commands.

### 8.2 Command Permissions

| Command | User | AI | Notes |
|---------|------|-----|-------|
| `enterEditMode` | YES | YES | |
| `exitEditMode` | YES | YES | |
| `moveModule` | YES | YES | |
| `showModule` | YES | YES | |
| `hideModule` | YES | YES | Protected modules throw |
| `updateGesture` | YES | YES | LOCKED gestures throw |
| `resetLayout` | YES | YES | |
| `resetGestures` | YES | YES | |

### 8.3 Command Locking

During user drag/resize:
- Command queue is locked
- AI commands are queued
- Queue replays after user action completes

This prevents AI/user race conditions.

---

## 9. Persistence Schema

### 9.1 Preference Bundle Shape

```typescript
interface FoundUpPreferences {
  version: string;
  foundupId: string;
  layoutSchema: {
    modules: ModuleDefinition[];
    gridSize: number;
    snapToGrid: boolean;
  };
  gestureSchema: {
    bindings: InteractionBinding[];
  };
  updatedAt: string;
}
```

### 9.2 Storage Location

- Primary: `localStorage` key `softproto_foundup_{foundupId}`
- Future: Server sync for cross-device

### 9.3 Version Migration

- Schema version checked on load
- Minor version: auto-migrate
- Major version: reset to defaults
- Corrupt schema: reset to defaults

---

## 10. Phase 1 Limits

For the initial SoftProto spike, the following limits apply:

### 10.1 Proof Modules Only

Phase 1 supports only 4 proof modules:
- Mic
- Search
- Logout/Options trigger
- Red Dog trigger

Additional modules come in later phases.

### 10.2 Single FoundUp Scope

Phase 1 preferences are per-FoundUp, not global.

No cross-FoundUp preference sync in phase 1.

### 10.3 Local Persistence Only

Phase 1 uses localStorage only.

Server sync and cross-device comes later.

---

## 11. Summary

| Aspect | Status |
|--------|--------|
| Layout customization | ALLOWED |
| Module repositioning | ALLOWED |
| Gesture override (object-scoped) | ALLOWED |
| Edit mode | ALLOWED |
| AI/user shared commands | ALLOWED |
| Overlay close gestures | LOCKED |
| Escape key | LOCKED |
| Protected modules | CANNOT HIDE |
| Return to Mall | CANNOT DISABLE |

**The FoundUp interior is user-owned space. SoftProto enables customization within guardrails.**

---

## 12. Related Documents

| Document | Scope |
|----------|-------|
| `PFMALL_MALL_NAVIGATION_CONTRACT.md` | Mall fixed infrastructure |
| `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` | System architecture |
| `SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md` | Implementation phases |

---

*Contract complete. FoundUp interiors are SoftProto-enabled within these guardrails.*
