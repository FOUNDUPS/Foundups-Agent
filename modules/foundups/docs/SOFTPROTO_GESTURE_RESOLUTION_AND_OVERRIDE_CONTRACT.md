# SoftProto Gesture Resolution and Override Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines the canonical gesture-resolution algorithm and override policy for SoftProto-enabled FoundUp interiors.

It ensures:
- Gesture bindings resolve deterministically across scope hierarchy
- Override rules are explicit per gesture class
- Mode-specific behavior (live/edit/overlay) is predictable
- Conflicts resolve with clear precedence

**Dependency**: This contract builds on:
- `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` (scope model)
- `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` (LOCKED gestures)
- `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` (command paths)
- `PFMALL_MALL_NAVIGATION_CONTRACT.md` (Mall boundary)

---

## 2. Resolution Model

### 2.1 Scope Hierarchy

Gestures resolve through a five-level scope hierarchy:

```
App (global root - outside FoundUp)
  -> FoundUp (interior root)
    -> Plane (main, detail, tool)
      -> Module (mic, search, widget)
        -> Submodule (input, results, panel)
          -> Object (button, card, video, canvas)
```

**Note**: For FoundUp interiors, `FoundUp` is the effective root. `App` scope applies only to Mall-level gestures (covered by Mall Navigation Contract).

### 2.2 Resolution Algorithm

When a gesture event fires:

```typescript
function resolveGesture(
  event: GestureEvent,
  targetPath: string,
  mode: "live" | "edit" | "overlay"
): GestureAction | null {

  // Step 1: Check mode-level intercepts
  const modeIntercept = checkModeIntercept(event.gesture, mode);
  if (modeIntercept) {
    return modeIntercept;
  }

  // Step 2: Check LOCKED gestures at FoundUp root
  if (isLockedGesture(event.gesture, mode)) {
    return getLockedAction(event.gesture);
  }

  // Step 3: Check local binding at target
  const localBinding = getBinding(targetPath, event.gesture);
  if (localBinding && localBinding.enabled) {
    return localBinding.action;
  }

  // Step 4: Walk up scope tree
  let currentPath = getParentPath(targetPath);
  while (currentPath) {
    const parentBinding = getBinding(currentPath, event.gesture);
    if (parentBinding && parentBinding.enabled && parentBinding.inheritable) {
      return parentBinding.action;
    }
    currentPath = getParentPath(currentPath);
  }

  // Step 5: No binding found
  return null;  // Gesture is no-op
}
```

### 2.3 Parent Fallback Behavior

When no local binding exists, resolution walks up:

```
object -> submodule -> module -> plane -> foundup_root
```

**Fallback rules**:
- Parent binding applies if `inheritable: true`
- Parent binding skipped if `inheritable: false`
- First found binding wins
- If no binding found at any level, gesture is no-op

### 2.4 Local Override Behavior

Local scope can override parent if:
- Parent binding has `overridable: true`
- Gesture is not LOCKED
- Current mode permits override

```typescript
type InteractionBinding = {
  gesture: GestureType;
  scope: ScopeLevel;
  targetPath: string;
  action: string;
  enabled: boolean;
  inheritable: boolean;   // Can children inherit this?
  overridable: boolean;   // Can children override this?
};
```

---

## 3. Gesture Classes

### 3.1 Tap Gestures

| Gesture | Detection | Scope Range | Default Behavior |
|---------|-----------|-------------|------------------|
| `tap` | Touch < 200ms, movement < 10px | Module → Object | Activate/select |
| `doubleTap` | Two taps < 300ms apart | Module → Object | Context action |
| `longPress` | Touch > 500ms, movement < 10px | Module → Object | Context menu |

**Tap timing priority**:
```
tap detected at 200ms
  -> wait 300ms for potential second tap
  -> if second tap: fire doubleTap, cancel tap
  -> if no second tap: fire tap
```

### 3.2 Swipe Gestures

| Gesture | Detection | Scope Range | Default Behavior |
|---------|-----------|-------------|------------------|
| `swipeUp` | Vertical movement > 50px, velocity > 0.3, direction up | FoundUp → Object | Scroll/navigate |
| `swipeDown` | Vertical movement > 50px, velocity > 0.3, direction down | FoundUp → Object | Scroll/navigate |
| `swipeLeft` | Horizontal movement > 50px, velocity > 0.3, direction left | FoundUp → Object | Navigate/dismiss |
| `swipeRight` | Horizontal movement > 50px, velocity > 0.3, direction right | FoundUp → Object | Navigate/back |

**Swipe thresholds**:
```typescript
const SWIPE_CONFIG = {
  minDistance: 50,      // pixels
  minVelocity: 0.3,     // pixels/ms
  maxDeviation: 30,     // degrees from primary axis
};
```

### 3.3 Drag Gestures

| Gesture | Detection | Scope Range | Default Behavior |
|---------|-----------|-------------|------------------|
| `drag` | Touch > 150ms, movement > 10px | Module → Object | Move element |
| `dragStart` | Drag initiated | Module → Object | Begin drag |
| `dragMove` | Drag in progress | Module → Object | Update position |
| `dragEnd` | Touch released during drag | Module → Object | Commit position |

**Drag detection**:
```typescript
const DRAG_CONFIG = {
  holdDelay: 150,       // ms before drag activates
  minMovement: 10,      // pixels to confirm drag intent
  edgePadding: 20,      // pixels from viewport edge for auto-scroll
};
```

### 3.4 Hold Gestures

| Gesture | Detection | Scope Range | Default Behavior |
|---------|-----------|-------------|------------------|
| `hold` | Touch > 500ms, no movement | Module → Object | Context action |
| `holdRelease` | Release after hold | Module → Object | Confirm/cancel |

**Hold vs longPress**: Functionally identical. Use `longPress` for backward compatibility.

### 3.5 Keyboard Gestures

| Gesture | Detection | Scope Range | Default Behavior |
|---------|-----------|-------------|------------------|
| `keyEscape` | Escape key | FoundUp (LOCKED) | Close/exit |
| `keyEnter` | Enter key | Module → Object | Confirm/activate |
| `keySpace` | Space key | Module → Object | Toggle/activate |
| `keyArrowUp` | Up arrow | Module → Object | Navigate up |
| `keyArrowDown` | Down arrow | Module → Object | Navigate down |
| `keyArrowLeft` | Left arrow | Module → Object | Navigate left |
| `keyArrowRight` | Right arrow | Module → Object | Navigate right |

---

## 4. Override Policy

### 4.1 Override Matrix by Gesture

| Gesture | FoundUp Root | Plane | Module | Submodule | Object |
|---------|--------------|-------|--------|-----------|--------|
| `tap` | N/A | N/A | default | override | override |
| `doubleTap` | N/A | N/A | default | override | override |
| `longPress` | N/A | N/A | default | override | override |
| `swipeUp` | LOCKED (overlay) | inherit | inherit | override | override |
| `swipeDown` | inherit | inherit | inherit | override | override |
| `swipeLeft` | inherit | inherit | inherit | override | override |
| `swipeRight` | inherit | inherit | inherit | override | override |
| `drag` | N/A | N/A | N/A | N/A | local only |
| `keyEscape` | LOCKED | LOCKED | LOCKED | LOCKED | LOCKED |
| `keyEnter` | N/A | default | override | override | override |
| `keySpace` | N/A | default | override | override | override |
| `keyArrow*` | default | inherit | override | override | override |

**Legend**:
- `LOCKED`: Cannot be overridden at any child scope
- `default`: Defines default behavior, can be overridden
- `inherit`: Uses parent binding (no local default)
- `override`: May define local behavior that overrides parent
- `local only`: Never inherits or propagates
- `N/A`: Not applicable at this scope

### 4.2 Inheritable-Only Gestures

These gestures propagate down but cannot be overridden:

| Gesture | Reason |
|---------|--------|
| `keyEscape` | Universal escape must work everywhere |
| `swipeUp` (overlay context) | Universal close must work |

### 4.3 Mode-Lockable Gestures

These gestures change meaning based on mode:

| Gesture | Live Mode | Edit Mode | Overlay Mode |
|---------|-----------|-----------|--------------|
| `tap` | Activate | Select | Activate |
| `doubleTap` | Context action | Edit properties | Context action |
| `drag` | Disabled | Move element | Disabled |
| `swipeUp` | Navigate | Disabled | Close overlay |
| `swipe*` | Navigate | Disabled | Navigate (if allowed) |

### 4.4 Local-Only Gestures

These never escape local object scope:

| Gesture | Reason |
|---------|--------|
| `drag` | Drag state is object-specific |
| `dragStart/Move/End` | Drag lifecycle is local |
| Pinch/zoom (future) | Transform state is local |

---

## 5. Mode Interactions

### 5.1 Live Mode Resolution

Standard resolution with full inheritance:

```typescript
function resolveLiveMode(gesture: GestureType, targetPath: string): GestureAction | null {
  // Check LOCKED first
  if (isLockedGesture(gesture)) {
    return getLockedAction(gesture);
  }

  // Standard resolution
  return resolveWithInheritance(gesture, targetPath);
}
```

### 5.2 Edit Mode Resolution

Edit mode suppresses most gestures, enables drag:

```typescript
function resolveEditMode(gesture: GestureType, targetPath: string): GestureAction | null {
  // LOCKED gestures still work (Escape exits edit mode)
  if (isLockedGesture(gesture)) {
    return getLockedAction(gesture);
  }

  // Edit mode gesture map
  const EDIT_MODE_GESTURES: Record<GestureType, GestureAction | "suppress"> = {
    tap: "select",
    doubleTap: "edit_properties",
    longPress: "context_menu",
    drag: "move_element",
    dragStart: "begin_move",
    dragMove: "update_position",
    dragEnd: "commit_position",
    swipeUp: "suppress",
    swipeDown: "suppress",
    swipeLeft: "suppress",
    swipeRight: "suppress",
    keyEscape: "exit_edit_mode",
    keyEnter: "confirm_edit",
    keySpace: "toggle_selection",
    keyArrowUp: "nudge_up",
    keyArrowDown: "nudge_down",
    keyArrowLeft: "nudge_left",
    keyArrowRight: "nudge_right",
  };

  const action = EDIT_MODE_GESTURES[gesture];
  return action === "suppress" ? null : action;
}
```

### 5.3 Overlay Mode Resolution

Overlay mode prioritizes close gestures:

```typescript
function resolveOverlayMode(gesture: GestureType, targetPath: string): GestureAction | null {
  // Close gestures are LOCKED in overlay mode
  const OVERLAY_CLOSE_GESTURES = ["swipeUp", "keyEscape"];
  if (OVERLAY_CLOSE_GESTURES.includes(gesture)) {
    return "close_overlay";
  }

  // Scrim tap closes
  if (gesture === "tap" && isScrimTarget(targetPath)) {
    return "close_overlay";
  }

  // Other gestures resolve within overlay content
  if (isWithinOverlayContent(targetPath)) {
    return resolveWithInheritance(gesture, targetPath);
  }

  // Outside overlay content = no action
  return null;
}
```

### 5.4 Protected Mode Resolution

When targeting protected elements:

```typescript
function resolveProtectedMode(gesture: GestureType, targetPath: string): GestureAction | null {
  const protectionLevel = getProtectionLevel(targetPath);

  // LOCKED elements: only LOCKED gestures work
  if (protectionLevel === "LOCKED") {
    return isLockedGesture(gesture) ? getLockedAction(gesture) : null;
  }

  // PROTECTED elements: standard resolution, but no hide/move
  if (protectionLevel === "PROTECTED") {
    const action = resolveWithInheritance(gesture, targetPath);
    if (action === "hide" || action === "remove") {
      return null;  // Blocked
    }
    return action;
  }

  // RESTRICTED/CONFIGURABLE: normal resolution
  return resolveWithInheritance(gesture, targetPath);
}
```

### 5.5 Mode Precedence

When multiple modes apply:

```
1. Protected mode check (always first)
2. Overlay mode (if overlay open)
3. Edit mode (if edit mode active)
4. Live mode (default)
```

```typescript
function resolveGestureWithMode(
  gesture: GestureType,
  targetPath: string,
  state: UIState
): GestureAction | null {
  // 1. Protected check
  if (isProtectedTarget(targetPath)) {
    const result = resolveProtectedMode(gesture, targetPath);
    if (result !== undefined) return result;
  }

  // 2. Overlay mode
  if (state.overlayOpen) {
    return resolveOverlayMode(gesture, targetPath);
  }

  // 3. Edit mode
  if (state.editMode) {
    return resolveEditMode(gesture, targetPath);
  }

  // 4. Live mode
  return resolveLiveMode(gesture, targetPath);
}
```

---

## 6. Conflict Rules

### 6.1 Drag vs Swipe Precedence

**Problem**: Both start with touch-and-move.

**Resolution**:
```typescript
function disambiguateDragSwipe(touchState: TouchState): "drag" | "swipe" | "pending" {
  const { duration, distance, velocity, target } = touchState;

  // Edit mode: prefer drag
  if (isEditMode() && isDraggableTarget(target)) {
    if (duration > DRAG_CONFIG.holdDelay) {
      return "drag";
    }
    return "pending";  // Wait for hold threshold
  }

  // Live mode: prefer swipe
  if (velocity > SWIPE_CONFIG.minVelocity && distance > SWIPE_CONFIG.minDistance) {
    return "swipe";
  }

  // Slow movement on draggable = drag (edit mode only)
  if (isEditMode() && duration > DRAG_CONFIG.holdDelay) {
    return "drag";
  }

  return "pending";
}
```

**Rule**: In edit mode, hold > 150ms before movement = drag. Fast flick = swipe (but swipe is suppressed in edit mode anyway).

### 6.2 Tap vs DoubleTap Timing

**Problem**: DoubleTap requires waiting to confirm single tap isn't first of double.

**Resolution**:
```typescript
let tapTimer: number | null = null;
let lastTapTime: number = 0;
let lastTapTarget: string | null = null;

function handleTapEnd(targetPath: string, timestamp: number): void {
  const timeSinceLastTap = timestamp - lastTapTime;

  // Same target, within double-tap window
  if (targetPath === lastTapTarget && timeSinceLastTap < DOUBLE_TAP_DELAY) {
    // Cancel pending single tap
    if (tapTimer) {
      clearTimeout(tapTimer);
      tapTimer = null;
    }
    // Fire double tap
    dispatchGesture("doubleTap", targetPath);
    lastTapTarget = null;
    return;
  }

  // New tap sequence
  lastTapTime = timestamp;
  lastTapTarget = targetPath;

  // Delay single tap to allow double-tap detection
  tapTimer = setTimeout(() => {
    dispatchGesture("tap", targetPath);
    tapTimer = null;
  }, DOUBLE_TAP_DELAY);
}
```

**Trade-off**: Single tap has ~300ms latency. Acceptable for UI activation.

### 6.3 Hold vs Drag Threshold

**Problem**: Both require sustained touch.

**Resolution**:
```typescript
function disambiguateHoldDrag(touchState: TouchState): "hold" | "drag" | "pending" {
  const { duration, distance, target } = touchState;

  // Movement detected = drag candidate
  if (distance > DRAG_CONFIG.minMovement) {
    if (isEditMode() && isDraggableTarget(target)) {
      return "drag";
    }
    // In live mode, movement cancels hold
    return "pending";  // Will resolve to swipe or nothing
  }

  // No movement, long duration = hold
  if (duration > LONG_PRESS_DELAY && distance < 10) {
    return "hold";
  }

  return "pending";
}
```

**Rule**: Movement > 10px cancels hold. Hold requires stillness.

### 6.4 Overlay Intercept Precedence

**Problem**: Gestures inside overlay content vs overlay close.

**Resolution**:
```typescript
function resolveOverlayGesture(gesture: GestureType, targetPath: string): GestureAction | null {
  // Close gestures always close (LOCKED)
  if (gesture === "swipeUp" || gesture === "keyEscape") {
    return "close_overlay";
  }

  // Scrim tap closes
  if (gesture === "tap" && targetPath.includes("scrim")) {
    return "close_overlay";
  }

  // Close button tap closes
  if (gesture === "tap" && targetPath.includes("close_btn")) {
    return "close_overlay";
  }

  // Inside overlay content: resolve normally
  if (isWithinOverlayContent(targetPath)) {
    return resolveWithInheritance(gesture, targetPath);
  }

  // Outside content, not close gesture: no-op
  return null;
}
```

**Rule**: Close gestures win. Content gestures resolve within content. Outside taps do nothing (except scrim).

### 6.5 Protected Close/Escape Precedence

**Problem**: Protected elements shouldn't block escape.

**Resolution**:
```typescript
// LOCKED gestures always execute, regardless of target protection
const ALWAYS_EXECUTE = ["keyEscape", "close_overlay", "return_to_mall"];

function canExecuteOnProtected(action: GestureAction): boolean {
  return ALWAYS_EXECUTE.includes(action);
}
```

**Rule**: Escape/close are never blocked by protection. User can always exit.

---

## 7. Failure and Recovery Behavior

### 7.1 Missing Binding Behavior

| Scenario | Behavior |
|----------|----------|
| No binding at target | Walk up scope tree |
| No binding at any scope | Gesture is no-op (silent) |
| Binding exists but `enabled: false` | Continue walking up |

```typescript
function handleMissingBinding(gesture: GestureType, targetPath: string): void {
  // Log for debugging (development only)
  if (isDevelopment()) {
    console.debug(`No binding for ${gesture} at ${targetPath}`);
  }
  // No user-visible error - gesture is simply ignored
}
```

### 7.2 Invalid Override Behavior

| Scenario | Behavior |
|----------|----------|
| Override LOCKED gesture | Reject command, log warning |
| Override with invalid action | Reject command, log error |
| Override non-existent target | Reject command, return error |

```typescript
function validateOverride(binding: InteractionBinding): ValidationResult {
  // Check LOCKED
  if (isLockedGesture(binding.gesture)) {
    return { valid: false, error: "LOCKED_GESTURE", message: `Cannot override LOCKED gesture: ${binding.gesture}` };
  }

  // Check action exists
  if (!isValidAction(binding.action)) {
    return { valid: false, error: "INVALID_ACTION", message: `Unknown action: ${binding.action}` };
  }

  // Check target exists
  if (!targetExists(binding.targetPath)) {
    return { valid: false, error: "TARGET_NOT_FOUND", message: `Target not found: ${binding.targetPath}` };
  }

  return { valid: true };
}
```

### 7.3 Ambiguous Gesture Resolution

| Scenario | Resolution |
|----------|------------|
| Tap vs drag undetermined | Wait for threshold, then decide |
| Tap vs doubleTap undetermined | Delay tap, wait for second |
| Swipe direction ambiguous | Use primary axis (larger delta) |

```typescript
function resolveAmbiguousDirection(deltaX: number, deltaY: number): SwipeDirection {
  const absX = Math.abs(deltaX);
  const absY = Math.abs(deltaY);

  // Check axis dominance (30 degree threshold)
  const ratio = Math.min(absX, absY) / Math.max(absX, absY);
  if (ratio > 0.577) {  // tan(30°)
    return "diagonal";  // Too ambiguous, treat as no-op
  }

  // Vertical dominant
  if (absY > absX) {
    return deltaY < 0 ? "up" : "down";
  }

  // Horizontal dominant
  return deltaX < 0 ? "left" : "right";
}
```

### 7.4 Safe Fallback Behavior

When gesture system encounters unexpected state:

```typescript
function safeFallback(gesture: GestureType, error: Error): void {
  console.error(`Gesture resolution error: ${error.message}`);

  // LOCKED gestures still work
  if (isLockedGesture(gesture)) {
    executeLockedAction(gesture);
    return;
  }

  // Clear any drag/selection state
  clearTransientState();

  // If in edit mode, exit to prevent stuck state
  if (isEditMode()) {
    exitEditMode();
  }

  // If overlay open, close it
  if (isOverlayOpen()) {
    closeOverlay();
  }
}
```

---

## 8. Phase 1 Limits

### 8.1 Supported Gestures

Phase 1 supports:

| Gesture | Status |
|---------|--------|
| `tap` | SUPPORTED |
| `doubleTap` | SUPPORTED |
| `longPress` | SUPPORTED |
| `swipeUp` | SUPPORTED |
| `swipeDown` | SUPPORTED |
| `swipeLeft` | SUPPORTED |
| `swipeRight` | SUPPORTED |
| `keyEscape` | SUPPORTED |
| `keyEnter` | SUPPORTED |
| `drag` | EDIT MODE ONLY |

Deferred to Phase 2:
- Pinch/zoom
- Multi-touch gestures
- Custom gesture definitions

### 8.2 Supported Scopes

Phase 1 supports:

| Scope | Override Support |
|-------|------------------|
| FoundUp root | LOCKED gestures only |
| Plane | Inherit only |
| Module | Full override |
| Submodule | Full override |
| Object | Full override |

### 8.3 Supported Modes

Phase 1 supports:
- Live mode (default)
- Edit mode (drag/position only)
- Overlay mode (close intercept)

Protected mode enforcement deferred to Phase 2.

---

## 9. Summary

| Aspect | Contract |
|--------|----------|
| Resolution order | LOCKED → local → parent → root → no-op |
| Scope hierarchy | FoundUp → Plane → Module → Submodule → Object |
| LOCKED gestures | Escape, swipeUp (overlay), close buttons |
| Edit mode | Suppresses swipe, enables drag |
| Overlay mode | Intercepts close gestures |
| Drag vs swipe | Hold 150ms = drag, fast flick = swipe |
| Tap vs doubleTap | 300ms delay, second tap cancels first |
| Missing binding | Silent no-op |
| Invalid override | Reject with error |
| Safe fallback | Exit edit mode, close overlay, clear state |

**This contract ensures gesture resolution is deterministic, mode-aware, and always escapable.**

---

## 10. Related Documents

| Document | Scope |
|----------|-------|
| `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` | System model |
| `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` | Interior guardrails |
| `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` | Command paths |
| `PFMALL_MALL_NAVIGATION_CONTRACT.md` | Mall fixed infrastructure |

---

*Contract complete. Gesture resolution is deterministic across scope hierarchy with explicit override rules.*
