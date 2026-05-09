# MCPA6C — MCP `holo_search` Conformance Re-Audit (Post Slice 6)

**Slice**: `MCPA6C_MCP_CONFORMANCE_REAUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-09
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_15 → WSP_97 → WSP_50
**Anchor contract**: WSP 96 Annex A (`Canonical holo_search Contract`)
**Predecessor audit**: `docs/audits/mcp_system/MCPA6B_MCP_CONFORMANCE_REAUDIT.md`

---

## 1. Executive Verdict

### **CONFORMANT** (Contract Layer) / **NOT_PRODUCTION_READY** (Operational Layer)

All Annex A contract conformance checks pass across S1, S2, and S3. Slice 6 closed the federation auth/scope enforcement gap on S3. The system is **contract-conformant** but **not production-ready** due to in-memory registry, no real transport, and hardcoded tool bodies.

| Dimension | Verdict | Evidence |
|-----------|---------|----------|
| Annex A.2/A.3 envelope conformance | ✅ CONFORMANT | All field-level checks pass (see §3) |
| S3 API key validation | ✅ CONFORMANT | `_validate_api_key()` at `server.py:495-522` |
| S3 cross-tenant rejection | ✅ CONFORMANT | `_validate_scope()` at `server.py:523-558` |
| S3 bootstrap boundary | ✅ CONFORMANT | `BOOTSTRAP_TOOLS` at `server.py:116` |
| Registry persistence | ❌ NOT READY | In-memory `dict` at `server.py:131-132` |
| Real transport | ❌ NOT READY | `start()` does not bind a port at `server.py:648-660` |
| Real backends | ❌ NOT READY | Tool bodies return hardcoded data |

---

## 2. Preconditions Verified

Verified on `origin/main` at `2026-05-09`:

| Check | Result | Evidence |
|-------|--------|----------|
| PR #526 merged | ✅ | `22d6a4442 feat(pavs_mcp): enforce api key ownership for federated FoundUp scope (#526)` |
| `MISSING_API_KEY` marker | ✅ | `server.py:100`: `AUTH_ERROR_MISSING_API_KEY = "MISSING_API_KEY"` |
| `UNKNOWN_API_KEY` marker | ✅ | `server.py:103`: `AUTH_ERROR_UNKNOWN_API_KEY = "UNKNOWN_API_KEY"` |
| `CROSS_TENANT_VIOLATION` marker | ✅ | `server.py:106`: `AUTH_ERROR_CROSS_TENANT = "CROSS_TENANT_VIOLATION"` |
| `BASIC_AUTH_ENFORCEMENT` marker | ✅ | `README.md:3`: `STATUS: PLACEHOLDER_STUB with BASIC_AUTH_ENFORCEMENT` |

All preconditions satisfied. Audit proceeds.

---

## 3. Contract Conformance Matrix

Legend: ✅ conformant · ⚠️ partial · ❌ missing

### S1 — `foundups-mcp-p1/servers/holo_index/canonical_search.py`

| Annex A check | Verdict | Evidence |
|---------------|---------|----------|
| Tool name `holo_search` | ✅ | `server.py:holo_search` delegates to `canonical_search.canonical_holo_search` |
| Request: `query`, `limit`, `doc_type_filter` | ✅ | `canonical_search.py:264-266, 307-321, 359-365` |
| Request: `foundup_id`, `include_shared` | ✅ | `canonical_search.py:265-266, 119-121` |
| Envelope: `status`/`data`/`meta` | ✅ | `canonical_search.py:114-133` |
| Unified `hits[]` with `type` discriminator | ✅ | `canonical_search.py:188-231` |
| `meta.surface = "S1"`, `meta.tool = "holo_search"` | ✅ | `canonical_search.py:159, 180-181` |
| Federation warning when `foundup_id` supplied | ✅ | `canonical_search.py:354-355` — truthful "not yet enforced" |

**S1 score: 22/22 ✅** (unchanged from MCPA6B — S1 is external MCP adapter, not federation gateway)

### S2 — `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py`

| Annex A check | Verdict | Evidence |
|---------------|---------|----------|
| Tool name `holo_search` | ✅ | `holo_tools.py:121` |
| Request: `query`, `limit`, `doc_type_filter` | ✅ | `holo_tools.py:126-127, 196-216, 238-247` |
| Request: `foundup_id`, `include_shared` | ✅ | `holo_tools.py:128-129, 234-235` |
| Envelope: `status`/`data`/`meta` | ✅ | `holo_tools.py:140-149` |
| Unified `hits[]` with `type` discriminator | ✅ | `holo_tools.py:281-326` |
| `meta.surface = "S2"`, `meta.tool = "holo_search"` | ✅ | `holo_tools.py:144, 402-403` |
| Federation warning when `foundup_id` supplied | ✅ | `holo_tools.py:234-235` — truthful "not yet enforced" |

**S2 score: 22/22 ✅** (unchanged from MCPA6B — S2 is internal adapter, not federation gateway)

### S3 — `modules/infrastructure/pavs_mcp/src/server.py`

| Annex A check | Verdict | Evidence |
|---------------|---------|----------|
| Tool name `holo_search` | ✅ | `server.py:166` registered in `_tools` |
| `holo_search` returns `not_implemented` envelope | ✅ | `server.py:375-407` |
| `error.code = "NOT_IMPLEMENTED"` | ✅ | `server.py:394` |
| `error.delegate_to = "S2"` | ✅ | `server.py:400` |
| `data.hits = []` (no fabrication) | ✅ | `server.py:386-387` |
| `meta.implementation_status = "placeholder_stub"` | ✅ | `server.py:32, 70` |
| **API key validation (MCPA1 Slice 6)** | ✅ | `_validate_api_key()` at `server.py:495-522` |
| **Cross-tenant rejection (MCPA1 Slice 6)** | ✅ | `_validate_scope()` at `server.py:523-558` |
| **Bootstrap boundary (MCPA1 Slice 6)** | ✅ | `BOOTSTRAP_TOOLS = {"foundup_register"}` at `server.py:116` |
| **`meta.auth_enforced` truthful** | ✅ | `_build_auth_meta()` at `server.py:483-494` |

**S3 score: 21/21 ✅** (upgraded from 18/21 ⚠️ in MCPA6B — auth/scope now enforced)

---

## 4. Slice 6 Closure Verification

MCPA6B identified 5 remaining items deferred to Slice 6. Verification:

| Item | MCPA6B Status | MCPA6C Status | Evidence |
|------|---------------|---------------|----------|
| **D24**: Cross-tenant `foundup_id` enforcement | ⚠️ deferred | ✅ CLOSED | `_validate_scope()` at `server.py:523-558` rejects mismatches with `CROSS_TENANT_VIOLATION` |
| **R1**: `api_key` validation | ⚠️ deferred | ✅ CLOSED | `_validate_api_key()` at `server.py:495-522` rejects missing/unknown keys |
| **R2**: Real WebSocket transport | ⚠️ deferred | ⚠️ DEFERRED | `start()` still does not bind — explicitly deferred to Slice 7+ |
| **R6**: Persistent registry | ⚠️ deferred | ⚠️ DEFERRED | `_api_key_to_foundup: dict` is in-memory — explicitly deferred to Slice 7+ |
| S1/S2 `foundup_id` enforcement | ⚠️ deferred | ⚠️ OUT OF SCOPE | S1/S2 are read-only search adapters, not federation gateways; enforcement on these surfaces was never in scope for Slice 6 |

**Slice 6 scope completed**: D24 and R1 closed. R2 and R6 explicitly documented as deferred.

### New Test Coverage

S3 test suite grew from 43 tests (MCPA6B) to **54 tests** (MCPA6C):

- `test_protected_tool_rejects_missing_api_key`
- `test_protected_tool_rejects_unknown_api_key`
- `test_registered_api_key_accepted`
- `test_cross_tenant_foundup_id_rejected`
- `test_matching_foundup_id_accepted`
- `test_foundup_register_accepts_no_api_key`
- `test_meta_auth_enforced_true_for_protected_tools`
- `test_meta_auth_enforced_false_for_bootstrap_tools`
- `test_all_protected_tools_reject_missing_api_key` (parametrized)
- + others

---

## 5. Production Readiness Boundary

**Contract conformance ≠ production readiness.** This distinction is critical.

| Aspect | Contract Status | Production Status |
|--------|-----------------|-------------------|
| Envelope shape | ✅ Conformant | ✅ Ready |
| API key validation | ✅ Conformant | ⚠️ In-memory only |
| Cross-tenant rejection | ✅ Conformant | ⚠️ In-memory only |
| Bootstrap registration | ✅ Conformant | ⚠️ In-memory only |
| Transport binding | n/a (not in contract) | ❌ Not implemented |
| Registry persistence | n/a (not in contract) | ❌ Not implemented |
| Real backend connections | n/a (not in contract) | ❌ Not implemented |
| Key rotation/revocation | n/a (not in contract) | ❌ Not implemented |

**Truth boundary** (README.md, PLACEHOLDER_BANNER):
- `implementation_status: placeholder_stub`
- `auth_enforcement: BASIC (api_key validated, in-memory)`
- `registry_persistence: NONE (lost on restart)`
- `server_transport: NONE (start() does not bind a port)`

These declarations are **truthful** — they match the runtime state.

---

## 6. Remaining Hardening Backlog

Tracked for MCPA1 Slice 7+:

| ID | Item | File:Line | Priority |
|----|------|-----------|----------|
| H1 | Persistent FoundUp registry (SQLite) | `server.py:131-132` → migrate | P1 |
| H2 | Real WebSocket/SSE transport | `server.py:648-660` → bind | P1 |
| H3 | Key rotation/revocation API | `server.py` → new tool | P2 |
| H4 | Real backend connections | `server.py:163-308` → connect | P2 |
| H5 | MCP Manager status flip to `RUNTIME_LIVE` | `mcp_manager.py:175-190` | P3 |
| H6 | S1/S2 federation warning deprecation | `canonical_search.py:59-63`, `holo_tools.py:99-103` | P3 |

**Note on H6**: S1 and S2 still emit "tenant scoping not yet enforced at {surface} (deferred to MCPA1 Slice 6)" warnings when `foundup_id` is supplied. This is technically stale now that S3 has enforcement, but S1/S2 themselves are not federation gateways — they don't enforce tenant scope on search queries (by design). A future slice should clarify the warning text or remove it if the surfaces are not expected to enforce scope.

---

## 7. Final Decision

### **CONFORMANT** (Contract)

All WSP 96 Annex A.2/A.3 field-level conformance checks pass on all three surfaces. The federation auth/scope enforcement gap on S3 is closed by Slice 6. The system meets the canonical `holo_search` contract.

### **NOT_PRODUCTION_READY** (Operational)

Production deployment remains blocked by:
1. In-memory registry (lost on restart)
2. No real transport (start() does not bind)
3. No real backends (tools return hardcoded data)

These are **operational hardening** items, not **contract conformance** items. The distinction is intentional per WSP 97 truth boundaries.

---

## Acceptance Criteria Verification

- ✓ Executive verdict distinguishes contract conformance from production readiness (§1, §5)
- ✓ Preconditions verified with grep evidence (§2)
- ✓ Contract conformance matrix with file:line citations (§3)
- ✓ Slice 6 closure verification with specific method citations (§4)
- ✓ Production readiness boundary clearly delineated (§5)
- ✓ Remaining hardening backlog with file:line references (§6)
- ✓ No overclaim — truthful declarations match runtime state

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA6C Slice 6 MCP conformance api key cross tenant BASIC_AUTH_ENFORCEMENT" --limit 5
```

**Top WSP hit**: `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md`
**Top DOCS hit**: `docs/mcp/WSP_UPDATE_RECOMMENDATIONS_MCP_FEDERATION.md`

---

## WSP 97 Applied

Three truth boundaries enforced by this re-audit:

1. **CONFORMANT ≠ PRODUCTION_READY.** The verdict explicitly separates contract conformance (envelope shapes, error codes, auth validation) from operational readiness (persistence, transport, backends). Neither is overclaimed.

2. **Slice 6 closure verified by method signature, not hand-wave.** Each closed item (D24, R1) cites the specific method name and line numbers. Deferred items (R2, R6) are explicitly marked as such with tracked remediation.

3. **In-memory limitation is declared at every layer.** README, PLACEHOLDER_BANNER, and this audit all state `registry_persistence: NONE`. No claim of durability.

WSP 50: All cited file:lines verified against `origin/main` post-#526 merge.
WSP 15: P0 narrow audit scope respected — single doc, no runtime edits.
WSP 00: Identity locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA6C_MCP_CONFORMANCE_REAUDIT.md` (NEW)

No runtime code edits. No commits made.
