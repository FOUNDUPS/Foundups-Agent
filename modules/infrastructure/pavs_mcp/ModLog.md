# pAVS MCP Server - ModLog

## 2026-05-10 - MCPA9E: S3 Qwen Plan Backend Connection

**Author**: 0102 (Worker W1)
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9E_QWEN_PLAN_BACKEND_CONNECTION_PHASE1`
**Closes (MCPA9D audit)**: H5c (qwen_plan now real)

### Why

Per MCPA9D progression, `qwen_plan` was the next backend connection target.
`QwenInferenceEngine` has a direct callable seam:
- `generate_response(prompt) -> str`

Uses `resolve_code_model_path()` from shared_utilities for model discovery.

### Changes

- `src/server.py`:
  - Added `_QWEN_BACKEND_AVAILABLE` flag
  - Added `_QWEN_ENGINE` lazy singleton
  - Added `_get_qwen_engine()` using `resolve_code_model_path()` + `QwenInferenceEngine`
  - Added `_call_qwen_plan()` adapter with prompt engineering for step extraction
  - Rewrote `qwen_plan()` method to delegate to Qwen backend
  - Returns `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="QWEN"`
  - Returns `BACKEND_UNAVAILABLE` if Qwen model fails or returns empty plan
  - Returns `INVALID_INPUT` for empty objective
  - Updated `PLACEHOLDER_BANNER` to show 6/8 tools with real backends

- `tests/test_server_holo_search.py`:
  - Added `TestQwenBackendDelegation` class (12 tests)
  - Tests plan generation, validation, constraints passthrough
  - Tests handle both success and BACKEND_UNAVAILABLE gracefully
  - Updated banner test for `qwen_plan : REAL`
  - Updated parametrized test for Qwen real backend

- `tests/test_transport.py`:
  - Added `TestQwenViaTransport` class (3 tests)
  - Tests qwen_plan via HTTP POST /tool

- `README.md`:
  - Updated status: 6/8 tools have real backends
  - Updated tool table: `qwen_plan` now **YES**

### Callable Seam Used

- `modules/infrastructure/shared_utilities/local_model_selection.py`:
  - `resolve_code_model_path()` for model path discovery
- `holo_index/qwen_advisor/llm_engine.py`:
  - `QwenInferenceEngine` class
  - `generate_response(prompt)` method
  - Uses llama_cpp with lazy loading

### Result

S3 `qwen_plan` delegates to QwenInferenceEngine for real strategic planning.
6/8 tools now have real backends: holo_search, fam_emit, pattern_recall, pattern_store, gemma_classify, qwen_plan.
1 tool remains placeholder: cabr_validate.
137/137 tests passing.

---

## 2026-05-09 - MCPA9D: S3 Gemma Classify Backend Connection

**Author**: 0102 (Worker W1)
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9D_GEMMA_CLASSIFY_BACKEND_CONNECTION_PHASE1`
**Closes (MCPA9C audit)**: H5b (gemma_classify now real)

### Why

Per MCPA9C re-audit, `gemma_classify` was identified as highest priority backend
(WSP 15 score: 13). `GemmaRAGInference._gemma_inference()` provides a direct
callable seam for text classification via llama_cpp.

### Changes

- `src/server.py`:
  - Added `_GEMMA_BACKEND_AVAILABLE` flag
  - Added `_get_gemma_engine()` lazy singleton
  - Added `_call_gemma_classify()` adapter with prompt engineering
  - Rewrote `gemma_classify()` method to delegate to Gemma backend
  - Returns `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="GEMMA"`
  - Returns `BACKEND_UNAVAILABLE` if Gemma model fails
  - Returns `INVALID_INPUT` for empty text or categories
  - Updated `PLACEHOLDER_BANNER` to show 5/8 tools with real backends

- `tests/test_server_holo_search.py`:
  - Added `TestGemmaBackendDelegation` class (11 tests)
  - Tests classification, validation, binary/multi-class
  - Updated banner test for `gemma_classify : REAL`
  - Updated parametrized test for Gemma real backend

- `tests/test_transport.py`:
  - Added `TestGemmaViaTransport` class (3 tests)
  - Tests gemma_classify via HTTP POST /tool

- `README.md`:
  - Updated status: 5/8 tools have real backends
  - Updated tool table: `gemma_classify` now **YES**

### Callable Seam Used

- `holo_index/qwen_advisor/gemma_rag_inference.py`:
  - `GemmaRAGInference` class (line 97)
  - `_gemma_inference(prompt)` method (line 351)
  - Uses llama_cpp with lazy loading
  - Model: gemma-3-270m via `resolve_triage_model_path()`

### Result

S3 `gemma_classify` delegates to GemmaRAGInference for real classification.
5/8 tools now have real backends: holo_search, fam_emit, pattern_recall, pattern_store, gemma_classify.
2 tools remain placeholders: cabr_validate, qwen_plan.
122/122 tests passing.

---

## 2026-05-09 - MCPA9C: S3 Pattern Memory Backend Connection

**Author**: 0102 (Worker W1)
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9C_PATTERN_MEMORY_BACKEND_CONNECTION_PHASE1`
**Closes (MCPA9B audit)**: H4e (pattern_recall + pattern_store now real)

### Why

Per MCPA9B re-audit, `pattern_recall` and `pattern_store` were identified as
high-priority backend connection targets (WSP 15 score: 13, lowest = highest priority).
`PatternMemory` has direct callable seams:
- `recall_successful_patterns(skill_name, min_fidelity, limit) -> List[Dict]`
- `store_outcome(SkillOutcome) -> None`

Uses singleton pattern (PatternMemory() with no args reuses shared instance).

### Changes

- `src/server.py`:
  - Added `_PATTERN_MEMORY_AVAILABLE` flag
  - Added `_call_pattern_recall()` adapter function
  - Added `_call_pattern_store()` adapter function constructing SkillOutcome
  - Rewrote `pattern_recall()` to delegate to PatternMemory backend
  - Rewrote `pattern_store()` to delegate to PatternMemory backend
  - Returns `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="PATTERN_MEMORY"`
  - Returns `BACKEND_UNAVAILABLE` error if PatternMemory fails
  - Returns `INVALID_OUTCOME` error for missing required fields
  - Updated `PLACEHOLDER_BANNER` to show 4/8 tools with real backends

- `tests/test_server_holo_search.py`:
  - Added `TestPatternMemoryBackendDelegation` class (25 tests)
  - Tests pattern_recall and pattern_store backend delegation
  - Tests validation errors, optional field defaults, round-trip
  - Updated banner test for `pattern_recall : REAL`, `pattern_store : REAL`
  - Updated parametrized test for real backend distinction

- `tests/test_transport.py`:
  - Added `TestPatternMemoryViaTransport` class (4 tests)
  - Tests pattern_recall and pattern_store via HTTP transport
  - Fixed timeout issue by using pattern_recall (fast) instead of holo_search (slow S2)

- `README.md`:
  - Updated status: 4/8 tools have real backends
  - Updated tool table: `pattern_recall`, `pattern_store` now **YES**

### Callable Seams Used

- `modules/infrastructure/wre_core/src/pattern_memory.py`:
  - `PatternMemory()` singleton (line 75-112)
  - `recall_successful_patterns()` (line 485)
  - `store_outcome()` (line 331)
  - `SkillOutcome` dataclass (line 35-53)

### Result

S3 `pattern_recall` and `pattern_store` delegate to PatternMemory SQLite.
4/8 tools now have real backends: holo_search, fam_emit, pattern_recall, pattern_store.
3 tools remain placeholders: cabr_validate, gemma_classify, qwen_plan.
108/108 tests passing.

---

## 2026-05-09 - MCPA9B: S3 fam_emit Backend Connection

**Author**: 0102 (Worker W1)
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9B_FAM_EMIT_BACKEND_CONNECTION_PHASE1`
**Closes (MCPA9A audit)**: H4d (fam_emit now real)

### Why

Per MCPA9A re-audit, `fam_emit` was identified as a high-priority backend connection
target because `fam_daemon.py` has a working `emit()` method with JSONL+SQLite
dual-write. This slice connects S3 `fam_emit` to the real FAM DAEmon backend.

### Changes

- `src/server.py`:
  - Added `_FAM_BACKEND_AVAILABLE` flag
  - Added `_call_fam_emit()` adapter function importing `get_fam_daemon()`
  - Rewrote `fam_emit()` method to delegate to FAM DAEmon
  - Returns `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="FAM_DAEMON"`
  - Returns `BACKEND_UNAVAILABLE` error if FAM backend fails
  - Updated `PLACEHOLDER_BANNER` to include `fam_emit : REAL`

- `tests/test_server_holo_search.py`:
  - Updated `test_fam_emit_matching_foundup_id_accepted` for real backend envelope
  - Added unique payload (uuid) to avoid FAM dedupe rejection
  - Updated banner test to require `fam_emit : REAL`

- `tests/test_transport.py`:
  - Added `TestFamEmitViaTransport` class
  - Tests fam_emit backend delegation via HTTP POST /tool

- `README.md`:
  - Updated status to include fam_emit as REAL
  - Updated tool table: `fam_emit` now shows **YES** for real backend

### Result

S3 `fam_emit` persists events to FAM DAEmon JSONL+SQLite.
`holo_search` and `fam_emit` are now real backends.
Other tools (CABR, Gemma, Qwen, pattern_*) remain placeholders.
86/86 tests passing.

---

## 2026-05-09 - MCPA9A: S3 holo_search Backend Connection

**Author**: 0102 (Worker W1)
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION_PHASE1`
**Closes (MCPA8B audit)**: H4 (partial — holo_search now real)

### Why

Per MCPA8B re-audit, all tool backends were placeholders returning hardcoded data.
This slice connects S3 `holo_search` to the real S2/HoloIndex backend, making it
the first tool with a real backend connection.

### Changes

- `src/server.py`:
  - Added `_REPO_ROOT` constant for HoloIndex location
  - Added `_call_s2_holo_search()` adapter function at lines 49-86
  - Rewrote `holo_search()` method to delegate to S2 backend
  - Returns `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="S2"`
  - Returns `BACKEND_UNAVAILABLE` error if S2 fails
  - Updated `PLACEHOLDER_BANNER` to `REAL_TRANSPORT + PARTIAL_BACKENDS`

- `tests/test_server_holo_search.py`:
  - Renamed `TestNotImplementedEnvelope` to `TestS2BackendDelegation`
  - Updated assertions: `status="ok"`, `real_backend=True`, no error on success
  - Added tests for `delegated_to`, `surface`, real hits
  - Updated banner test for new status strings

- `README.md`:
  - Updated status to `REAL_TRANSPORT + PARTIAL_BACKENDS`
  - Updated tool table: `holo_search` now shows **YES** for real backend

### Result

S3 `holo_search` returns real semantic search results from HoloIndex.
Other tools (CABR, Gemma, Qwen, etc.) remain placeholders.
85/85 tests passing.

---

## 2026-05-09 - MCPA8 Correction: Stdlib Transport (No External Deps)

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries)
**Slice**: `MCPA8_TRANSPORT_DEPENDENCY_CORRECTION_PHASE1`

### Why

Initial MCPA8 implementation used FastAPI/uvicorn which are not declared dependencies
for this module. This caused import failures in clean environments without those packages.

### Changes

- `src/server.py`:
  - Replaced FastAPI/uvicorn/pydantic imports with Python stdlib
  - Added `PAVSHTTPRequestHandler` class using `http.server.BaseHTTPRequestHandler`
  - Rewrote `start()`, `stop()`, `start_sync()`, `stop_sync()` to use `HTTPServer`
  - Removed `_setup_routes()`, `app` property, `ToolCallRequest` class
  - Same endpoint contract: GET /status, GET /tools, POST /tool, POST /tool/{name}

- `tests/test_transport.py`:
  - Replaced FastAPI TestClient with stdlib `urllib.request`
  - Added `_get_free_port()` helper for test isolation
  - Tests now start actual server in background thread
  - 12 transport tests all passing

- `README.md`:
  - Updated transport description to mention stdlib, no external dependencies

### Result

Module importable and tests pass without FastAPI/uvicorn installed.

---

## 2026-05-09 - MCPA8: Real Local Transport (HTTP_JSON)

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance)
**Slice**: `MCPA8_PAVS_REAL_TRANSPORT_PHASE1`
**Closes (MCPA7B audit)**: H2 (real transport)

### Why

Per MCPA7B re-audit, S3's `start()` was a sleep-loop placeholder — no port binding,
no client connections possible. This slice implements real local HTTP JSON transport
so external clients can connect to pAVS MCP for federation.

### Changes

- `src/server.py`:
  - Added FastAPI/uvicorn imports and `ToolCallRequest` Pydantic model.
  - Added `_setup_routes()` method with four HTTP endpoints:
    - `GET /status` — health check and server status
    - `GET /tools` — list available tools
    - `POST /tool` — main tool call endpoint (dispatches to `handle_tool_call`)
    - `POST /tool/{name}` — alternative endpoint with tool name in path
  - Added `app` property exposing FastAPI instance for TestClient usage.
  - Rewrote `start()` to use uvicorn.Server instead of sleep loop.
  - Added `stop()` for graceful async shutdown.
  - Added `start_sync()` / `stop_sync()` for thread-based testing.
  - Updated `PLACEHOLDER_BANNER`:
    - Title: `REAL_TRANSPORT + PLACEHOLDER_BACKENDS`
    - `server_transport: HTTP_JSON (local, real binding)`
    - `implementation_status: placeholder_stub (backends only)`
  - Updated docstring to reflect real transport status.

- `tests/test_transport.py` (NEW):
  - 14 focused transport tests using FastAPI TestClient:
    - `TestTransportEndpoints`: status and tools endpoints
    - `TestToolCallViaTransport`: tool call dispatch, auth, errors
    - `TestTransportErrorHandling`: invalid JSON, missing fields
    - `TestAuthThroughTransport`: auth errors pass through transport
    - `TestServerAppProperty`: app property and routes

- `tests/test_server_holo_search.py`:
  - Updated banner test to expect `REAL_TRANSPORT`, `HTTP_JSON`, etc.

- `README.md`:
  - Updated status from `PLACEHOLDER_STUB` to `REAL_TRANSPORT + PLACEHOLDER_BACKENDS`
  - Added HTTP Transport Endpoints section with endpoint contract

### Behavior boundaries (what did NOT change)

- Tool bodies still return hardcoded/fake data — backends not connected
- No key rotation/revocation API
- S1 and S2 untouched
- Registry persistence behavior unchanged

### Tests

```
PYTHONPATH=. python -m pytest modules/infrastructure/pavs_mcp/tests/ -q
-> 88 passed (74 existing + 14 new transport tests)
```

### Tracked follow-ups

- MCPA9+ — Real backend connections, key rotation/revocation API

---

## 2026-05-09 - MCPA7: Registry Persistence (LOCAL_JSON)

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance)
**Slice**: `MCPA7_PAVS_REGISTRY_PERSISTENCE_PHASE1`
**Closes (MCPA6C audit)**: H1 (persistent registry) — partial (JSON, not SQLite)

### Why

Per MCPA6C re-audit, S3's registry was in-memory only — FoundUp registrations
and API key bindings were lost on restart. This slice implements durable local
persistence so auth enforcement survives restarts without requiring external
infrastructure.

### Changes

- `src/server.py`:
  - Added `RegistryStore` class with JSON-based persistence:
    - `_load()`: Loads from disk on init; handles corrupt files gracefully
    - `_save()`: Atomic writes (temp file + rename pattern)
    - `register()`: Persists new registrations; handles re-registration
    - Properties: `registrations`, `api_key_to_foundup`, `load_error`
  - Added persistence constants:
    - `DEFAULT_REGISTRY_DIR = Path.home() / ".pavs_mcp"`
    - `REGISTRY_FILENAME = "registrations.json"`
    - `REGISTRY_PATH_ENV_VAR = "PAVS_REGISTRY_PATH"` (override for testing)
  - Added `to_dict()` and `from_dict()` to `FoundUpRegistration` dataclass
  - Updated `PAVSMCPServer.__init__`:
    - Added optional `registry_path` parameter for testing
    - Creates `RegistryStore` instead of raw dicts
    - Added property accessors for backwards compatibility
  - Updated `foundup_register()` to use `RegistryStore.register()`
  - Updated `PLACEHOLDER_BANNER`: `registry_persistence: LOCAL_JSON`

- `tests/test_server_holo_search.py`:
  - Added `TestRegistryPersistence` class with 7 focused tests:
    - `test_registration_persists_to_file`
    - `test_registration_survives_restart`
    - `test_corrupt_registry_starts_empty`
    - `test_missing_registry_starts_empty`
    - `test_env_var_override`
    - `test_reregistration_replaces_existing`
    - `test_atomic_write_creates_parent_dirs`
  - Updated banner test to expect `LOCAL_JSON` instead of `NONE`
  - Added imports: `json`, `tempfile`, `Path`, `RegistryStore`, `FoundUpRegistration`

- `README.md`:
  - Updated status to include `LOCAL_JSON` persistence
  - Added registry path and env var documentation
  - Updated tracked remediation to Slice 8+

### Behavior boundaries (what did NOT change)

- No WebSocket transport — `start()` still does not bind a port
- Tool bodies still return hardcoded/fake data — backends not connected
- No key rotation/revocation API
- S1 and S2 untouched

### Tests

```
PYTHONPATH=. python -m pytest modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py -q
-> 74 passed (67 existing + 7 new persistence tests)
```

### Tracked follow-ups

- MCPA1 Slice 8+ — Real transport (WebSocket/SSE), real backend connections,
  key rotation/revocation API
- Consider SQLite upgrade if concurrent access becomes a concern (current JSON
  approach is sufficient for single-server deployment)

---

## 2026-05-09 - MCPA1_SLICE_6: Federation Auth/Scope Enforcement (Phase 1)

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A)
**Slice**: `MCPA1_SLICE_6_S3_FEDERATION_AUTH_AND_SCOPE_PHASE1`
**Closes (MCPA1 audit)**: R1 (auth TODO), D24 (cross-tenant enforcement)

### Why

Per MCPA1 audit and MCPA6B re-audit, S3's `handle_tool_call` accepted `api_key`
but never validated it. Any caller could pass any `foundup_id` to tools like
`fam_emit` without ownership verification. This slice implements minimum viable
federation auth/scope enforcement.

### Changes

- `src/server.py`:
  - `FoundUpRegistration` extended with `owner_pubkey` and `registered_at` fields.
  - Added `_api_key_to_foundup: dict[str, str]` reverse lookup in `__init__`.
  - Added auth error codes: `MISSING_API_KEY`, `UNKNOWN_API_KEY`, `CROSS_TENANT_VIOLATION`.
  - Added `BOOTSTRAP_TOOLS = {"foundup_register"}` — tools that remain unauthenticated.
  - Added `_build_auth_meta()` helper for truthful `auth_enforced` flag.
  - Added `_validate_api_key()` — returns (valid, foundup_id, error_response).
  - Added `_validate_scope()` — rejects cross-tenant `foundup_id` attempts.
  - Rewrote `handle_tool_call()`:
    - Bootstrap tools (`foundup_register`) bypass auth.
    - Protected tools require valid registered API key.
    - `foundup_id` arguments validated against registered identity.
    - `meta.auth_enforced=True` when auth actually ran.
    - `meta.registered_foundup_id` echoed on successful auth.
  - Updated `foundup_register` to populate `_api_key_to_foundup` mapping.
  - Updated `PLACEHOLDER_BANNER` to declare `BASIC` auth enforcement.

- `tests/test_server_holo_search.py`:
  - Added `_register_and_get_key()` helper for auth tests.
  - Added `authed_server` fixture for tests requiring auth.
  - Updated 13 existing tests to pass API key where required.
  - Added `TestFederationAuth` class with 20 focused tests:
    - Bootstrap tool remains unauthenticated
    - Missing API key rejected
    - Unknown API key rejected
    - Registered API key accepted
    - Cross-tenant `foundup_id` rejected
    - Matching `foundup_id` accepted
    - No `foundup_id` argument OK
    - Meta flags truthful
    - Registration creates proper bindings
    - All protected tools enforce auth (parametrized)

- `README.md`:
  - Updated status from `NO_AUTH_ENFORCEMENT` to `BASIC_AUTH_ENFORCEMENT`.
  - Added `scope_enforcement` and `registry_persistence` status notes.

- `mcp_manager.py`:
  - Updated S3 descriptor notes to reflect MCPA1 Slice 6 completion.

### Behavior boundaries (what did NOT change)

- Registry is **in-memory only** — lost on restart. Persistent registry deferred.
- No WebSocket transport — `start()` still does not bind a port.
- Tool bodies still return hardcoded/fake data — backends not connected.
- S1 and S2 untouched.
- `foundup_register` remains unauthenticated (bootstrap-only pattern).

### Tests

```
PYTHONPATH=. python -m pytest modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py -q
-> 67 passed

PYTHONPATH=. python -m pytest modules/infrastructure/mcp_manager/tests/test_surface_discovery.py -q
-> 20 passed
```

### Tracked follow-ups

- ~~MCPA1 Slice 7 — Persistent registry~~ ✅ Done (LOCAL_JSON, see above)
- MCPA1 Slice 8+ — Real transport (WebSocket/SSE), real backend connections

---

## 2026-05-08 - MCPA1_SLICE_4: S3 holo_search → canonical not_implemented envelope

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.3)
**Slice**: `MCPA1_SLICE_4_S3_NOT_IMPLEMENTED_ENVELOPE_PHASE1`
**Closes (MCPA6 audit drift)**: D20, D21, D22, D23, D24 (request fields), D25 (canonical shape)

### Why

Per MCPA6 conformance audit (`docs/audits/mcp_system/MCPA6_MCP_CONFORMANCE_AUDIT.md`),
S3's `holo_search` was returning a flat `{matches: [...]}` payload with a
fabricated similarity score (`0.95`) and a fake file path. WSP 96 Annex A.3
mandates that placeholder surfaces emit a canonical `not_implemented` envelope
rather than fabricated data. MCPA4 added the truth-flag wrapper but the tool
body itself still synthesized fake matches.

### Changes

- `src/server.py`:
  - Replaced `holo_search` tool body with the canonical Annex A.3
    `not_implemented` envelope.
  - Signature now accepts the five canonical request fields:
    `query`, `limit`, `doc_type_filter`, `foundup_id`, `include_shared`.
  - Legacy `domain` parameter retained as deprecated alias for
    `doc_type_filter` (back-compat for callers from before this slice);
    surfaces a warning naming the canonical field.
  - `limit` is bounded 1..50 per Annex A.2 with truthful warning when clamped.
  - Returns `{status, data, error, meta}` with:
    - `status = "not_implemented"`
    - `data` echoes the request (query, doc_type_filter, foundup_id) and
      contains empty `hits[]` (hit_count = 0); `metadata.retrieval_mode = "none"`
      so no caller can confuse this with a semantic search.
    - `error` carries `code = "NOT_IMPLEMENTED"`, a message naming this surface
      and the canonical owners (S1, S2), and `delegate_to = "S2"`.
    - `meta` merges `_truth_meta()` (MCPA4 truth flags) with `tool` and
      `surface = "S3"` per Annex A.3.

- `tests/test_server_holo_search.py`:
  - Updated `test_holo_search_payload_remains_visible` →
    `test_holo_search_payload_uses_canonical_envelope`. The legacy assertion
    `assert "matches" in result["result"]` is replaced by canonical envelope
    assertions and an explicit ban on the `matches` key.
  - Added `TestNotImplementedEnvelope` class with 21 focused tests covering
    status field, no-fabrication invariants (no relevance/score/distance keys
    anywhere; no legacy `example.py` markers), error block (code, delegate_to,
    canonical-owner naming), data block (query/doc_type_filter/foundup_id echo,
    include_shared null when foundup_id absent, retrieval_mode = "none"),
    meta block (surface = "S3", tool, truth flag), all canonical request
    fields accepted, limit bound enforcement, garbage-limit fallback,
    legacy `domain` alias still accepted with warning, canonical wins over
    alias, and dispatch-path wrapping (handle_tool_call) preserves both
    inner canonical envelope and outer truth meta.

### Behavior boundaries (what did NOT change)

- No real auth implementation (still TODO; MCPA1 Slice 6 lane).
- No WebSocket transport (start() still does not bind a port).
- No real backend integration (no HoloIndex call, no engine wiring).
- S1 and S2 untouched.
- MCP Manager untouched.
- `_truth_meta()` semantics preserved — meta layer carries MCPA4 truth flags.
- Other tool bodies (`cabr_validate`, `gemma_classify`, `qwen_plan`, etc.)
  unchanged — Slice 4 scope is `holo_search` only per WSP 96 Annex A authority.

### Tests

```
PYTHONPATH=. python -m pytest \
  modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py -q
-> 43 passed (22 pre-existing MCPA4 tests + 21 new MCPA1-Slice-4 tests)
```

### Tracked follow-ups

- MCPA1 Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`) — once federation
  auth lands, S3's `holo_search` either delegates to S2/S1 with verified
  tenant scope or stops returning `not_implemented`. The truth meta and
  envelope shape established in this slice will continue to apply.
- MCPA6 audit Slice 6.3 (`S2_ANNEX_A_RENAME_AND_META_PHASE1`) — S2's
  request-field naming (`scope` → `doc_type_filter`, `top_k` → `limit`)
  is the next conformance step on the bridge side.

---

## 2026-05-08 - PAVS_HONESTY_PHASE1 (MCPA4) — Truth flag and placeholder labeling

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.5 C3)
**Slice**: `MCPA4_PAVS_HONESTY_PHASE1`

### Why

Per MCPA1 audit (`docs/audits/mcp_system/MCPA1_MCP_SURFACE_AUTHORITY_AUDIT.md`),
S3 (this server) was advertising itself as a federation MCP server while
returning hardcoded data, accepting `api_key` without validating it, and not
binding any port. WSP 96 Annex A.5 C3 requires every MCP surface to declare
its truth-status truthfully. This slice implements the minimal honesty
labeling without rewriting the placeholder bodies.

### Changes

- `README.md`:
  - Status banner at top declaring `PLACEHOLDER_STUB`, `NO_AUTH_ENFORCEMENT`,
    `TOOLS RETURN HARDCODED/FAKE DATA`, `NOT PRODUCTION READY`.
  - Tools table now declares `Real backend? = NO` for every tool with a
    one-line reason.
  - Client `.env` block annotated `(planned, not deployed)` with explicit
    warning that the documented `wss://pavs.foundups.com/mcp` endpoint is
    not live.

- `src/server.py`:
  - Module docstring extended with truth-boundary notice.
  - Added module-level constants `IMPLEMENTATION_STATUS = "placeholder_stub"`
    and `PLACEHOLDER_BANNER` (operator-facing startup warning).
  - Added `_truth_meta()` helper returning the canonical truth-meta block.
  - `handle_tool_call` now wraps every response (success, unknown-tool,
    internal error) with `meta` containing the truth flags. Auth branch is
    unchanged behaviorally but documented as ignored.
  - `start()` now prints and logs `PLACEHOLDER_BANNER` before the
    do-not-bind sleep loop.

- `tests/test_server_holo_search.py` (NEW):
  - 19 tests covering: module constant presence, banner phrase
    requirements, `_truth_meta` shape, holo_search response truth flag,
    parameterized truth-flag assertion across all 8 tools, error-path
    honesty (UNKNOWN_TOOL and INTERNAL_ERROR), and api_key-ignored proof.
  - `tests/__init__.py` (NEW, empty) to make the test package discoverable.

### Behavior boundaries (what did NOT change)

- No real auth implemented. `api_key` is still ignored at runtime; the
  truth flag merely declares this honestly.
- No real WebSocket transport. `start()` still does not bind. The new
  banner just makes that visible to operators.
- No tool body changes. `holo_search`, `cabr_validate`, etc. still return
  the same hardcoded payloads. The truth flag wraps them so callers can
  detect the placeholder state.
- S1 and S2 untouched.

### Tests

`PYTHONPATH=. python -m pytest modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py -q`
-> 19 passed.

### Tracked follow-ups

- MCPA1 Slice 4 (`MCP_HOLO_SEARCH_DELEGATION_PHASE1`) — switch S3's
  `holo_search` to either delegate to S1/S2 or return a structured
  `not_implemented` envelope per WSP 96 Annex A.3.
- MCPA1 Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`) — real api_key
  validation, persistent registry, transport binding.

---

## 2026-03-15 - Module Creation (WSP 103 Foundation)

**Author**: 0102
**WSP Compliance**: WSP 103, WSP 96, WSP 49

### Created

- `README.md` - Module overview and quick start
- `INTERFACE.md` - MCP tool API documentation
- `ROADMAP.md` - Phased delivery plan
- `src/__init__.py` - Module exports
- `src/server.py` - pAVS MCP Server implementation (placeholder)

### Architecture Decision

**WSP 103 FoundUp Federation Protocol** establishes that:
- FoundUps are independent repositories (not monorepo subdirectories)
- FoundUps connect to pAVS infrastructure via MCP
- pAVS MCP Server exposes: CABR, Gemma, Qwen, FAM, Pattern Memory, HoloIndex

### Tools Defined

| Tool | Purpose | Status |
|------|---------|--------|
| `cabr_validate` | V1/V2/V3 content validation | Placeholder |
| `gemma_classify` | Binary/multi-class classification | Placeholder |
| `qwen_plan` | Strategic planning | Placeholder |
| `fam_emit` | Event tracking | Placeholder |
| `pattern_recall` | Recall patterns | Placeholder |
| `pattern_store` | Store outcomes | Placeholder |
| `holo_search` | Semantic search | Placeholder |
| `foundup_register` | Register FoundUp | Placeholder |

### Next Steps

1. Connect tool implementations to actual infrastructure
2. Implement WebSocket MCP transport
3. Add authentication/rate limiting
4. Create SDK packages (@foundups/pavs-sdk, foundups-pavs)
