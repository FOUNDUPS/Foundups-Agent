# FoundUp Canonical Inventory and Stage Registry Audit - Phase 1

**Slice**: `FCISRA-W9`
**Worker**: W9 (audit/spec)
**Date**: 2026-05-18
**Patch**: 012 Correction Patch Applied
**WSP References**: WSP 3 (Domain Organization), WSP 49 (Module Structure), WSP 97 (Truth Boundaries), WSP 104 (Namespace)

---

## WSP 97 Constraints

```yaml
DOCS_ONLY: true
INVENTORY_CORRECTION_ONLY: true
NO_REGISTRY_IMPLEMENTATION: true
NO_MANIFEST_CREATION: true
NO_MODULE_DELETION: true
NO_TOKEN_ASSIGNMENT: true
NO_RUNTIME_CHANGE: true
NO_CABR_READY: true
NO_PAYOUT_READY: true
NO_DAO_ACTIVATION: true
```

---

## 1. Executive Summary

This audit inventories **all existing FoundUps and platform components** across the Foundups-Agent codebase and external repos, classifies their implementation stage, and defines a **typed registry schema** that must exist before VOTE-specific or any FoundUp-specific gate work proceeds.

**Finding**: The ecosystem has multiple entity types at varying implementation stages. A **typed registry** (not flat FoundUp list) is required to preserve distinctions between FoundUps, platform layers, infrastructure, tools, and external repos.

**Confirmed Manifest-Bearing FoundUps**: 5 (gotjunk_001, kosei, voteballots, trade, magadoom_001)

---

## 2. 012 Correction Notes

**CTO Decision**: Central registry YES, but **typed registry**. Not everything in `modules/foundups` is the same class of thing. The registry must preserve distinctions instead of forcing everything into "FoundUp."

### 2.1 pfmall Correction

- **pfmall / p.fMALL is PLATFORM LAYER**, not a FoundUp.
- It is the shell/funnel/RedDog interaction surface.
- Gemma PWA → WRE data path belongs here.
- Needs registry representation only if registry supports platform layers.
- **Do not treat as normal FoundUp.**

### 2.2 agent_market Correction

- **agent_market / FAM is PLATFORM/INFRA**, not a separate FoundUp.
- It is part of pfmall/CABR/FAM daemon infrastructure.
- **Do not list as FoundUp.**

### 2.3 move2japan Correction

- **DO NOT DELETE.**
- It is a YT monitor / live-stream access solution for FoundUps.
- Has real stakeholder/access code (`m2j_stakeholder_db.py`, base camp model).
- Requires full WSP_97 audit before any repurpose/deprecation.
- **Status: INVESTIGATE** (not questionable/delete).

### 2.4 social_twin Clarification

- **NOT a FoundUp.**
- It is a cross-FoundUp reporting / OpenClaw-Hermes layer.
- Should push to LinkedIn on milestones.
- Built but not utilized.
- **Needs integration into OpenClaw/Hermes reporting pipeline.**

### 2.5 simulator Clarification

- **Tool/economic engine**, not a FoundUp.
- Possible future FoundUp only after dedicated audit.

### 2.6 ecosystem_animation Clarification

- **Visualization/tool**, not a FoundUp.
- foundups.com landing animation.
- Gated service candidate only after dedicated audit.
- **Vision**: Per-FoundUp unique animations, realtime coding viz, 012 watches agents build.

### 2.7 Token Policy

- **Do not invent token symbols during inventory audit.**
- Unknown tokens are marked `TOKEN_DEFERRED`.
- Token assignment requires separate WSP_97/WSP_15 slice.

---

## 3. Canonical Inventory

### 3.1 FoundUps with Manifests (5)

| FoundUp ID | Name | Token | Tier | Lifecycle Stage | Manifest Location |
|------------|------|-------|------|-----------------|-------------------|
| `gotjunk_001` | GotJunk | JUNK | F0_DAE | proto | `modules/foundups/gotjunk/foundup_manifest.json` |
| `kosei` | Kosei AI Systems | KOSEI | F0_DAE | incubating | `modules/foundups/kosei/foundup_manifest.json` |
| `voteballots` | Vote/Ballots | VOTE | F0_DAE | incubating | `modules/foundups/voteballots/foundup_manifest.json` |
| `trade` | Trade.foundups | TRADE | F0_DAE | incubating | `modules/foundups/trade/foundup_manifest.json` |
| `magadoom_001` | MAGADOOM | DOOM | F0_DAE | incubating | `modules/gamification/whack_a_magat/foundup_manifest.json` |

**Note**: MAGADOOM is Whack-a-Maga / YT gamification moderators. Located in `modules/gamification/` domain per WSP 3.

### 3.2 FoundUps without Manifests

| Location | Name | Token | Status | Notes |
|----------|------|-------|--------|-------|
| `modules/foundups/pqn_portal/` | PQN Portal | TOKEN_DEFERRED | PARTIALLY_IMPLEMENTED | = Science Swarm public face. Needs drift audit. |
| `modules/foundups/geoze/` | Geoze | TOKEN_DEFERRED | SKELETON | Not started. Not developed yet. |
| `O:/repos/AutoPost/` | AutoPost | TOKEN_DEFERRED | POC_EXISTS | External FoundUp with web presence. Needs completion. |

### 3.3 Platform Layer (NOT FoundUps)

| Location | Name | Type | Status | Notes |
|----------|------|------|--------|-------|
| `modules/foundups/pfmall/` | p.fMALL | PLATFORM | IMPLEMENTED | Shell/funnel/RedDog surface. Gemma PWA → WRE. |
| `modules/foundups/agent_market/` | FAM | INFRA | IMPLEMENTED | CABR/FAM daemon. Part of pfmall platform. |

### 3.4 Layers and Tools (NOT FoundUps)

| Location | Name | Type | Status | Notes |
|----------|------|------|--------|-------|
| `modules/foundups/social_twin/` | Social Twin | LAYER | BUILT_NOT_USED | Cross-FoundUp reporting. OpenClaw/Hermes pipeline. |
| `modules/foundups/simulator/` | Simulator | TOOL | IMPLEMENTED | Economic engine. Possible future FoundUp after audit. |
| `modules/foundups/ecosystem_animation/` | Ecosystem Animation | TOOL | IMPLEMENTED | Visualization. Gated service candidate after audit. |
| `modules/foundups/agent/` | FoundUp Agent | INFRA | IMPLEMENTED | Core agent builder (hermes_foundup_builder.py). |

### 3.5 Requires Investigation

| Location | Name | Type | Status | Notes |
|----------|------|------|--------|-------|
| `modules/foundups/move2japan/` | Move2Japan | INVESTIGATE | IMPLEMENTED | YT monitor / live-stream access. Has real code. DO NOT DELETE. Needs WSP_97 audit. |
| `modules/foundups/pqn_swarm_hub/` | PQN Swarm Hub | INVESTIGATE | SPECIFIED | Internal proxy for external repo. Check drift vs pqn_portal. |
| `O:/repos/science-swarm-hub/` | Science Swarm Hub | EXTERNAL | STANDALONE | PyPI package. Check concatenation with pqn_portal. |

---

## 4. Lifecycle Stage Classification

### 4.1 Manifest Schema Stages (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)

| Stage | Definition | Shell Behavior |
|-------|------------|----------------|
| `incubating` | Architecture specified, implementation incomplete | Discoverable only, no runtime loading |
| `proto` | PoC complete, invite-only testing | Shell loads with `is_invite_only: true` |
| `externalized` | Public access, no federation | Shell loads for all authenticated users |
| `federated` | Cross-pAVS federation enabled | Full CABR/ROC integration |

### 4.2 Simulator Stages (per state_store.py)

| Stage | Definition |
|-------|------------|
| `PoC` | Proof of Concept (initial) |
| `Proto` | Prototype (testing) |
| `MVP` | Minimum Viable Product |

**INCONSISTENCY DETECTED**: Manifest schema uses `incubating/proto/externalized/federated`, simulator uses `PoC/Proto/MVP`. These must be reconciled.

### 4.3 Implementation Status Tags (per WSP 97)

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

## 5. Typed Registry Schema Specification

### 5.1 Registry Entity Types

The registry must support these distinct types:

| Type | Description | Example |
|------|-------------|---------|
| `foundup` | Full FoundUp with token, CABR contract, shell loading | gotjunk_001, voteballots |
| `platform` | Shell/funnel/interaction surface | pfmall |
| `infra` | Infrastructure/daemon services | agent_market (FAM) |
| `layer` | Cross-FoundUp capability layer | social_twin |
| `tool` | Modular utility/engine | simulator, ecosystem_animation |
| `external` | External repo FoundUp | AutoPost, science-swarm-hub |
| `candidate` | Skeleton/not-started | geoze |
| `investigate` | Requires audit before classification | move2japan |

### 5.2 Proposed Typed Schema

```json
{
  "$schema": "https://foundups.org/schemas/foundup-registry/v2.json",
  "registry_version": "2.0.0",
  "last_updated": "ISO 8601 timestamp",
  
  "entities": [
    {
      "entity_id": "string (slug)",
      "name": "string",
      "entity_type": "foundup | platform | infra | layer | tool | external | candidate | investigate",
      
      "tier": "F0_DAE | F1_OPO | ... | null (if not foundup)",
      "token_symbol": "string | TOKEN_DEFERRED | null",
      
      "lifecycle_stage": "incubating | proto | externalized | federated | null",
      "implementation_status": "SPECIFIED | IMPLEMENTED | TESTED | ...",
      
      "manifest_path": "string | null",
      "location": "string (module path or external repo)",
      
      "cabr_ready": false,
      "roc_eligible": false,
      
      "_012_notes": "string | null",
      "_audit_date": "ISO 8601",
      "_auditor": "W9 | W10 | ..."
    }
  ],
  
  "type_definitions": {
    "foundup": { "requires_manifest": true, "requires_token": true, "cabr_eligible": true },
    "platform": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false },
    "infra": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false },
    "layer": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false },
    "tool": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false },
    "external": { "requires_manifest": true, "requires_token": true, "cabr_eligible": true },
    "candidate": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false },
    "investigate": { "requires_manifest": false, "requires_token": false, "cabr_eligible": false }
  }
}
```

### 5.3 Registry File Location

**Canonical path**: `modules/foundups/foundup_registry.json`

---

## 6. Gap Analysis

### 6.1 Missing Manifests (FoundUps only)

| FoundUp | Token | Priority | Rationale |
|---------|-------|----------|-----------|
| `pqn_portal` | TOKEN_DEFERRED | P1 | Near-PoC, needs shell loading contract |
| `autopost` | TOKEN_DEFERRED | P1 | External FoundUp with PoC web presence |
| `geoze` | TOKEN_DEFERRED | P3 | Skeleton, defer until development starts |

### 6.2 Stage Inconsistency (High)

The dual stage systems (`incubating/proto/externalized/federated` vs `PoC/Proto/MVP`) create confusion:
- Which is authoritative for shell loading?
- How does MVP map to externalized?

**Recommendation**: Define mapping table and single source of truth.

### 6.3 Drift Risks

| Entity A | Entity B | Risk | Audit Required |
|----------|----------|------|----------------|
| `pqn_portal` | `science-swarm-hub` | Naming/scope drift | PQN_PORTAL_SCIENCE_SWARM_DRIFT_AUDIT_PHASE1 |
| `pqn_swarm_hub` | `science-swarm-hub` | Internal vs external sync | Same audit |

---

## 7. W9 Completion Packet

```yaml
slice_id: FCISRA-W9
worker: W9
status: STAGED_FOR_W10
worktree: .claude/worktrees/FCISRA-W9
branch: docs/foundup-canonical-inventory-audit-phase1
files_staged:
  - docs/audits/architecture/FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md
  
wsp97_verdict:
  DOCS_ONLY: PASS
  INVENTORY_CORRECTION_ONLY: PASS
  NO_REGISTRY_IMPLEMENTATION: PASS
  NO_MANIFEST_CREATION: PASS
  NO_MODULE_DELETION: PASS
  NO_TOKEN_ASSIGNMENT: PASS (all unknowns marked TOKEN_DEFERRED)
  NO_RUNTIME_CHANGE: PASS
  NO_CABR_READY: PASS
  NO_PAYOUT_READY: PASS
  NO_DAO_ACTIVATION: PASS

corrections_applied:
  - pfmall reclassified as PLATFORM (not FoundUp)
  - agent_market reclassified as INFRA (part of pfmall)
  - Confirmed 5 manifest-bearing FoundUps (added magadoom_001)
  - move2japan marked INVESTIGATE (not delete/questionable)
  - social_twin marked LAYER (not FoundUp)
  - simulator marked TOOL (not FoundUp)
  - ecosystem_animation marked TOOL (not FoundUp)
  - All unknown tokens marked TOKEN_DEFERRED
  - Registry schema updated to typed registry (v2)

pr_title: "docs(architecture): FoundUp canonical inventory with 012 corrections (Phase 1)"
```

---

## 8. Next Slice Recommendations

### 8.1 Primary

**FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1**
- Define typed registry JSON schema
- Support all entity types (foundup, platform, infra, layer, tool, external, candidate, investigate)
- Do not collapse all modules into FoundUps

### 8.2 Secondary

| Slice | Purpose |
|-------|---------|
| `MOVE2JAPAN_FOUNDUP_ROLE_AUDIT_PHASE1` | Audit move2japan purpose, determine if FoundUp or tool |
| `PQN_PORTAL_SCIENCE_SWARM_DRIFT_AUDIT_PHASE1` | Check pqn_portal vs science-swarm-hub naming/scope drift |
| `AUTOPOST_EXTERNAL_FOUNDUP_COMPLETION_AUDIT_PHASE1` | Audit AutoPost PoC, define token, create manifest |

---

## 9. Cross-References

- [PFMALL_FOUNDUP_MANIFEST_SCHEMA.md](../../foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md) - Manifest field definitions
- [FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.md](FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.md) - Public PoC funnel pattern
- [VOTE_EXISTING_FOUNDUP_CONCATENATION_AUDIT_PHASE1.md](VOTE_EXISTING_FOUNDUP_CONCATENATION_AUDIT_PHASE1.md) - Existing VOTE module analysis
- [WSP_100_DAE_SmartDAO_Escalation_Protocol.md](../../../WSP_framework/src/WSP_100_DAE_SmartDAO_Escalation_Protocol.md) - ROC state machine

---

**W9 Status**: 012 correction patch applied. Staged for W10 push/PR/merge.
