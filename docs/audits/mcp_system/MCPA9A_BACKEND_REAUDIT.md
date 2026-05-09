# MCPA9A — Backend Readiness Re-Audit

**Slice**: `MCPA9A_BACKEND_REAUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-09
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_97 → WSP_15 → WSP_50
**Predecessor audit**: `docs/audits/mcp_system/MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION.md`
**PR Verified**: `#535` merged at `1066cbeca`

---

## 1. Final Verdict

### **HOLO_SEARCH_BACKEND_CONFIRMED_PARTIAL_BACKEND_READY**

MCPA9A successfully connected S3 `holo_search` to the real S2/HoloIndex backend. pAVS MCP is now partially backend-ready. Non-search tools remain placeholders.

| Dimension | Status | Evidence |
|-----------|--------|----------|
| holo_search backend | ✅ REAL | `_call_s2_holo_search()` at `server.py:49-86` |
| S2 delegation | ✅ CONFIRMED | `meta.delegated_to = "S2"` at `server.py:754` |
| real_backend flag | ✅ CONFIRMED | `meta.real_backend = True` at `server.py:753` |
| BACKEND_UNAVAILABLE error | ✅ CONFIRMED | Error envelope at `server.py:778-802` |
| Other tools | ❌ PLACEHOLDER | CABR, Gemma, Qwen, FAM, Pattern still hardcoded |
| Production ready | ❌ NOT READY | Single tool real, others stub |

---

## 2. Precondition Verification

Verified on `origin/main` at commit `1066cbeca`:

| Check | Result | Evidence |
|-------|--------|----------|
| PR #535 merged | ✅ | `feat(pavs_mcp): connect S3 holo_search to real S2/HoloIndex backend (#535)` |
| `_call_s2_holo_search` | ✅ | `server.py:49` |
| `delegated_to` | ✅ | `server.py:754,760` |
| `real_backend` | ✅ | `server.py:753,759,802` |
| `BACKEND_UNAVAILABLE` | ✅ | `server.py:778,795` |
| MCPA9A audit doc | ✅ | `docs/audits/mcp_system/MCPA9A_S3_HOLO_SEARCH_BACKEND_CONNECTION.md` |

All preconditions satisfied. Audit proceeds.

---

## 3. What Changed After MCPA9A

### 3.1 Server Banner

Updated from `REAL_TRANSPORT + PLACEHOLDER_BACKENDS` to:

```
pAVS MCP Server - REAL_TRANSPORT + PARTIAL_BACKENDS
--------------------------------------------------------------
  implementation_status : partial (holo_search real, others stub)
  holo_search           : REAL (delegates to S2/HoloIndex)
  other tools           : HARDCODED / FAKE (CABR, Gemma, Qwen, etc)
```

### 3.2 holo_search Method

- **Before**: Returned `not_implemented` envelope with empty hits
- **After**: Delegates to S2 via `_call_s2_holo_search()`, returns real semantic search results

### 3.3 Response Envelope

- `meta.surface = "S3"` (unchanged)
- `meta.real_backend = True` (new)
- `meta.delegated_to = "S2"` (new)

### 3.4 Error Handling

- New `BACKEND_UNAVAILABLE` error code when S2 fails
- Explicit `real_backend = False` in error envelope

---

## 4. Backend Readiness Table

| Tool | Classification | Evidence | Next Action |
|------|----------------|----------|-------------|
| `holo_search` | **REAL_BACKEND** | Delegates to S2/HoloIndex at `server.py:742-774` | None (complete) |
| `cabr_validate` | PLACEHOLDER_BACKEND | Returns hardcoded `score=0.85` at `server.py:531` | Interface mismatch — `cabr_hooks.py` is for FoundUp health, not content V1/V2/V3 |
| `gemma_classify` | PLACEHOLDER_BACKEND | Returns hardcoded `confidence=0.92` at `server.py:558` | `gemma_rag_inference.py` exists but different interface |
| `qwen_plan` | PLACEHOLDER_BACKEND | Returns hardcoded 3-step plan at `server.py:584` | No direct callable backend |
| `fam_emit` | PLACEHOLDER_BACKEND | Computes hash but no emit at `server.py:620` | `fam_daemon.py` has emit capability — adapter needed |
| `pattern_recall` | PLACEHOLDER_BACKEND | Returns hardcoded `ptn_001` at `server.py:651` | `pattern_memory.py` has recall — adapter needed |
| `pattern_store` | PLACEHOLDER_BACKEND | Computes hash, no persist at `server.py:679` | `pattern_memory.py` has store — adapter needed |
| `foundup_register` | BOOTSTRAP_REGISTRY | JSON persistence working at `server.py:807-866` | Already functional |

---

## 5. Closed Blockers

From MCPA8B §5 (Remaining Operational Blockers):

| ID | Item | MCPA8B Status | MCPA9A Status | Evidence |
|----|------|---------------|---------------|----------|
| **H4** (partial) | No real backends | ❌ NOT READY | ✅ CLOSED (holo_search only) | S2 delegation at `server.py:742-774` |

---

## 6. Remaining Placeholder Tools

Tools still returning hardcoded data:

| Tool | Line | Hardcoded Return |
|------|------|------------------|
| `cabr_validate` | 531-538 | `score=0.85, passed=True` |
| `gemma_classify` | 558-563 | `confidence=0.92` |
| `qwen_plan` | 584-594 | 3-step plan, `optimal_time="2026-03-15T18:00:00Z"` |
| `fam_emit` | 620-630 | Hash-based event_id, no actual emit |
| `pattern_recall` | 651-660 | `ptn_001` hardcoded |
| `pattern_store` | 679-687 | Hash-based pattern_id, no persist |

---

## 7. Remaining Production Blockers

| ID | Blocker | Severity | Next Slice | Notes |
|----|---------|----------|------------|-------|
| **H4a** | cabr_validate placeholder | P2 | MCPA9B | Interface mismatch with `cabr_hooks.py` — may need new backend |
| **H4b** | gemma_classify placeholder | P2 | MCPA9C | `gemma_rag_inference.py` has different interface |
| **H4c** | qwen_plan placeholder | P2 | MCPA9D | No local callable backend |
| **H4d** | fam_emit placeholder | P1 | **MCPA9B** | `fam_daemon.py` is callable — adapter needed |
| **H4e** | pattern_recall placeholder | P1 | MCPA9E | `pattern_memory.py` is callable — adapter needed |
| **H4f** | pattern_store placeholder | P1 | MCPA9E | Same as pattern_recall |
| H3 | No key rotation | P2 | MCPA10 | Security hygiene |
| H5 | MCP Manager status | P3 | After H4 | Depends on backend completion |
| — | Production deployment | P0 | After all | No public endpoint |

---

## 8. Recommended Next Slice Order

Per WSP 15 prioritization, next slices ordered by implementation seam strength:

| Priority | Slice | Target | Rationale |
|----------|-------|--------|-----------|
| **P1** | **MCPA9B_FAM_EMIT_BACKEND_CONNECTION** | `fam_emit` | `fam_daemon.py` has working `emit_event()` — closest integration seam |
| P1 | MCPA9E_PATTERN_MEMORY_BACKEND_CONNECTION | `pattern_recall`, `pattern_store` | `pattern_memory.py` has working SQLite storage |
| P2 | MCPA9C_GEMMA_CLASSIFY_BACKEND_CONNECTION | `gemma_classify` | `gemma_rag_inference.py` exists but interface adaptation needed |
| P2 | MCPA9D_QWEN_PLAN_BACKEND_CONNECTION | `qwen_plan` | No direct backend — may need new implementation |
| P2 | MCPA9X_CABR_VALIDATE_BACKEND_CONNECTION | `cabr_validate` | Interface mismatch — `cabr_hooks.py` is FoundUp health, not content validation |

**Recommended next**: `MCPA9B_FAM_EMIT_BACKEND_CONNECTION_PHASE1`

Rationale: `fam_daemon.py` has a working `emit_event()` method with JSONL + SQLite dual-write. The pAVS `fam_emit` tool signature (foundup_id, event_type, payload) aligns well with the FAM daemon interface.

---

## 9. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| holo_search is real backend via S2/HoloIndex | ✅ TRUE | `_call_s2_holo_search()` imports and calls S2 backend |
| pAVS MCP is only partially backend-ready | ✅ TRUE | Banner says `PARTIAL_BACKENDS`, only 1 of 8 tools real |
| Non-search tools remain placeholders | ✅ TRUE | CABR, Gemma, Qwen, FAM, Pattern all return hardcoded data |
| No production readiness overclaim | ✅ TRUE | Banner says "Other backends remain PLACEHOLDERS" |
| `meta.real_backend=true` only for holo_search | ✅ TRUE | Other tools still use `_truth_meta()` with `real_backend=False` |

WSP 50: All cited file:lines verified against `origin/main` post-#535 merge.
WSP 15: FAM emit identified as strongest integration seam for next slice.
WSP 00: Identity locked as Worker W1 throughout.

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA9A S3 holo_search real_backend delegated_to S2 HoloIndex backend re-audit pAVS MCP" --limit 5
```

**Top CODE hit**: `modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py`
**Top DOCS hit**: `docs/audits/mcp_system/MCPA7B_PAVS_REGISTRY_PERSISTENCE_REAUDIT.md`

---

## Files Changed This Slice

- `docs/audits/mcp_system/MCPA9A_BACKEND_REAUDIT.md` (NEW)

No runtime code edits. No commits made.

---

*Worker W1 complete for MCPA9A_BACKEND_REAUDIT_PHASE1.*
