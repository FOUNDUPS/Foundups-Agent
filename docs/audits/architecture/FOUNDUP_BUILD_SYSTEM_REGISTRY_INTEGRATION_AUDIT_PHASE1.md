# FOUNDUP_BUILD_SYSTEM_REGISTRY_INTEGRATION_AUDIT_PHASE1

**Worker**: W6  
**Date**: 2026-05-20  
**Status**: READY_FOR_AUDIT  
**Context**: WSP 00 → WSP 97 → WSP 15 → WSP 50  
**Prerequisite**: PR #632 (Registry Population) merged at `56a82054e`

---

## 1. Audit Objective

Audit how the canonical FoundUp registry (`foundup_registry.json`) should integrate with the Hermes/OpenClaw build system for entity discovery and build contract enforcement.

---

## 2. Audit Scope

### Registry Source

| File | Entities | Status |
|------|----------|--------|
| `modules/foundups/foundup_registry.json` | 14 | CANONICAL |

### Entity Types for Build System

| Entity Type | Count | Build System Relevance |
|-------------|-------|------------------------|
| foundup | 4 | Primary build targets |
| skeleton_candidate | 3 | Scaffold/spec only |
| platform_layer | 1 | Infrastructure, not buildable |
| infra_service | 2 | Infrastructure, not buildable |
| tool_simulator | 1 | Tool, not buildable |
| access_service | 1 | Service, not buildable |
| external_foundup | 2 | External repos, different build path |

### Questions to Answer

1. Which entity types should be visible to Hermes/OpenClaw build system?
2. What `hermes_openclaw_build_status` values should gate build operations?
3. How should `manifest_status` affect build discovery?
4. Should external_foundups have a different build contract?
5. What registry fields does the build system need to query?

---

## 3. Expected Deliverables

1. Build system entity visibility matrix
2. Build gate field specification
3. Integration interface proposal (read-only registry query)
4. Test requirements for build system registry queries
5. WSP 97 truth boundary labels

---

## 4. WSP 97 Constraints

- AUDIT_ONLY
- NO_RUNTIME_CHANGE
- NO_REGISTRY_MODIFICATION
- NO_BUILD_EXECUTION
- NO_HERMES_ENABLEMENT
- NO_CABR_READY
- NO_PAYOUT_READY
- NO_DAO_ACTIVATION

---

## 5. Related Work

| Item | Status | Notes |
|------|--------|-------|
| PR #630 | MERGED | Registry schema |
| PR #632 | MERGED | Registry population |
| PR #513 | PARKED | MCP scope (conflicts) |

---

*Audit template prepared by W10 under WSP 00 → WSP 97.*
