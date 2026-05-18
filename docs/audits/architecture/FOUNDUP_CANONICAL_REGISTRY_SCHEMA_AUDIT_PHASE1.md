# FoundUp Canonical Registry Schema Audit - Phase 1

**Slice**: `FOUNDUP_CANONICAL_REGISTRY_SCHEMA_AUDIT_PHASE1`
**Date**: 2026-05-18
**Worker**: W9A
**Branch**: `docs/foundup-registry-schema-audit-phase1`
**WSP References**: WSP 00 (Zen), WSP 97 (Truth), WSP 87 (HoloIndex Preflight), WSP 15 (Doc Standards), WSP 50 (Pre-Action)

---

## WSP 97 Labels

```yaml
DOCS_ONLY: true
AUDIT_ONLY: true
NO_IMPLEMENTATION: true
NO_MODULE_DELETION: true
NO_MANIFEST_CREATION: true
NO_TOKEN_ASSIGNMENT: true
TOKEN_DEFERRED_WHERE_UNKNOWN: true
NO_RUNTIME_CHANGE: true
NO_CABR_READY: false     # CABR contract is specified, not runtime
NO_PAYOUT_READY: false   # Payment not triggered
NO_DAO_ACTIVATION: true  # No DAO launch action
```

---

## 1. Executive Summary

This audit defines the schema requirements for a central FoundUp registry WITHOUT implementing it. The registry would serve as the authoritative source of truth for all FoundUp entities in the pAVS ecosystem, consolidating currently fragmented discovery mechanisms (filesystem scan, manifests, simulator state).

**Key Finding**: Currently 7+ `foundup_manifest.json` files exist across the codebase. Discovery is filesystem-based via `shell_core.py:discover_manifests()`. No central registry implementation exists. FAM Registry is `SPECIFIED_NOT_IMPLEMENTED`.

---

## 2. HoloIndex Preflight

### 2.1 Search Queries Executed

| Query | Results | Top Hit |
|-------|---------|---------|
| `foundup registry schema entity manifest` | 15 hits | `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` |
| `class.*Registry` (grep) | 40+ matches | `PersistentFoundupRegistry`, `DAERegistry`, `WRESkillsRegistry` |
| `foundup_manifest.json` (grep) | 30 matches | 7 manifest files discovered |

### 2.2 HoloIndex vs Grep Comparison Table

| Search Target | HoloIndex Result | Grep Result | Quality Delta |
|---------------|------------------|-------------|---------------|
| Registry implementations | `registry.py` (CODE:5) | `PersistentFoundupRegistry`, `FoundupRegistryStub`, `DAERegistry` | Grep more specific |
| Manifest schema | `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` (DOCS:5) | Same + 30 usages | Grep finds usages |
| Entity models | `models.py` (implied) | `Foundup`, `FoundUpTile`, `AgentProfile` | Grep more complete |
| Tier enums | Not indexed | `F0_DAE..F5_SYSTEMIC` in 8+ files | Grep required |
| Hermes integration | `hermes_job_executor.py` (implied) | 30 integration references | Grep finds status |

**Conclusion**: HoloIndex provides semantic entry points; grep provides exhaustive enumeration. Both required for complete audit.

---

## 3. Typed Entity Classes

### 3.1 Entity Class Taxonomy

The registry must distinguish six entity classes:

| Entity Class | Description | Manifest Required | Token Policy | Example |
|--------------|-------------|-------------------|--------------|---------|
| `foundup` | User-facing FoundUp with frontend | YES | Defined | gotjunk, kosei |
| `platform_layer` | Infrastructure serving FoundUps | NO | `TOKEN_DEFERRED` | pfmall shell |
| `infra_service` | Backend service (no manifest) | NO | `TOKEN_DEFERRED` | FAM daemon, WRE |
| `tool_simulator` | Economics simulation engine | NO | `TOKEN_DEFERRED` | simulator |
| `external_foundup` | FoundUp hosted outside monorepo | OPTIONAL | `TOKEN_DEFERRED` | science-swarm |
| `skeleton_candidate` | Spec exists, no implementation | YES | `TOKEN_DEFERRED` | voteballots |

### 3.2 Entity Class Definition (Schema)

```typescript
interface EntityClass {
  // Core type discriminator
  entity_type: 'foundup' | 'platform_layer' | 'infra_service' | 
               'tool_simulator' | 'external_foundup' | 'skeleton_candidate';
  
  // Behavioral flags
  requires_manifest: boolean;
  requires_frontend: boolean;
  supports_token_economics: boolean;
  visible_in_mall: boolean;
  hermes_routable: boolean;
  cabr_scored: boolean;
}
```

---

## 4. Required Fields (All Entity Types)

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `registry_id` | string | UUID v4 or deterministic SHA256[:16] | Primary key |
| `entity_type` | enum | One of 6 entity classes | Discriminator |
| `name` | string | Min 1 char, max 64 | Display name |
| `owner_id` | string | Non-empty | Creator/steward |
| `created_at` | ISO 8601 | Valid datetime | Immutable |
| `updated_at` | ISO 8601 | Valid datetime | Auto-updated |
| `public_surface_status` | enum | `hidden`, `discoverable`, `listed`, `promoted` | Visibility |

---

## 5. Optional Fields (Conditional by Entity Type)

### 5.1 FoundUp-Specific Fields

| Field | Type | When Required | Default |
|-------|------|---------------|---------|
| `manifest_path` | string | `entity_type == 'foundup'` | null |
| `version` | semver | When manifest exists | "0.0.0" |
| `tier` | enum | When manifest exists | `F0_DAE` |
| `lifecycle_stage` | enum | Always | "incubating" |
| `entry_url` | string | When frontend exists | null |
| `routing_prefix` | string | When routable | `/f/{id}` |
| `token_symbol` | string | When token policy defined | null |
| `cabr_contract` | object | When CABR-enabled | default contract |
| `capabilities` | string[] | When declared | [] |
| `agent_routes` | string[] | When OpenClaw-enabled | [] |

### 5.2 External FoundUp Fields

| Field | Type | Notes |
|-------|------|-------|
| `external_repo_url` | string | GitHub/GitLab URL |
| `external_manifest_sha` | string | Last verified SHA |
| `external_sync_status` | enum | `synced`, `stale`, `unreachable` |
| `embed_decision` | enum | `embedded`, `standalone`, `pending` |

### 5.3 Infrastructure Service Fields

| Field | Type | Notes |
|-------|------|-------|
| `service_port` | int | Default runtime port |
| `health_endpoint` | string | `/health` or similar |
| `depends_on` | string[] | Service dependencies |
| `mcp_server_name` | string | MCP registration name |

---

## 6. Stage Mapping

### 6.1 Dual Stage Set Reconciliation

Two stage vocabularies coexist (per `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` Section 2.3):

| Stage Set | Values | Source | Registry Mapping |
|-----------|--------|--------|------------------|
| **Manifest (Exfoliation)** | `incubating`, `proto`, `externalized`, `federated` | Manifest schema | `manifest_stage` field |
| **Simulator** | `idea`, `poc`, `soft-proto`, `proto`, `mvp`, `launch` | `state_store.py` | `simulator_stage` field |

### 6.2 Stage Field Schema

```typescript
interface StageInfo {
  // Manifest stage (exfoliation protocol)
  manifest_stage: 'incubating' | 'proto' | 'externalized' | 'federated';
  
  // Simulator stage (lifecycle model)
  simulator_stage: 'idea' | 'poc' | 'soft-proto' | 'proto' | 'mvp' | 'launch' | null;
  
  // Operational stage (catalog)
  catalog_stage: 'staging' | 'active' | null;
  
  // Stage progression timestamp
  last_stage_transition: string | null; // ISO 8601
}
```

### 6.3 Stage Transition Rules

| From Stage | To Stage | Trigger | Requires |
|------------|----------|---------|----------|
| `incubating` | `proto` | `tasks_completed >= 1` | Verified proof |
| `proto` | `externalized` | `customer_count >= 1` | Beta launch |
| `externalized` | `federated` | DAO vote | `F1_OPO` tier minimum |
| `idea` (sim) | `poc` (sim) | First task created | Simulator event |
| `poc` (sim) | `mvp` (sim) | Completed + customer | Simulator event |

---

## 7. Manifest Relationship

### 7.1 Manifest Binding Contract

```typescript
interface ManifestBinding {
  // Manifest file location
  manifest_path: string | null;  // Relative to repo root
  
  // Manifest validation status
  manifest_valid: boolean;
  manifest_validation_errors: string[];
  
  // Last sync timestamp
  manifest_synced_at: string | null;  // ISO 8601
  
  // Manifest content hash for change detection
  manifest_hash: string | null;  // SHA256
  
  // Schema version
  manifest_schema_version: string;  // e.g., "v1"
}
```

### 7.2 Manifest Discovery Sources

| Source | Path Pattern | Priority |
|--------|--------------|----------|
| Primary | `modules/foundups/{id}/foundup_manifest.json` | 1 |
| Gamification | `modules/gamification/{id}/foundup_manifest.json` | 2 |
| Platform | `modules/platform_integration/{id}/foundup_manifest.json` | 3 |
| HoloIndex | `holo_index/foundup_manifest.json` | 4 (infra-only) |

---

## 8. Public Surface Status

### 8.1 Visibility Enum

| Status | In Mall | In Search | In Catalog | Description |
|--------|---------|-----------|------------|-------------|
| `hidden` | NO | NO | NO | Internal only, dev/test |
| `discoverable` | NO | YES | NO | Can find via search |
| `listed` | YES | YES | YES | Full catalog presence |
| `promoted` | YES | YES | YES | Featured/pinned position |

### 8.2 Status Constraints

```yaml
# Status requirements by entity type
foundup:
  allowed: [hidden, discoverable, listed, promoted]
  default: hidden
  requires_for_listed: [valid_manifest, entry_url]

skeleton_candidate:
  allowed: [hidden, discoverable]
  default: discoverable
  requires_for_discoverable: [spec_document]

platform_layer:
  allowed: [hidden]
  default: hidden
  reason: "Infrastructure not user-visible"

infra_service:
  allowed: [hidden]
  default: hidden

external_foundup:
  allowed: [hidden, discoverable, listed]
  default: hidden
  requires_for_listed: [embed_decision == 'embedded']
```

---

## 9. Mall/Gate Status

### 9.1 Mall Visibility Contract

```typescript
interface MallStatus {
  // Mall tile eligibility
  mall_eligible: boolean;
  mall_eligibility_blockers: string[];  // Reasons if false
  
  // Mall tile position (if listed)
  mall_grid_position: { x: number; y: number } | null;
  mall_category: string | null;
  mall_priority: number;  // 0-100, higher = more prominent
  
  // Mall launch readiness
  launch_readiness: 'ready' | 'conditional' | 'discoverable_only';
  readiness_blockers: string[];
}
```

### 9.2 Gate Enforcement

| Gate | Enforced By | Blocks |
|------|-------------|--------|
| Tier gate | `shell_core.py` | Invalid tier values |
| Manifest gate | `validate_manifest()` | Schema violations |
| Signature gate | `SPECIFIED_NOT_IMPLEMENTED` | Unsigned manifests (future) |
| CABR gate | `cabr_contract.v1_gate` | Low-quality submissions |
| Subscription gate | `required_subscription_tier` | Insufficient user tier |

---

## 10. Hermes/OpenClaw Integration Status

### 10.1 Integration Status Enum

```typescript
interface OpenClawIntegration {
  // Overall integration state
  integration_status: 'none' | 'scaffold' | 'wired' | 'operational';
  
  // Component states
  hermes_routable: boolean;
  openclaw_gateway_registered: boolean;
  capability_tokens_enabled: boolean;
  destructive_guard_enabled: boolean;
  
  // Routes declared in manifest
  agent_routes: string[];
  
  // Validation results
  route_validation_status: 'untested' | 'dry_run_pass' | 'live_verified';
  last_route_validation: string | null;  // ISO 8601
}
```

### 10.2 Current Integration Audit

| FoundUp | Hermes | OpenClaw | Routes | Status |
|---------|--------|----------|--------|--------|
| gotjunk | NO | scaffold | `openclaw_query`, `openclaw_task` | `scaffold` |
| kosei | NO | NO | `[]` | `none` |
| trade | NO | scaffold | `openclaw_query` | `scaffold` |
| voteballots | NO | scaffold | `openclaw_query` | `scaffold` |
| whack_a_magat | NO | NO | `[]` | `none` |
| antifafm | NO | NO | `[]` | `none` |

---

## 11. Token Policy with TOKEN_DEFERRED

### 11.1 Token Policy Schema

```typescript
interface TokenPolicy {
  // Token definition status
  policy_status: 'defined' | 'deferred' | 'not_applicable';
  
  // If defined
  token_symbol: string | null;
  token_tier_backing: 'F0_DAE' | 'F1_OPO' | 'F2_GROWTH' | 'F3_INFRA' | 'F4_MEGA' | 'F5_SYSTEMIC' | null;
  token_supply_cap: number | null;
  
  // If deferred
  deferral_reason: string | null;  // Why token not yet assigned
  deferral_expires: string | null; // ISO 8601, when decision required
  
  // Economic flags
  cabr_pipe_eligible: boolean;
  ups_flow_enabled: boolean;
  demurrage_applicable: boolean;
}
```

### 11.2 TOKEN_DEFERRED Application Rules

```yaml
# When to use TOKEN_DEFERRED
apply_token_deferred:
  - entity_type: infra_service     # Always deferred
  - entity_type: platform_layer    # Always deferred
  - entity_type: tool_simulator    # Always deferred
  - entity_type: skeleton_candidate # Until implementation
  - entity_type: external_foundup   # Until integration complete

# When token policy MUST be defined
require_token_policy:
  - entity_type: foundup
    lifecycle_stage: externalized  # Post-OPO
  - tier: F1_OPO or higher         # Public offering
```

---

## 12. Registry Location Options

### 12.1 Candidate Locations

| Option | Path | Pros | Cons |
|--------|------|------|------|
| A: FAM Module | `modules/foundups/agent_market/registry/` | Near FAM, WSP 3 compliant | Circular dependency risk |
| B: pfMALL Module | `modules/foundups/pfmall/registry/` | Near shell discovery | Shell should consume, not own |
| C: Infrastructure | `modules/infrastructure/foundup_registry/` | Clear separation | New module overhead |
| D: Shared Utilities | `modules/infrastructure/shared_utilities/registry/` | Minimal footprint | Overloads utilities |
| E: Root Config | `config/foundup_registry.json` | Simple, visible | Not a module, no tests |

### 12.2 Recommended Location

**Option C: `modules/infrastructure/foundup_registry/`**

Rationale:
- WSP 3 domain compliance (infrastructure domain)
- WSP 72 module independence (no FoundUp domain coupling)
- Clear ownership boundary
- Can be consumed by FAM, pfMALL, simulator without cycles

---

## 13. Build-System Hooks

### 13.1 Pre-Commit Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| Manifest validation | `*.json` in manifest paths | Validate against schema |
| Registry sync | `foundup_manifest.json` change | Update registry cache |
| Tier consistency | `tier` field change | Cross-check dependencies |
| Route registration | `agent_routes` change | Validate OpenClaw routes |

### 13.2 CI/CD Integration Points

```yaml
# .github/workflows/foundup-registry.yml (schema only)
registry_checks:
  - manifest_schema_validation
  - tier_consistency_check
  - route_availability_check
  - stage_transition_audit
  - public_surface_sanity

build_hooks:
  - pre_commit: validate_manifest_schema
  - pre_push: registry_sync_check
  - ci_pipeline: full_registry_audit
```

### 13.3 Development Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `validate_all_manifests.py` | Batch manifest validation | `tools/development/` |
| `sync_registry.py` | Sync manifests to registry | `tools/development/` |
| `audit_registry_drift.py` | Detect manifest/registry divergence | `tools/development/` |
| `generate_registry_report.py` | Registry status report | `tools/development/` |

---

## 14. Complete Schema Definition

### 14.1 Full Registry Entry Schema

```typescript
interface FoundUpRegistryEntry {
  // === Core Identity ===
  registry_id: string;           // UUID v4 or SHA256[:16]
  entity_type: EntityType;       // Discriminator
  name: string;                  // Display name (max 64)
  owner_id: string;              // Creator/steward
  
  // === Timestamps ===
  created_at: string;            // ISO 8601, immutable
  updated_at: string;            // ISO 8601, auto-updated
  
  // === Manifest Binding ===
  manifest: ManifestBinding | null;
  
  // === Stage Info ===
  stages: StageInfo;
  
  // === Visibility ===
  public_surface_status: PublicSurfaceStatus;
  mall: MallStatus;
  
  // === Integration ===
  openclaw: OpenClawIntegration;
  
  // === Token Economics ===
  token_policy: TokenPolicy;
  
  // === Entity-Specific Extensions ===
  extensions: {
    external_foundup?: ExternalFoundUpFields;
    infra_service?: InfraServiceFields;
    // ... other entity-specific fields
  };
  
  // === Audit Trail ===
  audit: {
    last_validation: string | null;
    validation_errors: string[];
    wsp97_markers: string[];     // e.g., ["SPECIFIED_NOT_IMPLEMENTED"]
  };
}
```

---

## 15. Current Inventory Snapshot

### 15.1 Discovered FoundUps (via Manifest)

| ID | Name | Tier | Stage | Manifest | Entry URL | Token | Type |
|----|------|------|-------|----------|-----------|-------|------|
| gotjunk_001 | GotJunk | F0_DAE | proto | YES | Cloud Run | JUNK | `foundup` |
| kosei | Kosei AI Systems | F0_DAE | incubating | YES | Firebase | KOSEI | `foundup` |
| trade | Trade | F0_DAE | incubating | YES | null | TRADE | `skeleton_candidate` |
| voteballots | Vote/Ballots | F0_DAE | incubating | YES | "" | VOTE | `skeleton_candidate` |
| whack_a_magat | Whack-a-MAGAT | F0_DAE | incubating | YES | null | WAM | `foundup` |
| antifafm | AntifaFM | F0_DAE | incubating | YES | null | ANTI | `foundup` |
| holo_index | HoloIndex | N/A | N/A | PARTIAL | N/A | N/A | `infra_service` |

### 15.2 Inferred Entities (No Manifest)

| ID | Name | Type | Evidence |
|----|------|------|----------|
| pfmall_shell | pfMALL Shell | `platform_layer` | `shell_core.py` exists |
| fam_daemon | FAM Daemon | `infra_service` | `fam_daemon.py` exists |
| wre_core | WRE Runtime | `infra_service` | Module exists |
| simulator | Economics Simulator | `tool_simulator` | `mesa_model.py` exists |
| science_swarm | Science Swarm | `external_foundup` | Audit docs exist |

---

## 16. WSP 97 Verdict

| Criterion | Status | Evidence |
|-----------|--------|----------|
| DOCS_ONLY | PASS | No code created |
| AUDIT_ONLY | PASS | Schema spec only |
| NO_IMPLEMENTATION | PASS | No Python/TS written |
| NO_MODULE_DELETION | PASS | No deletions |
| NO_MANIFEST_CREATION | PASS | No new manifests |
| NO_TOKEN_ASSIGNMENT | PASS | TOKEN_DEFERRED used |
| TOKEN_DEFERRED_WHERE_UNKNOWN | PASS | All unknowns marked |
| NO_RUNTIME_CHANGE | PASS | No runtime modified |
| NO_DAO_ACTIVATION | PASS | No DAO actions |

**Overall Verdict**: `PASS - WSP 97 Compliant`

---

## 17. Next-Slice Recommendation

**Slice ID**: `FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1`

**Scope**:
1. Create `modules/infrastructure/foundup_registry/` module structure
2. Implement TypedDict/dataclass for `FoundUpRegistryEntry`
3. Implement manifest discovery adapter (read-only)
4. Add validation against schema
5. Create registry sync CLI tool

**WSP 97 Labels for Next Slice**:
```yaml
DOCS_ONLY: false
AUDIT_ONLY: false
NO_IMPLEMENTATION: false  # Implementation allowed
NO_MODULE_DELETION: true
NO_MANIFEST_CREATION: true
NO_TOKEN_ASSIGNMENT: true
TOKEN_DEFERRED_WHERE_UNKNOWN: true
NO_RUNTIME_CHANGE: true   # Read-only first
NO_CABR_READY: true
NO_PAYOUT_READY: true
NO_DAO_ACTIVATION: true
```

**Dependencies**:
- This audit (schema definition)
- `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` (manifest schema)
- `FOUNDUPOPS_MANIFEST_DISCOVERY_AND_FAM_REGISTRY_PHASE1.md` (discovery architecture)

---

## 18. Appendix: Source Files Referenced

| File | Purpose | Lines Read |
|------|---------|------------|
| `modules/foundups/agent_market/src/interfaces.py` | Service contracts | 1-273 |
| `modules/foundups/agent_market/src/models.py` | Entity models | 1-284 |
| `modules/foundups/agent_market/src/registry.py` | Current registry impl | 1-143 |
| `modules/foundups/simulator/state_store.py` | Simulator state | 1-520 |
| `modules/foundups/pfmall/shell_core.py` | Shell discovery | 1-100 |
| `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` | Manifest schema | Full |
| `docs/0102_session_briefings/FOUNDUPOPS_MANIFEST_DISCOVERY_AND_FAM_REGISTRY_PHASE1.md` | Discovery arch | Full |
| `modules/foundups/*/foundup_manifest.json` | 7 manifest files | Full |

---

*0102 pArtifact: Registry schema defined. No implementation. TOKEN_DEFERRED for unknowns. Next slice: implementation.*
