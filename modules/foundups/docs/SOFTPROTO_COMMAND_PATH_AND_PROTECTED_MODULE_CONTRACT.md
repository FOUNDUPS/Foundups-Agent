# SoftProto Command Path and Protected Module Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines the canonical command-path addressing system and protected-module policy for SoftProto-enabled FoundUp interiors.

It ensures:
- AI and UI use the same addressing grammar
- Protected modules cannot be hidden or disabled
- Mutation conflicts resolve deterministically
- Failures fall back to safe states

**Dependency**: This contract builds on:
- `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` (system model)
- `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` (interior guardrails)
- `PFMALL_MALL_NAVIGATION_CONTRACT.md` (Mall boundary)

---

## 2. Command Path Format

### 2.1 Path Grammar

All addressable targets use dotted path notation:

```
foundup.{foundup_id}.{scope}.{target_id}[.{child_id}]*
```

**Components**:

| Component | Required | Description |
|-----------|----------|-------------|
| `foundup` | YES | Root namespace (always literal) |
| `{foundup_id}` | YES | FoundUp identifier (stable) |
| `{scope}` | YES | Scope level: `plane`, `module`, `submodule`, `object` |
| `{target_id}` | YES | Target identifier within scope |
| `{child_id}` | NO | Nested child path (recursive) |

### 2.2 Path Examples

```
foundup.f_abc123.plane.main
foundup.f_abc123.plane.detail
foundup.f_abc123.module.mic
foundup.f_abc123.module.search
foundup.f_abc123.module.reddog
foundup.f_abc123.module.logout
foundup.f_abc123.object.camera.primary
foundup.f_abc123.object.video.player
foundup.f_abc123.submodule.search.results
foundup.f_abc123.submodule.search.input
```

### 2.3 Naming Rules

| Rule | Specification |
|------|---------------|
| Character set | Lowercase alphanumeric + underscore (`[a-z0-9_]+`) |
| Separator | Dot (`.`) |
| Max depth | 6 levels |
| Max segment length | 32 characters |
| Reserved prefixes | `_sys_`, `_tmp_`, `_protected_` |

**Invalid paths**:
```
foundup.ABC123.module.mic          # uppercase
foundup.f_abc123.module.my-mic     # hyphen
foundup.f_abc123..module.mic       # empty segment
```

### 2.4 Scope Ownership

Each scope level owns its children:

```
foundup.{id}                        # FoundUp root (owns planes)
  -> foundup.{id}.plane.main        # Plane (owns modules)
    -> foundup.{id}.module.mic      # Module (owns submodules)
      -> foundup.{id}.submodule.mic.controls  # Submodule (owns objects)
        -> foundup.{id}.object.mic.mute_btn   # Object (leaf)
```

**Ownership rules**:
- Parent can create/destroy children
- Parent can set child visibility
- Child cannot modify parent
- Child can override parent gesture bindings locally

### 2.5 Stable IDs vs Ephemeral IDs

| ID Type | Pattern | Lifetime | Examples |
|---------|---------|----------|----------|
| Stable | `{type}_{hash}` | Persisted | `f_abc123`, `mic`, `reddog` |
| Ephemeral | `_tmp_{uuid}` | Session only | `_tmp_a1b2c3`, `_tmp_drag_preview` |

**Rules**:
- Stable IDs are used in persistence and commands
- Ephemeral IDs are used for transient UI state (drag previews, selection highlights)
- Commands targeting ephemeral IDs are not persisted
- Ephemeral IDs expire on session end or page navigation

---

## 3. Command Classes

### 3.1 Class Definitions

| Class | Description | Mutates State | Requires Lock |
|-------|-------------|---------------|---------------|
| `read` | Query state without mutation | NO | NO |
| `mutate` | Generic state change | YES | YES |
| `visibility` | Show/hide targets | YES | YES |
| `layout` | Position/size changes | YES | YES |
| `gesture` | Gesture binding changes | YES | YES |
| `reset` | Restore defaults | YES | YES |
| `protected` | Protected action (always allowed) | VARIES | NO |

### 3.2 Command Signatures

```typescript
// Read commands
type ReadCommand = {
  class: "read";
  path: string;
  property?: string;  // Optional specific property
};

// Mutate commands
type MutateCommand = {
  class: "mutate";
  path: string;
  property: string;
  value: unknown;
};

// Visibility commands
type VisibilityCommand = {
  class: "visibility";
  path: string;
  action: "show" | "hide" | "toggle";
};

// Layout commands
type LayoutCommand = {
  class: "layout";
  path: string;
  action: "move" | "resize" | "reorder";
  position?: { x: number; y: number };
  size?: { w: number; h: number };
  zIndex?: number;
};

// Gesture commands
type GestureCommand = {
  class: "gesture";
  path: string;
  gesture: "swipeUp" | "swipeDown" | "swipeLeft" | "swipeRight" | "tap" | "doubleTap" | "longPress";
  action: string | null;
};

// Reset commands
type ResetCommand = {
  class: "reset";
  path: string;
  scope: "layout" | "gestures" | "all";
};

// Protected commands (always succeed)
type ProtectedCommand = {
  class: "protected";
  action: "exit_edit_mode" | "return_to_mall" | "close_overlay" | "sign_out";
};
```

### 3.3 Command Dispatch

All commands flow through a single dispatcher:

```typescript
function dispatch(command: Command): CommandResult {
  // 1. Validate path format
  if (!isValidPath(command.path)) {
    return { success: false, error: "INVALID_PATH" };
  }

  // 2. Check protected status
  if (isProtectedTarget(command.path) && isMutatingClass(command.class)) {
    return { success: false, error: "PROTECTED_TARGET" };
  }

  // 3. Check LOCKED gestures
  if (command.class === "gesture" && isLockedGesture(command.gesture, command.path)) {
    return { success: false, error: "LOCKED_GESTURE" };
  }

  // 4. Acquire lock if needed
  if (requiresLock(command.class)) {
    if (!acquireLock(command.path)) {
      return { success: false, error: "LOCK_CONFLICT" };
    }
  }

  // 5. Execute command
  try {
    const result = executeCommand(command);
    return { success: true, result };
  } finally {
    releaseLock(command.path);
  }
}
```

---

## 4. Protected Module Policy

### 4.1 Protection Levels

| Level | Can Hide | Can Move | Can Disable | Can Override Gesture |
|-------|----------|----------|-------------|----------------------|
| `LOCKED` | NO | NO | NO | NO |
| `PROTECTED` | NO | YES (within bounds) | NO | NO |
| `RESTRICTED` | NO | YES | NO | YES (local scope only) |
| `CONFIGURABLE` | YES | YES | YES | YES |

### 4.2 Module Protection Registry

| Module | Path Pattern | Level | Reason |
|--------|--------------|-------|--------|
| Exit/Back | `*.module.exit` | LOCKED | Must always return to Mall |
| FoundUp Identity | `*.module.identity_header` | PROTECTED | User must know which FoundUp |
| Edit Mode Exit | `*.module.edit_exit` | LOCKED | Must always exit edit mode |
| Sign Out | `*.module.logout` | PROTECTED | Account escape path |
| Red Dog Trigger | `*.module.reddog` | PROTECTED | Recovery/help access |
| Close Button | `*.object.*_close` | LOCKED | Overlay navigation safety |

### 4.3 Protection Enforcement

```typescript
const PROTECTION_REGISTRY: Record<string, ProtectionLevel> = {
  "*.module.exit": "LOCKED",
  "*.module.identity_header": "PROTECTED",
  "*.module.edit_exit": "LOCKED",
  "*.module.logout": "PROTECTED",
  "*.module.reddog": "PROTECTED",
  "*.object.*_close": "LOCKED",
};

function getProtectionLevel(path: string): ProtectionLevel {
  for (const [pattern, level] of Object.entries(PROTECTION_REGISTRY)) {
    if (matchesPattern(path, pattern)) {
      return level;
    }
  }
  return "CONFIGURABLE";
}

function canHide(path: string): boolean {
  const level = getProtectionLevel(path);
  return level === "CONFIGURABLE";
}

function canMove(path: string): boolean {
  const level = getProtectionLevel(path);
  return level !== "LOCKED";
}

function canOverrideGesture(path: string): boolean {
  const level = getProtectionLevel(path);
  return level === "CONFIGURABLE" || level === "RESTRICTED";
}
```

### 4.4 Cannot Hide Policy

The following can NEVER be hidden:

| Target | Reason |
|--------|--------|
| Exit/Back control | Navigation escape |
| FoundUp identity header | Context awareness |
| Edit mode exit button | Edit mode escape |
| Sign out button | Account escape |
| Red Dog trigger | Help/recovery access |
| Overlay close buttons | Overlay escape |

### 4.5 Cannot Disable Policy

The following actions can NEVER be disabled:

| Action | Binding | Reason |
|--------|---------|--------|
| Close overlay | Escape key | Universal escape |
| Close overlay | Swipe-up (overlay scope) | Universal close |
| Close overlay | Scrim tap | Universal close |
| Return to Mall | Exit button | Navigation escape |
| Exit edit mode | Escape key / Done button | Edit mode escape |
| Sign out | Sign out button | Account escape |

### 4.6 Move-Only Policy

The following can be moved but NOT removed:

| Target | Bounds | Reason |
|--------|--------|--------|
| Red Dog trigger | Within viewport, min 44x44px visible | Help access |
| Sign out option | Within account plane | Account escape |
| Identity header | Top zone only | Context awareness |

---

## 5. Conflict and Lock Policy

### 5.1 Lock Types

| Lock Type | Scope | Duration | Owner |
|-----------|-------|----------|-------|
| `EDIT_LOCK` | Single path | User drag/resize duration | UI |
| `MUTATION_LOCK` | Single path | Command execution | Dispatcher |
| `BATCH_LOCK` | Multiple paths | Batch operation | Dispatcher |

### 5.2 User Edit Lock

When user begins drag/resize:

```typescript
function onDragStart(path: string): void {
  // Acquire edit lock
  editLocks.set(path, {
    owner: "user",
    startedAt: Date.now(),
    timeout: 30000  // 30 second max lock
  });

  // Queue incoming AI commands
  commandQueue.enableQueueing(path);
}

function onDragEnd(path: string): void {
  // Release edit lock
  editLocks.delete(path);

  // Replay queued commands
  commandQueue.replayQueued(path);
}
```

### 5.3 AI Mutation Lock

AI commands acquire short-lived locks:

```typescript
function acquireMutationLock(path: string): boolean {
  // Check for user edit lock
  if (editLocks.has(path)) {
    return false;  // User has priority
  }

  // Check for existing mutation lock
  if (mutationLocks.has(path)) {
    return false;  // Another command in progress
  }

  mutationLocks.set(path, {
    owner: "ai",
    startedAt: Date.now(),
    timeout: 1000  // 1 second max
  });

  return true;
}
```

### 5.4 Queue and Serialization

| Scenario | Behavior |
|----------|----------|
| AI command during user drag | Queue command, replay after drag |
| User drag during AI command | AI command completes first (fast) |
| Multiple AI commands same target | Serialize in arrival order |
| Conflicting AI commands | Last writer wins |

### 5.5 Collision Resolution

```typescript
function resolveCollision(
  existing: Lock,
  incoming: Command
): "queue" | "reject" | "override" {
  // User lock always wins
  if (existing.owner === "user") {
    return "queue";
  }

  // Protected commands always execute
  if (incoming.class === "protected") {
    return "override";
  }

  // Same owner, same path = serialize
  if (existing.owner === incoming.source) {
    return "queue";
  }

  // Different owner = reject (let retry logic handle)
  return "reject";
}
```

### 5.6 Lock Timeout

All locks have maximum duration:

| Lock Type | Timeout | On Expiry |
|-----------|---------|-----------|
| `EDIT_LOCK` | 30 seconds | Auto-release, save partial state |
| `MUTATION_LOCK` | 1 second | Auto-release, rollback |
| `BATCH_LOCK` | 5 seconds | Auto-release, partial commit |

---

## 6. Failure and Recovery Policy

### 6.1 Invalid Path Behavior

| Error | Response | Recovery |
|-------|----------|----------|
| Malformed path | Reject with `INVALID_PATH` | Log, no state change |
| Unknown target | Reject with `TARGET_NOT_FOUND` | Log, no state change |
| Scope mismatch | Reject with `SCOPE_MISMATCH` | Log, no state change |

```typescript
function validatePath(path: string): PathValidation {
  // Format check
  if (!PATH_REGEX.test(path)) {
    return { valid: false, error: "INVALID_PATH", message: "Path format invalid" };
  }

  // Target exists check
  const target = resolveTarget(path);
  if (!target) {
    return { valid: false, error: "TARGET_NOT_FOUND", message: `Target not found: ${path}` };
  }

  // Scope check
  const scope = extractScope(path);
  if (!isValidScope(scope, target)) {
    return { valid: false, error: "SCOPE_MISMATCH", message: `Scope mismatch for: ${path}` };
  }

  return { valid: true };
}
```

### 6.2 Protected Target Denial

| Attempt | Response | Recovery |
|---------|----------|----------|
| Hide protected module | Reject with `PROTECTED_TARGET` | No state change |
| Disable protected action | Reject with `PROTECTED_TARGET` | No state change |
| Override LOCKED gesture | Reject with `LOCKED_GESTURE` | No state change |

```typescript
function handleProtectedDenial(command: Command): CommandResult {
  const level = getProtectionLevel(command.path);

  console.warn(`Protected target denial: ${command.path} (level: ${level})`);

  return {
    success: false,
    error: "PROTECTED_TARGET",
    message: `Cannot ${command.class} protected target: ${command.path}`,
    protectionLevel: level
  };
}
```

### 6.3 Partial Mutation Rollback

For batch operations, rollback on failure:

```typescript
async function executeBatch(commands: Command[]): Promise<BatchResult> {
  const executed: Command[] = [];
  const snapshots: Map<string, State> = new Map();

  try {
    for (const cmd of commands) {
      // Snapshot before mutation
      snapshots.set(cmd.path, getState(cmd.path));

      // Execute
      const result = await dispatch(cmd);
      if (!result.success) {
        throw new Error(`Command failed: ${cmd.path}`);
      }

      executed.push(cmd);
    }

    return { success: true, executed: executed.length };
  } catch (error) {
    // Rollback all executed commands
    for (const cmd of executed.reverse()) {
      const snapshot = snapshots.get(cmd.path);
      if (snapshot) {
        restoreState(cmd.path, snapshot);
      }
    }

    return {
      success: false,
      error: "BATCH_FAILED",
      rolledBack: executed.length
    };
  }
}
```

### 6.4 Reset to Safe State

When corruption is detected:

```typescript
function resetToSafeState(foundupId: string): void {
  const path = `foundup.${foundupId}`;

  // 1. Exit edit mode if active
  dispatch({ class: "protected", action: "exit_edit_mode" });

  // 2. Close any open overlays
  dispatch({ class: "protected", action: "close_overlay" });

  // 3. Reset layout to defaults
  dispatch({ class: "reset", path, scope: "layout" });

  // 4. Reset gestures to defaults
  dispatch({ class: "reset", path, scope: "gestures" });

  // 5. Restore all protected modules to visible
  restoreProtectedModules(path);

  // 6. Clear ephemeral state
  clearEphemeralIds(path);

  // 7. Persist safe state
  persistState(path);

  console.log(`Reset to safe state: ${path}`);
}
```

### 6.5 Corruption Detection

| Corruption Type | Detection | Action |
|-----------------|-----------|--------|
| Missing protected module | Startup scan | Restore from defaults |
| Invalid path in state | Validation pass | Remove invalid entry |
| Orphaned child | Parent check | Reparent or remove |
| Circular reference | Depth check | Break cycle, log error |

---

## 7. Command Examples

### 7.1 AI Commands

```typescript
// Move mic module
dispatch({
  class: "layout",
  path: "foundup.f_abc123.module.mic",
  action: "move",
  position: { x: 100, y: 50 }
});

// Hide search module (configurable)
dispatch({
  class: "visibility",
  path: "foundup.f_abc123.module.search",
  action: "hide"
});

// Override gesture on video object
dispatch({
  class: "gesture",
  path: "foundup.f_abc123.object.video.player",
  gesture: "swipeUp",
  action: "showControls"
});

// Attempt to hide protected module (FAILS)
dispatch({
  class: "visibility",
  path: "foundup.f_abc123.module.reddog",
  action: "hide"
});
// Result: { success: false, error: "PROTECTED_TARGET" }
```

### 7.2 UI Commands

```typescript
// User drags module (same command path as AI)
onDragStart("foundup.f_abc123.module.mic");
// ... user drags ...
dispatch({
  class: "layout",
  path: "foundup.f_abc123.module.mic",
  action: "move",
  position: { x: 200, y: 100 }
});
onDragEnd("foundup.f_abc123.module.mic");

// User resets layout
dispatch({
  class: "reset",
  path: "foundup.f_abc123",
  scope: "layout"
});
```

### 7.3 Protected Commands

```typescript
// Always succeed regardless of locks
dispatch({ class: "protected", action: "exit_edit_mode" });
dispatch({ class: "protected", action: "return_to_mall" });
dispatch({ class: "protected", action: "close_overlay" });
dispatch({ class: "protected", action: "sign_out" });
```

---

## 8. Phase 1 Limits

### 8.1 Supported Paths

Phase 1 supports only these path patterns:

```
foundup.{id}.plane.main
foundup.{id}.module.mic
foundup.{id}.module.search
foundup.{id}.module.logout
foundup.{id}.module.reddog
```

### 8.2 Supported Commands

Phase 1 supports only these command classes:
- `read`
- `visibility` (non-protected targets only)
- `layout` (move only, no resize)
- `reset`
- `protected`

Gesture override (`gesture` class) deferred to Phase 2.

### 8.3 Supported Locks

Phase 1 supports:
- `EDIT_LOCK` (user drag)
- `MUTATION_LOCK` (command execution)

Batch locks deferred to Phase 2.

---

## 9. Summary

| Aspect | Contract |
|--------|----------|
| Path format | `foundup.{id}.{scope}.{target}[.{child}]*` |
| Character set | `[a-z0-9_]+`, dot separator |
| Command classes | read, mutate, visibility, layout, gesture, reset, protected |
| Protection levels | LOCKED, PROTECTED, RESTRICTED, CONFIGURABLE |
| Lock priority | User > AI > Batch |
| Collision handling | Queue during user edit, serialize AI commands |
| Failure behavior | Reject with error, no partial state |
| Batch failure | Full rollback |
| Reset path | Always available via `protected` class |

**This contract ensures AI and UI share a single addressing system with explicit protection boundaries.**

---

## 10. Related Documents

| Document | Scope |
|----------|-------|
| `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` | System model |
| `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` | Interior guardrails |
| `PFMALL_MALL_NAVIGATION_CONTRACT.md` | Mall fixed infrastructure |
| `SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md` | Implementation phases |

---

*Contract complete. AI and UI use the same command paths with protected-module enforcement.*
