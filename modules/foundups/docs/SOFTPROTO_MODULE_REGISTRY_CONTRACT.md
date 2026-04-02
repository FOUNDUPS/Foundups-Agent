# SoftProto Module Registry Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines the canonical module-registry contract for SoftProto-enabled FoundUp interiors.

The registry:
- Maps module keys to renderable implementations
- Declares module capabilities and constraints
- Provides default layout and gesture hints
- Defines protection levels and lifecycle hooks

**Dependency**: This contract builds on:
- `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` (system model)
- `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` (command paths)
- `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` (gesture bindings)
- `SOFTPROTO_SCHEMA_BUNDLE_AND_MIGRATION_CONTRACT.md` (schema persistence)

---

## 2. Registry Purpose

### 2.1 What the Registry Resolves

The registry resolves:

| Input | Output |
|-------|--------|
| Module key (e.g., `mic`) | Module definition |
| Module definition | Renderer implementation |
| Renderer + schema node | Mounted module instance |

The registry does NOT resolve:
- Layout positions (schema handles this)
- Gesture bindings (gesture schema handles this)
- User preferences (preference layer handles this)

### 2.2 How Schema References a Module

Schema nodes reference modules by key:

```typescript
// In LayoutSchema
const layoutNode: LayoutNode = {
  id: "mic",
  path: "foundup.f_abc123.module.mic",
  type: "module",
  // ...
};

// Registry lookup
const moduleDefinition = registry.resolve("mic");
const renderer = moduleDefinition.rendererKey;  // "MicModule"
```

### 2.3 Registry Lookup vs Command-Path Lookup

| Concern | Lookup System |
|---------|---------------|
| "What can render this module key?" | Registry |
| "What is the current state of this module?" | Command path (schema) |
| "What gestures apply to this module?" | Gesture schema |
| "Where is this module positioned?" | Layout schema |

```typescript
// Registry: static definition
const definition = registry.resolve("mic");
// -> { key: "mic", rendererKey: "MicModule", ... }

// Command path: dynamic state
const state = schema.getNode("foundup.f_abc123.module.mic");
// -> { position: {x: 20, y: 20}, visible: true, ... }
```

---

## 3. Module Definition Contract

### 3.1 Module Definition Shape

```typescript
interface ModuleDefinition {
  // Identity
  key: string;                         // Unique module key (e.g., "mic")
  version: string;                     // semver (e.g., "1.0.0")
  displayName: string;                 // Human-readable name

  // Implementation
  rendererKey: string;                 // Component identifier
  rendererBundle?: string;             // Lazy-load bundle path (optional)

  // Scope
  scopeLevel: ScopeLevel;              // Where this module lives

  // Capabilities
  capabilities: ModuleCapability[];

  // Layout hints
  defaultLayout: LayoutHints;

  // Gesture hints
  defaultGestures: GestureHints;

  // Protection
  protectionDefaults: ProtectionDefaults;

  // Zones
  allowedZones: ZoneId[];
  requiredAnchor?: AnchorPosition;     // Fixed anchor requirement

  // Dependencies
  requiredDependencies: string[];      // Must be present
  optionalDependencies: string[];      // Enhanced if present

  // Metadata
  description?: string;
  icon?: string;
  tags?: string[];
}
```

### 3.2 Capability Types

```typescript
type ModuleCapability =
  | "draggable"           // Can be repositioned by user
  | "resizable"           // Can be resized by user
  | "hideable"            // Can be hidden by user
  | "gesture_override"    // Supports local gesture overrides
  | "ai_commandable"      // Can receive AI commands
  | "voice_trigger"       // Has voice activation
  | "edit_mode_target"    // Participates in edit mode
  | "focus_receiver"      // Can receive keyboard focus
  | "context_menu"        // Has context menu actions
  | "state_persistent"    // State persists across sessions
  | "lazy_loadable";      // Can be loaded on demand
```

### 3.3 Layout Hints

```typescript
interface LayoutHints {
  // Default position (can be overridden by schema)
  defaultPosition: Position | null;    // null = system-positioned

  // Default size
  defaultSize: Size | null;            // null = auto-size

  // Constraints
  minSize?: Size;
  maxSize?: Size;

  // Z-index
  defaultZIndex: number;

  // Aspect ratio
  aspectRatio?: number;                // e.g., 1.0 for square

  // Margin/padding hints
  margin?: Spacing;
  padding?: Spacing;
}

interface Spacing {
  top: number;
  right: number;
  bottom: number;
  left: number;
}
```

### 3.4 Gesture Hints

```typescript
interface GestureHints {
  // Default gesture bindings for this module
  defaultBindings: GestureBinding[];

  // Gestures that this module wants to handle locally
  localGestures: GestureType[];

  // Gestures that should bubble to parent
  bubbleGestures: GestureType[];

  // Gestures this module explicitly blocks
  blockedGestures: GestureType[];
}

interface GestureBinding {
  gesture: GestureType;
  action: string;
  modes?: UIMode[];
}
```

### 3.5 Protection Defaults

```typescript
interface ProtectionDefaults {
  // Base protection level
  level: ProtectionLevel;

  // Specific permissions
  canHide: boolean;
  canRemove: boolean;
  canMove: boolean;
  canResize: boolean;
  canOverrideGestures: boolean;

  // Edit mode
  participatesInEditMode: boolean;
  selectableInEditMode: boolean;
}
```

---

## 4. Module Lifecycle Contract

### 4.1 Lifecycle Phases

```
register -> resolve -> mount -> hydrate -> [update]* -> suspend -> unmount
                                              ^
                                              |
                                         (state changes)
```

### 4.2 Phase Definitions

| Phase | Trigger | Module Receives | Module Returns |
|-------|---------|-----------------|----------------|
| `register` | App startup | Definition | Registration result |
| `resolve` | Schema references module | Key + version | Definition |
| `mount` | Module added to DOM | Context, container | Instance |
| `hydrate` | Schema state available | Schema node, preferences | void |
| `update` | State change | New props/state | void |
| `suspend` | Module hidden/overlay | void | Cleanup promise |
| `unmount` | Module removed | void | Cleanup promise |

### 4.3 Lifecycle Hooks

```typescript
interface ModuleLifecycle {
  // Called during registration
  onRegister?(registry: ModuleRegistry): RegistrationResult;

  // Called when module is resolved from registry
  onResolve?(key: string, version: string): ModuleDefinition | null;

  // Called when module is mounted to DOM
  onMount(context: ModuleContext, container: HTMLElement): ModuleInstance;

  // Called when schema state is ready
  onHydrate?(instance: ModuleInstance, node: LayoutNode, prefs: UserPreferences): void;

  // Called on state changes
  onUpdate?(instance: ModuleInstance, prevNode: LayoutNode, nextNode: LayoutNode): void;

  // Called when module is suspended (hidden, overlay opened)
  onSuspend?(instance: ModuleInstance): Promise<void>;

  // Called when module is unmounted
  onUnmount?(instance: ModuleInstance): Promise<void>;

  // Called when module fails to load
  onError?(error: Error, context: ModuleContext): FallbackResult;
}
```

### 4.4 Lifecycle State Machine

```typescript
type ModuleState =
  | "registered"    // In registry, not resolved
  | "resolved"      // Definition retrieved
  | "mounting"      // Being added to DOM
  | "mounted"       // In DOM, not yet hydrated
  | "hydrating"     // Receiving schema state
  | "active"        // Fully operational
  | "updating"      // State change in progress
  | "suspended"     // Hidden but preserving state
  | "unmounting"    // Being removed from DOM
  | "unmounted"     // Removed, cleanup complete
  | "error";        // Failed state

const VALID_TRANSITIONS: Record<ModuleState, ModuleState[]> = {
  registered: ["resolved"],
  resolved: ["mounting", "error"],
  mounting: ["mounted", "error"],
  mounted: ["hydrating", "unmounting", "error"],
  hydrating: ["active", "error"],
  active: ["updating", "suspended", "unmounting"],
  updating: ["active", "error"],
  suspended: ["active", "unmounting"],
  unmounting: ["unmounted"],
  unmounted: [],
  error: ["resolved", "unmounted"],  // Can retry or cleanup
};
```

---

## 5. Renderer/Context Contract

### 5.1 Module Context

What a module receives from the runtime:

```typescript
interface ModuleContext {
  // Identity
  moduleKey: string;
  instanceId: string;
  path: string;                        // Command path

  // Dispatcher
  dispatch: CommandDispatcher;

  // Schema access (read-only)
  getNode(): LayoutNode;
  getGestureBindings(): InteractionBinding[];

  // Protection
  protectionLevel: ProtectionLevel;
  permissions: ModulePermissions;

  // Persistence
  persistenceScope: PersistenceScope;
  getPersistedState<T>(): T | null;
  setPersistedState<T>(state: T): void;

  // Context payload (FoundUp-specific data)
  payload: ContextPayload;

  // Runtime
  mode: UIMode;
  isEditMode: boolean;
  isOverlayOpen: boolean;

  // Events
  on(event: ModuleEvent, handler: EventHandler): Unsubscribe;
  emit(event: ModuleEvent, data?: unknown): void;
}
```

### 5.2 Command Dispatcher

```typescript
interface CommandDispatcher {
  // Layout commands
  move(position: Position): CommandResult;
  resize(size: Size): CommandResult;
  setZIndex(zIndex: number): CommandResult;

  // Visibility commands
  show(): CommandResult;
  hide(): CommandResult;

  // Gesture commands
  updateGesture(gesture: GestureType, action: string): CommandResult;
  removeGesture(gesture: GestureType): CommandResult;

  // Generic command
  dispatch(command: Command): CommandResult;
}
```

### 5.3 Module Permissions

```typescript
interface ModulePermissions {
  canMove: boolean;
  canResize: boolean;
  canHide: boolean;
  canOverrideGestures: boolean;
  canReceiveAICommands: boolean;
  canPersistState: boolean;
}
```

### 5.4 Context Payload

```typescript
interface ContextPayload {
  // FoundUp context
  foundupId: string;
  foundupType?: string;

  // User context
  userId?: string;
  userRole?: string;

  // Module-specific data
  moduleData?: Record<string, unknown>;

  // Feature flags
  features: Record<string, boolean>;
}
```

---

## 6. Protection Integration

### 6.1 Protection Level Mapping

How registry entries declare protection:

```typescript
const PROTECTION_MAPPING: Record<string, ProtectionDefaults> = {
  // LOCKED: Cannot be modified in any way
  LOCKED: {
    level: "LOCKED",
    canHide: false,
    canRemove: false,
    canMove: false,
    canResize: false,
    canOverrideGestures: false,
    participatesInEditMode: false,
    selectableInEditMode: false,
  },

  // PROTECTED: Visible and functional, but not hideable
  PROTECTED: {
    level: "PROTECTED",
    canHide: false,
    canRemove: false,
    canMove: true,        // Can move within bounds
    canResize: false,
    canOverrideGestures: false,
    participatesInEditMode: true,
    selectableInEditMode: true,
  },

  // RESTRICTED: Some customization allowed
  RESTRICTED: {
    level: "RESTRICTED",
    canHide: false,
    canRemove: false,
    canMove: true,
    canResize: true,
    canOverrideGestures: true,  // Local scope only
    participatesInEditMode: true,
    selectableInEditMode: true,
  },

  // CONFIGURABLE: Full customization allowed
  CONFIGURABLE: {
    level: "CONFIGURABLE",
    canHide: true,
    canRemove: true,
    canMove: true,
    canResize: true,
    canOverrideGestures: true,
    participatesInEditMode: true,
    selectableInEditMode: true,
  },
};
```

### 6.2 Permission Enforcement

Registry protection is enforced at command dispatch:

```typescript
function enforceProtection(
  command: Command,
  definition: ModuleDefinition
): CommandResult {
  const protection = definition.protectionDefaults;

  switch (command.class) {
    case "visibility":
      if (command.action === "hide" && !protection.canHide) {
        return { success: false, error: "PROTECTED_NO_HIDE" };
      }
      break;

    case "layout":
      if (command.action === "move" && !protection.canMove) {
        return { success: false, error: "PROTECTED_NO_MOVE" };
      }
      if (command.action === "resize" && !protection.canResize) {
        return { success: false, error: "PROTECTED_NO_RESIZE" };
      }
      break;

    case "gesture":
      if (!protection.canOverrideGestures) {
        return { success: false, error: "PROTECTED_NO_GESTURE_OVERRIDE" };
      }
      break;
  }

  return { success: true };
}
```

### 6.3 Edit Mode Participation

```typescript
function canParticipateInEditMode(definition: ModuleDefinition): boolean {
  return definition.protectionDefaults.participatesInEditMode;
}

function canSelectInEditMode(definition: ModuleDefinition): boolean {
  return definition.protectionDefaults.selectableInEditMode;
}

function getEditModeActions(definition: ModuleDefinition): EditAction[] {
  const actions: EditAction[] = [];
  const protection = definition.protectionDefaults;

  if (protection.canMove) actions.push("move");
  if (protection.canResize) actions.push("resize");
  if (protection.canHide) actions.push("hide");
  if (protection.canOverrideGestures) actions.push("configure_gestures");

  return actions;
}
```

---

## 7. Phase 1 Built-in Modules

### 7.1 Mic Module

```typescript
const MIC_MODULE: ModuleDefinition = {
  // Identity
  key: "mic",
  version: "1.0.0",
  displayName: "Microphone",

  // Implementation
  rendererKey: "MicModule",

  // Scope
  scopeLevel: "module",

  // Capabilities
  capabilities: [
    "draggable",
    "gesture_override",
    "voice_trigger",
    "edit_mode_target",
    "ai_commandable",
  ],

  // Layout hints
  defaultLayout: {
    defaultPosition: { x: 20, y: 20 },
    defaultSize: { w: 60, h: 60 },
    minSize: { w: 44, h: 44 },
    maxSize: { w: 120, h: 120 },
    defaultZIndex: 100,
    aspectRatio: 1.0,
  },

  // Gesture hints
  defaultGestures: {
    defaultBindings: [
      { gesture: "tap", action: "toggle_listening" },
      { gesture: "longPress", action: "show_settings" },
    ],
    localGestures: ["tap", "longPress", "doubleTap"],
    bubbleGestures: ["swipeUp", "swipeDown", "swipeLeft", "swipeRight"],
    blockedGestures: [],
  },

  // Protection
  protectionDefaults: {
    level: "CONFIGURABLE",
    canHide: true,
    canRemove: true,
    canMove: true,
    canResize: false,
    canOverrideGestures: true,
    participatesInEditMode: true,
    selectableInEditMode: true,
  },

  // Zones
  allowedZones: ["any"],

  // Dependencies
  requiredDependencies: [],
  optionalDependencies: ["voice_service"],

  // Metadata
  description: "Voice input control for AI interaction",
  icon: "microphone",
  tags: ["input", "voice", "ai"],
};
```

### 7.2 Search Module

```typescript
const SEARCH_MODULE: ModuleDefinition = {
  // Identity
  key: "search",
  version: "1.0.0",
  displayName: "Search",

  // Implementation
  rendererKey: "SearchModule",

  // Scope
  scopeLevel: "module",

  // Capabilities
  capabilities: [
    "draggable",
    "resizable",
    "gesture_override",
    "edit_mode_target",
    "focus_receiver",
    "ai_commandable",
  ],

  // Layout hints
  defaultLayout: {
    defaultPosition: { x: 100, y: 20 },
    defaultSize: { w: 200, h: 44 },
    minSize: { w: 120, h: 36 },
    maxSize: { w: 400, h: 60 },
    defaultZIndex: 100,
  },

  // Gesture hints
  defaultGestures: {
    defaultBindings: [
      { gesture: "tap", action: "focus_input" },
      { gesture: "doubleTap", action: "clear_input" },
    ],
    localGestures: ["tap", "doubleTap"],
    bubbleGestures: ["swipeUp", "swipeDown", "swipeLeft", "swipeRight"],
    blockedGestures: [],
  },

  // Protection
  protectionDefaults: {
    level: "CONFIGURABLE",
    canHide: true,
    canRemove: true,
    canMove: true,
    canResize: true,
    canOverrideGestures: true,
    participatesInEditMode: true,
    selectableInEditMode: true,
  },

  // Zones
  allowedZones: ["top", "middle"],

  // Dependencies
  requiredDependencies: [],
  optionalDependencies: ["search_service"],

  // Metadata
  description: "Search input for finding FoundUps and content",
  icon: "search",
  tags: ["input", "search", "navigation"],
};
```

### 7.3 Logout/Options Module

```typescript
const LOGOUT_MODULE: ModuleDefinition = {
  // Identity
  key: "logout",
  version: "1.0.0",
  displayName: "Options",

  // Implementation
  rendererKey: "LogoutModule",

  // Scope
  scopeLevel: "module",

  // Capabilities
  capabilities: [
    "edit_mode_target",
  ],

  // Layout hints
  defaultLayout: {
    defaultPosition: null,             // System-positioned
    defaultSize: null,                 // Auto-size
    defaultZIndex: 200,
  },

  // Gesture hints
  defaultGestures: {
    defaultBindings: [
      { gesture: "tap", action: "show_options" },
    ],
    localGestures: ["tap"],
    bubbleGestures: ["swipeUp", "swipeDown", "swipeLeft", "swipeRight"],
    blockedGestures: [],
  },

  // Protection
  protectionDefaults: {
    level: "PROTECTED",
    canHide: false,
    canRemove: false,
    canMove: false,
    canResize: false,
    canOverrideGestures: false,
    participatesInEditMode: true,
    selectableInEditMode: false,
  },

  // Zones
  allowedZones: ["top"],
  requiredAnchor: "top-right",

  // Dependencies
  requiredDependencies: ["auth_service"],
  optionalDependencies: [],

  // Metadata
  description: "Account options and sign out",
  icon: "settings",
  tags: ["account", "settings", "auth"],
};
```

### 7.4 Red Dog Module

```typescript
const REDDOG_MODULE: ModuleDefinition = {
  // Identity
  key: "reddog",
  version: "1.0.0",
  displayName: "Red Dog",

  // Implementation
  rendererKey: "RedDogModule",

  // Scope
  scopeLevel: "module",

  // Capabilities
  capabilities: [
    "draggable",
    "ai_commandable",
    "edit_mode_target",
  ],

  // Layout hints
  defaultLayout: {
    defaultPosition: null,             // System-positioned (bottom-right)
    defaultSize: { w: 56, h: 56 },
    minSize: { w: 44, h: 44 },
    maxSize: { w: 80, h: 80 },
    defaultZIndex: 300,
    aspectRatio: 1.0,
  },

  // Gesture hints
  defaultGestures: {
    defaultBindings: [
      { gesture: "tap", action: "open_concierge" },
      { gesture: "longPress", action: "show_quick_actions" },
    ],
    localGestures: ["tap", "longPress"],
    bubbleGestures: ["swipeUp", "swipeDown", "swipeLeft", "swipeRight"],
    blockedGestures: [],
  },

  // Protection
  protectionDefaults: {
    level: "PROTECTED",
    canHide: false,
    canRemove: false,
    canMove: true,                     // Can move within bounds
    canResize: false,
    canOverrideGestures: false,
    participatesInEditMode: true,
    selectableInEditMode: true,
  },

  // Zones
  allowedZones: ["bottom", "right"],
  requiredAnchor: "bottom-right",

  // Dependencies
  requiredDependencies: [],
  optionalDependencies: ["concierge_service"],

  // Metadata
  description: "Digital twin concierge and help access",
  icon: "dog",
  tags: ["concierge", "help", "ai", "assistant"],
};
```

### 7.5 Phase 1 Registry

```typescript
const PHASE1_REGISTRY: ModuleDefinition[] = [
  MIC_MODULE,
  SEARCH_MODULE,
  LOGOUT_MODULE,
  REDDOG_MODULE,
];

const PHASE1_REGISTRY_MAP: Record<string, ModuleDefinition> = {
  mic: MIC_MODULE,
  search: SEARCH_MODULE,
  logout: LOGOUT_MODULE,
  reddog: REDDOG_MODULE,
};
```

---

## 8. Resolution and Fallback Rules

### 8.1 Missing Registry Entry

When schema references an unregistered module:

```typescript
function resolveMissingEntry(key: string): FallbackResult {
  console.warn(`Module not found in registry: ${key}`);

  return {
    type: "fallback",
    renderer: "FallbackModule",
    message: `Module "${key}" is not available`,
    actions: ["retry", "remove", "report"],
  };
}
```

**Behavior**:
- Log warning
- Render fallback placeholder
- Offer retry/remove options

### 8.2 Version Mismatch

When schema references a different version:

```typescript
function resolveVersionMismatch(
  key: string,
  requestedVersion: string,
  availableVersion: string
): ResolutionResult {
  const requested = parseVersion(requestedVersion);
  const available = parseVersion(availableVersion);

  // Same major = compatible
  if (requested.major === available.major) {
    return {
      type: "compatible",
      definition: registry.get(key),
      warning: `Version mismatch: requested ${requestedVersion}, using ${availableVersion}`,
    };
  }

  // Different major = incompatible
  return {
    type: "incompatible",
    renderer: "FallbackModule",
    message: `Module "${key}" v${requestedVersion} is not compatible with v${availableVersion}`,
    actions: ["use_available", "remove"],
  };
}
```

### 8.3 Disabled Module

When a module is disabled (feature flag, permission, etc.):

```typescript
function resolveDisabledModule(
  key: string,
  reason: DisableReason
): FallbackResult {
  return {
    type: "disabled",
    renderer: "DisabledModule",
    message: getDisableMessage(reason),
    actions: reason === "permission" ? ["request_permission"] : [],
  };
}

type DisableReason =
  | "feature_flag"
  | "permission"
  | "subscription"
  | "maintenance"
  | "admin_disabled";
```

### 8.4 Unsupported Capability

When schema requires a capability the module doesn't have:

```typescript
function resolveCapabilityMismatch(
  definition: ModuleDefinition,
  requiredCapability: ModuleCapability
): ResolutionResult {
  if (definition.capabilities.includes(requiredCapability)) {
    return { type: "supported", definition };
  }

  // Graceful degradation
  return {
    type: "degraded",
    definition,
    warning: `Module "${definition.key}" does not support "${requiredCapability}"`,
    degradedCapabilities: [requiredCapability],
  };
}
```

### 8.5 Safe Fallback Rendering

```typescript
interface FallbackModule {
  key: string;
  originalKey: string;
  reason: FallbackReason;
  message: string;
  retryable: boolean;
  removable: boolean;
}

function renderFallback(fallback: FallbackModule): HTMLElement {
  const container = document.createElement("div");
  container.className = "softproto-fallback-module";
  container.setAttribute("data-module-key", fallback.originalKey);
  container.setAttribute("data-fallback-reason", fallback.reason);

  container.innerHTML = `
    <div class="fallback-icon">⚠️</div>
    <div class="fallback-message">${escapeHtml(fallback.message)}</div>
    ${fallback.retryable ? '<button class="fallback-retry">Retry</button>' : ''}
    ${fallback.removable ? '<button class="fallback-remove">Remove</button>' : ''}
  `;

  return container;
}
```

---

## 9. Registry API

### 9.1 Registry Interface

```typescript
interface ModuleRegistry {
  // Registration
  register(definition: ModuleDefinition): RegistrationResult;
  unregister(key: string): boolean;

  // Resolution
  resolve(key: string, version?: string): ModuleDefinition | null;
  resolveOrFallback(key: string, version?: string): ResolutionResult;

  // Queries
  has(key: string): boolean;
  get(key: string): ModuleDefinition | undefined;
  getAll(): ModuleDefinition[];
  getByCapability(capability: ModuleCapability): ModuleDefinition[];
  getByTag(tag: string): ModuleDefinition[];

  // Validation
  validate(definition: ModuleDefinition): ValidationResult;

  // Events
  on(event: RegistryEvent, handler: EventHandler): Unsubscribe;
}

type RegistryEvent =
  | "registered"
  | "unregistered"
  | "resolved"
  | "resolution_failed";
```

### 9.2 Registration Flow

```typescript
function registerModule(
  registry: ModuleRegistry,
  definition: ModuleDefinition
): RegistrationResult {
  // Validate definition
  const validation = registry.validate(definition);
  if (!validation.valid) {
    return {
      success: false,
      error: "VALIDATION_FAILED",
      details: validation.errors,
    };
  }

  // Check for conflicts
  if (registry.has(definition.key)) {
    const existing = registry.get(definition.key)!;
    if (existing.version === definition.version) {
      return {
        success: false,
        error: "ALREADY_REGISTERED",
        existingVersion: existing.version,
      };
    }
  }

  // Register
  registry.register(definition);

  return {
    success: true,
    key: definition.key,
    version: definition.version,
  };
}
```

---

## 10. Phase 1 Limits

### 10.1 Supported Features

| Feature | Phase 1 Status |
|---------|----------------|
| Static registration | SUPPORTED |
| Synchronous resolution | SUPPORTED |
| Capability declaration | SUPPORTED |
| Protection defaults | SUPPORTED |
| Lifecycle hooks (basic) | SUPPORTED |
| Fallback rendering | SUPPORTED |

### 10.2 Deferred Features

| Feature | Deferred To |
|---------|-------------|
| Dynamic registration | Phase 2 |
| Lazy loading | Phase 2 |
| Module marketplace | Phase 3 |
| Custom module creation | Phase 3 |
| Version negotiation | Phase 2 |
| Cross-FoundUp modules | Phase 3 |

### 10.3 Registry Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Built-in modules | 4 | Phase 1 proof set |
| Custom modules | 0 | Phase 1 scope |
| Max total modules | 10 | Future headroom |
| Max capabilities per module | 20 | Reasonable limit |

---

## 11. Summary

| Aspect | Contract |
|--------|----------|
| Registry purpose | Map keys to definitions to renderers |
| Definition shape | Key, version, renderer, capabilities, layout/gesture hints, protection |
| Lifecycle phases | register → resolve → mount → hydrate → update → suspend → unmount |
| Context provided | Dispatcher, schema node, protection, persistence, payload |
| Protection integration | LOCKED/PROTECTED/RESTRICTED/CONFIGURABLE enforcement |
| Phase 1 modules | mic, search, logout, reddog |
| Missing entry | Fallback placeholder with retry/remove |
| Version mismatch | Same major = compatible, different major = fallback |

**This contract ensures modules are consistently defined, resolvable, and protectable.**

---

## 12. Related Documents

| Document | Scope |
|----------|-------|
| `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` | System model |
| `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` | Command paths |
| `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` | Gesture resolution |
| `SOFTPROTO_SCHEMA_BUNDLE_AND_MIGRATION_CONTRACT.md` | Schema persistence |

---

*Contract complete. Modules are registered, resolved, and rendered through a canonical registry.*
