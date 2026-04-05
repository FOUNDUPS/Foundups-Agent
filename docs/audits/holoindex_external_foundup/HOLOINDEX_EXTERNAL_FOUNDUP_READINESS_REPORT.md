# HoloIndex External FoundUp Readiness Report

**Canonical path** (this document): `docs/audits/holoindex_external_foundup/HOLOINDEX_EXTERNAL_FOUNDUP_READINESS_REPORT.md` — not the shorthand label `READINESS_REPORT.md`.

## Identity Lock
`IDENTITY LOCK: Acting as Worker H for HOLOINDEX_EXTERNAL_FOUNDUP_READINESS_AUDIT_PHASE1.`

## Mission
Audit what "external HoloIndex as a stand-alone FoundUp" would actually require.

## Discovery Questions
1. **What is the current internal HoloIndex footprint in this repo?**
   Currently, HoloIndex lives entirely within `o:\Foundups-Agent\holo_index` and operates as a standalone Python application CLI, MCP server, and infrastructural backend for `openclaw_dae` and `wre_core`. It includes the semantic code search, metadata generation, telemetry parsing, and HoloDAE intelligent agents (Qwen/Gemma integration).

2. **Which parts are core/internal and must stay here?**
   Per the `PFMALL_SHELL_CONTRACT.md`, the rule is explicit: "Infrastructure stays core: HoloIndex, OpenClaw, WRE are infrastructure — never in the catalog. HERMES rule: OpenClaw=control plane, WRE=execution, HoloIndex=memory". The indexing engine, SQLite database, ChromaDB vectors, AI Advisor subroutines, WSP-checking components, and the internal Python APIs are **CORE MEMORY**. They MUST stay internal to the monorepo.

3. **Which parts could be externalized into a stand-alone FoundUp without breaking internal consumers?**
   The external FoundUp would purely be the *client presentation layer* and *productized visualization surface* for contributors (the Experience Pipe). This would include the Web PWA front-end UI for searching, viewing Mermaid diagrams, reading WSP violations, and passing orchestration commands back to the shell via `postMessage`. 

4. **What contract boundary would the external HoloIndex FoundUp need?**
   A boundary compliant with `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`.
   - Setup a `foundup_manifest.json` describing the FoundUp capabilities (Tier: `F3_INFRA`, capabilities: `search`, agent routes: `openclaw_query`, `openclaw_search`).
   - A Control Pipe exposing `/metadata`, `/tasks`, `/feed` backed by the internal core layer.
   - An Experience Pipe via an in-scope routing (`/f/holoindex`).

5. **What repo shape would make sense:**
   **Separate repo**. The `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT` specifies: "Each FoundUp may live in its own repository. That is acceptable and preferred once a FoundUp is externalized... Mall indexes the route and metadata. Mall opens the FoundUp in-scope." The repo would only contain the FoundUp Frontend (React/JS), while its backend task endpoint connects securely back to the core HoloIndex infrastructure.

6. **What docs/specs already exist that help this?**
   - `holo_index/README.md` and `INTERFACE.md` (Core API boundaries)
   - `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` (Repo separation policy, control pipe vs experience pipe)
   - `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` (Manifest typing and agent routes)
   - `PFMALL_SHELL_CONTRACT.md` (Interaction via postMessage and infrastructure exclusions)
   - `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` (Document hierarchy)

7. **What is missing?**
   - A dedicated Web/HTTP API adapter in the internal HoloIndex module to securely serve the Control Pipe methods (`/metadata`, `/tasks`) specifically formatted for an external FoundUp.
   - A `foundup_manifest.json` for "HoloIndex UI" to formally register it with the shell launch catalog.
   - The UI frontend repository for the standalone external PWA.

8. **What is the smallest truthful next step to spawn external HoloIndex as a FoundUp?**
   Drafting the `foundup_manifest.json` conforming to `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` and creating the Control Pipe adapter stub in the core HoloIndex module to bind core functionality to the shell-facing API expectation.

## Current Status Update (2026-04-03)

Ground truth moved forward after this audit:

- `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` now exists and defines the `agent_request` / `agent_response` bridge.
- `holo_index/foundup_manifest.json` now exists as the FoundUp registration stub.
- `public/f/holoindex_prod_01/` now contains a standalone external UI scaffold that speaks the shell bridge contract through `postMessage`.

This changes the next-step calculus:

- The external HoloIndex FoundUp is no longer purely theoretical.
- It is still **not** a standalone runtime with its own search authority.
- It remains an **adjacent external FoundUp surface**, not a dependency of core pfMALL Mall / player / concierge runtime.
- Its future product role is a **search and intelligence surface** for locating code, WSPs, contracts, and other FoundUp-relevant artifacts that agents may later act on through Shell / Red Dog / OpenClaw orchestration.

## Phase 1 Adapter Hookup (2026-04-05)

**Worker**: H
**Slice**: `HOLOINDEX_EXTERNAL_FOUNDUP_ADAPTER_HOOKUP_PHASE1`

The internal adapter is now hooked to the bridge contract:

### Completed

1. **Bridge Adapter Enhanced** (`holo_index/foundup_adapter/bridge_stub.py`):
   - Added `health` action handler
   - Ensured response shapes match bridge contract Section 3.1
   - Added request validation per bridge contract Section 2
   - Added `_success_response()` / `_error_response()` helpers for consistent contract compliance
   - All responses now include `results` array and `quantum_coherence`

2. **Shell Interceptor Enhanced** (`public/member/js/shell-bridge-interceptor.js`):
   - Added `handleHealthCheck()` handler for health action
   - Health check returns contract-compliant response with stub marker

3. **Contract Verification Tests** (`holo_index/foundup_adapter/tests/test_bridge_contract.py`):
   - 21 tests covering request validation, response shapes, action handlers
   - Tests verify contract compliance for semantic_search, wsp_lookup, health
   - Tests verify MCP integration transforms results to contract shape

### Contract Status

| Action | Adapter (Python) | Browser path | UI | Status |
|--------|------------------|--------------|-----|--------|
| `semantic_search` | MCP-backed, contract-shaped | Stub unless backend registered via `registerShellBridgeBackend` | Ready | **Adapter-ready** / **Registered seam** when host supplies backend |
| `wsp_lookup` | MCP-backed, contract-shaped | Same | Ready | **Adapter-ready** / **Registered seam** when host supplies backend |
| `health` | Local / contract-shaped | Same | Ready | **Adapter-ready** / **Registered seam** when host supplies backend |

**Truthfulness**: **LIVE** (end-to-end production search authority) is **not** claimed here. Registration is an **explicit local seam**; core remains internal — no browser→core HTTP in this slice.

### Truthfulness Preserved

- No fake production network surface
- No second HoloIndex runtime
- No direct browser-to-core coupling
- UI/scaffold can target real adapter behavior OR explicit stub behavior

### Architect — Worker H closure + next slice

- **Closed for this lane**: `HOLOINDEX_EXTERNAL_FOUNDUP_ADAPTER_HOOKUP_PHASE1` (contract-shaped adapter, exports, `21` focused tests, interceptor `health`, this report).
- **Follow-on**: `HOLOINDEX_SHELL_BACKEND_REGISTRATION_PHASE1` (see below).

## Shell backend registration seam (2026-04-05)

**Worker**: H  
**Slice**: `HOLOINDEX_SHELL_BACKEND_REGISTRATION_PHASE1`

- **Registration**: `window.shellBridgeInterceptor.registerShellBridgeBackend(backend, { label })` validates `search` / `wspLookup` / `health` (all functions returning Promises). Clears with `clearShellBridgeBackend()`. Status: `getShellBridgeBackendStatus()` → `mode: stub|registered` (explicit **stub** responses keep `data.stub === true`; registered path does not imply “fully live HoloIndex production”).
- **Tests**: `public/member/tests/shell_bridge_interceptor_vm.mjs` (Node `vm` runtime) + `public/member/tests/test_shell_bridge_interceptor.py` (static + subprocess node).
- **Contract pointer**: `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` §5.

**Architect**: This slice is **closed** for the registration seam + focused verification; wiring a *particular* host (e.g. Electron IPC → Python adapter) is a future host-specific step, not a second HoloIndex runtime.

## Classification

- `HoloIndex Core Retrieval Engine`: **INTERNAL-ONLY**
- `HoloIndex ChromaDB/Vectors/Memory Storage`: **INTERNAL-ONLY**
- `HoloIndex Qwen/Gemma Advisor (HoloDAE)`: **INTERNAL-ONLY**
- `HoloIndex CLI Execution Surface`: **INTERNAL-ONLY**
- `HoloIndex Bridge Adapter`: **INTERNAL (serves external UI)**
- `Search Result Web Rendering UI`: **EXTERNALIZABLE-NOW**
- `Interactive Orchestration / Triage Frontend UI`: **EXTERNALIZABLE-LATER**
- `External Contributor Indexing Tasks UI`: **EXTERNALIZABLE-LATER**
