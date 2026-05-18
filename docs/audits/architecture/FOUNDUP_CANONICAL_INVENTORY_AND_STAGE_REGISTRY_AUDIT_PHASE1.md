# FoundUp Canonical Inventory and Stage Registry Audit - Phase 1

**Slice**: `FCISRA-W9`
**Worker**: W9 (audit/spec)
**Date**: 2026-05-14
**WSP References**: WSP 3 (Domain Organization), WSP 49 (Module Structure), WSP 97 (Truth Boundaries), WSP 104 (Namespace)

---

## 1. Executive Summary

This audit inventories **all existing FoundUps** across the Foundups-Agent codebase and external repos, classifies their implementation stage, and defines a **canonical stage registry schema** that must exist before VOTE-specific or any FoundUp-specific gate work proceeds.

**Finding**: The ecosystem has **14+ identified FoundUp entities** at varying implementation stages, but only **4 have canonical manifests** (`foundup_manifest.json`). The rest operate without manifest contracts, creating inconsistent shell loading, CABR integration, and observability gaps.

---

## 2. Canonical Inventory

### 2.1 FoundUps with Manifests (4)

| FoundUp ID | Name | Tier | Lifecycle Stage | Entry URL | Manifest Location |
|------------|------|------|-----------------|-----------|-------------------|
| `gotjunk_001` | GotJunk | F0_DAE | proto | https://gotjunk-56566376153.us-west1.run.app/ | `modules/foundups/gotjunk/foundup_manifest.json` |
| `kosei` | Kosei AI Systems | F0_DAE | incubating | https://foundupscom.web.app/kosei/app/ | `modules/foundups/kosei/foundup_manifest.json` |
| `voteballots` | Vote/Ballots | F0_DAE | incubating | (empty) | `modules/foundups/voteballots/foundup_manifest.json` |
| `trade` | Trade | F0_DAE | incubating | (null) | `modules/foundups/trade/foundup_manifest.json` |

**Observations**:
- All 4 are F0_DAE tier (pre-OPO)
- All 4 have `is_invite_only: true`
- Only `gotjunk_001` and `kosei` have entry URLs
- `voteballots` has explicit `_wsp97_implementation_state: SPECIFIED_NOT_IMPLEMENTED`
- All use default CABR contracts (`v3_score_min: 0.5`)

### 2.2 FoundUps without Manifests (10+)

| Location | Name | Description | Implementation Status | Missing Manifest |
|----------|------|-------------|----------------------|------------------|
| `modules/foundups/pfmall/` | p.fMALL | Video Mall shell | `IMPLEMENTED` (shell_core.py, api.py) | YES |
| `modules/foundups/move2japan/` | Move2Japan | Agent-driven relocation | `SPECIFIED` (README, base camps) | YES |
| `modules/foundups/social_twin/` | Social Twin | LinkedIn automation | `SPECIFIED` (architecture doc) | YES |
| `modules/foundups/pqn_portal/` | PQN Portal | PQN demo portal | `PARTIALLY_IMPLEMENTED` (frontend, docs) | YES |
| `modules/foundups/pqn_swarm_hub/` | PQN Swarm Hub | Science coordination | `SPECIFIED` (migration manifest) | YES |
| `modules/foundups/geoze/` | Geoze | Geo-based FoundUp | `SKELETON` (src/, tests/ dirs only) | YES |
| `modules/foundups/agent/` | FoundUp Agent | Core agent builder | `IMPLEMENTED` (hermes_foundup_builder.py) | YES |
| `modules/foundups/agent_market/` | Agent Market (FAM) | CABR/FAM daemon | `IMPLEMENTED` (fam_daemon.py, cabr_hooks.py) | YES |
| `modules/foundups/ecosystem_animation/` | Ecosystem Animation | Visualization | `IMPLEMENTED` (animation tools) | YES |
| `modules/foundups/simulator/` | Simulator | Economic simulation | `IMPLEMENTED` (mesa_model.py) | YES |

### 2.3 External FoundUp Repos

| Repo | Name | Description | Manifest Status |
|------|------|-------------|-----------------|
| `O:/repos/AutoPost/` | AutoPost | AI camera-to-post | NO manifest (metadata.json only) |
| `O:/repos/science-swarm-hub/` | Science Swarm Hub | Research coordination | NO manifest (standalone PyPI package) |

---

## 3. Lifecycle Stage Classification

### 3.1 Manifest Schema Stages (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)

| Stage | Definition | Shell Behavior |
|-------|------------|----------------|
| `incubating` | Architecture specified, implementation incomplete | Discoverable only, no runtime loading |
| `proto` | PoC complete, invite-only testing | Shell loads with `is_invite_only: true` |
| `externalized` | Public access, no federation | Shell loads for all authenticated users |
| `federated` | Cross-pAVS federation enabled | Full CABR/ROC integration |

### 3.2 Simulator Stages (per state_store.py)

| Stage | Definition |
|-------|------------|
| `PoC` | Proof of Concept (initial) |
| `Proto` | Prototype (testing) |
| `MVP` | Minimum Viable Product |

**INCONSISTENCY DETECTED**: Manifest schema uses `incubating/proto/externalized/federated`, simulator uses `PoC/Proto/MVP`. These must be reconciled.

### 3.3 Implementation Status Tags (per WSP 97)

| Tag | Definition |
|-----|------------|
| `SPECIFIED` | Architecture/spec exists, no implementation |
| `SPECIFIED_NOT_IMPLEMENTED` | Explicit spec, intentionally not implemented |
| `PARTIALLY_IMPLEMENTED` | Some code exists, incomplete |
| `IMPLEMENTED` | Code exists and runs |
| `TESTED` | Implementation has passing tests |
| `RUNTIME_ENFORCED` | Active in production |
| `DOC_ONLY` | Documentation artifact only |
| `SIMULATOR_ONLY` | Only runs in simulator |
| `GATED_NOT_ENABLED` | Code exists but feature-flagged off |
| `DEPRECATED` | Scheduled for removal |

---

## 4. Stage Registry Schema Specification

### 4.1 Proposed Canonical Schema

```json
{
  "$schema": "https://foundups.org/schemas/foundup-registry/v1.json",
  "registry_version": "1.0.0",
  "last_updated": "ISO 8601 timestamp",
  
  "foundups": [
    {
      "foundup_id": "string (slug)",
      "name": "string",
      "tier": "F0_DAE | F1_OPO | F2_GROWTH | F3_INFRA | F4_MEGA | F5_SYSTEMIC",
      
      "lifecycle_stage": "incubating | proto | externalized | federated",
      "implementation_status": "SPECIFIED | IMPLEMENTED | TESTED | RUNTIME_ENFORCED | ...",
      
      "manifest_path": "string | null",
      "entry_url": "string | null",
      "routing_prefix": "/f/{foundup_id}",
      
      "category": "string",
      "owner_id": "string",
      
      "cabr_ready": false,
      "roc_eligible": false,
      
      "_audit_date": "ISO 8601",
      "_auditor": "W9 | W10 | ..."
    }
  ],
  
  "stage_definitions": {
    "incubating": { "shell_load": false, "public_access": false, "cabr_gate": false },
    "proto": { "shell_load": true, "public_access": false, "cabr_gate": false },
    "externalized": { "shell_load": true, "public_access": true, "cabr_gate": true },
    "federated": { "shell_load": true, "public_access": true, "cabr_gate": true, "cross_pavs": true }
  },
  
  "tier_thresholds": {
    "F0_DAE": { "treasury_usd": 0, "backing_sats_per_token": 0 },
    "F1_OPO": { "treasury_usd": 100000, "backing_sats_per_token": 4.76 },
    "F2_GROWTH": { "treasury_usd": 1000000, "backing_sats_per_token": 47.6 },
    "F3_INFRA": { "treasury_usd": 10000000, "backing_sats_per_token": 476 },
    "F4_MEGA": { "treasury_usd": 100000000, "backing_sats_per_token": 4762 },
    "F5_SYSTEMIC": { "treasury_usd": 1000000000, "backing_sats_per_token": 47619 }
  }
}
```

### 4.2 Registry File Location

**Canonical path**: `modules/foundups/foundup_registry.json`

**Secondary indices**:
- `modules/foundups/pfmall/shell_core.py` - Runtime loader validation
- `modules/foundups/simulator/state_store.py` - Simulation state

---

## 5. Gap Analysis

### 5.1 Missing Manifests (Critical)

| FoundUp | Priority | Rationale |
|---------|----------|-----------|
| `pfmall` | P0 | Shell itself needs manifest for self-reference |
| `pqn_portal` | P1 | Near-PoC, needs shell loading contract |
| `move2japan` | P1 | Architecture complete, needs manifest |
| `social_twin` | P2 | Spec complete, manifest enables discovery |

### 5.2 Stage Inconsistency (High)

The dual stage systems (`incubating/proto/externalized/federated` vs `PoC/Proto/MVP`) create confusion:
- Which is authoritative for shell loading?
- How does MVP map to externalized?

**Recommendation**: Define mapping table and single source of truth.

### 5.3 CABR Integration Gap (High)

Only manifested FoundUps have CABR contracts. Non-manifested FoundUps cannot participate in:
- V1 gate validation
- V2 proof verification
- V3 scoring/pipe size calculation
- ROC candidate derivation

### 5.4 External Repo Integration (Medium)

`AutoPost` and `science-swarm-hub` operate outside the manifest system. They need:
- Either local `foundup_manifest.json` in their repos
- Or proxy entries in the central registry

---

## 6. Reconciliation Requirements

### 6.1 Stage Mapping Table

| Manifest Stage | Simulator Stage | Shell Load | CABR Gate | Public |
|----------------|-----------------|------------|-----------|--------|
| `incubating` | - | NO | NO | NO |
| `proto` | `PoC`/`Proto` | YES (invite) | NO | NO |
| `externalized` | `MVP` | YES | YES | YES |
| `federated` | - | YES | YES | YES |

### 6.2 Required Actions Before VOTE Gate Work

1. **Create central registry** (`modules/foundups/foundup_registry.json`)
2. **Generate missing manifests** for pfmall, pqn_portal, move2japan
3. **Add implementation_status field** to existing manifests
4. **Document stage mapping** in PFMALL_FOUNDUP_MANIFEST_SCHEMA.md
5. **Update shell_core.py** to validate against central registry

---

## 7. W9 Completion Packet

```yaml
slice_id: FCISRA-W9
worker: W9
status: STAGED_FOR_W10
branch: docs/foundup-canonical-inventory-audit-phase1
files_staged:
  - docs/audits/architecture/FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md
commit_message: |
  docs(architecture): audit FoundUp canonical inventory and stage registry
  
  - Inventory 14+ FoundUps across codebase and external repos
  - Identify 4 manifested vs 10+ non-manifested gap
  - Define canonical stage registry schema
  - Classify lifecycle stage inconsistency (manifest vs simulator)
  - Specify reconciliation requirements before VOTE gate work
  
  WSP: 3, 49, 97, 104
  Slice: FCISRA-W9
  Worker-Lane: W9 (audit/spec)
pr_title: "docs(architecture): FoundUp canonical inventory and stage registry audit (Phase 1)"
next_slice_recommendation: |
  FOUNDUP_REGISTRY_BOOTSTRAP_PHASE1 - Create central registry JSON
  and generate manifests for pfmall, pqn_portal, move2japan
```

---

## 8. Cross-References

- [PFMALL_FOUNDUP_MANIFEST_SCHEMA.md](../../foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md) - Manifest field definitions
- [FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.md](FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.md) - Public PoC funnel pattern
- [VOTE_EXISTING_FOUNDUP_CONCATENATION_AUDIT_PHASE1.md](VOTE_EXISTING_FOUNDUP_CONCATENATION_AUDIT_PHASE1.md) - Existing VOTE module analysis
- [WSP_100_DAE_SmartDAO_Escalation_Protocol.md](../../../WSP_framework/src/WSP_100_DAE_SmartDAO_Escalation_Protocol.md) - ROC state machine

---

**W9 Status**: Audit complete. Staged for W10 push/PR/merge.
