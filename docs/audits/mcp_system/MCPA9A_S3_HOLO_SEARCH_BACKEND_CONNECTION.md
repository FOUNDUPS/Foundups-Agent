# MCPA9A — S3 holo_search Backend Connection

**Slice**: `MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION_PHASE1`
**Worker**: W1
**Date**: 2026-05-09
**Mode**: Implementation + audit
**WSP Lock**: WSP_00 → WSP_97 → WSP_15 → WSP_50 → WSP_96
**Predecessor audit**: `docs/audits/mcp_system/MCPA8B_PAVS_TRANSPORT_REAUDIT.md`

---

## 1. Executive Verdict

### **HOLO_SEARCH_BACKEND_CONNECTED**

MCPA9A successfully connected S3 `holo_search` to the real S2/HoloIndex backend. S3 now delegates all semantic search queries to S2 and returns real results with `meta.real_backend=true`.

| Dimension | Verdict | Evidence |
|-----------|---------|----------|
| S2 backend import | ✅ CONFIRMED | `from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import holo_search` at `server.py:68` |
| Delegation call | ✅ CONFIRMED | `_call_s2_holo_search()` at `server.py:49-86` |
| S3 surface marking | ✅ CONFIRMED | `meta.surface = "S3"` at `server.py:753` |
| Real backend flag | ✅ CONFIRMED | `meta.real_backend = True` at `server.py:754` |
| Delegation tracking | ✅ CONFIRMED | `meta.delegated_to = "S2"` at `server.py:755` |
| BACKEND_UNAVAILABLE error | ✅ CONFIRMED | Error envelope at `server.py:780-805` |
| Tests updated | ✅ CONFIRMED | `TestS2BackendDelegation` class with 21 tests |
| No fabrication | ✅ CONFIRMED | Real hits from HoloIndex, no hardcoded data |
| Other tools still placeholder | ✅ CONFIRMED | CABR, Gemma, Qwen, etc. unchanged |

---

## 2. Implementation Details

### 2.1 S2 Backend Adapter

Added `_call_s2_holo_search()` function at `server.py:49-86`:

```python
def _call_s2_holo_search(
    query: str,
    *,
    limit: int = 10,
    doc_type_filter: str = "all",
    foundup_id: Optional[str] = None,
    include_shared: bool = True,
) -> dict[str, Any]:
    """Call S2 holo_search backend and return the result."""
    from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import holo_search as s2_holo_search

    result = s2_holo_search(
        repo_root=_REPO_ROOT,
        query=query,
        limit=limit,
        doc_type_filter=doc_type_filter,
        foundup_id=foundup_id,
        include_shared=include_shared,
    )
    return result
```

### 2.2 holo_search Method Rewrite

The `holo_search` method at `server.py:691-805` now:

1. **Delegates to S2**: Calls `_call_s2_holo_search()` with all canonical parameters
2. **Adapts response**: Sets `meta.surface="S3"`, `meta.real_backend=True`, `meta.delegated_to="S2"`
3. **Handles errors**: Returns `BACKEND_UNAVAILABLE` error envelope if S2 fails
4. **Preserves domain alias**: Legacy `domain` parameter still works with deprecation warning

### 2.3 Error Handling

On S2 failure, returns:
```python
{
    "status": "error",
    "error": {
        "code": "BACKEND_UNAVAILABLE",
        "message": "S2 backend unavailable: <exception>"
    },
    "meta": {
        "surface": "S3",
        "real_backend": False,
    }
}
```

---

## 3. Test Coverage Update

### 3.1 Renamed Test Class

`TestNotImplementedEnvelope` → `TestS2BackendDelegation`

### 3.2 Updated Tests

| Test | Old Assertion | New Assertion |
|------|---------------|---------------|
| `test_successful_delegation_returns_ok_status` | `status == "not_implemented"` | `status == "ok"` |
| `test_meta_carries_real_backend_flag` | `real_backend == False` | `real_backend == True` |
| `test_meta_indicates_delegation_to_s2` | N/A (new) | `delegated_to == "S2"` |
| `test_real_backend_may_return_hits` | `hits == []` | `hits` is list (may have results) |
| `test_successful_call_has_no_error_block` | `error.code == "NOT_IMPLEMENTED"` | No error on success |

### 3.3 Test Results

```
85 passed, 39 warnings in 26.57s
```

---

## 4. Banner & README Updates

### 4.1 PLACEHOLDER_BANNER

Updated from `REAL_TRANSPORT + PLACEHOLDER_BACKENDS` to:
```
pAVS MCP Server - REAL_TRANSPORT + PARTIAL_BACKENDS
--------------------------------------------------------------
  implementation_status : partial (holo_search real, others stub)
  holo_search           : REAL (delegates to S2/HoloIndex)
  other tools           : HARDCODED / FAKE (CABR, Gemma, Qwen, etc)
```

### 4.2 README.md

- Status updated to `REAL_TRANSPORT + PARTIAL_BACKENDS`
- Tool table updated: `holo_search` now shows **YES** for real backend
- Tracked remediation updated to MCPA10+

---

## 5. Closed Backlog Items

From MCPA8B §5 (Remaining Operational Blockers):

| ID | Item | MCPA8B Status | MCPA9A Status | Evidence |
|----|------|---------------|---------------|----------|
| **H4** (partial) | No real backends | ❌ NOT READY | ✅ CLOSED (holo_search) | S2 delegation at `server.py:743-774` |
| H3 | No key rotation | ❌ NOT READY | ❌ NOT READY | Not addressed this slice |
| H5 | MCP Manager status | ❌ NOT READY | ❌ NOT READY | Not addressed this slice |

---

## 6. Remaining Operational Blockers

| ID | Blocker | Severity | Next Slice |
|----|---------|----------|------------|
| H4 (remaining) | No real backends for CABR, Gemma, Qwen, etc. | P1 | MCPA9B+ |
| H3 | No key rotation/revocation | P2 | MCPA10 |
| H5 | MCP Manager status not updated | P3 | After H4 |

---

## 7. WSP 97 Truth Boundaries

Three truth boundaries verified by this implementation:

1. **S3 is not canonical owner, but now has real backend.** `meta.canonical_owner=false` but `meta.real_backend=true` — S3 delegates to S2, so results are real even though S3 doesn't own the implementation.

2. **PARTIAL_BACKENDS is truthful.** The banner and README accurately state that holo_search is real while other tools remain placeholders.

3. **BACKEND_UNAVAILABLE is honest.** When S2 fails, S3 returns an explicit error rather than falling back to fabricated data.

WSP 50: All cited file:lines verified against implementation.
WSP 15: Remaining backends (CABR, Gemma, Qwen) identified as next priority.
WSP 00: Identity locked as Worker W1 throughout.
WSP 96: Annex A.3 canonical envelope preserved through delegation.

---

## 8. Files Modified This Slice

| File | Change |
|------|--------|
| `modules/infrastructure/pavs_mcp/src/server.py` | Added S2 adapter, rewrote holo_search, updated banner |
| `modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py` | Updated tests for S2 delegation |
| `modules/infrastructure/pavs_mcp/README.md` | Updated status and tool table |
| `docs/audits/mcp_system/MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION.md` | NEW |

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA9A S3 holo_search S2 backend delegation real" --limit 5
```

**Top hit**: `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py` (S2 implementation)
**Audit chain**: MCPA7B → MCPA8B → MCPA9A (this document)

---

*Worker W1 | Slice MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION_PHASE1 | 2026-05-09*
