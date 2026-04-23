# FoundUp Manifest Discovery and FAM Registry Architecture

**Date**: 2026-04-23
**Slice**: FOUNDUPOPS-MANIFEST-DISCOVERY-FIX
**WSP References**: WSP 97 (Truth State), WSP 104 (Namespace)

---

## WSP 97 Truthfulness Statement

> This document describes the current filesystem-based discovery mechanism, fixes applied, and the architectural migration path to FAM Registry as the authoritative source of FoundUp truth. HoloIndex is explicitly NOT the registry — it provides recall/search over artifacts that exist elsewhere.

---

## 1. Current Discovery Architecture

### 1.1 Mechanism

pfMALL discovers FoundUps via filesystem scan:

```python
# modules/foundups/pfmall/api.py lines 37-41
DEFAULT_SEARCH_PATHS = [
    _REPO_ROOT / "modules" / "foundups",
    _REPO_ROOT / "modules" / "gamification",
    _REPO_ROOT / "modules" / "platform_integration",
]
```

`shell_core.py:discover_manifests()` scans one level deep in each search path for subdirectories containing `foundup_manifest.json`.

### 1.2 Discovery Flow (Current)

```
Filesystem scan → find foundup_manifest.json → validate schema → build catalog → pfMALL displays
```

### 1.3 Truth Assessment

| Claim | WSP 97 State |
|-------|--------------|
| Discovery is filesystem-based | `VERIFIED_FACT` |
| Manifests are handwritten | `VERIFIED_FACT` |
| FAM Registry is authoritative | `SPECIFIED_NOT_IMPLEMENTED` |
| HoloIndex discovers FoundUps | `VERIFIED_FACT: NO` |

---

## 2. Problem: voteballots Not Discoverable

### 2.1 Root Cause

`modules/foundups/voteballots/` had `module.json` but no `foundup_manifest.json`.

The module documentation structure (`README.md`, `INTERFACE.md`, `ROADMAP.md`) is separate from the pfMALL catalog registration (`foundup_manifest.json`).

### 2.2 Fix Applied

Created `modules/foundups/voteballots/foundup_manifest.json` with:

| Field | Value | Rationale |
|-------|-------|-----------|
| `lifecycle_stage` | `incubating` | Architecture spec exists, no implementation |
| `launch_readiness` | `discoverable_only` | No frontend, catalog info card only |
| `required_subscription_tier` | `free` | Political transparency should be accessible |
| `_wsp97_implementation_state` | `SPECIFIED_NOT_IMPLEMENTED` | Only specs exist |

### 2.3 Verification

```python
from modules.foundups.pfmall.api import list_foundups
foundups = list_foundups()
# voteballots now in discovered list
```

---

## 3. HoloIndex Role Decision

### 3.1 Architectural Boundary

| System | Role | Answers |
|--------|------|---------|
| **HoloIndex** | Recall/Search | "What can I find?" |
| **FAM Registry** | Source of Truth | "What exists and what state is it in?" |
| **pfMALL** | Display Layer | "What can the user see/load?" |

### 3.2 Decision: HoloIndex is Infrastructure-Only

**Status**: `holo_index/foundup_manifest.json` is NOT added to pfMALL catalog search paths.

**Rationale**:
1. HoloIndex is platform infrastructure, not a user-facing FoundUp
2. Making HoloIndex authoritative creates a truth problem: stale index = stale reality
3. HoloIndex should index manifests for search, not determine lifecycle/capability truth

**Current manifest status**:
- Path: `holo_index/foundup_manifest.json`
- Schema validity: `INCOMPLETE` (missing `tier`, `lifecycle_stage`)
- Catalog inclusion: `NO` — infrastructure-only

**If HoloIndex becomes a user FoundUp later**:
1. Make manifest schema-valid
2. Add `holo_index/` to DEFAULT_SEARCH_PATHS explicitly
3. Document product decision and access policy

---

## 4. Target Architecture: FAM Registry as Authority

### 4.1 Migration Path

**Phase 1 (Current)**: Filesystem manifests
- Handwritten `foundup_manifest.json` files
- pfMALL scans and discovers
- Manual process, prone to missing registrations

**Phase 2 (Near-term)**: FAM Registry validates manifests
- FAM Registry stores authoritative FoundUp records
- Manifests can be generated from registry
- pfMALL still reads manifests, but registry is source of truth

**Phase 3 (Target)**: Genesis Envelope flow
- RedDog creates Genesis Envelope
- FAM Registry accepts and registers
- Manifest generated/validated from registry entry
- pfMALL discovers generated manifests
- HoloIndex indexes for search

### 4.2 Target Flow

```
012 outcome description
    │
    ▼
RedDog intake → Genesis Envelope
    │
    ▼
FAM Registry (authoritative record)
    │
    ├──▶ foundup_manifest.json generated/validated
    │
    ▼
pfMALL filesystem discovery
    │
    ▼
HoloIndex indexes manifest for search
```

### 4.3 Key Invariants

1. **FAM Registry is the write authority** — creates/updates FoundUp records
2. **Manifests are read artifacts** — generated from or validated against registry
3. **HoloIndex is read-only indexer** — never mutates truth, only searches it
4. **pfMALL consumes manifests** — displays what filesystem discovery finds

### 4.4 Why Not HoloIndex as Registry?

| Problem | Consequence |
|---------|-------------|
| Stale index | FoundUp appears to not exist when it does |
| Index rebuild | Temporary catalog loss during reindex |
| No lifecycle authority | Can't enforce stage transitions |
| No validation | Can't reject invalid manifests |

HoloIndex answers "what matches this query?" — not "what is the canonical state of this FoundUp?"

---

## 5. Implementation Status

| Component | Status | Evidence |
|-----------|--------|----------|
| voteballots manifest | `VERIFIED_FACT` | File exists, discovered by pfMALL |
| HoloIndex catalog exclusion | `VERIFIED_FACT` | Not in DEFAULT_SEARCH_PATHS |
| FAM Registry implementation | `SPECIFIED_NOT_IMPLEMENTED` | Architecture defined, no code |
| Genesis Envelope → manifest flow | `SPECIFIED_NOT_IMPLEMENTED` | See REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md |

---

## 6. Related Documents

| Document | Purpose |
|----------|---------|
| `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` | Manifest schema definition |
| `REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md` | Genesis Envelope architecture |
| `modules/foundups/agent_market/README.md` | FAM overview |
| `modules/foundups/pfmall/api.py` | DEFAULT_SEARCH_PATHS definition |

---

## 7. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| voteballots has schema-consistent manifest | PASS |
| pfMALL discovery finds voteballots | PASS |
| HoloIndex manifest decision documented | PASS (infrastructure-only) |
| FAM Registry spec note added | PASS |
| No HoloIndex-as-truth overclaim | PASS |

---

*0102 pArtifact: Filesystem manifests are current truth. FAM Registry is future authority. HoloIndex recalls, does not register.*
