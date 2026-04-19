# DE2 -- Hermes Extraction Sandbox Validation Gates, Phase 1

**Date**: 2026-04-18  
**Sandbox**: `O:/tmp/de_sandbox/gotjunk_extraction`  
**Target**: GotJunk FoundUp

---

## Gate Results Summary

| Gate | Description | Result |
|------|-------------|--------|
| G1 | Orphaned import scan | **FAIL** -- 4 blockers |
| G2 | Secrets scan | **PASS** (regex-only) |
| G3 | Standalone test run | **PASS** -- 12/12 tests |
| G4 | BoundaryAnalysis delta | **FAIL** -- orphans block boundary |
| G5 | Remote binding decision | **NOT READY** |

---

## G1: Orphaned Import Scan

### Blockers (Python imports that won't resolve standalone)

| File | Line | Import | Severity |
|------|------|--------|----------|
| `backend/api.py` | 18 | `from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory` | BLOCKER |
| `backend/api.py` | 29 | `from modules.communication.liberty_alert.src.mesh_network import MeshNetwork` | BLOCKER |
| `backend/api.py` | 30 | `from modules.communication.liberty_alert.src.models import Alert, GeoPoint, ThreatType` | BLOCKER |
| `backend/api.py` | 31 | `from modules.communication.liberty_alert.src.alert_broadcaster import AlertBroadcaster` | BLOCKER |

### Informational (doc references, not runtime blockers)

| File | Line | Reference |
|------|------|-----------|
| `INTERFACE.md` | 327 | `WSP_framework/src/WSP_11_Interface_Protocol.md` |
| `README.md` | 208 | `../../WSP_framework/` |
| `README.md` | 213 | Reference to WSP_framework as platform definitions |

### Resolution Options

1. **Vendor**: Copy `pattern_memory.py` and `liberty_alert` into extracted repo
2. **Stub**: Replace with local stubs/interfaces
3. **Remove**: Delete integration code if not required for standalone operation
4. **Package**: Publish shared deps as pip packages

---

## G2: Secrets Scan

**Method**: Regex-only (no dedicated scanner tool installed)

| Check | Patterns | Result |
|-------|----------|--------|
| API keys | `sk-*`, `AIza*` | None found |
| Passwords | `password[:=]` | None found |
| .env files | `*.env*` | None found |
| Credential files | `*credential*`, `*secret*`, `*.pem`, `*.key` | None found |
| Private keys | `private_key` in JSON | None found |

**Status**: PASS (no secrets detected)

**Caveat**: Regex scan only. Recommend running `gitleaks` or `trufflehog` before public push.

---

## G3: Standalone Test Run

**Test file**: `tests/test_manifest.py`

**Command**: `python -m pytest tests/test_manifest.py -v`

**Result**:
```
12 passed in 0.04s
```

**Tests**:
- TestManifestSchema: 8 tests (required fields, tier, lifecycle, cabr contract)
- TestManifestValues: 4 tests (gotjunk-specific values)

**Dependencies**: pytest (available in parent venv)

**Status**: PASS

**Note**: Only manifest tests exist. Backend tests would fail due to G1 blockers.

---

## G4: BoundaryAnalysis Delta vs DD Dry-Run

### Expected (from DD dry-run snapshot)

```json
{
  "core_imports": ["modules.infrastructure.wre_core"],
  "module_boundary_clear": true
}
```

### Actual (extracted repo)

```json
{
  "core_imports": [
    "modules.infrastructure.wre_core",
    "modules.communication.liberty_alert"
  ],
  "module_boundary_clear": false,
  "blockers": [
    "backend/api.py:18 - PatternMemory",
    "backend/api.py:29-31 - liberty_alert (3 imports)"
  ]
}
```

### Delta

| Aspect | DD Snapshot | Extraction | Drift |
|--------|-------------|------------|-------|
| wre_core dependency | Expected | Found | Aligned |
| liberty_alert dependency | Not mentioned | Found | **Drift** |
| Boundary clear | true | false | **Drift** |

### Root Cause

DD dry-run analyzed boundary from monorepo perspective where imports resolve. Actual extraction reveals runtime import failures that weren't visible until `git filter-repo` isolated the module.

---

## G5 - Remote Binding Recommendation

**ready_for_remote_binding:** false

**Decision:** Do not create `FOUNDUPS/gotjunk`, do not add a remote, and do not push this extraction yet.

**Blocker:** G4 failed. The sandbox extraction preserves the expected GotJunk file/directory structure, but `backend/api.py` still contains 4 orphaned imports that reference monorepo-only dependencies. This means the repo would not run cleanly as an external FoundUp without either dependency extraction, adapter shims, or import boundary cleanup.

**Delta From DD:** DD dry-run expected a clear module boundary with `core_imports: ["modules.infrastructure.wre_core"]`. DE2 found an additional `liberty_alert` dependency plus 4 orphaned backend imports, so the boundary is not clean.

**Required Before Phase 2:**
1. Resolve or shim the 4 orphaned imports in `backend/api.py`.
2. Decide whether `liberty_alert` is a real external dependency, a copied adapter, or dead code.
3. Re-run G1 orphaned import scan.
4. Re-run standalone tests.
5. Only if G1-G4 pass, reconsider remote binding.

**Next Slice:** `DE3 -- GOTJUNK_EXTRACTION_BOUNDARY_CLEANUP_PHASE1`

---

## Constraint Compliance

| Constraint | Status |
|------------|--------|
| No GitHub repo creation | ✅ |
| No remote added | ✅ |
| No push | ✅ |
| No edit to extracted repo (except report) | ✅ |
| No mutation to live monorepo | ✅ |
| No git filter-repo re-run | ✅ |

---

## Artifacts

- This report: `O:/tmp/de_sandbox/gotjunk_extraction/DE2_HERMES_EXTRACTION_SANDBOX_VALIDATION_GATES_PHASE1.md`
- Sandbox location: `O:/tmp/de_sandbox/gotjunk_extraction`
- Live monorepo: unchanged

---

**WSP 97 Truthfulness**: This report reflects actual scan results. G2 was regex-only, not a dedicated scanner. G3 tested only manifest, not backend. G4 delta was compared against DD briefing expectations.
