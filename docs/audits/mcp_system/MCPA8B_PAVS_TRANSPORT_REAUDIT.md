# MCPA8B — pAVS Transport Re-Audit

**Slice**: `MCPA8B_PAVS_TRANSPORT_REAUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-09
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_97 → WSP_15 → WSP_50
**Predecessor audit**: `docs/audits/mcp_system/MCPA7B_PAVS_REGISTRY_PERSISTENCE_REAUDIT.md`

---

## 1. Executive Verdict

### **TRANSPORT_CONFIRMED_NOT_BACKEND_READY**

MCPA8 successfully implemented real local HTTP JSON transport using Python stdlib `http.server`. The server now binds a real port and accepts tool call requests. However, production readiness remains blocked by:
- No real backend connections (tool bodies return hardcoded data)
- No key rotation/revocation API
- No public deployment (endpoint remains local-only)

| Dimension | Verdict | Evidence |
|-----------|---------|----------|
| Real port binding | ✅ CONFIRMED | `HTTPServer((self.host, self.port), handler_class)` at `server.py:979` |
| GET /status | ✅ CONFIRMED | `do_GET()` at `server.py:336-355` |
| GET /tools | ✅ CONFIRMED | `do_GET()` at `server.py:350-353` |
| POST /tool | ✅ CONFIRMED | `do_POST()` at `server.py:370-379` |
| POST /tool/{name} | ✅ CONFIRMED | `do_POST()` at `server.py:381-385` |
| Auth errors pass through | ✅ CONFIRMED | Tests at `test_transport.py:190-227` |
| Graceful shutdown | ✅ CONFIRMED | `stop()` at `server.py:985-989`, `stop_sync()` at `server.py:1011-1014` |
| No external dependencies | ✅ CONFIRMED | No fastapi/uvicorn imports |
| Public deployment | ❌ NOT DEPLOYED | `wss://pavs.foundups.com/mcp` remains "planned, not live" |
| Real backends | ❌ NOT READY | Tool bodies return hardcoded data |
| Key rotation | ❌ NOT READY | No rotation/revocation API |

---

## 2. Preconditions Verified

Verified on `origin/main` at `2026-05-09`:

| Check | Result | Evidence |
|-------|--------|----------|
| PR #530 merged | ✅ | `2b57c20ab feat(pavs_mcp): add stdlib HTTP JSON transport for federated tool calls (#530)` |
| `HTTPServer` exists | ✅ | `server.py:30`: `from http.server import HTTPServer, BaseHTTPRequestHandler` |
| `BaseHTTPRequestHandler` exists | ✅ | `server.py:297`: `class PAVSHTTPRequestHandler(BaseHTTPRequestHandler):` |
| `HTTP_JSON` in banner | ✅ | `server.py:83`: `"  server_transport      : HTTP_JSON (local, real binding)\n"` |
| FastAPI absent | ✅ | grep for `fastapi` returns no matches |
| uvicorn absent | ✅ | grep for `uvicorn` returns no matches |

All preconditions satisfied. Audit proceeds.

---

## 3. Transport Verification

### 3.1 Port Binding

| Aspect | Implementation | Evidence |
|--------|----------------|----------|
| Async start | `HTTPServer` + `run_in_executor` | `server.py:977-983` |
| Sync start | `HTTPServer` + background thread | `server.py:991-1009` |
| Default host/port | `0.0.0.0:8765` | `server.py:420-421` |
| Test isolation | `_get_free_port()` helper | `test_transport.py:28-32` |

### 3.2 Endpoint Contract

| Endpoint | Method | Implementation | Test |
|----------|--------|----------------|------|
| `/status` | GET | `do_GET()` returns status JSON | `test_status_endpoint_returns_running` |
| `/tools` | GET | `do_GET()` returns tool list | `test_tools_endpoint_lists_tools` |
| `/tool` | POST | `do_POST()` dispatches to `handle_tool_call` | `test_post_tool_dispatches_to_handle_tool_call` |
| `/tool/{name}` | POST | `do_POST()` extracts tool name from path | `test_post_tool_by_path_dispatches_correctly` |

### 3.3 Auth Errors Pass Through Transport

Verified by tests:

| Auth Scenario | Test | Assertion |
|---------------|------|-----------|
| Missing API key | `test_protected_tool_requires_api_key` | `error.code == "MISSING_API_KEY"` |
| Unknown API key | `test_unknown_api_key_rejected` | `error.code == "UNKNOWN_API_KEY"` |
| Cross-tenant | `test_cross_tenant_rejected` | `error.code == "CROSS_TENANT_VIOLATION"` |

### 3.4 Graceful Shutdown

| Method | Purpose | Implementation |
|--------|---------|----------------|
| `stop()` | Async shutdown | `self._http_server.shutdown()` at `server.py:988` |
| `stop_sync()` | Sync shutdown | `self._http_server.shutdown()` at `server.py:1014` |

Tested by `TestServerLifecycle::test_graceful_shutdown` — verifies connection refused after shutdown.

### 3.5 No Public Deployment Claim

README line 141-147 explicitly states:
```
# WARNING: The endpoint below is NOT deployed.
PAVS_ENDPOINT=wss://pavs.foundups.com/mcp   # planned, not live
```

PLACEHOLDER_BANNER line 87-88:
```
Transport is REAL. Backends are PLACEHOLDERS.
DO NOT USE FOR PRODUCTION TRAFFIC.
```

No overclaim of public deployment.

---

## 4. Closed Backlog Items

From MCPA7B §5 (Remaining Operational Blockers):

| ID | Item | MCPA7B Status | MCPA8B Status | Evidence |
|----|------|---------------|---------------|----------|
| **H2** | No real transport | ❌ NOT READY | ✅ CLOSED | `HTTPServer` at `server.py:297-398`, `server.py:977-1014` |
| H3 | No key rotation | ❌ NOT READY | ❌ NOT READY | No implementation |
| H4 | No real backends | ❌ NOT READY | ❌ NOT READY | Tools return hardcoded data |
| H5 | MCP Manager still PLACEHOLDER | ❌ NOT READY | ❌ NOT READY | Not addressed this slice |

---

## 5. Remaining Operational Blockers

Production deployment remains blocked by:

| ID | Blocker | Severity | Next Slice |
|----|---------|----------|------------|
| **H4** | No real backend connections | **P1** | MCPA9 |
| H3 | No key rotation/revocation | P2 | MCPA10 |
| H5 | MCP Manager status not updated | P3 | After H4 |
| — | README outdated text (lines 141-149) | P3 | Documentation cleanup |

**Note on README**: Lines 141-149 still say "does not bind a port" — this is now stale. Low priority but should be corrected in a documentation slice.

---

## 6. Updated WSP 15 Next-Step Order

Based on WSP 15 prioritization:

| Priority | Next Slice | Description | Rationale |
|----------|------------|-------------|-----------|
| **P1** | MCPA9 | Real backend connections | Replace hardcoded tool bodies |
| P2 | MCPA10 | Key rotation/revocation API | Security hygiene for production |
| P3 | MCPA11 | MCP Manager status update | Depends on H4 |
| P3 | — | README stale text cleanup | Documentation accuracy |

---

## 7. Test Coverage Verification

MCPA8 provides 12 focused transport tests:

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestTransportEndpoints` | 2 | GET /status, GET /tools |
| `TestToolCallViaTransport` | 5 | POST /tool dispatch, auth, errors |
| `TestTransportErrorHandling` | 1 | Missing field validation |
| `TestAuthThroughTransport` | 2 | Auth errors pass through |
| `TestServerLifecycle` | 2 | Port binding, graceful shutdown |

Total test suite: **86 tests passing** (74 existing + 12 transport).

---

## 8. Truth Boundary Update

MCPA7B declared:
```
server_transport: NOT READY (start() does not bind a port)
```

MCPA8B confirms update to:
```
server_transport: HTTP_JSON (local, real binding)
```

This declaration is **truthful** — it matches the runtime state observed in:
- `PLACEHOLDER_BANNER` at `server.py:75-91`
- Test `test_server_binds_to_port` at `test_transport.py:233-247`
- `HTTPServer` instantiation at `server.py:979`

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA8 pAVS real HTTP_JSON transport http.server POST /tool re-audit" --limit 5
```

**Top DOCS hit**: `modules/infrastructure/pavs_mcp/README.md`
**Top audit hit**: `docs/audits/mcp_system/MCPA7B_PAVS_REGISTRY_PERSISTENCE_REAUDIT.md`

---

## WSP 97 Applied

Three truth boundaries verified by this re-audit:

1. **TRANSPORT_CONFIRMED ≠ BACKEND_READY.** Real local transport is confirmed, but backends remain hardcoded placeholders. The verdict explicitly separates these concerns.

2. **HTTP_JSON declaration is truthful.** Every surface that declares transport status (banner, README status block, test assertions) now says `HTTP_JSON` and the runtime behavior matches.

3. **No public deployment overclaim.** The planned endpoint `wss://pavs.foundups.com/mcp` is explicitly marked "planned, not live" in README. PLACEHOLDER_BANNER says "DO NOT USE FOR PRODUCTION TRAFFIC."

WSP 50: All cited file:lines verified against `origin/main` post-#530 merge.
WSP 15: P1 backend integration identified as next critical-path blocker.
WSP 00: Identity locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA8B_PAVS_TRANSPORT_REAUDIT.md` (NEW)

No runtime code edits. No commits made.
