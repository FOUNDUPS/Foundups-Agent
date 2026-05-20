# MCP_FOUNDUP_SCOPE_REGISTRY_LOADER_SPEC_PHASE1

**Worker**: W9
**Date**: 2026-05-21
**Status**: SPEC_COMPLETE
**Mode**: DOCS_ONLY
**Context**: WSP 00 -> WSP 15 -> WSP 50 -> WSP 87 -> WSP 96 -> WSP 97

---

## 1. current_main_commit

```
bb06ebf3a5a966dbe5d80289e3a887dd67d00d16
```

Verified via `git rev-parse HEAD` after checkout from origin/main.

---

## 2. source_audits_used

| Document | Location | Purpose |
|----------|----------|---------|
| MCP_FOUNDUP_SCOPE_CURRENT_ARCHITECTURE_REAUDIT_PHASE1 | `docs/audits/mcp_system/` | Template establishing reaudit scope for #633 |
| WSP 96 Annex A | `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md` | Canonical `holo_search` contract and `foundup_id` semantics |
| WSP 104 | `WSP_framework/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` | Tenant isolation model (`/f/{foundup_id}`) |
| foundup_registry.json | `modules/foundups/foundup_registry.json` | Canonical registry with 14 entities |
| foundup_registry.schema.json | `modules/foundups/foundup_registry.schema.json` | Schema v1.0.0 with `foundup_id` pattern constraint |
| pavs_mcp/server.py | `modules/infrastructure/pavs_mcp/src/server.py` | S3 surface with cross-tenant detection |
| foundups_mcp_bridge/holo_tools.py | `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py` | S2 surface with `foundup_id` warning |

---

## 3. canonical_identifier_model

### 3.1 foundup_id Definition

**Source**: `foundup_registry.schema.json` lines 142-145

```json
"foundup_id": {
  "type": "string",
  "pattern": "^[a-z0-9_]+$",
  "description": "Canonical identifier (lowercase, underscores, digits)"
}
```

**Constraint**: MCP scope identifiers MUST match the `^[a-z0-9_]+$` pattern.

### 3.2 WSP 96 Annex A.2 foundup_id Semantics

**Source**: WSP 96 lines 278-289

- `foundup_id` is optional (null = global query)
- When set, the surface MUST verify caller authority over the named tenant
- `include_shared` controls cross-tenant corpus inclusion (default true)

### 3.3 Registry-Backed Validation

**Spec Decision**: MCP surfaces SHOULD validate that `foundup_id` values exist in `foundup_registry.json` before scoping queries.

**Rationale**:
1. Prevents typo-based scope confusion (e.g., `gotjunk_01` vs `gotjunk_001`)
2. Enables early rejection of unknown tenants
3. Provides audit trail for scope attempts

### 3.4 Canonical Identifier for MCP Scope

**Answer to Spec Question 1**: The canonical identifier for MCP scope is the `foundup_id` field from `foundup_registry.json`, validated against the `^[a-z0-9_]+$` pattern.

---

## 4. read_only_loader_contract_needed

### 4.1 Purpose

A read-only registry loader provides runtime access to `foundup_registry.json` without mutation capability.

### 4.2 Loader Contract (Phase 1)

```python
class FoundUpRegistryLoader:
    """Read-only loader for foundup_registry.json (WSP 97: NO_REGISTRY_MUTATION)."""
    
    def __init__(self, registry_path: Path):
        """Load registry once at construction time."""
        pass
    
    def is_valid_foundup_id(self, foundup_id: str) -> bool:
        """Check if foundup_id exists in registry."""
        pass
    
    def get_module_path(self, foundup_id: str) -> Optional[str]:
        """Return module_path for given foundup_id, or None if not found."""
        pass
    
    def get_entity_type(self, foundup_id: str) -> Optional[str]:
        """Return entity_type for given foundup_id (for scoping decisions)."""
        pass
    
    def list_foundup_ids(self) -> List[str]:
        """Return all known foundup_ids (for debugging/discovery)."""
        pass
```

### 4.3 Forbidden Operations (WSP 97 Boundary)

The loader MUST NOT:
- Write to `foundup_registry.json`
- Add/remove/modify registry entries
- Cache with TTL that could serve stale data after registry update
- Expose mutation methods even as placeholders

### 4.4 Answer to Spec Question 5

**Phase 1 loader MUST expose**:
1. `is_valid_foundup_id(foundup_id) -> bool`
2. `get_module_path(foundup_id) -> Optional[str]`
3. `get_entity_type(foundup_id) -> Optional[str]`
4. `list_foundup_ids() -> List[str]`

---

## 5. MCP_scope_resolution_flow

### 5.1 Current State (Pre-Loader)

```
S3 (pavs_mcp)          S2 (holo_tools)
     |                       |
     v                       v
 foundup_id param       foundup_id param
     |                       |
     v                       v
 _validate_scope()      federation_scope_warning()
     |                       |
     v                       v
 CROSS_TENANT_VIOLATION   Warning only (no filter)
 if mismatch
```

**Current gaps**:
- S3 checks against `registered_foundup_id` from API key binding, not canonical registry
- S2 emits warning but does not validate `foundup_id` exists
- Neither surface filters results by `foundup_id`

### 5.2 Target State (With Loader)

```
                Registry Loader (read-only)
                         |
          +--------------+---------------+
          |              |               |
          v              v               v
     S3 scope       S2 scope        HoloIndex
     validation     validation      query layer
          |              |               |
          v              v               v
     is_valid?       is_valid?       module_path
          |              |            filter
          v              v               |
     REJECT if       REJECT if          v
     unknown         unknown         Scoped hits
```

### 5.3 Where Should Filtering Happen?

**Answer to Spec Question 4**:

| Layer | Role | Spec Recommendation |
|-------|------|---------------------|
| MCP Server (S3) | Auth/scope gate | MUST validate `foundup_id` exists before forwarding |
| Bridge (S2) | Internal adapter | SHOULD validate `foundup_id` exists; SHOULD pass to HoloIndex |
| HoloIndex Query Layer | Retrieval filtering | SHOULD filter by `module_path` prefix when `foundup_id` is set |
| Registry Loader | Validation source | MUST provide `is_valid_foundup_id()` and `get_module_path()` |

**Primary filter location**: HoloIndex query layer (after validation).
**Validation location**: MCP server/bridge (before query).

---

## 6. allowed_behavior

### 6.1 Phase 1 Allowed

| Behavior | Rationale |
|----------|-----------|
| Load `foundup_registry.json` at startup | Read-only operation |
| Validate `foundup_id` against registry | Prevents typo-based scope confusion |
| Return validation errors for unknown `foundup_id` | Fail-closed behavior |
| Pass validated `foundup_id` to HoloIndex | Enables future filtering |
| Log scope validation attempts | Audit trail |
| Cache registry in memory (no TTL mutation) | Performance |

### 6.2 Answer to Spec Question 2

**Should MCP accept only registry-backed `foundup_id` values?**

**SPEC DECISION**: YES, with the following constraints:
- Unknown `foundup_id` values MUST be rejected at the MCP server layer
- Rejection MUST use structured error (`INVALID_FOUNDUP_ID`)
- Rejection MUST NOT leak whether the `foundup_id` exists (timing attack prevention)

---

## 7. forbidden_behavior

### 7.1 WSP 97 Labels Applied

- **NO_MCP_ROUTE_CHANGE**: Implementation slice cannot add/modify MCP routes
- **NO_HOLOINDEX_MUTATION**: Implementation slice cannot modify HoloIndex storage
- **NO_REGISTRY_MUTATION**: Loader MUST be read-only
- **NO_PFMALL_CATALOG_CHANGE**: Loader does not affect pfMALL
- **NO_RUNTIME_FILTERING**: Phase 1 is spec-only; no query filtering yet
- **NO_STALE_PR_RESURRECTION**: PR #513 MUST NOT be rebased
- **NO_CABR_READY**: This slice is not CABR-related
- **NO_PAYOUT_READY**: This slice does not affect payouts
- **NO_DAO_ACTIVATION**: This slice does not affect DAO

### 7.2 Answer to Spec Question 6

**What must remain forbidden?**

| Forbidden Action | Rationale |
|-----------------|-----------|
| Writing to `foundup_registry.json` | Registry mutations require dedicated audit trail |
| Modifying MCP tool signatures | Requires broader conformance audit |
| Adding runtime filtering in this spec | Implementation deferred to Phase 2 |
| Resurrecting PR #513 | 116 commits behind; conflicts with WSP 96 Annex A |
| Adding new MCP routes | Scope limited to loader contract |

---

## 8. fail_closed_vs_warn_only_decision

### 8.1 Analysis

| Option | Pros | Cons |
|--------|------|------|
| **Fail closed** | Prevents silent scope confusion; audit-friendly | May break existing callers expecting warn-only |
| **Warn only** | Backward compatible | Scope confusion continues; audit gaps |

### 8.2 Current Behavior

- **S3 (pavs_mcp)**: Fails closed for cross-tenant violations (`CROSS_TENANT_VIOLATION`)
- **S2 (holo_tools)**: Warns only (`federation_scope_warning()`)

### 8.3 Answer to Spec Question 3

**Should unknown `foundup_id` fail closed or warn only?**

**SPEC DECISION**: **FAIL CLOSED** for unknown `foundup_id` values.

**Rationale**:
1. WSP 96 Annex A.5 C5 requires surfaces to "verify caller authority over the named tenant"
2. Unknown `foundup_id` cannot have verified authority
3. Warn-only allows silent scope confusion
4. S3 already fails closed; S2 should align

**Error shape**:
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_FOUNDUP_ID",
    "message": "Unknown foundup_id: '<id>'. Verify identifier against canonical registry.",
    "registry_path": "modules/foundups/foundup_registry.json"
  },
  "meta": { "surface": "S2|S3", "tool": "holo_search" }
}
```

---

## 9. implementation_test_requirements

### 9.1 Answer to Spec Question 7

**What exact tests must the implementation slice include?**

| Test ID | Description | Assert |
|---------|-------------|--------|
| `test_loader_valid_foundup_id` | Known `foundup_id` returns True | `loader.is_valid_foundup_id("gotjunk_001") == True` |
| `test_loader_invalid_foundup_id` | Unknown `foundup_id` returns False | `loader.is_valid_foundup_id("nonexistent_xyz") == False` |
| `test_loader_get_module_path_exists` | Known `foundup_id` returns path | `loader.get_module_path("gotjunk_001") == "modules/foundups/gotjunk"` |
| `test_loader_get_module_path_missing` | Unknown `foundup_id` returns None | `loader.get_module_path("fake") is None` |
| `test_loader_pattern_enforcement` | Invalid pattern rejected | `loader.is_valid_foundup_id("UPPERCASE") == False` (not in registry) |
| `test_loader_list_all` | List returns all known IDs | `"gotjunk_001" in loader.list_foundup_ids()` |
| `test_loader_readonly` | No mutation methods exist | `hasattr(loader, "add_entry") == False` |
| `test_loader_registry_not_found` | Missing registry raises clear error | `FoundUpRegistryLoader(Path("/nonexistent"))` raises `FileNotFoundError` |
| `test_mcp_unknown_foundup_fails` | S3 rejects unknown `foundup_id` | Response contains `INVALID_FOUNDUP_ID` error code |
| `test_bridge_unknown_foundup_fails` | S2 rejects unknown `foundup_id` | Response contains `INVALID_FOUNDUP_ID` error code |

---

## 10. risk_matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Loader caches stale registry | Medium | Medium | Reload on schema version mismatch; document reload behavior |
| Pattern mismatch with registry schema | Low | High | Loader validates pattern at load time |
| Cross-surface inconsistency (S2 vs S3) | Medium | Medium | Shared loader instance; unified error codes |
| Breaking existing callers | Low | Medium | Fail-closed only for `foundup_id` param; global queries unaffected |
| Timing attack on `foundup_id` validation | Low | Low | Constant-time comparison not required (IDs are public) |
| Registry file locking on Windows | Low | Medium | Read-only opens do not lock; document concurrent access |

---

## 11. HoloIndex_assessment

### 11.1 HoloIndex Query Results

**Query 1**: "MCP FoundUp scope registry loader foundup_id WSP 96 Annex A"
- Found: `pavs_mcp/server.py`, `foundup_spawner.py`, `mcp_manager.py`
- WSP hits: WSP 103, WSP 58, WSP 106
- Assessment: Existing infrastructure uses `foundup_id` but lacks registry validation

**Query 2**: "foundup_registry read only loader MCP scope module_path"
- Found: `pavs_mcp/server.py`, `test_server_holo_search.py`, `mcp_manager.py`
- Assessment: `module_path` field exists in registry; no loader abstraction yet

**Query 3**: "pavs_mcp foundup_id cross tenant violation filter results"
- Found: `pavs_mcp/server.py` with `_validate_scope()` method
- Assessment: S3 detects cross-tenant but validates against API key binding, not registry

**Query 4**: "foundups_mcp_bridge holo_tools foundup_id warning filter"
- Found: `holo_tools.py` with `federation_scope_warning()`
- Assessment: S2 warns but does not validate or filter

### 11.2 HoloIndex Gap Summary

| Gap | Current State | Required State |
|-----|---------------|----------------|
| Registry loader | None | Read-only loader exposing validation |
| S3 validation | API key binding only | API key + registry validation |
| S2 validation | Warning only | Fail-closed + registry validation |
| Result filtering | Not implemented | Deferred to Phase 2 |

---

## 12. WSP_97_truth_boundary

### 12.1 Labels Applied to This Spec

```yaml
DOCS_ONLY: true
SPEC_ONLY: true
NO_MCP_ROUTE_CHANGE: true
NO_HOLOINDEX_MUTATION: true
NO_REGISTRY_MUTATION: true
NO_PFMALL_CATALOG_CHANGE: true
NO_RUNTIME_FILTERING: true
NO_STALE_PR_RESURRECTION: true
NO_CABR_READY: true
NO_PAYOUT_READY: true
NO_DAO_ACTIVATION: true
```

### 12.2 Truth Assertions

| Assertion | Evidence |
|-----------|----------|
| This spec does not modify runtime behavior | File is `.md` only |
| This spec does not resurrect PR #513 | PR reference is for context only |
| This spec does not modify `foundup_registry.json` | Loader is read-only by design |
| This spec does not modify HoloIndex | Filtering deferred to Phase 2 |

---

## 13. WSP_15_next_slice

### 13.1 Recommended Next Slice

**Slice ID**: `FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1`

**Scope**:
1. Implement `FoundUpRegistryLoader` class per Section 4.2 contract
2. Add loader to `modules/foundups/src/` (not `modules/infrastructure/`)
3. Write tests per Section 9.1 requirements
4. Document loader in `modules/foundups/INTERFACE.md`
5. DO NOT integrate with MCP surfaces (deferred to Phase 2)

**Dependencies**:
- `foundup_registry.json` (exists)
- `foundup_registry.schema.json` (exists)

**WSP 15 Score Estimate**:
- Urgency: Medium (scope confusion exists)
- Complexity: Low (read-only loader is trivial)
- Impact: Medium (enables future MCP scope enforcement)
- Priority: P2

### 13.2 Subsequent Slices

| Order | Slice ID | Scope |
|-------|----------|-------|
| 2 | `MCP_FOUNDUP_SCOPE_S2_INTEGRATION_PHASE1` | Integrate loader with S2 (holo_tools.py) |
| 3 | `MCP_FOUNDUP_SCOPE_S3_INTEGRATION_PHASE1` | Integrate loader with S3 (pavs_mcp/server.py) |
| 4 | `MCP_FOUNDUP_SCOPE_HOLOINDEX_FILTER_PHASE1` | Add `module_path` filtering to HoloIndex queries |

---

## 14. W10 Readiness Summary

### 14.1 Spec Deliverables

| Deliverable | Status |
|-------------|--------|
| current_main_commit | `bb06ebf3a` |
| source_audits_used | 7 documents cited |
| canonical_identifier_model | `foundup_id` per schema |
| read_only_loader_contract | 4 methods specified |
| MCP_scope_resolution_flow | Diagrammed |
| allowed_behavior | 6 behaviors specified |
| forbidden_behavior | 9 behaviors enumerated |
| fail_closed_vs_warn_only_decision | FAIL CLOSED |
| implementation_test_requirements | 10 tests specified |
| risk_matrix | 6 risks assessed |
| HoloIndex_assessment | 4 queries, 4 gaps identified |
| WSP_97_truth_boundary | 11 labels applied |
| WSP_15_next_slice | `FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1` |

### 14.2 Branch/Worktree Information

| Field | Value |
|-------|-------|
| Worktree | `.claude/worktrees/MCPRLS-W9` |
| Branch | `docs/mcp-foundup-scope-registry-loader-spec-phase1` |
| Base commit | `bb06ebf3a5a966dbe5d80289e3a887dd67d00d16` |
| File changed | `docs/audits/mcp_system/MCP_FOUNDUP_SCOPE_REGISTRY_LOADER_SPEC_PHASE1.md` |

### 14.3 WSP 97 Verdict

**SPEC_COMPLETE**: This document specifies the read-only registry loader contract for MCP FoundUp scoping without modifying runtime behavior.

### 14.4 W10 Readiness

**READY**: W10 may proceed with `FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1` implementation slice using this spec as the authoritative contract.

---

*Spec authored by W9 under WSP 00 -> WSP 97 -> WSP 15.*
