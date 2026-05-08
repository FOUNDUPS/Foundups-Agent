# MCPA1 — MCP Surface Authority Audit (Phase 1)

**Slice**: `MCPA1_MCP_SURFACE_AUTHORITY_AUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-08
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_50 → WSP_97
**Companion audits**: `docs/audits/openclaw_hermes/HXA1_*.md`, `HXA2_*.md`

---

## HoloIndex Research

```bash
python holo_index.py --search "MCP holo_index server foundups_mcp_bridge pavs_mcp mcp_manager holo_search authority routing auth scope" --limit 6
```

**Top CODE hit**: `modules/infrastructure/pavs_mcp/src/server.py`
**Top WSP hit**: `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md`
**Top DOCS hit**: `modules/infrastructure/pavs_mcp/INTERFACE.md`

---

## 1. Surface Inventory

### Status legend

- **`RUNTIME_LIVE`** — real, exercised path that calls actual backends.
- **`RUNTIME_INTERNAL_ONLY`** — real backend access, but not exposed over MCP transport (Python-class CLI only).
- **`PLACEHOLDER_STUB`** — file exists but every tool returns hardcoded data; `# TODO: Connect to actual <X>` markers in code.
- **`MANAGER_ONLY`** — orchestration helper, not itself an MCP surface.

| # | Surface | Path | Transport | Status | Intended Consumers |
|---|---------|------|-----------|--------|---------------------|
| S1 | HoloIndex MCP Server (P1) | `foundups-mcp-p1/servers/holo_index/server.py` | FastMCP (stdio/sse) | **RUNTIME_LIVE** | External AI clients (Cursor, Windsurf, ChatGPT) via FastMCP transport |
| S2 | FoundUps Private MCP Bridge | `modules/infrastructure/foundups_mcp_bridge/src/bridge_server.py` | Python class + CLI (no MCP wire transport) | **RUNTIME_INTERNAL_ONLY** | Internal 0102 / AI architect via direct Python calls or `python -m ... --call <tool>` CLI |
| S3 | pAVS MCP Server | `modules/infrastructure/pavs_mcp/src/server.py` | None (asyncio sleep loop, no actual server) | **PLACEHOLDER_STUB** | (Claimed) Federated FoundUp repos (autopost, gotjunk, move2japan); (actual) nobody — server doesn't bind a port |
| S4 | MCP Manager | `modules/infrastructure/mcp_manager/src/mcp_manager.py` | None (subprocess orchestrator) | **MANAGER_ONLY** | Local main.py menu — discovers and starts S1-class servers |

### Status evidence

- **S1 — RUNTIME_LIVE**: `foundups-mcp-p1/servers/holo_index/server.py:1` imports `FastMCP`. Line 17: `app = FastMCP("Foundups HoloIndex MCP Server")`. Line 21: `self.holo_index = HoloIndex()` instantiates the real engine. Line 28: `self.holo_index.search(query, limit=limit)` is a real call. File is 557 lines.
- **S2 — RUNTIME_INTERNAL_ONLY**: `bridge_server.py:54-74` defines a `FoundUpsMCPBridge` Python class. Tools registered at lines 79-131. Real backend access via `holo_tools._get_holoindex` (`holo_tools.py:40-72`). CLI entry at lines 232-289 (`--call <tool>`). **No MCP transport** — nothing in this file binds stdio, sse, websocket, or HTTP. The README claims "MCP Bridge" but the code is a Python class with a CLI shim.
- **S3 — PLACEHOLDER_STUB**: Every tool body has `# TODO: Connect to actual <X>` with hardcoded return:
  - `cabr_validate` (`pavs_mcp/src/server.py:79-91`): hardcoded `score=0.85, passed=True`. TODO at line 79.
  - `gemma_classify` (lines 108-116): hardcoded confidence `0.92`.
  - `qwen_plan` (lines 133-147): hardcoded 3-step plan.
  - `fam_emit` (lines 166-181): TODO at line 166; computes a hash but does not emit to FAM DAEmon.
  - `pattern_recall` (lines 198-213): TODO at line 198; returns a hardcoded fake pattern `ptn_001`.
  - `pattern_store` (lines 230-241): TODO at line 230; computes a hash, no persistence.
  - `holo_search` (lines 259-273): TODO at line 260; returns a hardcoded match for `modules/foundups/agent_market/src/example.py`.
  - `handle_tool_call` (line 329): `# TODO: Implement proper auth`. The `api_key` parameter is accepted but never validated.
  - `start` (lines 352-363): `# TODO: Implement actual WebSocket server`. Does not bind. Just `await asyncio.sleep(60)` in a loop.
- **S4 — MANAGER_ONLY**: `mcp_manager.py:122-138` `_discover_mcp_servers` scans only `foundups-mcp-p1/servers/`. It does NOT discover S2 or S3.

---

## 2. Authority Matrix

For each capability, identify the canonical owner surface and any duplicates/conflicts.

### 2.1 `holo_search` (semantic search)

| Surface | Tool name | Real backend? | Schema | Auth | Notes |
|---------|-----------|---------------|--------|------|-------|
| **S1** | `semantic_code_search` (`server.py:24-75`) | **YES** — `self.holo_index.search(query, limit)` | quantum-coherence-decorated | None at app layer (FastMCP transport only) | **Canonical external owner** |
| **S2** | `holo_search` (`holo_tools.py:80-199`) | **YES** — `holo.search(query, limit, doc_type_filter)` via lazy `_get_holoindex` | `ok_response`-wrapped `{hits[], hit_count, metadata}` | None | **Canonical internal owner** (perception layer); has ripgrep fallback at lines 167-198 |
| **S3** | `holo_search` (`pavs_mcp/src/server.py:243-273`) | **NO** — hardcoded match | `{matches[]}` flat | None (api_key TODO) | **Duplication conflict** — claims to be federation surface but contains zero real logic |

**Duplication conflict**: S1, S2, and S3 all expose a `holo_search`-shaped capability. S1 and S2 both call the real `holo_index.core.holo_index.HoloIndex.search`. S3 lies about doing so.

**Canonical recommendation** (anchored to the real backend at `holo_index/core/holo_index.py:178-198` and `search_engine.py:execute_search`): one canonical engine (the `HoloIndex` class) with two intentional adapters — S1 for external MCP clients, S2 for internal Python/CLI callers. S3 must either delegate to S1/S2 or be removed.

### 2.2 Auth (api key validation, tenant identity)

| Surface | Auth mechanism | Evidence | Status |
|---------|----------------|----------|--------|
| S1 | None at app layer; relies on FastMCP transport (no `api_key`/`tenant_id` checks in tool bodies) | grep `api_key|auth|tenant|scope|authorize` in `server.py`: 0 hits | UNENFORCED |
| S2 | None | grep same patterns in `bridge_server.py`: 0 hits (the only `api_key` refs are for Google AI Studio at `holo_tools.py`-adjacent files, not MCP auth) | UNENFORCED |
| S3 | Stub: `handle_tool_call` accepts `api_key` parameter but never validates it (`pavs_mcp/src/server.py:329` — `# TODO: Implement proper auth`) | Confirmed; the `foundup_register` method generates `api_keys` but no surface checks them | UNENFORCED |
| S4 | N/A (manager, not gateway) | — | N/A |

**Canonical owner**: NONE today. The README at `pavs_mcp/README.md:117` claims "WSP 71: Security - API key auth, encrypted transport"; this claim has no enforcement code behind it.

### 2.3 Tenant scope / `foundup_id` ownership

| Surface | Mechanism | Evidence | Status |
|---------|-----------|----------|--------|
| S1 | None | No `foundup_id` parameter on any tool in `server.py` | NOT ENFORCED |
| S2 | None | Tools accept paths/queries; no caller-foundup binding | NOT ENFORCED |
| S3 | `FoundUpRegistration` dataclass exists (`pavs_mcp/src/server.py:21-28`); registration generates `api_key` mapping to `foundup_id` (`foundup_register` lines 275-310). But the registry is never consulted by any tool. Tools accept `foundup_id` as a request parameter (e.g. `fam_emit`) and trust it without verifying it matches the caller's `api_key` | Cross-tenant risk: any `api_key` can pass any `foundup_id` to `fam_emit`/`pattern_store` and the surface accepts it | NOT ENFORCED |

### 2.4 Registration

| Surface | Mechanism | Authority |
|---------|-----------|-----------|
| S1 | Implicit — FastMCP picks up tools via `@app.tool()` decorators (`server.py:23, 77, 112, ...`) | Within S1 only |
| S2 | Explicit in `bridge_server._register_tools` (`bridge_server.py:76-131`) | Within S2 only |
| S3 | `FoundUpRegistration` dataclass + `foundup_register` tool (`pavs_mcp/src/server.py:21-28, 275-310`) | Claims to be a system-wide registry but persistence is in-memory `self.registrations: dict[str, FoundUpRegistration]` (line 48) — lost on restart, never read by any other surface |
| S4 | Subprocess discovery in `_discover_mcp_servers` (`mcp_manager.py:122-138`) | Discovers S1-class servers only; ignores S2 and S3 |

**Canonical owner**: There is no shared FoundUp registration authority. S3's in-memory dict is the only "registry" claim and it neither persists nor cross-references with any other surface.

### 2.5 Tool dispatch

| Surface | Mechanism | Evidence |
|---------|-----------|----------|
| S1 | FastMCP `@app.tool()` decorator → FastMCP routes via stdio/sse | `server.py:23, 77, 112, ...` |
| S2 | `_tools: Dict[str, Callable]` registry + `call_tool(name, **kwargs)` (`bridge_server.py:171-194`) | Direct Python dispatch; no transport |
| S3 | `_tools: dict[str, callable]` + `handle_tool_call` (`pavs_mcp/src/server.py:51-62, 312-350`) | Same pattern as S2 but dispatch is wired to placeholder bodies |

**Drift**: S2 and S3 use lookalike but incompatible dispatch surfaces (different return wrappers, different error envelopes — see §4).

---

## 3. Routing Matrix

### Ingress points → which MCP surface is actually called

| Ingress | Caller | Reaches | Bypass risk |
|---------|--------|---------|-------------|
| FastMCP client (Cursor, Windsurf, external IDE) | External AI tool | **S1** (via stdio/sse) | None (transport-locked); no app auth gate, but transport pairing is local-only |
| `python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server --call <tool>` | Local 0102/operator | **S2** (Python class) | None — direct local invocation |
| `from modules.infrastructure.foundups_mcp_bridge.src import FoundUpsMCPBridge` | Internal Python code | **S2** | None — direct import |
| (Documented) `wss://pavs.foundups.com/mcp` | (Claimed) federated FoundUps via TS/Python SDK | **NOWHERE** — S3 does not bind a port (`server.py:354` is a TODO; `start` just sleeps) | Endpoint is fictional; clients written against `pavs_mcp/README.md:108` ("PAVS_ENDPOINT=wss://pavs.foundups.com/mcp") will fail to connect |
| `python main.py --mcp` (menu option 14) | Local operator | **S4 → S1** (manager auto-starts S1-class servers from `foundups-mcp-p1/servers/`) | S4 cannot start S2 or S3 (auto-discovery only scans the p1 dir) |

### Bypass-of-policy paths

1. **No app-layer auth on S1 or S2**: any caller reaching the transport (FastMCP local pairing for S1, local Python import for S2) can call any tool. Policy intent (per `pavs_mcp/README.md:117` and `WSP 96`) is never executed because S3 — the only surface that even tried — is a stub.
2. **`mcp_manager` does not orchestrate S2 or S3**: a local operator running `python main.py --mcp` will start S1 but will not expose, monitor, or even know about S2 and S3.
3. **S3 silent failure**: clients written against the documented `wss://pavs.foundups.com/mcp` will hang — the server starts but never accepts connections. There is no error surfacing to the operator.
4. **`FoundUp federation` claim has no enforcement**: a federated FoundUp could try to pass any `foundup_id` to `fam_emit` (S3 line 149-181) and the surface would happily accept it (if S3 were running). Not a live exploit because S3 isn't running, but the design is fail-open.

---

## 4. Response Contract Drift

`holo_search` result schemas across the three surfaces:

### S1 (foundups-mcp-p1) — `semantic_code_search` (server.py:53-66)

```json
{
  "query": "<query>",
  "code_results": [
    {"content": "...", "path": "...", "function": "...", "line": 0,
     "relevance": 1.0, "snippet": "..."}
  ],
  "wsp_results": [
    {"content": "...", "path": "...", "protocol": "...",
     "relevance": 1.0, "snippet": "..."}
  ],
  "total_results": 0,
  "quantum_coherence": <float>,
  "bell_state_alignment": <bool>,
  "timestamp": <float>,
  "search_metadata": {"limit": 5, "file_types": [], "execution_time": 0}
}
```

### S2 (foundups_mcp_bridge) — `holo_search` (holo_tools.py:149-160)

```json
{
  "status": "ok",
  "data": {
    "query": "<query>",
    "scope": "all|code|wsp|test|skill",
    "hits": [
      {"type": "code|wsp|test|skill", "path": "...", "relevance": 0.0,
       "preview": "...", "title": "...", "summary": "..."}
    ],
    "hit_count": 0,
    "metadata": {...}
  },
  "meta": {"timestamp": "...", "source": "holoindex|fallback", "tool": "holo_search", "confidence": 0.8}
}
```

### S3 (pavs_mcp) — `holo_search` (server.py:264-273)

```json
{
  "matches": [
    {"file": "...", "line": 42, "content": "...", "score": 0.95}
  ]
}
```

### Compatibility verdict

| Pair | Compatible? | Why |
|------|-------------|-----|
| S1 vs S2 | **INCOMPATIBLE** | Different envelopes (S1 flat; S2 status/data/meta), different hit collection names (`code_results`+`wsp_results` vs unified `hits[]` with `type`), different relevance scaling (S1: HoloIndex distance, S2: parsed similarity 0-1), S1 adds quantum/bell-state fields that S2 omits |
| S1 vs S3 | **INCOMPATIBLE + STALE** | S3 has no `code_results`/`wsp_results` split, no quantum/bell fields; S3's `matches[]` schema does not match anything S1 returns. Stale: S3 was written before S1 stabilized and has not been reconciled |
| S2 vs S3 | **INCOMPATIBLE + STALE** | S2 wraps in `ok_response`; S3 returns flat dict. S3's `matches[]` is closer to S2's `hits[]` shape but uses different keys (`file`/`line`/`content`/`score` vs `path`/`preview`/`relevance`) |

**No common contract exists.** A client cannot today be written against a single `holo_search` schema.

---

## 5. Auth & Scope Enforcement Audit

### Surface-by-surface enforcement reality

| Surface | API key check | `foundup_id` ownership check | Cross-tenant risk |
|---------|---------------|------------------------------|--------------------|
| S1 (P1 holo_index server) | Not implemented; relies on FastMCP transport pairing | No `foundup_id` field on any tool | **MEDIUM** — transport binds locally; risk is operator-side leakage, not cross-tenant |
| S2 (foundups_mcp_bridge) | Not implemented | No `foundup_id` field on any tool | **LOW** — internal-only, no remote ingress |
| S3 (pavs_mcp) | Stub (`# TODO: Implement proper auth` at line 329) | Stub (`FoundUpRegistration` defined but never consulted) | **N/A** (server isn't running) but **CRITICAL** the moment it is — design is fail-open |

### Severity-ranked risks

| ID | Risk | Severity | Surface | Evidence |
|----|------|----------|---------|----------|
| R1 | S3 documented as a federation auth boundary but has zero enforcement; if started without remediation, any caller can register any `foundup_id` and call any tool against any other tenant's data | **CRITICAL** | S3 | `pavs_mcp/src/server.py:329` (auth TODO), `:312-350` (handler ignores `api_key`), `pavs_mcp/README.md:117` (claim) |
| R2 | S3 documented client endpoint (`wss://pavs.foundups.com/mcp`) does not exist — S3 does not bind any port | **CRITICAL** (silent failure for any consumer) | S3 | `pavs_mcp/src/server.py:354` (TODO), `:362` (sleep loop), `pavs_mcp/README.md:108` (endpoint claim) |
| R3 | Three divergent `holo_search` result schemas; clients cannot interop | **HIGH** | S1, S2, S3 | §4 above |
| R4 | `mcp_manager` only discovers S1-class servers; S2 and S3 are invisible to the gateway | **HIGH** | S4 | `mcp_manager.py:122-138` |
| R5 | S1 and S2 do not enforce app-layer auth; any local pairing/import can call all tools | **MEDIUM** | S1, S2 | Empty grep results for `auth`/`tenant`/`api_key` on tool surfaces |
| R6 | S3's in-memory `registrations` dict is the only registration "registry" — does not persist across restarts and is not read by any other surface | **MEDIUM** | S3 | `pavs_mcp/src/server.py:48, 275-310` |
| R7 | Three separate "holo_search" implementations create maintenance drift; future fixes to the `HoloIndex` engine must be re-validated against three callers (or two, since S3 doesn't actually call the engine) | **MEDIUM** | All | §2.1 |
| R8 | Bridge README and pAVS README both describe themselves as "MCP" surfaces but neither speaks any MCP wire protocol (S2 = Python CLI; S3 = nothing) | **MEDIUM** | S2, S3 | `foundups_mcp_bridge/README.md:5` ("MCP bridge"), `pavs_mcp/README.md:1` ("MCP Server") |

**Risk count**: Critical = 2; High = 2; Medium = 4.

---

## 6. Canonicalization Decision

### **MULTI_SURFACE_DRIFT_BLOCKING**

Three surfaces claim `holo_search`. Only two implement it; one (S3) is a placeholder. The two real ones return incompatible schemas. None enforce app-layer auth. The MCP Manager only knows about one of them. The pAVS README documents an endpoint that does not exist.

Until the drift is resolved, **further MCP feature prompts must NOT add new tools to S3 or assume any of the three surfaces is the canonical authority**. Any feature added to one surface today will need to be re-implemented on the other two — which is exactly the failure pattern WSP 96 (MCP Governance) is meant to prevent.

---

## 7. Minimum Remediation Plan

Six atomic slices, ordered by risk. **Slice 1 is the trunk blocker.**

### Slice 1 (Trunk) — `MCP_HOLO_SEARCH_CANONICAL_CONTRACT_PHASE1`

- **Objective**: Define the canonical `holo_search` request/response contract (one envelope, one hit shape) and document it in `WSP_framework/src/WSP_96_*` or a new `MCP_CONTRACTS.md`. No code changes; contract artifact only.
- **Files**: `docs/mcp/MCP_HOLO_SEARCH_CONTRACT.md` (NEW). Optional ModLog entry.
- **Acceptance**: Single document defines the response envelope (status/data/meta), the hit object (type/path/relevance/preview/...), and the relevance scale (0-1). Document is referenced from S1, S2, and S3 docstrings in subsequent slices.

### Slice 2 — `MCP_PAVS_HONESTY_PHASE1` (de-overclaim)

- **Objective**: Stop the false-compliance pattern in S3. Either (a) clearly mark S3 as `STATUS=PROTOTYPE_NOT_RUNNING` in README and replace `wss://pavs.foundups.com/mcp` with `<not yet deployed>`, or (b) remove S3 entirely. Decision in this slice; execution in slice 5.
- **Files**: `modules/infrastructure/pavs_mcp/README.md` (MODIFY — status banner), `modules/infrastructure/pavs_mcp/src/server.py` (MODIFY — startup banner clarifying placeholder status if kept). No business logic change.
- **Acceptance**: Operator running `python -m modules.infrastructure.pavs_mcp.src.server` sees an explicit "PLACEHOLDER — TOOLS RETURN HARDCODED DATA — NO AUTH — DO NOT USE FOR REAL TENANTS" banner. README endpoint claim is removed or marked `(planned)`.

### Slice 3 — `MCP_MANAGER_DISCOVERY_EXPANSION_PHASE1`

- **Objective**: Extend `MCPServerManager._discover_mcp_servers` to also surface S2 and S3 as known surfaces (with explicit status: live/internal-only/placeholder), so the gateway report does not lie about what exists.
- **Files**: `modules/infrastructure/mcp_manager/src/mcp_manager.py:122-138`. Plus tests in `modules/infrastructure/mcp_manager/tests/`.
- **Acceptance**: `python main.py --mcp` lists three rows (HoloIndex P1 server, foundups_mcp_bridge, pavs_mcp) with truthful status flags. No transport changes.

### Slice 4 — `MCP_HOLO_SEARCH_DELEGATION_PHASE1`

- **Objective**: Make S3's `holo_search` either (a) delegate to S2's `holo_search` (so behavior is real), or (b) return `{"status": "not_implemented", "error": "pavs_mcp.holo_search is a placeholder"}` instead of fake data. Choose path (b) until the federation auth/scope layer (Slice 6) lands.
- **Files**: `modules/infrastructure/pavs_mcp/src/server.py:243-273`.
- **Acceptance**: S3's `holo_search` no longer returns hardcoded matches; returns explicit `not_implemented` until federation is real.

### Slice 5 — `MCP_AUTH_BASELINE_PHASE1`

- **Objective**: Add the simplest credible app-layer auth on S2 (the surface that's actually used). Single shared-secret env var (`FOUNDUPS_MCP_BRIDGE_TOKEN`) checked on `call_tool`. Not federation-grade — just closes the "any local Python import can run anything" gap if/when the bridge is exposed beyond direct internal use.
- **Files**: `modules/infrastructure/foundups_mcp_bridge/src/bridge_server.py:171-194`. Tests.
- **Acceptance**: With the env var set, calls without the matching token are rejected with `error_response("auth required")`. With the var unset (current default), behavior is unchanged (back-compat).

### Slice 6 — `MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`

- **Objective**: Real federation auth/scope on S3 (the surface that claims to need it). API-key → `foundup_id` mapping, persistent registry, per-tool scope enforcement. Only proceeds after Slice 1 (canonical contract) and Slice 4 (no fake data) so the new auth doesn't cement a broken contract.
- **Files**: `modules/infrastructure/pavs_mcp/src/server.py` (full rewrite of `handle_tool_call` and `foundup_register`); persistent registry adapter (likely SQLite via existing `agent_market` patterns); transport layer.
- **Acceptance**: S3's `handle_tool_call` rejects calls without a registered API key. `foundup_id` arguments on tools are verified against the registered identity. Cross-tenant attempts fail with explicit error.

---

## Acceptance Criteria Verification

- ✓ Every claim tied to file:line (sections 1-5).
- ✓ No speculative claims — distinguished `RUNTIME_LIVE` vs `RUNTIME_INTERNAL_ONLY` vs `PLACEHOLDER_STUB` with specific TODO line numbers.
- ✓ Clear canonical owner recommendation for `holo_search`: `holo_index/core/holo_index.py` is the engine; S1 is the canonical external MCP adapter; S2 is the canonical internal Python adapter; S3 must delegate or stand down.
- ✓ Clear no-go for further MCP feature prompts until Slice 1 (canonical contract) lands.

---

## WSP 97 Applied

- **CoT (retrieve before stating)**: HoloIndex run before any conclusion; canonical WSP 96 reference surfaced as top WSP hit and confirms the governance lens used here.
- **CoR (dialectic sweep before committing)**: considered one-server consolidation (collapse S1+S2+S3 into one) vs. canonical-owner-with-adapters; chose `MULTI_SURFACE_DRIFT_BLOCKING` because the S1/S2 split has legitimate transport reasons (external MCP vs internal Python) and only S3 is the actual drift hazard. The remediation plan reflects this — S1 and S2 keep their roles; S3 must stand down or be rebuilt to a real spec.
- **Truth distinction**: avoided the trap of treating S3 as "an MCP server with a TODO" — it is a placeholder with `# TODO` markers and an `asyncio.sleep(60)` body that does not bind a port. Calling it a server overclaims.
- **WSP 50 verification**: every required file was read in full or via targeted grep with line-numbered evidence; file existence and sizes verified before reading.
- **WSP 00 identity**: locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA1_MCP_SURFACE_AUTHORITY_AUDIT.md` (NEW)

No runtime code edits. No commits made.
