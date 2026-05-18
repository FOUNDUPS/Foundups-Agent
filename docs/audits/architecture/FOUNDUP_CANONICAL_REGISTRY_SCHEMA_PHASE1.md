# FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1

**Slice**: `FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1`
**Worker**: W6 (session coordinator with internal sub-workers)
**Date**: 2026-05-18
**Mode**: Schema/scaffold only
**WSP Lock**: WSP_00, WSP_97, WSP_87, WSP_15, WSP_50

---

## WSP 97 Labels

```yaml
REGISTRY_SCHEMA_ONLY: true
NO_RUNTIME_CHANGE: true
NO_MANIFEST_CREATION: true
NO_TOKEN_ASSIGNMENT: true
NO_MODULE_DELETION: true
NO_PUBLIC_ROUTE_CHANGE: true
NO_AUTH_CHANGE: true
NO_CABR_READY: true
NO_PAYOUT_READY: true
NO_DAO_ACTIVATION: true
```

---

## 1. Executive Summary

This slice implements the **first canonical FoundUp registry schema artifact** based on the merged FoundUp inventory audit suite (PRs #624-629). The registry defines a typed entity classification system that distinguishes FoundUps from platform layers, infrastructure services, tools, and external repos.

**Key Deliverables**:
- JSON Schema v1.0.0 at `modules/foundups/foundup_registry.schema.json`
- Example registry with 6 evidence-backed entries
- 22 validation tests (all passing)

**Not Implemented** (per WSP 97):
- No registry population beyond examples
- No token assignment (uses TOKEN_DEFERRED)
- No manifest creation for entities without one
- No runtime/route/auth changes

---

## 2. Prerequisites Verified

| PR | Title | Status |
|----|-------|--------|
| #624 | FoundUp canonical inventory | MERGED |
| #625 | FoundUp registry schema audit | MERGED |
| #626 | FoundUp public surface status | MERGED |
| #627 | move2japan role | MERGED |
| #628 | PQN Portal / Science Swarm drift | MERGED |
| #629 | AutoPost completion | MERGED |

All 6 audit docs confirmed present in `docs/audits/architecture/`.

---

## 3. HoloIndex Assessment

### Queries Executed

| Query | Results | Top Hits |
|-------|---------|----------|
| FoundUp canonical registry schema entity classes | 20 hits | envelope.py, holo_tools.py, PFMALL_FOUNDUP_MANIFEST_SCHEMA.md |
| FOUNDUP_CANONICAL_REGISTRY_SCHEMA_AUDIT_PHASE1 | 20 hits | envelope.py, contracts.py, CANONICAL_FOUNDUP_INVENTORY.md |
| FoundUp manifest gotjunk kosei voteballots | 20 hits | trade tests, swarm dispatch tests |
| Hermes OpenClaw FoundUp build registry | 20 hits | hermes_foundup_builder.py, hermes_adapter.py |
| FoundUp public surface status gate model | 20 hits | build_plan.py, foundup_job_router.py |

### Assessment

| Metric | Value |
|--------|-------|
| **Useful?** | PARTIAL - found related foundups code and existing docs |
| **Noisy?** | YES - WSP docs, knowledge papers not directly relevant to audit docs |
| **Missing?** | YES - None of the 6 merged audit docs appeared in results |
| **Fallback needed?** | YES - Direct file reads required for audit docs |
| **Root cause** | Audit docs just merged, HoloIndex not reindexed |

---

## 4. Schema Fields Implemented

### 4.1 Entity Types

| Type | Description | Evidence Source |
|------|-------------|-----------------|
| `foundup` | Full FoundUp with token, CABR | Inventory audit Section 5.1 |
| `platform_layer` | Shell/funnel surface (pfmall) | 012 correction (Section 2.1) |
| `infra_service` | Backend service (FAM, WRE) | 012 correction (Section 2.2) |
| `tool_simulator` | Economics engine | 012 correction (Section 2.6) |
| `external_foundup` | External repo FoundUp | AutoPost audit |
| `skeleton_candidate` | Spec exists, no impl | Schema audit Section 3.1 |
| `access_service` | YT monitor/funnel (move2japan) | Move2Japan audit (Section 10) |

### 4.2 Implementation Status

| Status | Definition |
|--------|------------|
| `SPECIFIED` | Spec exists, no implementation |
| `IMPLEMENTED` | Code exists and runs |
| `TESTED` | Has passing tests |
| `RUNTIME_ENFORCED` | Active in production |
| `DOC_ONLY` | Documentation artifact only |
| `SIMULATOR_ONLY` | Only runs in simulator |
| `REVIEW_ONLY` | Human review required |
| `GATED_NOT_ENABLED` | Feature-flagged off |
| `DEPRECATED` | Scheduled for removal |
| `UNKNOWN` | Status not determined |

### 4.3 Token Status

| Status | Description |
|--------|-------------|
| `EXISTS` | Token symbol assigned (requires symbol field) |
| `TOKEN_DEFERRED` | Token not yet assigned |
| `NOT_APPLICABLE` | Entity type doesn't support tokens |
| `UNKNOWN` | Token status undetermined |

### 4.4 Public Surface Status

| Status | In Mall | In Search | Description |
|--------|---------|-----------|-------------|
| `hidden` | NO | NO | Internal only |
| `discoverable` | NO | YES | Findable via search |
| `listed` | YES | YES | Full catalog presence |
| `promoted` | YES | YES | Featured position |

---

## 5. Example Entries Included

| Entity ID | Type | Token Status | Evidence Doc |
|-----------|------|--------------|--------------|
| `gotjunk_001` | foundup | EXISTS (JUNK) | Inventory audit |
| `voteballots` | skeleton_candidate | EXISTS (VOTE) | Inventory audit |
| `pfmall` | platform_layer | NOT_APPLICABLE | 012 correction |
| `move2japan` | access_service | TOKEN_DEFERRED | Move2Japan audit |
| `autopost` | external_foundup | TOKEN_DEFERRED | AutoPost audit |
| `pqn_portal` | skeleton_candidate | TOKEN_DEFERRED | PQN Portal audit |

---

## 6. Schema Validation Rules

### 6.1 Conditional Requirements

| Condition | Required Fields |
|-----------|-----------------|
| `token_status == EXISTS` | `token_symbol` must be non-empty string |
| `entity_type == foundup` | `tier` and `stage` required |
| `entity_type == external_foundup` | `related_external_repo` required |

### 6.2 Type Nullability

| Field | Nullable? | Reason |
|-------|-----------|--------|
| `stage` | YES | Platform layers/services don't have stages |
| `tier` | YES | Non-FoundUp types don't have tiers |
| `module_path` | YES | External FoundUps have no monorepo path |
| `token_symbol` | YES | TOKEN_DEFERRED entries have no symbol |

---

## 7. Test Results

```
============================= test session starts =============================
collected 22 items

modules/foundups/tests/test_foundup_registry_schema.py ...................... [100%]

============================= 22 passed in 0.15s ==============================
```

### Test Classes

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestSchemaStructure` | 6 | Schema file structure |
| `TestExampleRegistryValidation` | 4 | Example validates |
| `TestInvalidEntityTypeRejection` | 1 | Invalid types rejected |
| `TestTokenStatusValidation` | 2 | Token/symbol rules |
| `TestVoteSpecifiedNotImplemented` | 1 | VOTE can be SPECIFIED |
| `TestMove2JapanAccessService` | 2 | access_service validates |
| `TestExternalFoundupRequiresRepo` | 2 | External requires repo |
| `TestFoundupRequiresTierAndStage` | 2 | FoundUp requires tier |
| `TestNoInventedTokens` | 2 | No invented tokens |

---

## 8. Files Created/Modified

| File | Action | Lines |
|------|--------|-------|
| `modules/foundups/foundup_registry.schema.json` | CREATED | ~200 |
| `modules/foundups/foundup_registry.example.json` | CREATED | ~150 |
| `modules/foundups/tests/test_foundup_registry_schema.py` | CREATED | ~280 |
| `docs/audits/architecture/FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1.md` | CREATED | This file |
| `modules/foundups/ModLog.md` | UPDATED | +entry |

---

## 9. Internal Sub-Workers Used

| Sub-worker | Purpose | Output |
|------------|---------|--------|
| discovery_subworker | Read 6 audit docs | Entity types, field requirements |
| schema_subworker | Create JSON Schema | foundup_registry.schema.json |
| example_subworker | Create example registry | foundup_registry.example.json |
| test_subworker | Create validation tests | test_foundup_registry_schema.py |
| docs_subworker | Create audit doc, ModLogs | This file, ModLog entry |
| verification_subworker | Verify forbidden files | No violations |

---

## 10. WSP 97 Verification

| Claim | Status | Evidence |
|-------|--------|----------|
| REGISTRY_SCHEMA_ONLY | PASS | Only schema and example created |
| NO_RUNTIME_CHANGE | PASS | No runtime files modified |
| NO_MANIFEST_CREATION | PASS | No new manifests created |
| NO_TOKEN_ASSIGNMENT | PASS | TOKEN_DEFERRED used for unknowns |
| NO_MODULE_DELETION | PASS | No modules deleted |
| NO_PUBLIC_ROUTE_CHANGE | PASS | No routes modified |
| NO_AUTH_CHANGE | PASS | No auth files touched |
| NO_CABR_READY | PASS | No CABR claims |
| NO_PAYOUT_READY | PASS | No payout claims |
| NO_DAO_ACTIVATION | PASS | No DAO claims |

**WSP 97 Verdict**: COMPLIANT

---

## 11. Next Slice Recommendation

**Slice ID**: `FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1`

**Scope**:
1. Populate registry with all 5 manifest-bearing FoundUps
2. Add platform layers (pfmall, agent_market)
3. Add infrastructure services (WRE, FAM daemon)
4. Add tools (simulator, ecosystem_animation)
5. Create registry loading utility

**WSP 97 Labels**:
```yaml
REGISTRY_POPULATION_ALLOWED: true
NO_TOKEN_ASSIGNMENT: true  # Still deferred for unknowns
NO_RUNTIME_CHANGE: true
```

---

## 12. Hermes/OpenClaw Build Contract

This registry serves as the **Hermes/OpenClaw build contract** by providing:

1. **Entity Discovery**: Typed entities with module paths
2. **Build Eligibility**: `hermes_openclaw_build_status` field (none/scaffold/wired/operational)
3. **Manifest Binding**: `manifest_path` for manifest-bearing entities
4. **Stage Gating**: `stage` and `poc_status` for progression gates
5. **Token Validation**: `token_status` and `token_symbol` for economics integration

OpenClaw can query the registry to determine which entities are eligible for:
- Job creation
- Capability token issuance
- CABR contract binding
- Route registration

---

**END OF AUDIT**

Worker: W6
Slice: FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1
WSP 97 Verdict: COMPLIANT
Tests: 22/22 passing
W10 Readiness: YES
