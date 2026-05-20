# MCP_FOUNDUP_SCOPE_CURRENT_ARCHITECTURE_REAUDIT_PHASE1

**Worker**: W9  
**Date**: 2026-05-20  
**Status**: READY_FOR_AUDIT  
**Context**: WSP 00 → WSP 97 → WSP 15 → WSP 50

---

## 1. Audit Objective

Re-audit the current MCP architecture to determine whether FoundUp scope params are still needed for `holo_search` surfaces, given the WSP 96 Annex A conformance work now on main.

**Background**: PR #513 (FoundUp scope params) was parked after 116 commits of drift caused non-trivial conflicts with newer WSP 96 Annex A / MCP architecture. This audit determines the current-main-compatible path forward.

---

## 2. Audit Scope

### Files to Inspect

| File | Purpose |
|------|---------|
| `modules/infrastructure/pavs_mcp/src/server.py` | MCP server routes |
| `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py` | HoloIndex MCP integration |
| `holo_index/core/search_engine.py` | Search engine with tenant context |
| `holo_index/core/holo_index.py` | HoloIndex main interface |

### Questions to Answer

1. Does current `pavs_mcp` server expose `foundup_id` params?
2. Does current `holo_tools.py` support tenant scoping?
3. What WSP 96 Annex A constraints apply to scope params?
4. Is `foundup_id` filtering still needed for Hermes/OpenClaw build isolation?
5. If needed, what is the current-main-compatible implementation path?

---

## 3. Expected Deliverables

1. Current architecture snapshot (what exists)
2. Gap analysis (what #513 intended vs what's needed now)
3. Implementation recommendation (adopt/defer/redesign)
4. If adopt: current-main-compatible spec
5. WSP 97 truth boundary labels

---

## 4. WSP 97 Constraints

- AUDIT_ONLY
- NO_RUNTIME_CHANGE
- NO_MCP_ROUTE_MODIFICATION
- NO_HOLOINDEX_CHANGE
- NO_CABR_READY
- NO_PAYOUT_READY
- NO_DAO_ACTIVATION

---

## 5. Related PRs

| PR | Status | Notes |
|----|--------|-------|
| #511 | CLOSED | Superseded by #513 |
| #512 | CLOSED | Superseded by #513 |
| #513 | PARKED | 116 commits behind, conflicts with WSP 96 Annex A |

---

*Audit template prepared by W10 under WSP 00 → WSP 97.*
