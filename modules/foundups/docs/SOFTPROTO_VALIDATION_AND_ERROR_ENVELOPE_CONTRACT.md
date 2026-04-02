# SoftProto Validation and Error Envelope Contract

**Version**: 1.0.0
**Date**: 2026-04-01
**Status**: Contract

---

## 1. Purpose

This document defines the canonical validation and error-envelope contract for SoftProto-enabled FoundUp interiors.

It ensures:
- Validation is consistent across all SoftProto domains
- Errors use a standard envelope format
- Failures map to predictable recovery behaviors
- Reporting is consistent for developers and runtime

**Dependency**: This contract validates against:
- `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` (protected elements)
- `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` (command paths)
- `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` (gesture bindings)
- `SOFTPROTO_SCHEMA_BUNDLE_AND_MIGRATION_CONTRACT.md` (schema structure)
- `SOFTPROTO_MODULE_REGISTRY_CONTRACT.md` (module definitions)

---

## 2. Validation Domains

### 2.1 Schema Bundle Validation

Validates the root `SoftProtoBundle` structure:

```typescript
interface BundleValidation {
  domain: "bundle";
  checks: [
    "version_present",
    "version_format",
    "foundupId_present",
    "foundupId_format",
    "timestamps_valid",
    "layoutSchema_present",
    "gestureSchema_present",
  ];
}

function validateBundle(bundle: unknown): ValidationResult {
  const errors: ValidationError[] = [];

  if (!bundle || typeof bundle !== "object") {
    return fail("BUNDLE_INVALID_TYPE", "Bundle must be an object");
  }

  const b = bundle as Record<string, unknown>;

  // Version
  if (!b.version) {
    errors.push(error("BUNDLE_MISSING_VERSION", "version field required"));
  } else if (!isValidVersion(b.version)) {
    errors.push(error("BUNDLE_INVALID_VERSION", `Invalid version: ${b.version}`));
  }

  // FoundUp ID
  if (!b.foundupId) {
    errors.push(error("BUNDLE_MISSING_FOUNDUP_ID", "foundupId field required"));
  } else if (!isValidFoundupId(b.foundupId)) {
    errors.push(error("BUNDLE_INVALID_FOUNDUP_ID", `Invalid foundupId: ${b.foundupId}`));
  }

  // Timestamps
  if (b.createdAt && !isValidISO8601(b.createdAt)) {
    errors.push(warning("BUNDLE_INVALID_CREATED_AT", "createdAt should be ISO 8601"));
  }
  if (b.updatedAt && !isValidISO8601(b.updatedAt)) {
    errors.push(warning("BUNDLE_INVALID_UPDATED_AT", "updatedAt should be ISO 8601"));
  }

  // Nested schemas
  if (!b.layoutSchema) {
    errors.push(error("BUNDLE_MISSING_LAYOUT", "layoutSchema required"));
  }
  if (!b.gestureSchema) {
    errors.push(error("BUNDLE_MISSING_GESTURES", "gestureSchema required"));
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

### 2.2 Layout Node Validation

Validates individual `LayoutNode` entries:

```typescript
interface LayoutNodeValidation {
  domain: "layout_node";
  checks: [
    "id_present",
    "id_matches_key",
    "path_format",
    "type_valid",
    "parent_exists",
    "children_exist",
    "position_valid",
    "size_valid",
    "zIndex_valid",
    "protection_valid",
    "zone_valid",
  ];
}

function validateLayoutNode(
  nodeId: string,
  node: unknown,
  allNodes: Record<string, unknown>
): ValidationResult {
  const errors: ValidationError[] = [];

  if (!node || typeof node !== "object") {
    return fail("NODE_INVALID_TYPE", `Node ${nodeId} must be an object`);
  }

  const n = node as Record<string, unknown>;

  // ID consistency
  if (n.id !== nodeId) {
    errors.push(error("NODE_ID_MISMATCH", `Node id ${n.id} doesn't match key ${nodeId}`));
  }

  // Path format
  if (typeof n.path !== "string" || !isValidCommandPath(n.path)) {
    errors.push(error("NODE_INVALID_PATH", `Invalid path: ${n.path}`));
  }

  // Type
  if (!isValidNodeType(n.type)) {
    errors.push(error("NODE_INVALID_TYPE", `Invalid type: ${n.type}`));
  }

  // Parent reference
  if (n.parentId !== null && !allNodes[n.parentId as string]) {
    errors.push(error("NODE_ORPHAN", `Parent ${n.parentId} not found for ${nodeId}`));
  }

  // Child references
  if (Array.isArray(n.childIds)) {
    for (const childId of n.childIds) {
      if (!allNodes[childId]) {
        errors.push(warning("NODE_MISSING_CHILD", `Child ${childId} not found for ${nodeId}`));
      }
    }
  }

  // Position bounds
  if (n.position && typeof n.position === "object") {
    const pos = n.position as { x?: number; y?: number };
    if (typeof pos.x !== "number" || typeof pos.y !== "number") {
      errors.push(error("NODE_INVALID_POSITION", `Invalid position for ${nodeId}`));
    }
  }

  // Size bounds
  if (n.size && typeof n.size === "object") {
    const size = n.size as { w?: number; h?: number };
    if (typeof size.w !== "number" || size.w < 0 ||
        typeof size.h !== "number" || size.h < 0) {
      errors.push(error("NODE_INVALID_SIZE", `Invalid size for ${nodeId}`));
    }
  }

  // Protection level
  if (n.protectionLevel && !isValidProtectionLevel(n.protectionLevel)) {
    errors.push(error("NODE_INVALID_PROTECTION", `Invalid protection: ${n.protectionLevel}`));
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

### 2.3 Gesture Binding Validation

Validates `InteractionBinding` entries:

```typescript
interface GestureBindingValidation {
  domain: "gesture_binding";
  checks: [
    "id_present",
    "scope_valid",
    "targetPath_format",
    "gesture_type_valid",
    "action_present",
    "modes_valid",
    "protection_valid",
    "not_locked_override",
  ];
}

function validateGestureBinding(binding: unknown): ValidationResult {
  const errors: ValidationError[] = [];

  if (!binding || typeof binding !== "object") {
    return fail("BINDING_INVALID_TYPE", "Binding must be an object");
  }

  const b = binding as Record<string, unknown>;

  // ID
  if (!b.id || typeof b.id !== "string") {
    errors.push(error("BINDING_MISSING_ID", "Binding id required"));
  }

  // Scope
  if (!isValidScopeLevel(b.scope)) {
    errors.push(error("BINDING_INVALID_SCOPE", `Invalid scope: ${b.scope}`));
  }

  // Target path
  if (typeof b.targetPath !== "string") {
    errors.push(error("BINDING_MISSING_TARGET", "targetPath required"));
  } else if (!isValidCommandPath(b.targetPath) && !isWildcardPath(b.targetPath)) {
    errors.push(error("BINDING_INVALID_TARGET", `Invalid targetPath: ${b.targetPath}`));
  }

  // Gesture type
  if (!isValidGestureType(b.gesture)) {
    errors.push(error("BINDING_INVALID_GESTURE", `Invalid gesture: ${b.gesture}`));
  }

  // Action
  if (!b.action || typeof b.action !== "string") {
    errors.push(error("BINDING_MISSING_ACTION", "action required"));
  }

  // Modes
  if (b.allowedModes && Array.isArray(b.allowedModes)) {
    for (const mode of b.allowedModes) {
      if (!isValidUIMode(mode)) {
        errors.push(warning("BINDING_INVALID_MODE", `Invalid mode: ${mode}`));
      }
    }
  }

  // LOCKED gesture override attempt
  if (b.isUserOverride && isLockedGesture(b.gesture as string, b.targetPath as string)) {
    errors.push(error("BINDING_LOCKED_OVERRIDE", `Cannot override LOCKED gesture: ${b.gesture}`));
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

### 2.4 Command Path Validation

Validates command path format:

```typescript
interface CommandPathValidation {
  domain: "command_path";
  checks: [
    "format_valid",
    "segments_valid",
    "scope_valid",
    "target_exists",
  ];
}

const PATH_REGEX = /^foundup\.[a-z0-9_]+(\.(plane|module|submodule|object)\.[a-z0-9_]+)+$/;

function validateCommandPath(path: string, schema?: LayoutSchema): ValidationResult {
  const errors: ValidationError[] = [];

  // Format
  if (!PATH_REGEX.test(path)) {
    errors.push(error("PATH_INVALID_FORMAT", `Invalid path format: ${path}`));
    return { valid: false, errors };
  }

  // Segments
  const segments = path.split(".");
  if (segments.length < 3 || segments.length > 8) {
    errors.push(error("PATH_INVALID_DEPTH", `Path depth out of range: ${segments.length}`));
  }

  // Target exists (if schema provided)
  if (schema) {
    const node = resolvePathToNode(path, schema);
    if (!node) {
      errors.push(error("PATH_TARGET_NOT_FOUND", `Target not found: ${path}`));
    }
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

### 2.5 Module Registry Reference Validation

Validates module references against registry:

```typescript
interface ModuleRefValidation {
  domain: "module_ref";
  checks: [
    "key_present",
    "key_registered",
    "version_compatible",
    "capabilities_satisfied",
  ];
}

function validateModuleRef(
  ref: unknown,
  registry: ModuleRegistry
): ValidationResult {
  const errors: ValidationError[] = [];

  if (!ref || typeof ref !== "object") {
    return fail("MODULE_REF_INVALID", "Module ref must be an object");
  }

  const r = ref as Record<string, unknown>;

  // Key
  if (!r.moduleId || typeof r.moduleId !== "string") {
    errors.push(error("MODULE_REF_MISSING_KEY", "moduleId required"));
    return { valid: false, errors };
  }

  // Registered
  if (!registry.has(r.moduleId)) {
    errors.push(error("MODULE_REF_NOT_FOUND", `Module not registered: ${r.moduleId}`));
    return { valid: false, errors };
  }

  // Version compatible
  const definition = registry.get(r.moduleId)!;
  if (r.version && !isVersionCompatible(r.version as string, definition.version)) {
    errors.push(warning("MODULE_REF_VERSION_MISMATCH",
      `Version mismatch: requested ${r.version}, available ${definition.version}`));
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

### 2.6 Protection Level Violation Validation

Validates protection constraints:

```typescript
interface ProtectionValidation {
  domain: "protection";
  checks: [
    "locked_not_hidden",
    "locked_not_moved",
    "protected_not_hidden",
    "protected_not_removed",
    "gesture_not_locked_override",
  ];
}

function validateProtectionConstraints(
  command: Command,
  target: LayoutNode | InteractionBinding
): ValidationResult {
  const errors: ValidationError[] = [];
  const protection = target.protectionLevel;

  if (protection === "LOCKED") {
    if (command.class === "visibility" && command.action === "hide") {
      errors.push(error("PROTECTION_LOCKED_HIDE", "Cannot hide LOCKED target"));
    }
    if (command.class === "layout") {
      errors.push(error("PROTECTION_LOCKED_LAYOUT", "Cannot modify LOCKED layout"));
    }
    if (command.class === "gesture") {
      errors.push(error("PROTECTION_LOCKED_GESTURE", "Cannot override LOCKED gesture"));
    }
  }

  if (protection === "PROTECTED") {
    if (command.class === "visibility" && command.action === "hide") {
      errors.push(error("PROTECTION_PROTECTED_HIDE", "Cannot hide PROTECTED target"));
    }
  }

  return { valid: errors.length === 0, errors };
}
```

### 2.7 Migration Validation

Validates migration inputs and outputs:

```typescript
interface MigrationValidation {
  domain: "migration";
  checks: [
    "source_version_valid",
    "target_version_valid",
    "migration_path_exists",
    "output_valid",
  ];
}

function validateMigration(
  source: SoftProtoBundle,
  target: SoftProtoBundle
): ValidationResult {
  const errors: ValidationError[] = [];

  // Source version
  if (!isValidVersion(source.version)) {
    errors.push(error("MIGRATION_INVALID_SOURCE", `Invalid source version: ${source.version}`));
  }

  // Target version
  if (!isValidVersion(target.version)) {
    errors.push(error("MIGRATION_INVALID_TARGET", `Invalid target version: ${target.version}`));
  }

  // Migration didn't corrupt
  const bundleResult = validateBundle(target);
  if (!bundleResult.valid) {
    errors.push(error("MIGRATION_OUTPUT_INVALID", "Migration produced invalid bundle"));
    errors.push(...bundleResult.errors);
  }

  // FoundUp ID preserved
  if (source.foundupId !== target.foundupId) {
    errors.push(error("MIGRATION_ID_CHANGED", "Migration changed foundupId"));
  }

  return { valid: errors.filter(e => e.severity === "error").length === 0, errors };
}
```

---

## 3. Validation Timing

### 3.1 When Validation Occurs

| Timing | What Is Validated | On Failure |
|--------|-------------------|------------|
| Load-time | Full bundle structure | Reset to defaults |
| Pre-mutation | Command target, protection | Reject command |
| Post-mutation | Affected nodes/bindings | Rollback mutation |
| Pre-persist | Full bundle integrity | Block persist, warn |
| Migration-time | Migration output | Reset to defaults |
| Runtime fallback | Module resolution | Render fallback |

### 3.2 Load-Time Validation

```typescript
function validateOnLoad(foundupId: string): LoadResult {
  const raw = localStorage.getItem(getStorageKey(foundupId));

  // Missing = use defaults
  if (!raw) {
    return { bundle: getDefaultBundle(foundupId), source: "default" };
  }

  // Parse
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    logError("LOAD_PARSE_FAILED", { foundupId });
    return { bundle: getDefaultBundle(foundupId), source: "default", error: "parse_failed" };
  }

  // Validate
  const bundleResult = validateBundle(parsed);
  if (!bundleResult.valid) {
    logError("LOAD_VALIDATION_FAILED", { foundupId, errors: bundleResult.errors });
    return attemptPartialRecovery(parsed, foundupId) ||
           { bundle: getDefaultBundle(foundupId), source: "default", error: "validation_failed" };
  }

  // Migrate if needed
  const bundle = parsed as SoftProtoBundle;
  if (bundle.version !== CURRENT_VERSION) {
    const migrated = migrateBundle(bundle);
    const migrationResult = validateMigration(bundle, migrated);
    if (!migrationResult.valid) {
      logError("LOAD_MIGRATION_FAILED", { foundupId, errors: migrationResult.errors });
      return { bundle: getDefaultBundle(foundupId), source: "default", error: "migration_failed" };
    }
    return { bundle: migrated, source: "migrated" };
  }

  return { bundle, source: "persisted" };
}
```

### 3.3 Pre-Mutation Validation

```typescript
function validatePreMutation(command: Command, schema: LayoutSchema): ValidationResult {
  const errors: ValidationError[] = [];

  // Path validation
  const pathResult = validateCommandPath(command.path, schema);
  if (!pathResult.valid) {
    return pathResult;
  }

  // Target lookup
  const target = resolvePathToNode(command.path, schema);
  if (!target) {
    errors.push(error("MUTATION_TARGET_NOT_FOUND", `Target not found: ${command.path}`));
    return { valid: false, errors };
  }

  // Protection check
  const protectionResult = validateProtectionConstraints(command, target);
  if (!protectionResult.valid) {
    return protectionResult;
  }

  return { valid: true, errors: [] };
}
```

### 3.4 Post-Mutation Validation

```typescript
function validatePostMutation(
  beforeNode: LayoutNode,
  afterNode: LayoutNode
): ValidationResult {
  // Re-validate the mutated node
  return validateLayoutNode(afterNode.id, afterNode, {});
}
```

### 3.5 Pre-Persist Validation

```typescript
function validatePrePersist(bundle: SoftProtoBundle): ValidationResult {
  const errors: ValidationError[] = [];

  // Full bundle validation
  const bundleResult = validateBundle(bundle);
  errors.push(...bundleResult.errors);

  // All layout nodes
  for (const [nodeId, node] of Object.entries(bundle.layoutSchema.nodes)) {
    const nodeResult = validateLayoutNode(nodeId, node, bundle.layoutSchema.nodes);
    errors.push(...nodeResult.errors);
  }

  // All gesture bindings
  for (const binding of bundle.gestureSchema.bindings) {
    const bindingResult = validateGestureBinding(binding);
    errors.push(...bindingResult.errors);
  }

  // Fatal errors block persist
  const hasErrors = errors.some(e => e.severity === "error" || e.severity === "fatal");
  return { valid: !hasErrors, errors };
}
```

---

## 4. Error Envelope Format

### 4.1 Error Envelope Shape

```typescript
interface ValidationError {
  // Identity
  code: ErrorCode;
  domain: ValidationDomain;

  // Severity
  severity: ErrorSeverity;

  // Human-readable
  message: string;

  // Context
  targetPath?: string;
  offendingValue?: unknown;

  // Recovery
  recoverable: boolean;
  fallbackAction?: FallbackAction;

  // Correlation
  correlationId?: string;
  requestId?: string;

  // Metadata
  timestamp: string;
  stack?: string;
}

type ValidationDomain =
  | "bundle"
  | "layout_node"
  | "gesture_binding"
  | "command_path"
  | "module_ref"
  | "protection"
  | "migration"
  | "runtime";

type FallbackAction =
  | "reset_node"
  | "reset_binding"
  | "reset_layout"
  | "reset_gestures"
  | "reset_all"
  | "disable_module"
  | "use_default"
  | "skip"
  | "block";
```

### 4.2 Error Code Format

```typescript
type ErrorCode = `${ValidationDomain}_${string}`;

// Examples:
// BUNDLE_MISSING_VERSION
// NODE_INVALID_PATH
// BINDING_LOCKED_OVERRIDE
// PATH_TARGET_NOT_FOUND
// MODULE_REF_NOT_FOUND
// PROTECTION_LOCKED_HIDE
// MIGRATION_OUTPUT_INVALID
```

### 4.3 Error Factory

```typescript
function createError(
  code: ErrorCode,
  message: string,
  options: Partial<ValidationError> = {}
): ValidationError {
  const domain = code.split("_")[0] as ValidationDomain;

  return {
    code,
    domain,
    severity: options.severity ?? "error",
    message,
    targetPath: options.targetPath,
    offendingValue: options.offendingValue,
    recoverable: options.recoverable ?? false,
    fallbackAction: options.fallbackAction,
    correlationId: options.correlationId ?? generateCorrelationId(),
    timestamp: new Date().toISOString(),
    stack: options.stack,
  };
}

// Convenience helpers
const error = (code: ErrorCode, message: string, opts?: Partial<ValidationError>) =>
  createError(code, message, { ...opts, severity: "error" });

const warning = (code: ErrorCode, message: string, opts?: Partial<ValidationError>) =>
  createError(code, message, { ...opts, severity: "warning" });

const info = (code: ErrorCode, message: string, opts?: Partial<ValidationError>) =>
  createError(code, message, { ...opts, severity: "info" });

const fatal = (code: ErrorCode, message: string, opts?: Partial<ValidationError>) =>
  createError(code, message, { ...opts, severity: "fatal" });

const fail = (code: ErrorCode, message: string) =>
  ({ valid: false, errors: [error(code, message)] });
```

---

## 5. Severity Classes

### 5.1 Severity Definitions

| Severity | Description | Runtime Behavior |
|----------|-------------|------------------|
| `info` | Informational, no action needed | Log only |
| `warning` | Potential issue, degraded behavior | Log, continue with warning |
| `error` | Invalid state, requires fallback | Log, apply fallback, continue |
| `fatal` | Unrecoverable, cannot continue | Log, block operation, surface to user |

### 5.2 Severity Mapping

```typescript
interface SeverityBehavior {
  log: boolean;
  userVisible: boolean;
  blockOperation: boolean;
  applyFallback: boolean;
  reportToMonitoring: boolean;
}

const SEVERITY_BEHAVIOR: Record<ErrorSeverity, SeverityBehavior> = {
  info: {
    log: true,
    userVisible: false,
    blockOperation: false,
    applyFallback: false,
    reportToMonitoring: false,
  },
  warning: {
    log: true,
    userVisible: false,
    blockOperation: false,
    applyFallback: true,
    reportToMonitoring: false,
  },
  error: {
    log: true,
    userVisible: false,
    blockOperation: false,
    applyFallback: true,
    reportToMonitoring: true,
  },
  fatal: {
    log: true,
    userVisible: true,
    blockOperation: true,
    applyFallback: false,
    reportToMonitoring: true,
  },
};
```

### 5.3 Severity Escalation

```typescript
function escalateSeverity(errors: ValidationError[]): ErrorSeverity {
  if (errors.some(e => e.severity === "fatal")) return "fatal";
  if (errors.some(e => e.severity === "error")) return "error";
  if (errors.some(e => e.severity === "warning")) return "warning";
  return "info";
}
```

---

## 6. Failure Handling Rules

### 6.1 Invalid Schema

| Corruption Type | Fallback Action | User Notification |
|-----------------|-----------------|-------------------|
| `parse_error` | Reset to defaults | Toast: "Preferences reset" |
| `missing_version` | Attempt v0 migration | None |
| `invalid_version` | Reset to defaults | Toast: "Preferences updated" |
| `invalid_layout` | Reset layout only | Toast: "Layout reset" |
| `invalid_gestures` | Reset gestures only | Toast: "Gestures reset" |
| `both_invalid` | Reset to defaults | Toast: "Preferences reset" |

### 6.2 Missing Module Registry Entry

```typescript
function handleMissingModule(key: string): FallbackResult {
  return {
    fallbackAction: "use_default",
    fallbackRenderer: "FallbackModule",
    error: error("MODULE_REF_NOT_FOUND", `Module not found: ${key}`, {
      targetPath: `*.module.${key}`,
      recoverable: true,
      fallbackAction: "disable_module",
    }),
  };
}
```

### 6.3 Invalid Command Target

```typescript
function handleInvalidTarget(path: string): CommandResult {
  return {
    success: false,
    error: error("PATH_TARGET_NOT_FOUND", `Target not found: ${path}`, {
      targetPath: path,
      recoverable: false,
    }),
  };
}
```

### 6.4 Forbidden Override

```typescript
function handleForbiddenOverride(
  gesture: GestureType,
  path: string
): CommandResult {
  return {
    success: false,
    error: error("BINDING_LOCKED_OVERRIDE", `Cannot override ${gesture} at ${path}`, {
      targetPath: path,
      offendingValue: gesture,
      recoverable: false,
    }),
  };
}
```

### 6.5 Protected Module Mutation

```typescript
function handleProtectedMutation(
  command: Command,
  protection: ProtectionLevel
): CommandResult {
  const code = protection === "LOCKED"
    ? `PROTECTION_LOCKED_${command.class.toUpperCase()}`
    : `PROTECTION_PROTECTED_${command.class.toUpperCase()}`;

  return {
    success: false,
    error: error(code as ErrorCode, `Cannot ${command.class} ${protection} target`, {
      targetPath: command.path,
      recoverable: false,
    }),
  };
}
```

### 6.6 Gesture Resolution Ambiguity

```typescript
function handleAmbiguousGesture(
  gesture: GestureType,
  candidates: InteractionBinding[]
): ResolutionResult {
  // Log the ambiguity
  logWarning("GESTURE_AMBIGUOUS", {
    gesture,
    candidateCount: candidates.length,
    candidates: candidates.map(c => c.targetPath),
  });

  // Use first candidate (deterministic)
  return {
    binding: candidates[0],
    warning: warning("GESTURE_AMBIGUOUS", `Multiple bindings for ${gesture}, using first`, {
      recoverable: true,
    }),
  };
}
```

### 6.7 Migration Failure

```typescript
function handleMigrationFailure(
  source: SoftProtoBundle,
  error: ValidationError
): SoftProtoBundle {
  logError("MIGRATION_FAILED", {
    sourceVersion: source.version,
    targetVersion: CURRENT_VERSION,
    error,
  });

  // Reset to defaults
  return getDefaultBundle(source.foundupId);
}
```

### 6.8 Corrupted Persisted Bundle

```typescript
function handleCorruptedBundle(
  foundupId: string,
  corruption: CorruptionType,
  raw: string | null
): RecoveryResult {
  logError("BUNDLE_CORRUPTED", { foundupId, corruption });

  // Attempt partial recovery
  if (corruption === "invalid_layout" || corruption === "invalid_gestures") {
    const partial = attemptPartialRecovery(raw, foundupId);
    if (partial) {
      return {
        bundle: partial,
        recovered: true,
        notification: `${corruption === "invalid_layout" ? "Layout" : "Gestures"} reset`,
      };
    }
  }

  // Full reset
  return {
    bundle: getDefaultBundle(foundupId),
    recovered: false,
    notification: "Preferences reset due to corruption",
  };
}
```

---

## 7. Safe Fallback Rules

### 7.1 Fallback Decision Tree

```typescript
function determineFallback(error: ValidationError): FallbackAction {
  switch (error.domain) {
    case "layout_node":
      if (error.code.includes("ORPHAN") || error.code.includes("INVALID")) {
        return "reset_node";
      }
      break;

    case "gesture_binding":
      if (error.code.includes("LOCKED") || error.code.includes("INVALID")) {
        return "reset_binding";
      }
      break;

    case "module_ref":
      return "disable_module";

    case "bundle":
      if (error.code.includes("LAYOUT")) {
        return "reset_layout";
      }
      if (error.code.includes("GESTURE")) {
        return "reset_gestures";
      }
      return "reset_all";

    case "migration":
      return "reset_all";

    case "protection":
      return "skip";
  }

  return "skip";
}
```

### 7.2 Reset Node

```typescript
function resetNode(nodeId: string, schema: LayoutSchema): LayoutNode {
  const defaultDef = DEFAULT_LAYOUT_NODES[nodeId];

  if (!defaultDef) {
    // Unknown node - remove it
    delete schema.nodes[nodeId];
    return null as any;
  }

  // Reset to default
  schema.nodes[nodeId] = {
    ...schema.nodes[nodeId],
    position: defaultDef.position || null,
    size: defaultDef.size || null,
    visible: defaultDef.visible ?? true,
    isDefault: true,
    isUserOverride: false,
  };

  return schema.nodes[nodeId];
}
```

### 7.3 Reset Binding

```typescript
function resetBinding(
  gesture: GestureType,
  targetPath: string,
  schema: GestureSchema
): void {
  // Remove user override
  schema.bindings = schema.bindings.filter(
    b => !(b.targetPath === targetPath && b.gesture === gesture && b.isUserOverride)
  );
}
```

### 7.4 Reset Layout

```typescript
function resetLayout(foundupId: string, schema: LayoutSchema): LayoutSchema {
  return getDefaultLayoutSchema(foundupId);
}
```

### 7.5 Reset Gestures

```typescript
function resetGestures(foundupId: string, schema: GestureSchema): GestureSchema {
  return getDefaultGestureSchema(foundupId);
}
```

### 7.6 Block and Surface Fatal

```typescript
function handleFatalError(error: ValidationError): void {
  // Log
  logFatal(error.code, {
    message: error.message,
    targetPath: error.targetPath,
    stack: error.stack,
  });

  // Report to monitoring
  reportToMonitoring(error);

  // Surface to user
  showFatalErrorUI({
    title: "Unable to Load",
    message: "Your layout preferences could not be loaded. Please try refreshing or resetting.",
    actions: [
      { label: "Refresh", action: () => location.reload() },
      { label: "Reset All", action: () => resetAndReload() },
    ],
  });
}
```

---

## 8. Developer/Runtime Reporting

### 8.1 Logging Levels

| Error Severity | Console Level | Include Stack |
|----------------|---------------|---------------|
| `info` | `console.info` | NO |
| `warning` | `console.warn` | NO |
| `error` | `console.error` | YES |
| `fatal` | `console.error` | YES |

### 8.2 Log Format

```typescript
interface LogEntry {
  level: "info" | "warn" | "error";
  code: ErrorCode;
  message: string;
  context: Record<string, unknown>;
  timestamp: string;
  correlationId: string;
}

function logValidationError(error: ValidationError): void {
  const level = error.severity === "info" ? "info" :
                error.severity === "warning" ? "warn" : "error";

  const entry: LogEntry = {
    level,
    code: error.code,
    message: error.message,
    context: {
      domain: error.domain,
      targetPath: error.targetPath,
      offendingValue: error.offendingValue,
      recoverable: error.recoverable,
      fallbackAction: error.fallbackAction,
    },
    timestamp: error.timestamp,
    correlationId: error.correlationId!,
  };

  console[level](`[SoftProto] ${error.code}: ${error.message}`, entry);

  if (error.severity === "error" || error.severity === "fatal") {
    console.error(error.stack);
  }
}
```

### 8.3 User-Visible Errors

Only these errors are surfaced to users:

| Scenario | UI Treatment |
|----------|--------------|
| Preferences reset on corruption | Toast notification |
| Migration performed | Silent (unless failed) |
| Module unavailable | Placeholder with message |
| Fatal load failure | Modal dialog with recovery options |

```typescript
function shouldShowToUser(error: ValidationError): boolean {
  // Fatal always shows
  if (error.severity === "fatal") return true;

  // Specific recoveries show toast
  const TOAST_CODES = [
    "BUNDLE_CORRUPTED",
    "MIGRATION_FAILED",
    "MODULE_REF_NOT_FOUND",
  ];

  return TOAST_CODES.some(c => error.code.includes(c));
}
```

### 8.4 Silent Auto-Recovery

These errors are silently auto-recovered:

| Error | Recovery | User Sees |
|-------|----------|-----------|
| Missing optional field | Use default | Nothing |
| Minor version mismatch | Auto-migrate | Nothing |
| Orphaned child reference | Remove reference | Nothing |
| Redundant binding | Deduplicate | Nothing |

### 8.5 Validation Report Shape

```typescript
interface ValidationReport {
  // Summary
  valid: boolean;
  errorCount: number;
  warningCount: number;
  infoCount: number;

  // Severity
  highestSeverity: ErrorSeverity;

  // Errors by domain
  byDomain: Record<ValidationDomain, ValidationError[]>;

  // All errors
  errors: ValidationError[];

  // Recovery actions taken
  recoveryActions: FallbackAction[];

  // Timing
  validatedAt: string;
  durationMs: number;
}

function generateValidationReport(
  errors: ValidationError[],
  startTime: number
): ValidationReport {
  return {
    valid: !errors.some(e => e.severity === "error" || e.severity === "fatal"),
    errorCount: errors.filter(e => e.severity === "error").length,
    warningCount: errors.filter(e => e.severity === "warning").length,
    infoCount: errors.filter(e => e.severity === "info").length,
    highestSeverity: escalateSeverity(errors),
    byDomain: groupBy(errors, e => e.domain),
    errors,
    recoveryActions: errors
      .filter(e => e.fallbackAction)
      .map(e => e.fallbackAction!),
    validatedAt: new Date().toISOString(),
    durationMs: Date.now() - startTime,
  };
}
```

---

## 9. Phase 1 Limits

### 9.1 Supported Validation

| Domain | Phase 1 Status |
|--------|----------------|
| Bundle structure | SUPPORTED |
| Layout nodes | SUPPORTED |
| Gesture bindings | SUPPORTED |
| Command paths | SUPPORTED |
| Module references | SUPPORTED |
| Protection constraints | SUPPORTED |
| Migration | SUPPORTED |

### 9.2 Deferred Validation

| Feature | Deferred To |
|---------|-------------|
| Cross-FoundUp validation | Phase 3 |
| Server-side validation | Phase 2 |
| Custom validator plugins | Phase 3 |
| Real-time validation streaming | Phase 2 |

### 9.3 Error Reporting Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max errors per validation | 100 | Performance |
| Max logged per session | 500 | Storage |
| Stack trace depth | 10 | Readability |

---

## 10. Summary

| Aspect | Contract |
|--------|----------|
| Validation domains | bundle, layout_node, gesture_binding, command_path, module_ref, protection, migration |
| Validation timing | load, pre-mutation, post-mutation, pre-persist, migration, runtime |
| Error envelope | code, domain, severity, message, targetPath, offendingValue, recoverable, fallbackAction |
| Severity levels | info (log), warning (degrade), error (fallback), fatal (block) |
| Fallback actions | reset_node, reset_binding, reset_layout, reset_gestures, reset_all, disable_module, skip, block |
| User notification | Toast for recovery, modal for fatal |
| Silent recovery | Missing optional, minor migration, orphans, duplicates |

**This contract ensures validation is consistent and errors are predictable and recoverable.**

---

## 11. Related Documents

| Document | Scope |
|----------|-------|
| `SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md` | Protected elements |
| `SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md` | Command paths |
| `SOFTPROTO_GESTURE_RESOLUTION_AND_OVERRIDE_CONTRACT.md` | Gesture bindings |
| `SOFTPROTO_SCHEMA_BUNDLE_AND_MIGRATION_CONTRACT.md` | Schema structure |
| `SOFTPROTO_MODULE_REGISTRY_CONTRACT.md` | Module definitions |

---

*Contract complete. Validation is consistent, errors are enveloped, and fallbacks are predictable.*
