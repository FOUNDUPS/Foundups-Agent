# PQN Portal / Science Swarm Hub Drift Audit - Phase 1

**Worker**: W9C
**Date**: 2026-05-18
**Slice**: `PQN_PORTAL_SCIENCE_SWARM_DRIFT_AUDIT_PHASE1`
**WSP Lock**: WSP_00, WSP_97, WSP_87, WSP_15, WSP_50
**Status**: AUDIT COMPLETE

---

## WSP 97 Labels

```
DOCS_ONLY, AUDIT_ONLY, NO_IMPLEMENTATION, NO_MODULE_DELETION, 
NO_MANIFEST_CREATION, NO_TOKEN_ASSIGNMENT, TOKEN_DEFERRED_WHERE_UNKNOWN, 
NO_RUNTIME_CHANGE, NO_CABR_READY, NO_PAYOUT_READY, NO_DAO_ACTIVATION
```

---

## 1. Executive Summary

| Module | Location | Status | Public Surface |
|--------|----------|--------|----------------|
| `pqn_portal` | `modules/foundups/pqn_portal/` | STUB/SCAFFOLD | `/f/pqn_portal` (claimed, not implemented) |
| `pqn_swarm_hub` | `modules/foundups/pqn_swarm_hub/` | STUB (delegates to external) | None (backend only) |
| `science-swarm-hub` | `O:/repos/science-swarm-hub/` (external repo) | OPERATIONAL (v0.12.0) | GitHub repo (pip installable from source) |

**Key Finding**: `pqn_portal` is NOT the public face of `science-swarm-hub`. They are distinct modules with different purposes:
- `pqn_portal` = Public demo/gallery FoundUp (DAE-neutral PQN experience)
- `science-swarm-hub` = Work registry backend (verification/contribution engine)

The relationship is: `pqn_portal` **consumes** `pqn_swarm_hub` (science-swarm-hub) as a dependency for work unit verification, but presents through `pqn_alignment` detector APIs directly.

---

## 2. pqn_portal Inventory

### 2.1 Code/Docs Inventory

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `README.md` | 85 | Documented | Route namespace, WSP refs |
| `INTERFACE.md` | 30 | Documented | SSE contract, API endpoints |
| `ROADMAP.md` | EXISTS | Documented | PoC/Prototype/MVP phases |
| `ModLog.md` | EXISTS | Documented | Change history |
| `module.json` | 20 | Documented | DAE manifest (docs, api, memory) |
| `requirements.txt` | EXISTS | Empty | No dependencies listed |
| `src/pqn_portal.py` | 30 | **PLACEHOLDER** | `class PqnPortal` with TODO comments |
| `src/api.py` | ~100 | Partial | FastAPI routes (imports pqn_alignment) |
| `src/docs.py` | EXISTS | Functional | Docs index endpoint |
| `src/__init__.py` | EXISTS | Empty | Package marker |
| `frontend/demo.html` | EXISTS | Static | Demo UI |
| `frontend/gallery.html` | EXISTS | Static | Gallery UI |
| `frontend/index.html` | EXISTS | Static | Landing page |
| `tests/README.md` | EXISTS | Documented | Test structure |
| `tests/__init__.py` | EXISTS | Empty | Package marker |

**Total Source Lines**: ~130 (excluding docs/HTML)

### 2.2 Dependencies Referenced

| Dependency | Import Path | Status |
|------------|-------------|--------|
| `pqn_alignment.run_detector` | `modules.ai_intelligence.pqn_alignment.src.detector.api` | Documented in INTERFACE.md |
| `pqn_alignment.results_db` | `modules.ai_intelligence.pqn_alignment.src.results_db` | Documented in INTERFACE.md |
| `pqn_mcp` | Referenced in README.md | Not implemented |

### 2.3 Public Surface Claims

| Claim | Source | Status |
|-------|--------|--------|
| `/f/pqn_portal` landing route | README.md | **CLAIMED, NOT LIVE** |
| `/f/pqn_portal/app` app mount | README.md | **CLAIMED, NOT LIVE** |
| `/docs` endpoint | INTERFACE.md | Partial (docs.py exists) |
| `/runs/demo` endpoint | INTERFACE.md | **CLAIMED, NOT IMPLEMENTED** |
| `/runs/{id}/stream` SSE | INTERFACE.md | **CLAIMED, NOT IMPLEMENTED** |
| `/gallery` endpoint | INTERFACE.md | **CLAIMED, NOT IMPLEMENTED** |

### 2.4 Manifest Status

| Type | File | Status |
|------|------|--------|
| DAE Manifest | `module.json` | **EXISTS** (20 lines, valid JSON) |
| WSP 49 Module | Structure compliant | **YES** (README, INTERFACE, src/, tests/) |
| pFMALL Catalog | N/A | **NOT LISTED** (no entry in mall-video-catalog.json) |

---

## 3. pqn_swarm_hub Inventory (Monorepo Stub)

### 3.1 Code/Docs Inventory

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `README.md` | 65 | REDIRECT | Points to external repos |
| `INTERFACE.md` | 592 | **STALE** | Full API docs (code now external) |
| `ROADMAP.md` | 156 | HISTORICAL | Phase plan (all phases complete) |
| `ModLog.md` | 864 | HISTORICAL | V0.1.0-V0.15.0 |
| `RUNBOOK.md` | EXISTS | HISTORICAL | Preserved |
| `CONTRIBUTING.md` | EXISTS | REDIRECT | Points to external |
| `__init__.py` | 111 | STUB | Re-exports from installed package |
| `requirements.txt` | EXISTS | Empty | Dependencies in external repo |
| `docs/DISCORD_COMMUNITY_SCAFFOLD.md` | EXISTS | HISTORICAL | Discord planning |

**Historical Docs Preserved**:
- `PROTO_EXFOLIATION_CHECKLIST.md`
- `MIGRATION_MANIFEST.md`
- `DUAL_REMOTE_PLAN.md`
- `EXFOLIATION_PLAN.md`

### 3.2 Stub Behavior

The monorepo `__init__.py` delegates to the installed package:

```python
try:
    from pqn_swarm_hub import (
        WorkUnitRegistry, SubmissionSink, VerificationEngine, ...
    )
except ImportError as e:
    raise ImportError(
        "pqn_swarm_hub has been externalized...\n"
        "Install from source: git clone https://github.com/FOUNDUPS/science-swarm-hub..."
    ) from e
```

### 3.3 Manifest Status

| Type | File | Status |
|------|------|--------|
| DAE Manifest | `module.json` | **ABSENT** (no module.json in stub) |
| WSP 49 Module | Structure partial | No `src/`, no `tests/` (deleted at cutover) |

---

## 4. science-swarm-hub Inventory (External Repo)

### 4.1 Repository Status

| Field | Value |
|-------|-------|
| Primary URL | `https://github.com/FOUNDUPS/science-swarm-hub` |
| Backup URL | `https://github.com/Foundup/science-swarm-hub` (PRIVATE) |
| Version | v0.12.0 |
| License | MIT |
| Created | 2026-03-29 |
| Last Push | 2026-04-05 |
| CI Status | PASSING (GitHub Actions) |
| Python | >=3.12 |

### 4.2 Code Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `src/pqn_swarm_hub/__init__.py` | 97 | Package exports (30 symbols) |
| `src/pqn_swarm_hub/contracts.py` | ~150 | Dataclasses (PQNWorkUnit, rESPSubmission, etc.) |
| `src/pqn_swarm_hub/registry.py` | ~100 | Work unit registry |
| `src/pqn_swarm_hub/submission_sink.py` | ~120 | Result intake |
| `src/pqn_swarm_hub/verification.py` | ~100 | Accept/reject logic |
| `src/pqn_swarm_hub/contribution.py` | ~120 | ROC reporting |
| `src/pqn_swarm_hub/gate.py` | ~300 | Participant entry policy |
| `src/pqn_swarm_hub/persistence.py` | ~400 | SQLite storage |
| `src/pqn_swarm_hub/publication_adapter.py` | ~200 | MoltBook integration |
| `src/pqn_swarm_hub/fam_adapter.py` | ~150 | FAM daemon integration |
| `src/pqn_swarm_hub/detector_bridge.py` | ~120 | pqn_alignment bridge |

**Total Source Lines**: ~1,840

### 4.3 Test Inventory

| File | Test Count |
|------|------------|
| `test_contracts.py` | 13 |
| `test_detector_bridge.py` | 5 |
| `test_external_contributor.py` | 22 |
| `test_external_submission.py` | 14 |
| `test_fam_live_validation.py` | 15 |
| `test_persistence.py` | 18 |
| `test_poc_flow.py` | 5 |
| `test_publication_adapter.py` | 16 |

**Total Tests**: 108 (all passing per CI)

### 4.4 Documentation

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | 157 | Install/quickstart |
| `INTERFACE.md` | 17,229 | Full API contracts |
| `ROADMAP.md` | 8,199 | Phase plan |
| `ModLog.md` | 24,213 | Change history |
| `RUNBOOK.md` | 15,558 | Execution guide |
| `CONTRIBUTING.md` | 9,593 | External contributor guide |
| `RELEASE_CHECKLIST.md` | 1,695 | Release procedure |

### 4.5 Manifest Status

| Type | File | Status |
|------|------|--------|
| Python Package | `pyproject.toml` | **EXISTS** (valid, `name=science-swarm-hub`) |
| DAE Manifest | `module.json` | **ABSENT** |
| pFMALL Catalog Entry | N/A | **EXISTS** as `science_swarm` (discovery-only) |

---

## 5. Cross-References Between Modules

### 5.1 pqn_portal -> pqn_swarm_hub References

| Source | Reference | Type |
|--------|-----------|------|
| `pqn_portal/README.md` | No direct reference | **NONE** |
| `pqn_portal/INTERFACE.md` | `pqn_alignment` only | Indirect via detector |
| `pqn_portal/src/api.py` | `pqn_alignment` imports | Indirect via detector |

**Finding**: `pqn_portal` does NOT reference `pqn_swarm_hub` or `science-swarm-hub` directly.

### 5.2 pqn_swarm_hub -> pqn_portal References

| Source | Reference | Type |
|--------|-----------|------|
| `pqn_swarm_hub/INTERFACE.md` | `pqn_portal` = public demo/gallery | Documented relationship |
| `science-swarm-hub/ModLog.md` | "Reuses: pqn_portal" | Historical note |

**Finding**: `pqn_swarm_hub` documents `pqn_portal` as a separate frontend module.

### 5.3 Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Control Plane Split                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  pqn_portal (public demo)                                       │
│  ├── /f/pqn_portal landing                                      │
│  ├── /runs/demo, /gallery                                       │
│  └── REUSES: pqn_alignment.run_detector (directly)              │
│                                                                  │
│  pqn_swarm_hub (work registry) [externalized]                   │
│  ├── WorkUnitRegistry                                           │
│  ├── SubmissionSink                                             │
│  ├── VerificationEngine                                         │
│  ├── ContributionReporter                                       │
│  └── REUSES: pqn_alignment via DetectorBridge                   │
│                                                                  │
│  pqn_alignment (detector engine)                                │
│  └── run_detector(), results_db                                 │
│                                                                  │
│  pqn_mcp (gated MCP surface)                                    │
│  └── External tool access                                       │
│                                                                  │
│  moltbook_distribution_adapter (downstream publish)             │
│  └── MoltBook social distribution                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Drift Analysis

### 6.1 Naming/Scope Drift Risks

| Risk | Severity | Description |
|------|----------|-------------|
| **Name confusion** | MEDIUM | `pqn_swarm_hub` (monorepo) vs `science-swarm-hub` (external) vs `pqn_portal` - three similar names |
| **Package name** | LOW | External package is `pqn_swarm_hub` (import) but repo is `science-swarm-hub` - intentional but confusing |
| **Public surface confusion** | MEDIUM | `pqn_portal` claims public routes not implemented; `science-swarm-hub` has no public surface |
| **INTERFACE.md staleness** | HIGH | Monorepo `pqn_swarm_hub/INTERFACE.md` is 592 lines describing code that no longer exists there |

### 6.2 Missing Artifacts

| Module | Missing | Impact |
|--------|---------|--------|
| `pqn_portal` | No pFMALL catalog entry | Not discoverable in mall |
| `pqn_portal` | No working implementation | Public routes are stubs |
| `pqn_swarm_hub` (monorepo) | No `module.json` | DAE cannot discover |
| `science-swarm-hub` (external) | No `module.json` | DAE cannot discover |
| `pqn_portal` | No reference to `pqn_swarm_hub` | Unclear dependency relationship |

### 6.3 Implementation Gap

| Claimed | Reality |
|---------|---------|
| `pqn_portal` is "public PQN experience" | Core logic is placeholder (`TODO` comments) |
| `pqn_portal` SSE streaming | Not implemented |
| `pqn_portal` gallery | Not implemented |
| `pqn_swarm_hub` in monorepo | Stub only; code in external repo |

---

## 7. HoloIndex vs Grep Comparison

| Query | HoloIndex Result | Grep Result | Notes |
|-------|------------------|-------------|-------|
| `pqn_portal science swarm hub relationship` | **TIMEOUT** (SentenceTransformer >20s) | N/A | HoloIndex unavailable |
| `pqn_portal` (grep) | N/A | 83 files | Found all monorepo refs + worktrees |
| `pqn_swarm_hub` (grep) | N/A | 48 files | Found stub + worktrees + external refs |
| `science-swarm-hub` (grep) | N/A | 113 files | Found gitignore + audits + papers |

**HoloIndex Status**: UNAVAILABLE - SentenceTransformer timeout on Windows
**Grep Status**: FUNCTIONAL - Used for all discovery

---

## 8. Public Surface Status

### 8.1 pqn_portal

| Surface | Claimed Route | Status |
|---------|---------------|--------|
| Landing | `/f/pqn_portal` | **NOT DEPLOYED** |
| App Mount | `/f/pqn_portal/app` | **NOT DEPLOYED** |
| Demo API | `/runs/demo` | **NOT IMPLEMENTED** |
| Gallery | `/gallery` | **NOT IMPLEMENTED** |
| Docs | `/docs` | Partial (docs.py exists) |

**Verdict**: NO PUBLIC SURFACE

### 8.2 science-swarm-hub

| Surface | Status |
|---------|--------|
| PyPI Package | **NOT PUBLISHED** |
| GitHub Repo | PUBLIC (FOUNDUPS/science-swarm-hub) |
| pfMALL Entry | `science_swarm` (discovery-only, no app route) |
| API Endpoints | **NONE** (library, not service) |

**Verdict**: DISCOVERABLE (GitHub), NOT DEPLOYED

---

## 9. Manifest Absence Summary

| Module | module.json | pyproject.toml | pFMALL Entry |
|--------|-------------|----------------|--------------|
| `pqn_portal` | EXISTS | ABSENT | **ABSENT** |
| `pqn_swarm_hub` (stub) | **ABSENT** | ABSENT | N/A (redirect) |
| `science-swarm-hub` (external) | **ABSENT** | EXISTS | EXISTS (discovery) |

**Key Gap**: Neither backend module has a DAE manifest (`module.json`). The external repo relies on `pyproject.toml` for Python packaging but has no DAE discovery surface.

---

## 10. Token Status

| Module | Token Assignment | Status |
|--------|-----------------|--------|
| `pqn_portal` | N/A | **TOKEN_DEFERRED** |
| `pqn_swarm_hub` | N/A | **TOKEN_DEFERRED** |
| `science-swarm-hub` | N/A | **TOKEN_DEFERRED** |

Per WSP 97: `NO_TOKEN_ASSIGNMENT`, `TOKEN_DEFERRED_WHERE_UNKNOWN`

---

## 11. Recommended Classification

### 11.1 pqn_portal

| Field | Value |
|-------|-------|
| Classification | **SCAFFOLD** |
| Lifecycle Stage | **PoC** (not yet Prototype) |
| Readiness | **NOT OPERATIONAL** |
| Blockers | Core logic not implemented; routes are stubs |
| Token | DEFERRED |

### 11.2 pqn_swarm_hub (monorepo stub)

| Field | Value |
|-------|-------|
| Classification | **STUB/REDIRECT** |
| Lifecycle Stage | **EXTERNALIZED** |
| Readiness | **PASS-THROUGH** (delegates to external package) |
| Blockers | INTERFACE.md staleness (592 lines, code no longer here) |
| Token | DEFERRED |

### 11.3 science-swarm-hub (external)

| Field | Value |
|-------|-------|
| Classification | **LIBRARY** (not FoundUp app) |
| Lifecycle Stage | **RELEASE-READY** (v0.12.0) |
| Readiness | **OPERATIONAL** (install from source, 108 tests passing) |
| Blockers | None for current scope |
| Token | DEFERRED |

---

## 12. WSP 97 Compliance Verdict

| Gate | Status |
|------|--------|
| DOCS_ONLY | **PASS** - No code changes |
| AUDIT_ONLY | **PASS** - Analysis only |
| NO_IMPLEMENTATION | **PASS** - No implementation |
| NO_MODULE_DELETION | **PASS** - No deletions |
| NO_MANIFEST_CREATION | **PASS** - No manifests created |
| NO_TOKEN_ASSIGNMENT | **PASS** - Tokens deferred |
| NO_RUNTIME_CHANGE | **PASS** - No runtime changes |
| NO_CABR_READY | **PASS** - No CABR claims |
| NO_PAYOUT_READY | **PASS** - No payout claims |
| NO_DAO_ACTIVATION | **PASS** - No DAO activation |

**Overall WSP 97 Verdict**: **COMPLIANT**

---

## 13. Next Slice Recommendation

**Slice Name**: `PQN_PORTAL_SCIENCE_SWARM_MANIFEST_READINESS_PHASE1`

**Scope**:
1. Create `module.json` for `pqn_portal` with proper DAE fields
2. Truncate/redirect `pqn_swarm_hub/INTERFACE.md` to external repo (remove 592 stale lines)
3. Add pFMALL catalog entry for `pqn_portal` (discovery-only until implementation)
4. Document explicit dependency: `pqn_portal` -> `pqn_alignment` (direct), `pqn_swarm_hub` (optional)
5. Create `module.json` for external `science-swarm-hub` (if DAE discovery needed for standalone)

**Estimated Effort**: 45-60 minutes
**Risk**: LOW (documentation/manifest only)
**WSP 97 Labels**: `DOCS_ONLY`, `MANIFEST_CREATION_ALLOWED`

---

## 14. Audit Artifacts

| Artifact | Path |
|----------|------|
| This audit | `docs/audits/architecture/PQN_PORTAL_SCIENCE_SWARM_DRIFT_AUDIT_PHASE1.md` |
| Prior audit | `docs/audits/science_swarm_external_foundup/SCIENCE_SWARM_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md` |

---

*Audit complete. pqn_portal is a scaffold (not public face). science-swarm-hub is a backend library. They serve different purposes with minimal direct integration.*
