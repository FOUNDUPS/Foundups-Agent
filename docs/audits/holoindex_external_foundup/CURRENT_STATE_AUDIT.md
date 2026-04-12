# HoloIndex External FoundUp: Current State Audit

**Date**: 2026-04-12
**Worker**: BY
**Slice**: `HOLOINDEX_EXTERNAL_FOUNDUP_READINESS_AUDIT_PHASE1`
**WSP References**: WSP 15, WSP 97, WSP 104

---

## Executive Summary

HoloIndex has partial external FoundUp infrastructure but **most of it is workspace-local, not repo truth**. Only the shell interceptor and bridge contract doc are tracked. The adapter, manifest, and UI scaffold all exist locally but are untracked — anyone cloning the repo won't have them.

---

## 1. Repo-Real Components (Tracked in Git)

### 1.1 Shell Bridge Interceptor (REPO-REAL)
- **Path**: `public/member/js/shell-bridge-interceptor.js`
- **Git status**: Tracked
- **Behavior**: Intercepts `agent_request` postMessage events, dispatches to registered backend or returns stub responses
- **Contract alignment**: Implements `EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` Section 2-3

### 1.2 Bridge Contract Documentation (REPO-REAL)
- **Path**: `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md`
- **Git status**: Tracked
- **Defines**: Inbound/outbound message formats, HTTP stub endpoints, shell registration API

---

## 2. Workspace-Local Components (UNTRACKED)

**Critical**: The following components exist locally but are `??` (untracked). They do not exist for anyone cloning the repo.

### 2.1 Bridge Adapter (UNTRACKED)
- **Path**: `holo_index/foundup_adapter/bridge_stub.py`
- **Git status**: `??` untracked
- **Behavior**: Provides `handle_agent_request()`, `get_metadata()`, `get_status()`, `get_tasks()`
- **Backend**: Uses `HoloIndexMCPClient` for actual search if configured
- **Issue**: Contract implementation exists locally but not in repo

### 2.2 FoundUp Manifest (UNTRACKED)
- **Path**: `holo_index/foundup_manifest.json`
- **Git status**: `??` untracked
- **Fields present locally**:
  - `foundup_id`: `holoindex_prod_01`
  - `routing_prefix`: `/f/holoindex_prod_01`
  - `data_namespace`: `idb_holoindex_prod_01`
  - `entry_url`: `/f/holoindex_prod_01/index.html`
- **Issue**: Manifest claims an `entry_url` that itself is also untracked — double dishonesty

### 2.3 UI Scaffold (UNTRACKED)
- **Path**: `public/f/holoindex_prod_01/`
- **Git status**: `??` untracked (entire directory)
- **Contents**:
  - `index.html` (17 lines, minimal stub)
  - `js/connector.js` (15 lines, postMessage bridge)
  - `css/style.css` (minimal)
- **Issue**: Target of manifest `entry_url`, but not committed

### 2.4 Bridge Tests (MISSING)
- **Path**: `holo_index/foundup_adapter/tests/`
- **Git status**: Directory exists but contains only `__pycache__/`
- **Issue**: No verification that bridge contract is actually honored

---

## 3. Missing Integration

### 3.1 Catalog Binding (MISSING)
- **Path**: `public/member/mall-video-catalog.json`
- **Status**: HoloIndex is NOT in the catalog
- **Issue**: Cannot route to `/f/holoindex_prod_01` via canonical shell landing page

---

## 4. Contract Truth (Distinguishing Repo vs Local)

| Contract Element | Status | Location | Tracked? |
|------------------|--------|----------|----------|
| `agent_request` postMessage | REPO-REAL | shell-bridge-interceptor.js:118-134 | YES |
| `agent_response` postMessage | REPO-REAL | shell-bridge-interceptor.js:137-213 | YES |
| Shell backend registration | REPO-REAL | shell-bridge-interceptor.js:91-98 | YES |
| `semantic_search` action | LOCAL-ONLY | bridge_stub.py:87-94 | NO |
| `wsp_lookup` action | LOCAL-ONLY | bridge_stub.py:96-102 | NO |
| `health` action | LOCAL-ONLY | bridge_stub.py:64-65 | NO |
| HTTP `/metadata` stub | LOCAL-ONLY | bridge_stub.py:26-33 | NO |
| HTTP `/status` stub | LOCAL-ONLY | bridge_stub.py:35-41 | NO |
| HTTP `/tasks` stub | LOCAL-ONLY | bridge_stub.py:43-49 | NO |

---

## 5. Immediate Blockers

1. **Entire external FoundUp bundle is untracked** — manifest, adapter, and UI scaffold all exist locally but not in repo
2. **No bridge tests** — Cannot verify contract compliance without tests
3. **No catalog entry** — Shell landing page cannot resolve `holoindex_prod_01`

### End-to-End Gap

The bridge contract is architecturally sound but has never been verified end-to-end:
- External UI -> postMessage -> Shell Interceptor -> Python Adapter -> MCP Client -> Response

The shell interceptor (repo-real) has nothing to connect to because the adapter is not tracked.

---

## 6. Recommended Next Slice

### Option A: Track Full HoloIndex External Bundle (TRUTHFUL)
**Scope**: Commit ALL untracked components:
- `holo_index/foundup_manifest.json`
- `holo_index/foundup_adapter/` (entire directory)
- `public/f/holoindex_prod_01/` (entire directory)

**Why**: Make the external FoundUp infrastructure repo-real (WSP 97)
**Risk**: Low
**Time**: 30 min

### Option B: Downgrade to Local-Only Status (ALTERNATIVE)
**Scope**: If not ready to commit, explicitly mark these as workspace artifacts:
- Remove manifest `entry_url` reference to untracked path
- Document that adapter/UI are local development artifacts only
- Do not claim production readiness

**Why**: Avoid dishonest claims about what exists in the repo
**Risk**: Low
**Time**: 15 min

### Option C: Bridge Contract Tests (AFTER A or B)
**Scope**: Add `holo_index/foundup_adapter/tests/test_bridge_contract.py`
**Why**: Verify adapter honors contract before integration
**Prerequisite**: Option A must complete first (tests need the adapter tracked)
**Risk**: Low
**Time**: 1-2 hours

### Option D: Catalog Route Binding (LAST)
**Scope**: Add `holoindex_prod_01` to `mall-video-catalog.json` with proper WSP 104 fields
**Why**: Enable `/f/holoindex_prod_01` landing route
**Prerequisite**: Options A and C must complete first
**Risk**: Medium (introduces discoverable surface)
**Time**: 30 min

### Recommended Order
1. **Option A first** — Track the full external FoundUp bundle
2. **Option C second** — Add bridge tests to verify contract
3. **Option D third** — Catalog binding after tests pass

---

## 7. Previous Audit Doc Reconciliation

### NEXT_BUILD_ORDER.md (line 9)
> `public/f/holoindex_prod_01/` exists as a standalone UI scaffold

**Truth update**: It EXISTS LOCALLY but is UNTRACKED. This is a workspace artifact, not repo truth.

### GAP_QUEUE.md (Gap 2)
> The `foundup_manifest.json` for HoloIndex Explorer does not exist

**Truth update**: STILL OPEN — manifest exists locally at `holo_index/foundup_manifest.json` but is UNTRACKED. Not repo truth.

### GAP_QUEUE.md (Gap 4)
> No empty repository or boilerplate exists yet for the frontend product UI

**Truth update**: STILL OPEN — `public/f/holoindex_prod_01/` exists locally but is UNTRACKED. Not repo truth.

---

## 8. Conclusion

HoloIndex external FoundUp is **workspace-prepared** but **not repo-real**:

| Component | Repo Status |
|-----------|-------------|
| Shell bridge interceptor | TRACKED |
| Bridge contract doc | TRACKED |
| Bridge adapter | UNTRACKED |
| FoundUp manifest | UNTRACKED |
| UI scaffold | UNTRACKED |
| Bridge tests | MISSING |
| Catalog binding | MISSING |

**Next truthful slice**: Track the full external FoundUp bundle (Option A), then add bridge tests (Option C).
