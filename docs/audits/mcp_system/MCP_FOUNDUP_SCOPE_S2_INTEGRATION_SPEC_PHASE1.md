# MCP FoundUp Scope S2 Integration Spec Phase 1

**Contract ID**: MCP_FOUNDUP_SCOPE_S2_INTEGRATION_SPEC_PHASE1
**Status**: SPEC_READY
**Author**: W9
**Date**: 2026-05-18
**Base Commit**: 7091d17330b904bde7e00f70cc085b9b923ad137
**Branch**: docs/mcp-foundup-scope-s2-integration-spec-phase1
**Worktree**: .claude/worktrees/MCPS2S-W9

---

## WSP 97 Labels

- DOCS_ONLY
- SPEC_ONLY
- NO_MCP_ROUTE_CHANGE
- NO_HOLOINDEX_MUTATION
- NO_REGISTRY_MUTATION
- NO_RUNTIME_FILTERING
- VALIDATION_ONLY_SPEC
- FAIL_CLOSED_REQUIRED
- NO_PFMALL_CATALOG_CHANGE
- NO_AUTH_CHANGE
- NO_CABR_READY
- NO_PAYOUT_READY
- NO_DAO_ACTIVATION

---

## 1. current_main_commit

```
7091d17330b904bde7e00f70cc085b9b923ad137
```

Commit message: `feat(foundups): add read-only registry loader for MCP scope validation (#638)`

---

## 2. source_artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Registry Loader | `modules/foundups/src/foundup_registry_loader.py` | MERGED (PR #638) |
| Registry JSON | `modules/foundups/foundup_registry.json` | PRODUCTION (14 entities) |
| Registry Schema | `modules/foundups/foundup_registry.schema.json` | PRODUCTION |
| S2 holo_tools | `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py` | PRODUCTION |
| S3 pAVS server | `modules/infrastructure/pavs_mcp/src/server.py` | PLACEHOLDER (6/8 real backends) |
| S2 INTERFACE | `modules/infrastructure/foundups_mcp_bridge/INTERFACE.md` | PRODUCTION |
| WSP 96 | `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md` | ACTIVE |
| Loader Tests | `modules/foundups/tests/test_foundup_registry_loader.py` | PASSING |

### Loader API (from PR #638)

```python
# Module-level functions (singleton pattern for default registry)
load_registry(path: Path | None = None) -> dict[str, Any]
list_foundup_ids(path: Path | None = None) -> tuple[str, ...]
is_valid_foundup_id(foundup_id: str, path: Path | None = None) -> bool
get_module_path(foundup_id: str, path: Path | None = None) -> str | None
get_entity_type(foundup_id: str, path: Path | None = None) -> str | None

# Class (for explicit path control)
FoundUpRegistryLoader(registry_path: Path | None = None)
  .is_valid_foundup_id(foundup_id: str) -> bool
  .get_module_path(foundup_id: str) -> str | None
  .get_entity_type(foundup_id: str) -> str | None
  .list_foundup_ids() -> tuple[str, ...]
  .get_registry() -> dict[str, Any]
  .path -> Path

# Exceptions
RegistryLoadError  # Malformed JSON or schema violations
FileNotFoundError  # Registry file missing
```

---

## 3. S2_current_behavior

### Current State (holo_tools.py lines 148-357)

S2 `holo_search` currently:

1. **Accepts `foundup_id` parameter** (line 155)
2. **Echoes `foundup_id` in response** (lines 364, 392)
3. **Does NOT validate** whether `foundup_id` exists in registry
4. **Does NOT filter** results by `foundup_id` scope
5. **Emits warning** via `federation_scope_warning(S2_SURFACE_ID)` (lines 99-121, 234-235)

Current warning emitted when `foundup_id` is supplied:

```
foundup_id received; tenant scoping not yet enforced at S2 (deferred to MCPA1 Slice 6 / federation auth).
```

### WSP 96 Annex A.2/A.5 Compliance Gap

Per WSP 96 Annex A.2:
> When `foundup_id` is set, the surface MUST verify caller authority over the named tenant before scoping.

Current S2 state violates this requirement but truthfully reports the gap via the warning (WSP 97 compliant on truth, not on enforcement).

---

## 4. loader_integration_point

### Recommended Integration File

**Primary**: `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py`

### Why S2 First

1. S2 is the **internal Python adapter** (no external MCP transport)
2. S2 is marked `RUNTIME_INTERNAL_ONLY` per WSP 96 Annex A.1
3. S3 delegates to S2 for `holo_search` (pavs_mcp/src/server.py lines 1509-1517)
4. S1 is external MCP adapter (foundups-mcp-p1 repo) - out of scope for monorepo Phase 1
5. Validating at S2 automatically covers S3 via delegation

### Integration Location

The validation should happen in `holo_search()` function (line 148) BEFORE any search execution:

```python
# PROPOSED LOCATION: After line 237 (empty-query rejection), before line 247 (backend path)
# Exact insertion point: Between EMPTY_QUERY rejection and HoloIndex instantiation
```

---

## 5. validation_flow

### Phase 1 Validation Flow (VALIDATION_ONLY, NO_RUNTIME_FILTERING)

```
                       holo_search() called
                              |
                              v
               +---------------------------------+
               | 1. Parse and normalize inputs   |
               |    (limit, doc_type_filter)     |
               +---------------------------------+
                              |
                              v
               +---------------------------------+
               | 2. EMPTY_QUERY rejection        |
               |    (existing, lines 238-245)    |
               +---------------------------------+
                              |
                              v
    +--------------------------------------------------+
    | 3. NEW: foundup_id validation                    |
    |    if foundup_id is not None:                    |
    |      if not is_valid_foundup_id(foundup_id):     |
    |        -> return INVALID_FOUNDUP_ID error        |
    |      else:                                       |
    |        -> add warning: "valid but not filtered"  |
    +--------------------------------------------------+
                              |
                              v
               +---------------------------------+
               | 4. HoloIndex search execution   |
               |    (existing, lines 247-357)    |
               +---------------------------------+
                              |
                              v
               +---------------------------------+
               | 5. Return response with         |
               |    warnings array populated     |
               +---------------------------------+
```

### Validation Decision Tree

```
foundup_id provided?
  |
  +-- NO --> Skip validation, proceed to search
  |
  +-- YES --> is_valid_foundup_id(foundup_id)?
                |
                +-- FALSE --> FAIL CLOSED
                |             Return error: INVALID_FOUNDUP_ID
                |             Status: "error"
                |             Do NOT execute search
                |
                +-- TRUE --> Add warning to metadata.warnings:
                             "foundup_id validated against registry but
                              result filtering deferred to Phase 2"
                             Proceed to search (unfiltered)
```

---

## 6. fail_closed_behavior

### Definition

When an unknown `foundup_id` is provided:
- **MUST NOT** execute the HoloIndex search
- **MUST NOT** fall back to ripgrep
- **MUST** return an error response immediately
- **MUST** include error code `INVALID_FOUNDUP_ID`

### Rationale

Per WSP 96 Annex A.5 C5:
> Surfaces respecting `foundup_id` scoping. [...] Cross-tenant queries without `include_shared=true` MUST be rejected with `error.code="TENANT_UNAUTHORIZED"`.

Phase 1 extends this to reject unknown tenants entirely, since we cannot authorize what does not exist.

### Registry Load Failure

If registry cannot be loaded (FileNotFoundError or RegistryLoadError):
- **MUST** return error code `REGISTRY_UNAVAILABLE`
- **MUST NOT** proceed with search
- **MUST** include diagnostic in `error.details`

---

## 7. error_response_contract

### INVALID_FOUNDUP_ID Error

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_FOUNDUP_ID",
    "message": "Unknown foundup_id: '{provided_id}'. Valid IDs must be registered in foundup_registry.json.",
    "details": {
      "provided_id": "...",
      "pattern_valid": true | false,
      "registry_checked": true
    }
  },
  "data": {
    "query": "...",
    "doc_type_filter": "...",
    "foundup_id": "...",
    "include_shared": null,
    "hits": [],
    "hit_count": 0,
    "metadata": {
      "retrieval_mode": "none",
      "engine_version": "validation_rejected",
      "warnings": []
    }
  },
  "meta": {
    "timestamp": "ISO8601",
    "source": "validation",
    "tool": "holo_search",
    "surface": "S2",
    "confidence": 0.0
  }
}
```

### REGISTRY_UNAVAILABLE Error

```json
{
  "status": "error",
  "error": {
    "code": "REGISTRY_UNAVAILABLE",
    "message": "FoundUp registry could not be loaded. Scope validation requires registry access.",
    "details": {
      "exception_type": "FileNotFoundError | RegistryLoadError",
      "exception_message": "..."
    }
  },
  "data": {
    "query": "...",
    "doc_type_filter": "...",
    "foundup_id": "...",
    "include_shared": null,
    "hits": [],
    "hit_count": 0,
    "metadata": {
      "retrieval_mode": "none",
      "engine_version": "registry_unavailable",
      "warnings": []
    }
  },
  "meta": {
    "timestamp": "ISO8601",
    "source": "validation",
    "tool": "holo_search",
    "surface": "S2",
    "confidence": 0.0
  }
}
```

---

## 8. allowed_behavior

Phase 1 implementation MAY:

1. Import `is_valid_foundup_id` from `modules.foundups.src.foundup_registry_loader`
2. Call `is_valid_foundup_id(foundup_id)` before search execution
3. Return `INVALID_FOUNDUP_ID` error for unknown IDs
4. Return `REGISTRY_UNAVAILABLE` error if registry cannot load
5. Add validation-related warnings to `metadata.warnings` array
6. Update `meta.source` to `"validation"` when validation rejects
7. Log validation outcomes at INFO level

Phase 1 implementation MAY also:

1. Cache the `FoundUpRegistryLoader` singleton for performance
2. Add validation timing to response metadata

---

## 9. forbidden_behavior

Phase 1 implementation MUST NOT:

1. Filter HoloIndex search results by `foundup_id` (deferred to Phase 2)
2. Modify HoloIndex collections or indexes
3. Add new collections for tenant scoping
4. Modify foundup_registry.json
5. Add new MCP routes or endpoints
6. Change S3 pAVS server routes
7. Modify pFMALL catalog structure
8. Implement authentication changes
9. Activate CABR validation
10. Enable payout flows
11. Activate DAO governance

---

## 10. deferred_filtering_phase

### What Remains for Phase 2

1. **Result Filtering**: Filter HoloIndex hits by `foundup_id` module path
2. **Collection Scoping**: Query tenant-specific collections (if created)
3. **include_shared Logic**: Implement cross-tenant inclusion/exclusion
4. **S3 Tenant Binding**: Connect `api_key` to `foundup_id` in S3

### Phase 2 Prerequisites

- Phase 1 validation passing all tests
- HoloIndex collection strategy decided (per-tenant vs shared)
- S3 auth/scope refactor complete (MCPA1 Slice 6)

### Phase 2 Spec ID

`MCP_FOUNDUP_SCOPE_S2_FILTERING_IMPL_PHASE2`

---

## 11. test_plan

### Unit Tests (test_holo_tools_foundup_validation.py)

| Test ID | Description | Assertion |
|---------|-------------|-----------|
| T1 | Valid foundup_id passes validation | `status == "ok"`, search executes |
| T2 | Invalid foundup_id fails closed | `status == "error"`, `error.code == "INVALID_FOUNDUP_ID"` |
| T3 | Unknown but pattern-valid ID fails | `error.details.pattern_valid == True`, `error.code == "INVALID_FOUNDUP_ID"` |
| T4 | Pattern-invalid ID fails | `error.details.pattern_valid == False` |
| T5 | null/None foundup_id skips validation | `status == "ok"`, no validation error |
| T6 | Registry load failure returns REGISTRY_UNAVAILABLE | `error.code == "REGISTRY_UNAVAILABLE"` |
| T7 | Valid foundup_id adds appropriate warning | `"validated against registry"` in warnings |
| T8 | Response includes validation source | `meta.source == "validation"` when rejected |

### Integration Tests

| Test ID | Description | Setup |
|---------|-------------|-------|
| I1 | S3 delegates to S2 with validation | Call S3 `holo_search` with invalid `foundup_id` |
| I2 | S2 loads production registry | No temp file, uses default path |
| I3 | Concurrent validation requests | Thread safety of singleton loader |

### Regression Tests

| Test ID | Description | Assertion |
|---------|-------------|-----------|
| R1 | Existing tests still pass | All test_holo_tools.py tests green |
| R2 | S2 response envelope unchanged for valid queries | Schema conformance maintained |
| R3 | Fallback behavior preserved | Ripgrep fallback unaffected by validation |

---

## 12. risk_matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Registry load breaks search globally | Low | High | Graceful error with REGISTRY_UNAVAILABLE; does not crash |
| Import path changes break loader | Low | Medium | Direct import from src/; no __init__.py dependency |
| Performance regression from validation | Low | Low | Singleton caching; validation is O(1) hashtable lookup |
| S3 delegation breaks | Low | Medium | S3 tests cover delegation path |
| False positives (valid ID rejected) | Very Low | High | Loader uses exact registry match; test coverage |
| False negatives (invalid ID passes) | Low | Medium | Phase 1 only validates existence, not authorization |

---

## 13. HoloIndex_assessment

### Queries Executed

1. `S2 holo_tools foundup_id validation FoundUp registry loader`
   - Result: No files found (query too specific)

2. `foundups_mcp_bridge holo_tools S2 MCP scope validation`
   - Code hits: `holo_tools.py`, `test_mcp_bridge.py`
   - WSP hits: WSP 96, WSP 103, WSP 104
   - Docs hits: foundups_mcp_bridge/INTERFACE.md

3. `pavs_mcp foundup_id cross tenant fail closed WSP 96 Annex A`
   - Code hits: `pavs_mcp/server.py`, `mcp_manager.py`
   - WSP hits: WSP 103, WSP 104, WSP 106

4. `foundup_registry_loader is_valid_foundup_id MCP integration`
   - Code hits: `mcp_integration.py`, `mcp_manager.py`, `pavs_mcp/server.py`
   - WSP hits: WSP 103, WSP 106, WSP 58

### Assessment

- **S2 holo_tools.py**: Confirmed as integration target (lines 148-357)
- **S3 pavs_mcp/server.py**: Confirmed delegation to S2 (lines 1509-1517)
- **Registry loader**: Confirmed merged at `modules/foundups/src/foundup_registry_loader.py`
- **WSP 96 Annex A**: Confirmed `foundup_id` validation requirement (Annex A.2, A.5 C5)
- **No existing validation**: Confirmed `is_valid_foundup_id` not called anywhere in MCP surfaces

---

## 14. WSP_97_truth_boundary

### Truth Claims in This Spec

| Claim | Evidence | Status |
|-------|----------|--------|
| Registry loader merged | PR #638, commit 7091d1733 | VERIFIED |
| S2 accepts foundup_id | holo_tools.py line 155 | VERIFIED |
| S2 does not validate | Grep for `is_valid_foundup_id` returns 0 hits in foundups_mcp_bridge | VERIFIED |
| S3 delegates to S2 | pavs_mcp/server.py lines 1509-1517 | VERIFIED |
| Registry has 14 entities | foundup_registry.json entities array | VERIFIED |
| Loader singleton exists | foundup_registry_loader.py lines 137-152 | VERIFIED |

### WSP 97 Compliance Status

This spec:
- **DOES** document actual current behavior
- **DOES** specify required future behavior
- **DOES NOT** claim implementation complete
- **DOES NOT** modify any code or routes

---

## 15. WSP_15_next_slice

### Next Slice ID

`MCP_FOUNDUP_SCOPE_S2_VALIDATION_IMPL_PHASE1`

### Next Slice Scope

Implement the validation logic specified in this document:
1. Import `is_valid_foundup_id` into `holo_tools.py`
2. Add validation check after EMPTY_QUERY rejection
3. Return `INVALID_FOUNDUP_ID` error for unknown IDs
4. Add validation warning for known IDs
5. Create `test_holo_tools_foundup_validation.py`
6. Update `INTERFACE.md` with validation behavior

### Next Worker Readiness

**W10 Prerequisites**:
- This spec merged to main
- No open questions on error response format
- No blockers from S3 delegation path

**W10 Scope**:
- IMPLEMENTATION_ONLY
- NO_ROUTE_CHANGE
- TESTS_REQUIRED
- NO_FILTERING (deferred to Phase 2)

---

## Appendix A: Related Audits

| Audit | Path | Relevance |
|-------|------|-----------|
| MCPA1_MCP_SURFACE_AUTHORITY_AUDIT | docs/audits/mcp_system/MCPA1_MCP_SURFACE_AUTHORITY_AUDIT.md | S1/S2/S3 surface definitions |
| MCPA6B_MCP_CONFORMANCE_REAUDIT | docs/audits/mcp_system/MCPA6B_MCP_CONFORMANCE_REAUDIT.md | WSP 96 Annex A conformance |

---

## Appendix B: Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-05-18 | W9 | Initial spec |
