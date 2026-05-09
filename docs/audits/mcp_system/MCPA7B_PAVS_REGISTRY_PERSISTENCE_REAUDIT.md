# MCPA7B — pAVS Registry Persistence Re-Audit

**Slice**: `MCPA7B_PAVS_REGISTRY_PERSISTENCE_REAUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-09
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_97 → WSP_15 → WSP_50
**Predecessor audit**: `docs/audits/mcp_system/MCPA6C_MCP_CONFORMANCE_REAUDIT.md`

---

## 1. Executive Verdict

### **PERSISTENCE_CONFIRMED_NOT_PRODUCTION_READY**

MCPA7 successfully implemented durable local registry persistence. API key ownership now survives server restart. However, production readiness remains blocked by:
- No real transport (start() does not bind a port)
- No real backend connections (tool bodies return hardcoded data)
- No key rotation/revocation API

| Dimension | Verdict | Evidence |
|-----------|---------|----------|
| Registry persistence | ✅ CONFIRMED | `RegistryStore` at `server.py:138-263` |
| API key survives restart | ✅ CONFIRMED | `_load()` at `server.py:165-195` |
| Atomic writes | ✅ CONFIRMED | `_save()` at `server.py:197-218` |
| Corrupt file handling | ✅ CONFIRMED | Graceful fallback at `server.py:190-195` |
| Env var override | ✅ CONFIRMED | `PAVS_REGISTRY_PATH` at `server.py:40` |
| Real transport | ❌ NOT READY | `start()` does not bind at `server.py:821-836` |
| Real backends | ❌ NOT READY | Tool bodies return hardcoded data |
| Key rotation | ❌ NOT READY | No rotation/revocation API exists |

---

## 2. Preconditions Verified

Verified on `origin/main` at `2026-05-09`:

| Check | Result | Evidence |
|-------|--------|----------|
| PR #528 merged | ✅ | `e55ea6beb feat(pavs_mcp): persist federated FoundUp registrations locally (#528)` |
| `RegistryStore` exists | ✅ | `server.py:138`: `class RegistryStore:` |
| `PAVS_REGISTRY_PATH` exists | ✅ | `server.py:40`: `REGISTRY_PATH_ENV_VAR = "PAVS_REGISTRY_PATH"` |
| `LOCAL_JSON` in banner | ✅ | `server.py:74`: `"  registry_persistence  : LOCAL_JSON (survives restart)\n"` |
| `LOCAL_JSON` in README | ✅ | `README.md:3`: `BASIC_AUTH_ENFORCEMENT` + `LOCAL_JSON` persistence` |
| `LOCAL_JSON` in tests | ✅ | `test_server_holo_search.py:54`: `"registry_persistence  : LOCAL_JSON"` |

All preconditions satisfied. Audit proceeds.

---

## 3. Persistence Verification

### 3.1 Registry Path and Override

| Aspect | Implementation | Evidence |
|--------|----------------|----------|
| Default path | `~/.pavs_mcp/registrations.json` | `server.py:34`: `DEFAULT_REGISTRY_DIR = Path.home() / ".pavs_mcp"` |
| Override mechanism | `PAVS_REGISTRY_PATH` env var | `server.py:40-53`: `_get_registry_path()` |
| Test injection | `registry_path` constructor param | `server.py:315`: `registry_path: Optional[Path] = None` |

### 3.2 API Key Ownership Survives Restart

Verified by test `test_registration_survives_restart` at `test_server_holo_search.py:820-847`:

```python
# First server instance: register a FoundUp
srv1 = PAVSMCPServer(registry_path=registry_path)
result1 = _run(srv1.handle_tool_call("foundup_register", {...}))
api_key = result1["result"]["api_key"]

# Second server instance: should load the registration
srv2 = PAVSMCPServer(registry_path=registry_path)
assert "survivor_foundup" in srv2.registrations
assert srv2._api_key_to_foundup[api_key] == "survivor_foundup"
```

### 3.3 Corrupt/Missing Registry Handling

| Scenario | Behavior | Evidence |
|----------|----------|----------|
| Missing file | Start empty, no error | `server.py:167-169` |
| Corrupt JSON | Log warning, start empty | `server.py:190-192` |
| Invalid format | Log warning, start empty | `server.py:175-178` |
| Individual invalid registration | Skip with warning | `server.py:185-186` |

### 3.4 Duplicate Registration Behavior

Re-registration replaces existing entry:
- Old API key removed from reverse lookup (`server.py:232-235`)
- New registration stored (`server.py:237-238`)
- Persisted immediately (`server.py:239`)

Verified by test `test_reregistration_replaces_existing` at `test_server_holo_search.py:869-895`.

### 3.5 Secrets Audit

| Field | Classification | Risk |
|-------|----------------|------|
| `foundup_id` | Identifier | None |
| `repo_url` | Public URL | None |
| `api_key` | Generated token (`fp_{hex}`) | Local only — not external secret |
| `owner_pubkey` | Public key | None (public by definition) |
| `tier` | Metadata | None |
| `registered_at` | Timestamp | None |

**No real secrets committed.** The `api_key` is server-generated for local testing, stored in user-local directory (`~/.pavs_mcp/`), not in the repository. This matches the expected pattern for `PLACEHOLDER_STUB` status.

---

## 4. Closed Backlog Items

From MCPA6C §6 (Remaining Hardening Backlog):

| ID | Item | MCPA6C Status | MCPA7B Status | Evidence |
|----|------|---------------|---------------|----------|
| **H1** | Persistent FoundUp registry | ❌ NOT READY | ✅ CLOSED | `RegistryStore` at `server.py:138-263` |
| H2 | Real WebSocket/SSE transport | ❌ NOT READY | ❌ NOT READY | `start()` at `server.py:821-836` |
| H3 | Key rotation/revocation API | ❌ NOT READY | ❌ NOT READY | No implementation |
| H4 | Real backend connections | ❌ NOT READY | ❌ NOT READY | Tools return hardcoded data |
| H5 | MCP Manager status flip | ❌ NOT READY | ❌ NOT READY | Still `PLACEHOLDER_STUB` |
| H6 | S1/S2 federation warning | ⚠️ STALE | ⚠️ STALE | Not addressed this slice |

### Implementation Note

MCPA6C specified "SQLite" for H1. MCPA7 delivered JSON instead. This is acceptable because:
1. JSON is human-readable and debuggable
2. Single-server deployment doesn't require concurrent write safety
3. JSON meets the functional requirement (survives restart)
4. SQLite upgrade remains available if concurrent access becomes a concern

---

## 5. Remaining Operational Blockers

Production deployment remains blocked by:

| ID | Blocker | Severity | Next Slice |
|----|---------|----------|------------|
| **H2** | No real transport | **P1** | MCPA8 |
| H3 | No key rotation | P2 | MCPA9+ |
| H4 | No real backends | P2 | MCPA10+ |
| H5 | MCP Manager still PLACEHOLDER | P3 | After H2 |
| H6 | S1/S2 warning text stale | P3 | Cleanup slice |

**Critical path**: H2 (transport) must be resolved before any real federation can occur. Auth enforcement (Slice 6) and registry persistence (Slice 7) are prerequisites satisfied.

---

## 6. Updated WSP 15 Next-Step Order

Based on WSP 15 prioritization:

| Priority | Next Slice | Description | Rationale |
|----------|------------|-------------|-----------|
| **P1** | MCPA8 | Real transport (WebSocket/SSE) | No federation possible without port binding |
| P2 | MCPA9 | Key rotation/revocation API | Security hygiene for production |
| P2 | MCPA10 | Real backend connections | Replace hardcoded tool bodies |
| P3 | MCPA11 | MCP Manager status flip | Depends on H2/H4 |
| P3 | MCPA12 | S1/S2 warning cleanup | Low priority cleanup |

---

## 7. Test Coverage Verification

MCPA7 added 7 focused persistence tests:

| Test | Purpose | Status |
|------|---------|--------|
| `test_registration_persists_to_file` | Verifies disk write | ✅ PASS |
| `test_registration_survives_restart` | Verifies load on init | ✅ PASS |
| `test_corrupt_registry_starts_empty` | Verifies graceful degradation | ✅ PASS |
| `test_missing_registry_starts_empty` | Verifies no-file handling | ✅ PASS |
| `test_env_var_override` | Verifies path override | ✅ PASS |
| `test_reregistration_replaces_existing` | Verifies duplicate handling | ✅ PASS |
| `test_atomic_write_creates_parent_dirs` | Verifies directory creation | ✅ PASS |

Total test suite: **74 tests passing** (67 existing + 7 new).

---

## 8. Truth Boundary Update

MCPA6C declared:
```
registry_persistence: NONE (lost on restart)
```

MCPA7B confirms update to:
```
registry_persistence: LOCAL_JSON (survives restart)
```

This declaration is **truthful** — it matches the runtime state observed in:
- `PLACEHOLDER_BANNER` at `server.py:67-83`
- `README.md` status block
- Test assertion at `test_server_holo_search.py:54`

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA7 pAVS registry persistence LOCAL_JSON PAVS_REGISTRY_PATH RegistryStore re-audit" --limit 5
```

**Top CODE hit**: `modules/infrastructure/pavs_mcp/src/server.py`
**Top DOCS hit**: `modules/infrastructure/pavs_mcp/INTERFACE.md`

---

## WSP 97 Applied

Three truth boundaries verified by this re-audit:

1. **PERSISTENCE_CONFIRMED ≠ PRODUCTION_READY.** Registry persistence is confirmed, but transport and backends remain placeholder. The verdict explicitly separates these concerns.

2. **LOCAL_JSON declaration is truthful.** Every surface that declares persistence status (banner, README, tests) now says `LOCAL_JSON` and the runtime behavior matches.

3. **No secrets committed.** The `api_key` field in persisted registrations is server-generated for local testing, stored in user-local directory, not in the repository.

WSP 50: All cited file:lines verified against `origin/main` post-#528 merge.
WSP 15: P1 transport identified as next critical-path blocker.
WSP 00: Identity locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA7B_PAVS_REGISTRY_PERSISTENCE_REAUDIT.md` (NEW)

No runtime code edits. No commits made.
