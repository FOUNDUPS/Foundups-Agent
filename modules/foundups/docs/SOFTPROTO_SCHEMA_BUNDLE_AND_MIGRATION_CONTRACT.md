# SoftProto Schema Bundle and Migration Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines the canonical persisted schema bundle and migration contract for SoftProto-enabled FoundUp interiors.

It ensures:
- Bundle shape is consistent across save/load cycles
- Schema versions are tracked and migrated safely
- Corruption is detected and recovered
- Preference layering resolves deterministically

**Dependency**: This contract builds on:
- `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` (schema model)
- `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` (protected elements)
- `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` (path format)
- `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` (gesture bindings)

---

## 2. Bundle Shape

### 2.1 Root Bundle Structure

```typescript
interface SoftProtoBundle {
  // Metadata
  version: SchemaVersion;
  foundupId: string;
  createdAt: string;       // ISO 8601
  updatedAt: string;       // ISO 8601

  // Schemas
  layoutSchema: LayoutSchema;
  gestureSchema: GestureSchema;

  // References
  moduleRegistry: ModuleRegistryRef[];

  // Flags
  isDirty: boolean;        // Unsaved changes exist
  isCorrupted: boolean;    // Recovery mode active
}
```

### 2.2 Schema Version Format

```typescript
type SchemaVersion = `${number}.${number}.${number}`;
// Examples: "1.0.0", "1.1.0", "2.0.0"

interface VersionComponents {
  major: number;  // Breaking changes (reset required)
  minor: number;  // Additive changes (migration possible)
  patch: number;  // Bug fixes (no migration needed)
}
```

### 2.3 Current Version

```typescript
const CURRENT_SCHEMA_VERSION: SchemaVersion = "1.0.0";
```

### 2.4 Storage Key Format

```typescript
// localStorage key pattern
const STORAGE_KEY_PATTERN = "softproto_bundle_{foundupId}";

// Examples:
// softproto_bundle_f_abc123
// softproto_bundle_f_xyz789
```

---

## 3. Layout Schema Contract

### 3.1 Layout Schema Shape

```typescript
interface LayoutSchema {
  version: SchemaVersion;
  foundupId: string;
  rootNodeId: string;
  nodes: Record<string, LayoutNode>;
  gridConfig: GridConfig;
  editModeState: EditModeState;
}
```

### 3.2 Layout Node Shape

```typescript
interface LayoutNode {
  // Identity
  id: string;                          // Stable ID (e.g., "mic", "search")
  path: string;                        // Full command path
  type: NodeType;

  // Hierarchy
  parentId: string | null;             // null for root
  childIds: string[];                  // Ordered children

  // Position and size
  position: Position | null;           // null = use default
  size: Size | null;                   // null = use default
  zIndex: number;

  // Visibility and state
  visible: boolean;
  locked: boolean;                     // Cannot be moved/resized
  draggable: boolean;
  resizable: boolean;

  // Constraints
  allowedZones: ZoneId[];              // Where this node can be placed
  minSize: Size | null;
  maxSize: Size | null;

  // Override markers
  isDefault: boolean;                  // Using system default position
  isUserOverride: boolean;             // User has customized this

  // Protection
  protectionLevel: ProtectionLevel;
}

type NodeType = "foundup" | "plane" | "module" | "submodule" | "object";

interface Position {
  x: number;
  y: number;
}

interface Size {
  w: number;
  h: number;
}

type ZoneId = "top" | "middle" | "bottom" | "left" | "right" | "center" | "any";

type ProtectionLevel = "LOCKED" | "PROTECTED" | "RESTRICTED" | "CONFIGURABLE";
```

### 3.3 Grid Configuration

```typescript
interface GridConfig {
  enabled: boolean;
  snapToGrid: boolean;
  gridSize: number;          // 4-32 pixels
  showGuides: boolean;       // Visual guides in edit mode
}

const DEFAULT_GRID_CONFIG: GridConfig = {
  enabled: true,
  snapToGrid: true,
  gridSize: 8,
  showGuides: true,
};
```

### 3.4 Edit Mode State

```typescript
interface EditModeState {
  active: boolean;
  selectedNodeIds: string[];
  clipboard: LayoutNode[] | null;
  undoStack: LayoutSnapshot[];
  redoStack: LayoutSnapshot[];
  maxUndoDepth: number;
}

interface LayoutSnapshot {
  timestamp: string;
  nodes: Record<string, LayoutNode>;
  description: string;
}

const DEFAULT_EDIT_MODE_STATE: EditModeState = {
  active: false,
  selectedNodeIds: [],
  clipboard: null,
  undoStack: [],
  redoStack: [],
  maxUndoDepth: 20,
};
```

### 3.5 Layout Defaults

```typescript
const DEFAULT_LAYOUT_NODES: Record<string, Partial<LayoutNode>> = {
  mic: {
    type: "module",
    position: { x: 20, y: 20 },
    size: { w: 60, h: 60 },
    zIndex: 100,
    visible: true,
    locked: false,
    draggable: true,
    resizable: false,
    allowedZones: ["any"],
    protectionLevel: "CONFIGURABLE",
  },
  search: {
    type: "module",
    position: { x: 100, y: 20 },
    size: { w: 200, h: 44 },
    zIndex: 100,
    visible: true,
    locked: false,
    draggable: true,
    resizable: true,
    allowedZones: ["top", "middle"],
    protectionLevel: "CONFIGURABLE",
  },
  logout: {
    type: "module",
    position: null,  // System-positioned
    size: null,
    zIndex: 200,
    visible: true,
    locked: true,
    draggable: false,
    resizable: false,
    allowedZones: ["top"],
    protectionLevel: "PROTECTED",
  },
  reddog: {
    type: "module",
    position: null,  // System-positioned (bottom-right)
    size: { w: 56, h: 56 },
    zIndex: 300,
    visible: true,
    locked: false,
    draggable: true,
    resizable: false,
    allowedZones: ["bottom", "right"],
    minSize: { w: 44, h: 44 },
    protectionLevel: "PROTECTED",
  },
};
```

---

## 4. Gesture Schema Contract

### 4.1 Gesture Schema Shape

```typescript
interface GestureSchema {
  version: SchemaVersion;
  foundupId: string;
  bindings: InteractionBinding[];
  defaults: GestureDefaults;
}
```

### 4.2 Interaction Binding Shape

```typescript
interface InteractionBinding {
  // Identity
  id: string;                          // Unique binding ID

  // Scope and target
  scope: ScopeLevel;
  targetPath: string;                  // Command path to target

  // Gesture
  gesture: GestureType;

  // Action
  action: string;                      // Action identifier
  actionParams?: Record<string, unknown>;  // Optional parameters

  // State
  enabled: boolean;

  // Inheritance
  inheritable: boolean;                // Can children inherit?
  overridable: boolean;                // Can children override?

  // Mode restrictions
  allowedModes: UIMode[];              // Empty = all modes

  // Protection
  protectionLevel: ProtectionLevel;
  isSystemBinding: boolean;            // System-defined, not user-created
  isUserOverride: boolean;             // User has customized this
}

type ScopeLevel = "foundup" | "plane" | "module" | "submodule" | "object";

type GestureType =
  | "tap"
  | "doubleTap"
  | "longPress"
  | "swipeUp"
  | "swipeDown"
  | "swipeLeft"
  | "swipeRight"
  | "drag"
  | "keyEscape"
  | "keyEnter"
  | "keySpace"
  | "keyArrowUp"
  | "keyArrowDown"
  | "keyArrowLeft"
  | "keyArrowRight";

type UIMode = "live" | "edit" | "overlay";
```

### 4.3 Gesture Defaults

```typescript
interface GestureDefaults {
  // LOCKED bindings (cannot be overridden)
  locked: InteractionBinding[];

  // System defaults (can be overridden)
  system: InteractionBinding[];
}

const DEFAULT_LOCKED_BINDINGS: InteractionBinding[] = [
  {
    id: "sys_escape_close",
    scope: "foundup",
    targetPath: "foundup.*",
    gesture: "keyEscape",
    action: "close_or_exit",
    enabled: true,
    inheritable: true,
    overridable: false,
    allowedModes: [],
    protectionLevel: "LOCKED",
    isSystemBinding: true,
    isUserOverride: false,
  },
  {
    id: "sys_overlay_swipeup",
    scope: "foundup",
    targetPath: "foundup.*.overlay",
    gesture: "swipeUp",
    action: "close_overlay",
    enabled: true,
    inheritable: true,
    overridable: false,
    allowedModes: ["overlay"],
    protectionLevel: "LOCKED",
    isSystemBinding: true,
    isUserOverride: false,
  },
  {
    id: "sys_scrim_tap",
    scope: "object",
    targetPath: "foundup.*.overlay.scrim",
    gesture: "tap",
    action: "close_overlay",
    enabled: true,
    inheritable: false,
    overridable: false,
    allowedModes: ["overlay"],
    protectionLevel: "LOCKED",
    isSystemBinding: true,
    isUserOverride: false,
  },
];

const DEFAULT_SYSTEM_BINDINGS: InteractionBinding[] = [
  {
    id: "sys_module_tap",
    scope: "module",
    targetPath: "foundup.*.module.*",
    gesture: "tap",
    action: "activate",
    enabled: true,
    inheritable: true,
    overridable: true,
    allowedModes: ["live"],
    protectionLevel: "CONFIGURABLE",
    isSystemBinding: true,
    isUserOverride: false,
  },
  {
    id: "sys_module_doubletap",
    scope: "module",
    targetPath: "foundup.*.module.*",
    gesture: "doubleTap",
    action: "context_action",
    enabled: true,
    inheritable: true,
    overridable: true,
    allowedModes: ["live"],
    protectionLevel: "CONFIGURABLE",
    isSystemBinding: true,
    isUserOverride: false,
  },
];
```

---

## 5. Module Registry References

### 5.1 Registry Reference Shape

```typescript
interface ModuleRegistryRef {
  moduleId: string;                    // e.g., "mic", "search"
  moduleType: string;                  // Component type identifier
  version: string;                     // Module version
  capabilities: ModuleCapability[];
  requiredPermissions: string[];
}

type ModuleCapability =
  | "draggable"
  | "resizable"
  | "gesture_override"
  | "ai_commandable"
  | "voice_trigger";
```

### 5.2 Phase 1 Registry

```typescript
const PHASE1_MODULE_REGISTRY: ModuleRegistryRef[] = [
  {
    moduleId: "mic",
    moduleType: "MicModule",
    version: "1.0.0",
    capabilities: ["draggable", "gesture_override", "voice_trigger"],
    requiredPermissions: ["microphone"],
  },
  {
    moduleId: "search",
    moduleType: "SearchModule",
    version: "1.0.0",
    capabilities: ["draggable", "resizable", "gesture_override"],
    requiredPermissions: [],
  },
  {
    moduleId: "logout",
    moduleType: "LogoutModule",
    version: "1.0.0",
    capabilities: [],
    requiredPermissions: [],
  },
  {
    moduleId: "reddog",
    moduleType: "RedDogModule",
    version: "1.0.0",
    capabilities: ["draggable", "ai_commandable"],
    requiredPermissions: [],
  },
];
```

---

## 6. Preference Layering

### 6.1 Layer Hierarchy

Preferences merge in this order (later wins):

```
1. System defaults (hardcoded)
2. FoundUp defaults (from FoundUp config, if any)
3. User overrides (persisted in localStorage)
4. Session overrides (transient, not persisted)
```

### 6.2 Merge Algorithm

```typescript
function mergePreferences(
  systemDefaults: SoftProtoBundle,
  foundupDefaults: Partial<SoftProtoBundle> | null,
  userOverrides: Partial<SoftProtoBundle> | null,
  sessionOverrides: Partial<SoftProtoBundle> | null
): SoftProtoBundle {

  // Start with system defaults
  let result = deepClone(systemDefaults);

  // Apply FoundUp defaults
  if (foundupDefaults) {
    result = mergeLayout(result, foundupDefaults);
    result = mergeGestures(result, foundupDefaults);
  }

  // Apply user overrides
  if (userOverrides) {
    result = mergeLayout(result, userOverrides);
    result = mergeGestures(result, userOverrides);
  }

  // Apply session overrides (not persisted)
  if (sessionOverrides) {
    result = mergeLayout(result, sessionOverrides);
    result = mergeGestures(result, sessionOverrides);
  }

  // Enforce protection levels
  result = enforceProtection(result);

  return result;
}
```

### 6.3 Layout Merge Rules

```typescript
function mergeLayout(
  base: SoftProtoBundle,
  overlay: Partial<SoftProtoBundle>
): SoftProtoBundle {
  if (!overlay.layoutSchema) return base;

  const result = deepClone(base);

  for (const [nodeId, overlayNode] of Object.entries(overlay.layoutSchema.nodes || {})) {
    const baseNode = result.layoutSchema.nodes[nodeId];

    if (!baseNode) {
      // New node from overlay (only if CONFIGURABLE)
      if (overlayNode.protectionLevel === "CONFIGURABLE") {
        result.layoutSchema.nodes[nodeId] = overlayNode;
      }
      continue;
    }

    // Skip if base is LOCKED
    if (baseNode.protectionLevel === "LOCKED") {
      continue;
    }

    // Merge allowed fields
    if (overlayNode.position && baseNode.draggable) {
      baseNode.position = overlayNode.position;
      baseNode.isDefault = false;
      baseNode.isUserOverride = true;
    }

    if (overlayNode.size && baseNode.resizable) {
      baseNode.size = overlayNode.size;
      baseNode.isUserOverride = true;
    }

    if (overlayNode.visible !== undefined && baseNode.protectionLevel === "CONFIGURABLE") {
      baseNode.visible = overlayNode.visible;
      baseNode.isUserOverride = true;
    }

    if (overlayNode.zIndex !== undefined) {
      baseNode.zIndex = overlayNode.zIndex;
    }
  }

  return result;
}
```

### 6.4 Gesture Merge Rules

```typescript
function mergeGestures(
  base: SoftProtoBundle,
  overlay: Partial<SoftProtoBundle>
): SoftProtoBundle {
  if (!overlay.gestureSchema) return base;

  const result = deepClone(base);

  for (const overlayBinding of overlay.gestureSchema.bindings || []) {
    // Find matching base binding
    const baseIndex = result.gestureSchema.bindings.findIndex(
      b => b.targetPath === overlayBinding.targetPath && b.gesture === overlayBinding.gesture
    );

    if (baseIndex === -1) {
      // New binding (only if not targeting LOCKED gesture)
      if (!isLockedGesture(overlayBinding.gesture, overlayBinding.targetPath)) {
        result.gestureSchema.bindings.push({
          ...overlayBinding,
          isUserOverride: true,
        });
      }
      continue;
    }

    const baseBinding = result.gestureSchema.bindings[baseIndex];

    // Skip if LOCKED
    if (baseBinding.protectionLevel === "LOCKED") {
      continue;
    }

    // Skip if not overridable
    if (!baseBinding.overridable) {
      continue;
    }

    // Apply override
    result.gestureSchema.bindings[baseIndex] = {
      ...baseBinding,
      action: overlayBinding.action,
      actionParams: overlayBinding.actionParams,
      enabled: overlayBinding.enabled ?? baseBinding.enabled,
      isUserOverride: true,
    };
  }

  return result;
}
```

### 6.5 Session Overrides

Session overrides are transient and not persisted:

```typescript
interface SessionOverrides {
  // Temporary visibility changes
  hiddenModules: string[];

  // Temporary position adjustments
  positionOffsets: Record<string, Position>;

  // Edit mode scratch state
  editModeSnapshot: LayoutSnapshot | null;
}

// Session overrides are stored in memory only
let sessionOverrides: SessionOverrides = {
  hiddenModules: [],
  positionOffsets: {},
  editModeSnapshot: null,
};

// Cleared on page navigation
window.addEventListener('beforeunload', () => {
  sessionOverrides = {
    hiddenModules: [],
    positionOffsets: {},
    editModeSnapshot: null,
  };
});
```

---

## 7. Versioning and Migration

### 7.1 Version Change Types

| Change Type | Version Bump | Migration Required | Example |
|-------------|--------------|-------------------|---------|
| Bug fix | Patch (0.0.X) | NO | Fix typo in default |
| New optional field | Minor (0.X.0) | YES (additive) | Add `opacity` field |
| Field rename | Minor (0.X.0) | YES (transform) | `pos` → `position` |
| Field removal | Major (X.0.0) | RESET | Remove `legacy` field |
| Schema restructure | Major (X.0.0) | RESET | Flatten node hierarchy |

### 7.2 Version Compatibility Matrix

| Stored Version | Current Version | Action |
|----------------|-----------------|--------|
| Same | Same | Load as-is |
| Lower patch | Higher patch | Load as-is |
| Lower minor | Higher minor | Migrate forward |
| Lower major | Higher major | Reset to defaults |
| Higher than current | Current | Reset to defaults |
| Missing/invalid | Any | Reset to defaults |

### 7.3 Migration Registry

```typescript
type MigrationFn = (bundle: SoftProtoBundle) => SoftProtoBundle;

const MIGRATIONS: Record<string, MigrationFn> = {
  // Example: 1.0.0 -> 1.1.0
  "1.1.0": (bundle) => {
    // Add new optional field with default
    for (const node of Object.values(bundle.layoutSchema.nodes)) {
      if (node.opacity === undefined) {
        node.opacity = 1.0;
      }
    }
    bundle.version = "1.1.0";
    return bundle;
  },

  // Example: 1.1.0 -> 1.2.0
  "1.2.0": (bundle) => {
    // Rename field
    for (const node of Object.values(bundle.layoutSchema.nodes)) {
      if (node.pos && !node.position) {
        node.position = node.pos;
        delete node.pos;
      }
    }
    bundle.version = "1.2.0";
    return bundle;
  },
};
```

### 7.4 Migration Algorithm

```typescript
function migrateBundle(stored: SoftProtoBundle): SoftProtoBundle {
  const storedVersion = parseVersion(stored.version);
  const currentVersion = parseVersion(CURRENT_SCHEMA_VERSION);

  // Major version mismatch = reset
  if (storedVersion.major !== currentVersion.major) {
    console.warn(`Major version mismatch: ${stored.version} -> ${CURRENT_SCHEMA_VERSION}`);
    return getDefaultBundle(stored.foundupId);
  }

  // Future version = reset (time travel not supported)
  if (compareVersions(stored.version, CURRENT_SCHEMA_VERSION) > 0) {
    console.warn(`Future version detected: ${stored.version}`);
    return getDefaultBundle(stored.foundupId);
  }

  // Same version = no migration
  if (stored.version === CURRENT_SCHEMA_VERSION) {
    return stored;
  }

  // Apply migrations sequentially
  let migrated = deepClone(stored);
  const versions = getSortedMigrationVersions();

  for (const targetVersion of versions) {
    if (compareVersions(migrated.version, targetVersion) < 0 &&
        compareVersions(targetVersion, CURRENT_SCHEMA_VERSION) <= 0) {
      const migrationFn = MIGRATIONS[targetVersion];
      if (migrationFn) {
        migrated = migrationFn(migrated);
        console.log(`Migrated: ${stored.version} -> ${targetVersion}`);
      }
    }
  }

  migrated.version = CURRENT_SCHEMA_VERSION;
  migrated.updatedAt = new Date().toISOString();

  return migrated;
}
```

### 7.5 Corruption Handling

```typescript
type CorruptionType =
  | "missing"           // Key not in localStorage
  | "parse_error"       // JSON.parse failed
  | "wrong_type"        // Not an object
  | "missing_version"   // No version field
  | "invalid_version"   // Version format invalid
  | "invalid_layout"    // Layout schema validation failed
  | "invalid_gestures"  // Gesture schema validation failed
  | "none";             // No corruption

function detectCorruption(raw: string | null): CorruptionType {
  if (raw === null) return "missing";

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return "parse_error";
  }

  if (typeof parsed !== "object" || parsed === null) {
    return "wrong_type";
  }

  const bundle = parsed as Record<string, unknown>;

  if (!bundle.version) return "missing_version";
  if (!isValidVersion(bundle.version)) return "invalid_version";
  if (!validateLayoutSchema(bundle.layoutSchema)) return "invalid_layout";
  if (!validateGestureSchema(bundle.gestureSchema)) return "invalid_gestures";

  return "none";
}

function handleCorruption(
  foundupId: string,
  corruption: CorruptionType,
  raw: string | null
): SoftProtoBundle {
  console.error(`Schema corruption detected: ${corruption}`);

  // Attempt partial recovery for some corruption types
  if (corruption === "invalid_layout" && raw) {
    try {
      const parsed = JSON.parse(raw);
      // Keep gestures, reset layout
      return {
        ...getDefaultBundle(foundupId),
        gestureSchema: parsed.gestureSchema || getDefaultGestureSchema(foundupId),
      };
    } catch {
      // Fall through to full reset
    }
  }

  if (corruption === "invalid_gestures" && raw) {
    try {
      const parsed = JSON.parse(raw);
      // Keep layout, reset gestures
      return {
        ...getDefaultBundle(foundupId),
        layoutSchema: parsed.layoutSchema || getDefaultLayoutSchema(foundupId),
      };
    } catch {
      // Fall through to full reset
    }
  }

  // Full reset for unrecoverable corruption
  return getDefaultBundle(foundupId);
}
```

### 7.6 Reset to Safe Defaults

```typescript
function getDefaultBundle(foundupId: string): SoftProtoBundle {
  return {
    version: CURRENT_SCHEMA_VERSION,
    foundupId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    layoutSchema: getDefaultLayoutSchema(foundupId),
    gestureSchema: getDefaultGestureSchema(foundupId),
    moduleRegistry: PHASE1_MODULE_REGISTRY,
    isDirty: false,
    isCorrupted: false,
  };
}

function getDefaultLayoutSchema(foundupId: string): LayoutSchema {
  const nodes: Record<string, LayoutNode> = {};

  // Create root node
  nodes["root"] = {
    id: "root",
    path: `foundup.${foundupId}`,
    type: "foundup",
    parentId: null,
    childIds: ["plane_main"],
    position: null,
    size: null,
    zIndex: 0,
    visible: true,
    locked: true,
    draggable: false,
    resizable: false,
    allowedZones: ["any"],
    isDefault: true,
    isUserOverride: false,
    protectionLevel: "LOCKED",
  };

  // Create main plane
  nodes["plane_main"] = {
    id: "plane_main",
    path: `foundup.${foundupId}.plane.main`,
    type: "plane",
    parentId: "root",
    childIds: ["mic", "search", "logout", "reddog"],
    position: null,
    size: null,
    zIndex: 1,
    visible: true,
    locked: true,
    draggable: false,
    resizable: false,
    allowedZones: ["any"],
    isDefault: true,
    isUserOverride: false,
    protectionLevel: "LOCKED",
  };

  // Create module nodes from defaults
  for (const [moduleId, defaults] of Object.entries(DEFAULT_LAYOUT_NODES)) {
    nodes[moduleId] = {
      id: moduleId,
      path: `foundup.${foundupId}.module.${moduleId}`,
      type: defaults.type || "module",
      parentId: "plane_main",
      childIds: [],
      position: defaults.position || null,
      size: defaults.size || null,
      zIndex: defaults.zIndex || 100,
      visible: defaults.visible ?? true,
      locked: defaults.locked ?? false,
      draggable: defaults.draggable ?? true,
      resizable: defaults.resizable ?? false,
      allowedZones: defaults.allowedZones || ["any"],
      minSize: defaults.minSize || null,
      maxSize: defaults.maxSize || null,
      isDefault: true,
      isUserOverride: false,
      protectionLevel: defaults.protectionLevel || "CONFIGURABLE",
    };
  }

  return {
    version: CURRENT_SCHEMA_VERSION,
    foundupId,
    rootNodeId: "root",
    nodes,
    gridConfig: DEFAULT_GRID_CONFIG,
    editModeState: DEFAULT_EDIT_MODE_STATE,
  };
}

function getDefaultGestureSchema(foundupId: string): GestureSchema {
  return {
    version: CURRENT_SCHEMA_VERSION,
    foundupId,
    bindings: [],
    defaults: {
      locked: DEFAULT_LOCKED_BINDINGS,
      system: DEFAULT_SYSTEM_BINDINGS,
    },
  };
}
```

---

## 8. Persistence Boundaries

### 8.1 Phase 1: Local Storage Only

```typescript
const PERSISTENCE_CONFIG = {
  // Storage backend
  backend: "localStorage",

  // Scoping
  scope: "per-foundup",         // Each FoundUp has separate storage
  crossFoundupSync: false,       // No sync between FoundUps
  crossDeviceSync: false,        // No server sync

  // Limits
  maxBundleSize: 64 * 1024,     // 64KB per bundle
  maxTotalSize: 5 * 1024 * 1024, // 5MB total localStorage

  // Keys
  keyPrefix: "softproto_bundle_",
  metaKey: "softproto_meta",
};
```

### 8.2 Per-FoundUp Scoping

Each FoundUp has isolated storage:

```typescript
function getStorageKey(foundupId: string): string {
  return `${PERSISTENCE_CONFIG.keyPrefix}${foundupId}`;
}

function loadBundle(foundupId: string): SoftProtoBundle {
  const key = getStorageKey(foundupId);
  const raw = localStorage.getItem(key);

  const corruption = detectCorruption(raw);
  if (corruption !== "none") {
    return handleCorruption(foundupId, corruption, raw);
  }

  const parsed = JSON.parse(raw!) as SoftProtoBundle;
  return migrateBundle(parsed);
}

function saveBundle(bundle: SoftProtoBundle): void {
  const key = getStorageKey(bundle.foundupId);

  // Update timestamp
  bundle.updatedAt = new Date().toISOString();
  bundle.isDirty = false;

  // Serialize
  const serialized = JSON.stringify(bundle);

  // Check size
  if (serialized.length > PERSISTENCE_CONFIG.maxBundleSize) {
    throw new Error(`Bundle exceeds max size: ${serialized.length} > ${PERSISTENCE_CONFIG.maxBundleSize}`);
  }

  // Save
  try {
    localStorage.setItem(key, serialized);
  } catch (e) {
    if (e instanceof DOMException && e.name === "QuotaExceededError") {
      throw new Error("Storage quota exceeded");
    }
    throw e;
  }
}
```

### 8.3 No Cross-FoundUp Sync

Phase 1 does not sync preferences between FoundUps:

```typescript
// Each FoundUp is independent
// User customizes FoundUp A -> only affects FoundUp A
// User visits FoundUp B -> starts with defaults for B

// Future: Cross-FoundUp templates
// - User can export layout from FoundUp A
// - User can import layout to FoundUp B
// - Not implemented in Phase 1
```

### 8.4 Future Extension Notes

Reserved for future phases (not implemented in Phase 1):

```typescript
interface FutureExtensions {
  // Phase 2: Server sync
  serverSync: {
    enabled: false,
    endpoint: null,
    conflictResolution: "last-write-wins" | "merge" | "prompt-user",
  };

  // Phase 3: Cross-device
  crossDevice: {
    enabled: false,
    syncInterval: 60000,  // ms
    offlineQueue: true,
  };

  // Phase 4: Templates
  templates: {
    enabled: false,
    exportFormat: "json",
    importValidation: true,
  };
}
```

---

## 9. Validation

### 9.1 Layout Schema Validation

```typescript
function validateLayoutSchema(schema: unknown): schema is LayoutSchema {
  if (!schema || typeof schema !== "object") return false;

  const s = schema as Record<string, unknown>;

  if (typeof s.version !== "string") return false;
  if (typeof s.foundupId !== "string") return false;
  if (typeof s.rootNodeId !== "string") return false;
  if (typeof s.nodes !== "object" || s.nodes === null) return false;

  // Validate each node
  for (const [nodeId, node] of Object.entries(s.nodes as Record<string, unknown>)) {
    if (!validateLayoutNode(nodeId, node)) return false;
  }

  // Validate root exists
  if (!(s.nodes as Record<string, unknown>)[s.rootNodeId]) return false;

  // Validate parent-child consistency
  if (!validateHierarchy(s.nodes as Record<string, LayoutNode>)) return false;

  return true;
}

function validateLayoutNode(nodeId: string, node: unknown): node is LayoutNode {
  if (!node || typeof node !== "object") return false;

  const n = node as Record<string, unknown>;

  if (n.id !== nodeId) return false;
  if (typeof n.path !== "string") return false;
  if (!isValidNodeType(n.type)) return false;
  if (typeof n.visible !== "boolean") return false;
  if (typeof n.locked !== "boolean") return false;

  return true;
}
```

### 9.2 Gesture Schema Validation

```typescript
function validateGestureSchema(schema: unknown): schema is GestureSchema {
  if (!schema || typeof schema !== "object") return false;

  const s = schema as Record<string, unknown>;

  if (typeof s.version !== "string") return false;
  if (typeof s.foundupId !== "string") return false;
  if (!Array.isArray(s.bindings)) return false;

  // Validate each binding
  for (const binding of s.bindings) {
    if (!validateInteractionBinding(binding)) return false;
  }

  return true;
}

function validateInteractionBinding(binding: unknown): binding is InteractionBinding {
  if (!binding || typeof binding !== "object") return false;

  const b = binding as Record<string, unknown>;

  if (typeof b.id !== "string") return false;
  if (!isValidScopeLevel(b.scope)) return false;
  if (typeof b.targetPath !== "string") return false;
  if (!isValidGestureType(b.gesture)) return false;
  if (typeof b.action !== "string") return false;
  if (typeof b.enabled !== "boolean") return false;

  return true;
}
```

---

## 10. Phase 1 Limits

### 10.1 Supported Features

| Feature | Phase 1 Status |
|---------|----------------|
| Local persistence | SUPPORTED |
| Per-FoundUp storage | SUPPORTED |
| Schema versioning | SUPPORTED |
| Minor migrations | SUPPORTED |
| Corruption recovery | SUPPORTED |
| Layout persistence | SUPPORTED |
| Gesture override persistence | SUPPORTED |

### 10.2 Deferred Features

| Feature | Deferred To |
|---------|-------------|
| Server sync | Phase 2 |
| Cross-device sync | Phase 3 |
| Cross-FoundUp templates | Phase 4 |
| Export/import UI | Phase 4 |
| Conflict resolution UI | Phase 3 |

### 10.3 Bundle Size Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max bundle size | 64KB | Reasonable for 4 modules |
| Max total storage | 5MB | localStorage limit |
| Max nodes per FoundUp | 100 | Phase 1 scope |
| Max bindings per FoundUp | 200 | Phase 1 scope |

---

## 11. Summary

| Aspect | Contract |
|--------|----------|
| Bundle shape | SoftProtoBundle with layout + gesture schemas |
| Version format | semver (major.minor.patch) |
| Storage key | `softproto_bundle_{foundupId}` |
| Storage backend | localStorage (Phase 1) |
| Scope | Per-FoundUp, no cross-sync |
| Layering order | System → FoundUp → User → Session |
| Migration | Minor = migrate, Major = reset |
| Corruption | Detect, partial recover, or reset |
| Max bundle | 64KB |

**This contract ensures persisted preferences are versioned, recoverable, and isolated per FoundUp.**

---

## 12. Related Documents

| Document | Scope |
|----------|-------|
| `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` | System model |
| `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` | Interior guardrails |
| `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` | Command paths |
| `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` | Gesture resolution |

---

*Contract complete. Schema bundles are versioned, layered, and recoverable.*
