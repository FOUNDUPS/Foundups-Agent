# MCPA6 — MCP `holo_search` Conformance Audit (Phase 1)

**Slice**: `MCPA6_MCP_CONFORMANCE_AUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-08
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_15 → WSP_97 → WSP_50
**Anchor contract**: WSP 96 Annex A (`Canonical holo_search Contract`, MCPA3, PR #517)
**Companion audits**: `docs/audits/mcp_system/MCPA1_MCP_SURFACE_AUTHORITY_AUDIT.md`

---

## HoloIndex Research

```bash
python holo_index.py --search "MCP conformance holo_search WSP 96 Annex A S1 S2 S3 request response envelope" --limit 5
```

**Top WSP hit**: `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md`
**Top CODE hit**: `modules/gamification/_archived_duplicates_per_wsp3/mcp_whack_server.py` (false positive — archived demo, not in scope)
**Top DOCS hit**: `docs/mcp/WSP_UPDATE_RECOMMENDATIONS_MCP_FEDERATION.md`

The HoloIndex retrieval anchored the audit against WSP 96. The on-main version of WSP 96 does NOT yet contain Annex A (see Truthful State below); the canonical contract used in this audit is the Annex A content authored in MCPA3 PR #517.

---

## Truthful State (WSP 97 / WSP 50 verification)

WSP 50 verification of the on-main repo at audit time:

| Artifact | Expected (post-MCPA series) | On-main state | Source |
|----------|------------------------------|----------------|--------|
| `WSP_framework/src/WSP_96_*.md` | 504 lines (with Annex A) | **278 lines (no Annex A)** | `wc -l` |
| `modules/infrastructure/pavs_mcp/src/server.py` | Has `IMPLEMENTATION_STATUS` constant | **375 lines, no constant** | `grep IMPLEMENTATION_STATUS` returns 0 |
| `modules/infrastructure/mcp_manager/src/mcp_manager.py` | Has `KnownSurface` class | **1289 lines, no class** | `grep KnownSurface` returns 0 |
| `docs/audits/mcp_system/MCPA1_*.md` | tracked | gitignored on main (MCPA2 not merged) | `git check-ignore` |

This audit therefore reports against:
- **The canonical Annex A spec** authored in MCPA3 PR #517 (treated as the contract).
- **The on-main runtime state** of S1, S2, S3 (treated as "what actually exists today").

The drift table below is the gap between those two truths. When MCPA3, MCPA4, MCPA5 land on main, several drift items will be partially closed without further work.

---

## 1. Canonical Contract Checklist (Annex A.2 + A.3)

### A.2 Request schema (per Annex A)

| Field | Required | Default | Type | Notes |
|-------|----------|---------|------|-------|
| `query` | yes | — | string | non-empty; surfaces MUST reject empty |
| `limit` | no | 10 | int | range 1..50 |
| `doc_type_filter` | no | `all` | enum | `all`/`code`/`wsp`/`test`/`skill`/`docs`/`knowledge` |
| `foundup_id` | no | null | string | federation tenant scope |
| `include_shared` | no | true | bool | only meaningful when `foundup_id` set |

### A.3 Response envelope (per Annex A)

```
{
  "status": "ok | error | not_implemented",
  "data": {
    "query": ..., "doc_type_filter": ..., "foundup_id": ...,
    "hits": [
      { "type", "path", "title?", "preview", "relevance",
        "line_num?", "summary?" }
    ],
    "hit_count": int,
    "metadata": { "retrieval_mode", "engine_version",
                  "collections_searched", "warnings" }
  },
  "meta": {
    "timestamp": ISO8601,
    "source": "holoindex | fallback",
    "tool": "holo_search",
    "surface": "S1|S2|S3",
    "confidence": float
  }
}
```

Required relevance rule: ChromaDB-backed surfaces use `1/(1+distance)`; lexical fallback caps at `0.6`; surfaces that cannot compute similarity must omit the field.

Required empty-query rule: `status="error"`, `error.code="EMPTY_QUERY"`.

---

## 2. Surface-by-Surface Conformance Matrix

Legend: ✅ conformant · ⚠️ partial · ❌ missing/non-conformant · n/a not applicable

### S1 — `foundups-mcp-p1/servers/holo_index/server.py:24-75`

Tool name: **`semantic_code_search`** (not `holo_search`).

| Annex A check | S1 reality | Verdict |
|---------------|------------|---------|
| Tool name `holo_search` | tool is `semantic_code_search` (`server.py:24`) | ❌ |
| Request: `query` | accepts `query` param | ✅ |
| Request: `limit` (1..50, default 10) | accepts `limit`, default `5` (not 10), no upper-bound clamp | ⚠️ |
| Request: `doc_type_filter` enum | accepts `file_types: list` instead — different field, different shape (`server.py:24`) | ❌ |
| Request: `foundup_id` | not accepted | ❌ |
| Request: `include_shared` | not accepted | ❌ |
| Empty-query rejection | no validation; falls into try/except (`server.py:67-75`) | ❌ |
| Envelope: `status`/`data`/`meta` | returns flat dict; no top-level `status` (`server.py:53-66`) | ❌ |
| Hits: unified `hits[]` array | splits into `code_results[]` + `wsp_results[]` (`server.py:55-56`) | ❌ |
| Hit fields: `type`/`path`/`preview`/`relevance` | uses `path`/`snippet`/`relevance` per side; no `type` discriminator | ❌ |
| Relevance scale 0..1 | uses raw `distance` (line 40, 49) — not transformed to similarity | ❌ |
| Fallback cap at 0.6 | no fallback path | n/a |
| `meta.source = holoindex|fallback` | absent; emits `quantum_coherence`/`bell_state_alignment` instead (`server.py:58-59`) | ❌ |
| `meta.surface = "S1"` | absent | ❌ |
| `meta.tool` | absent | ❌ |
| Truth/implementation_status | absent | ❌ |
| Authority role (Annex A.1: canonical external) | runtime backed by real `HoloIndex().search` ✓ | ✅ |

### S2 — `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py:80-199`

Tool name: **`holo_search`** ✅.

| Annex A check | S2 reality | Verdict |
|---------------|------------|---------|
| Tool name `holo_search` | matches | ✅ |
| Request: `query` | accepts; rejects empty with `error_response("Query cannot be empty")` (`holo_tools.py:98-99`) | ✅ |
| Request: `limit` | accepts as `top_k` (default 10) — name drift only | ⚠️ |
| Request: `doc_type_filter` | accepts as `scope` instead — name drift; same enum semantics (`holo_tools.py:83`) | ⚠️ |
| Request: `foundup_id` | not accepted | ❌ |
| Request: `include_shared` | not accepted | ❌ |
| Empty-query rejection with `EMPTY_QUERY` code | rejects but returns generic `error_response` (no code field) | ⚠️ |
| Envelope: `status`/`data`/`meta` | uses `ok_response` wrapper that produces `{status, data, meta}` (`holo_tools.py:149-160`) | ✅ |
| Hits: unified `hits[]` with `type` | already unified across `code|wsp|test|skill` (`holo_tools.py:111-143`) | ✅ |
| Hit fields | `type`/`path`/`relevance`/`preview`/`title`/`summary` present (`holo_tools.py:113-128`) | ✅ |
| Relevance scale 0..1 | `_parse_similarity` converts "85.1%" → 0.851 (`holo_tools.py:651-660`) | ✅ |
| Fallback cap at 0.6 | fallback hard-codes `relevance: 0.5` (`holo_tools.py:184`) — under cap by accident, not policy | ⚠️ |
| `meta.source = holoindex|fallback` | sets `source="holoindex"` or `"fallback"` (`holo_tools.py:158, 196`) | ✅ |
| `meta.surface = "S2"` | absent | ❌ |
| `meta.tool = "holo_search"` | sets `tool="holo_search"` (`holo_tools.py:159, 198`) | ✅ |
| `metadata.retrieval_mode` | passed through from `results.get("metadata", {})` (`holo_tools.py:155`) | ✅ |
| Truth/implementation_status | absent | ❌ |
| Authority role (Annex A.1: canonical internal) | runtime backed by real engine + ripgrep fallback | ✅ |

### S3 — `modules/infrastructure/pavs_mcp/src/server.py:243-273` *(on-main, pre-MCPA4)*

Tool name: **`holo_search`** ✅.

| Annex A check | S3 reality | Verdict |
|---------------|------------|---------|
| Tool name `holo_search` | matches | ✅ |
| Request: `query` | accepts (`server.py:243-247`) | ✅ |
| Request: `limit` | accepts (default 10) | ✅ |
| Request: `doc_type_filter` | accepts as `domain: Optional[str]` instead — different name, different default | ❌ |
| Request: `foundup_id` | not accepted | ❌ |
| Request: `include_shared` | not accepted | ❌ |
| Empty-query rejection | no validation; returns hardcoded match regardless | ❌ |
| Envelope: `status`/`data`/`meta` | returns flat `{matches: [...]}` (`server.py:264-273`) | ❌ |
| Hits: unified `hits[]` | uses `matches[]` not `hits[]`; different keys (`file`/`line`/`content`/`score`) | ❌ |
| Relevance scale | hardcoded `score: 0.95` (line 271) — fabricated, not measured | ❌ |
| Fallback cap | n/a (no real backend at all) | ❌ |
| `meta.source` | absent | ❌ |
| `meta.surface = "S3"` | absent | ❌ |
| `meta.tool` | absent | ❌ |
| `not_implemented` envelope (Annex A.3 mandate for placeholder surfaces) | not emitted; returns fake data masquerading as real | ❌ |
| Truth/implementation_status | absent | ❌ |
| Authority role: `no_authority` until federation lands | code does not declare this; README claims federation role (`pavs_mcp/README.md:9-27`, `:117`) | ❌ |

S3 also: `handle_tool_call` accepts `api_key` but does not validate (`server.py:329` `# TODO: Implement proper auth`); `start()` does not bind a port (`server.py:354, 362`).

### Summary table

| Surface | Annex A checks passed | Annex A checks failed | Authority alignment |
|---------|------------------------|------------------------|---------------------|
| S1 | 2/16 | 13/16 (1 n/a) | ✅ canonical external (real backend) |
| S2 | 11/16 | 3/16 (3 partial) | ✅ canonical internal (real backend) |
| S3 | 3/16 | 13/16 | ❌ claims federation but is placeholder stub |

---

## 3. Drift Table (field-level, file:line evidence)

| ID | Surface | Drift | Annex A reference | Evidence (file:line) |
|----|---------|-------|--------------------|----------------------|
| D1 | S1 | Tool name is `semantic_code_search`, not `holo_search` | A.2 — tool MUST be named `holo_search` | `foundups-mcp-p1/servers/holo_index/server.py:24` |
| D2 | S1 | Returns flat dict, not `{status, data, meta}` envelope | A.3 envelope | `server.py:53-66` |
| D3 | S1 | Hits split into `code_results`/`wsp_results` arrays instead of unified `hits[]` with `type` | A.3 hit shape | `server.py:55-56` |
| D4 | S1 | Uses `file_types: list` instead of `doc_type_filter: str` enum | A.2 — `doc_type_filter` | `server.py:24` |
| D5 | S1 | Relevance reports raw `distance`, not similarity in 0..1 | A.3 relevance scale rule | `server.py:40, 49` |
| D6 | S1 | Decoration fields `quantum_coherence`/`bell_state_alignment` not in canonical envelope | A.3 — meta MUST contain only specified fields (additions allowed inside `data.metadata` if explicit) | `server.py:58-59` |
| D7 | S1 | No `foundup_id` request field | A.2 — `foundup_id` (federation scope) | `server.py:24` (signature) |
| D8 | S1 | No `include_shared` request field | A.2 — `include_shared` | `server.py:24` (signature) |
| D9 | S1 | No empty-query rejection | A.2 — surfaces MUST reject empty queries | `server.py:24-75` (no validation block) |
| D10 | S1 | Default limit is 5, not 10; no upper-bound cap | A.2 — default 10, range 1..50 | `server.py:24` |
| D11 | S1 | Missing `meta.surface`, `meta.tool`, `meta.source` | A.3 envelope `meta` block | `server.py:53-66` |
| D12 | S2 | Request field `scope` instead of `doc_type_filter` | A.2 field naming | `holo_tools.py:83` |
| D13 | S2 | Request field `top_k` instead of `limit` | A.2 field naming | `holo_tools.py:84` |
| D14 | S2 | No `foundup_id` request field | A.2 | `holo_tools.py:80-85` |
| D15 | S2 | No `include_shared` request field | A.2 | `holo_tools.py:80-85` |
| D16 | S2 | Empty-query error lacks `error.code = "EMPTY_QUERY"` | A.3 error envelope | `holo_tools.py:98-99` |
| D17 | S2 | Fallback relevance hardcoded to 0.5 (under cap by accident, not policy) | A.3 fallback cap rule | `holo_tools.py:184` |
| D18 | S2 | Missing `meta.surface = "S2"` | A.3 meta.surface | `holo_tools.py:149-160, 188-198` |
| D19 | S2, S3 | No `data.foundup_id` echo in response | A.3 envelope | `holo_tools.py:149-160`; `pavs_mcp/server.py:264-273` |
| D20 | S3 | Returns hardcoded fake data instead of `not_implemented` envelope | A.3 — placeholder surfaces MUST emit `not_implemented` | `pavs_mcp/server.py:264-273` |
| D21 | S3 | No envelope at all — flat `{matches[]}` | A.3 envelope | `pavs_mcp/server.py:264-273` |
| D22 | S3 | `score: 0.95` is fabricated, not measured — violates "surfaces that cannot compute similarity MUST omit the field" | A.3 relevance rule | `pavs_mcp/server.py:271` |
| D23 | S3 | Request field is `domain`, not `doc_type_filter` | A.2 | `pavs_mcp/server.py:243-247` |
| D24 | S3 | No `foundup_id`, no `include_shared` | A.2 | `pavs_mcp/server.py:243-247` |
| D25 | S3 | No empty-query rejection | A.2 | `pavs_mcp/server.py:243-273` |
| D26 | S3 | No truth flag / implementation_status declared on responses | A.5 C3 (truthful meta) | entire `holo_search` body |
| D27 | S3 | README claims `WSP 71: Security - API key auth, encrypted transport` while `handle_tool_call` ignores `api_key` | A.5 C6 (README must match runtime) | `pavs_mcp/README.md:117` vs `pavs_mcp/server.py:329` |
| D28 | S3 | README claims endpoint `wss://pavs.foundups.com/mcp` while `start()` does not bind | A.5 C6 | `pavs_mcp/README.md:108` vs `pavs_mcp/server.py:354, 362` |

**Drift count by surface**: S1 = 11, S2 = 7, S3 = 11 (with 2 cross-surface — D19 spans S2+S3).

---

## 4. Severity + WSP 15 MPS Score per Drift Item

WSP 15 axes: **C** = Complexity (1=trivial, 5=highly complex), **I** = Importance (1=cosmetic, 5=critical), **D** = Deferability (1=must do now, 5=can defer indefinitely), **Im** = Impact (1=narrow, 5=systemic). MPS = C+I+D+Im (lower D + higher I/Im = higher priority).

Top items shown; full table below.

| ID | Sev | C | I | D | Im | MPS | Priority bucket |
|----|-----|---|---|---|----|-----|------------------|
| D20 | **Critical** — S3 fakes data while claiming federation auth | 1 | 5 | 1 | 4 | 11 | P0 |
| D26 | **Critical** — S3 has no truth flag (clients cannot detect fake) | 1 | 5 | 1 | 4 | 11 | P0 |
| D27 | **Critical** — S3 README/runtime claim divergence on auth | 1 | 5 | 1 | 4 | 11 | P0 |
| D28 | **Critical** — S3 README/runtime claim divergence on transport | 1 | 5 | 1 | 4 | 11 | P0 |
| D2 | **High** — S1 envelope drift (no status/data/meta) | 2 | 4 | 2 | 4 | 12 | P0/P1 |
| D3 | **High** — S1 hits split, not unified | 2 | 4 | 2 | 4 | 12 | P0/P1 |
| D7,D8 | **High** — S1 missing federation request fields | 2 | 5 | 3 | 5 | 15 | P1 (depends on auth slice) |
| D14,D15 | **High** — S2 missing federation request fields | 2 | 5 | 3 | 5 | 15 | P1 (depends on auth slice) |
| D11 | **High** — S1 missing meta.surface/meta.tool/meta.source | 1 | 4 | 2 | 3 | 10 | P0 |
| D5 | **Medium** — S1 reports raw `distance` not 0..1 similarity | 1 | 3 | 2 | 3 | 9 | P0 |
| D17 | **Medium** — S2 fallback cap is incidental, not enforced | 1 | 3 | 3 | 2 | 9 | P1 |
| D18 | **Medium** — S2 missing `meta.surface` | 1 | 3 | 2 | 2 | 8 | P0 |
| D21 | **High** — S3 has no envelope at all | 1 | 5 | 1 | 4 | 11 | P0 |
| D22 | **High** — S3 fabricates `score: 0.95` | 1 | 5 | 1 | 3 | 10 | P0 |
| D1 | **High** — S1 wrong tool name | 1 | 4 | 3 | 4 | 12 | P1 (breaking change for callers) |
| D4 | **Medium** — S1 `file_types` vs `doc_type_filter` | 1 | 3 | 3 | 3 | 10 | P1 |
| D6 | **Low** — S1 quantum/bell-state decoration fields | 1 | 2 | 4 | 1 | 8 | P2 |
| D9, D25 | **Medium** — empty-query rejection missing | 1 | 3 | 2 | 2 | 8 | P0 |
| D10 | **Medium** — S1 default limit / no cap | 1 | 3 | 3 | 2 | 9 | P1 |
| D12, D13 | **Low** — S2 field renames | 1 | 2 | 3 | 1 | 7 | P2 |
| D16 | **Low** — S2 missing `error.code` | 1 | 2 | 3 | 2 | 8 | P1 |
| D19 | **Low** — S2/S3 no `data.foundup_id` echo | 1 | 2 | 3 | 1 | 7 | P2 (depends on D7-D15) |
| D23 | **Medium** — S3 `domain` vs `doc_type_filter` | 1 | 3 | 1 | 2 | 7 | P0 (covered by D20 fix) |
| D24 | **Medium** — S3 missing federation fields | 1 | 3 | 3 | 2 | 9 | P1 (covered by Slice 6) |

**Top-5 by priority** (lowest D, highest I/Im):

1. **D20** (S3 fake data) — Critical, P0, MPS=11. Already partially addressed by MCPA4 (truth flag) and fully addressed by MCPA1 Slice 4 (delegate or `not_implemented`).
2. **D26** (S3 no truth flag) — Critical, P0, MPS=11. Addressed by MCPA4 (`implementation_status: "placeholder_stub"` in every response).
3. **D27** (S3 auth claim drift) — Critical, P0, MPS=11. Addressed by MCPA4 (README banner, runtime banner, `meta.auth_enforced=False`).
4. **D28** (S3 endpoint claim drift) — Critical, P0, MPS=11. Addressed by MCPA4 (README qualifier, startup banner).
5. **D2 + D3** (S1 envelope and hit-shape drift) — High, P0/P1, MPS=12 each. NOT yet scheduled — requires a new slice (see Slice S6.1 below).

---

## 5. Minimal Fix Plan

The plan is ordered by trunk-blocker first. Slices already in flight (MCPA3, MCPA4, MCPA5) close many drift items on merge — those are listed first as "merge gates" before any new work is started.

### Merge Gate 0 — Land MCPA3 / MCPA4 / MCPA5 PRs already in flight

Closes (or partially closes): D17 (S2 fallback by intentional cap once Annex A.3 is canonical on main), D26, D27, D28 (S3 truth flag + README/runtime alignment via MCPA4), D26 + D11 in part via MCPA5 (manager surfaces truth status). No new work; these PRs already exist.

**Acceptance**: `WSP_96` on main contains Annex A; `pavs_mcp/server.py` has `IMPLEMENTATION_STATUS = "placeholder_stub"` and per-response `meta.implementation_status`; `mcp_manager.py` has `KnownSurface` + `discover_all_surfaces`.

### Slice S6.1 (Trunk after Gate 0) — `MCPA1_SLICE_4_S3_NOT_IMPLEMENTED_ENVELOPE_PHASE1`

Already tracked in MCPA1 remediation plan. Switch S3's `holo_search` (and other tools) from hardcoded data to either delegate to S2 or return the `not_implemented` envelope from Annex A.3.

- **Files**: `modules/infrastructure/pavs_mcp/src/server.py:243-273` (and same pattern for other tool bodies).
- **Closes**: D20, D21, D22.
- **MPS**: C=2, I=5, D=1, Im=4 → 12. P0.
- **Acceptance**: S3 `holo_search` returns `{"status": "not_implemented", "error": {"code": "NOT_IMPLEMENTED", "delegate_to": "S2"}, "meta": {...}}`. No fake `matches[]` array.

### Slice S6.2 — `S1_ANNEX_A_ENVELOPE_ADAPTER_PHASE1`

Bring S1's response shape into Annex A conformance. This is the single largest drift after Gate 0.

- **Files**: `foundups-mcp-p1/servers/holo_index/server.py:24-75` only.
- **Changes**:
  - Rename tool `semantic_code_search` → `holo_search` (or add `holo_search` as a new tool that delegates and mark old name deprecated).
  - Wrap response in `{status, data, meta}`.
  - Unify hits into `hits[]` with `type` discriminator.
  - Map `file_types` → `doc_type_filter`.
  - Convert raw `distance` → `1/(1+distance)` similarity per Annex A.3.
  - Add `meta.source`, `meta.surface = "S1"`, `meta.tool`.
  - Move `quantum_coherence`/`bell_state_alignment` into `data.metadata` under explicit keys (or drop).
  - Default `limit = 10`, clamp 1..50.
  - Reject empty queries with `error.code = "EMPTY_QUERY"`.
- **Closes**: D1, D2, D3, D4, D5, D6, D9, D10, D11.
- **MPS**: C=3, I=4, D=2, Im=4 → 13. P0/P1 (depends on whether external clients are pinned to old shape — investigate first).
- **Acceptance**: S1 `holo_search` (new name) returns Annex A envelope; existing `semantic_code_search` either deprecated with shim or removed after caller audit.

### Slice S6.3 — `S2_ANNEX_A_RENAME_AND_META_PHASE1`

S2 is closest to canonical; this is the smallest viable conformance slice.

- **Files**: `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py:80-199` only.
- **Changes**:
  - Rename request field `scope` → `doc_type_filter` (keep `scope` as alias for back-compat, deprecation warning).
  - Rename request field `top_k` → `limit` (alias same way).
  - Add `meta.surface = "S2"` to both happy-path and error-path responses.
  - Replace hardcoded fallback `relevance: 0.5` with Annex A's `min(parsed_relevance, 0.6)` cap rule.
  - Add `error.code = "EMPTY_QUERY"` to empty-query rejection at line 98-99.
- **Closes**: D12, D13, D16, D17, D18.
- **MPS**: C=1, I=3, D=2, Im=2 → 8. P0.
- **Acceptance**: existing tests still pass; new fields surfaced; aliases keep old callers working.

### Slice S6.4 — `S1_S2_FOUNDUP_ID_REQUEST_FIELDS_PHASE1`

Add `foundup_id` and `include_shared` request fields to S1 and S2. **Important**: this is a contract addition, NOT auth enforcement. Auth lands later.

- **Files**: S1 server, S2 holo_tools.
- **Changes**:
  - Accept `foundup_id` and `include_shared` parameters (default `None` and `True`).
  - Echo back in `data.foundup_id`.
  - When `foundup_id` is provided, add `data.metadata.warnings: ["foundup_id received but tenant scoping not yet enforced"]` — truthful per WSP 97.
- **Closes**: D7, D8, D14, D15, D19, D24 (partially).
- **MPS**: C=2, I=5, D=3, Im=5 → 15. P1.
- **Acceptance**: signature accepts new fields; payload echoes them; warning surfaces honestly.

### Slice S6.5 — `MCPA1_SLICE_6_S3_FEDERATION_AUTH_AND_SCOPE_PHASE1`

Already tracked in MCPA1 plan. The federation auth/scope work for S3. Closes: residual D24 (when S3 actually enforces tenant scope) + the auth/transport issues outside this audit's scope.

- Defer per the slice's own boundary; this is multi-week work, not minimal-fix.

---

## 6. Final Decision

### **NON_CONFORMANT_BLOCKING**

S1 and S3 fail more than half of the Annex A conformance checks. S2 passes the majority but still has 3 outstanding drifts and lacks federation fields. No surface today emits the canonical envelope across the board. S3 in particular is actively misleading callers (returns fabricated similarity scores while claiming federation MCP role).

Live-flip readiness: **NO-GO** for federation rollout.
Internal-only usage of S2 from the foundups_mcp_bridge: acceptable today (it is the canonical internal adapter and is mostly conformant); operators must understand the field-name drift (`scope` vs `doc_type_filter`).
External MCP usage of S1: works for callers pinned to the current `semantic_code_search` shape, but does NOT satisfy Annex A.

The drift will partially close as MCPA3 (Annex A on main), MCPA4 (S3 truth flag), and MCPA5 (manager truthful discovery) merge — those PRs are the **Merge Gate 0** above. After that, Slices S6.1 → S6.3 in order are the minimum to upgrade conformance from `NON_CONFORMANT_BLOCKING` to `PARTIAL_CONFORMANCE`. Full `CONFORMANT` requires S6.4 + S6.5 (federation auth lane).

---

## Acceptance Criteria Verification

- ✓ Field-level conformance is explicit for S1/S2/S3 (Section 2 + Drift Table in Section 3).
- ✓ Every drift claim has file:line evidence (column 4 of Drift Table).
- ✓ Priority and order scored with WSP 15 MPS (Section 4).
- ✓ No vibe-coded assumptions — Truthful State block (top of audit) discloses on-main vs PR-only state of MCPA3/4/5.
- ✓ No runtime edits.

---

## WSP 97 Applied

Three truth boundaries enforced inside this audit:

1. **On-main vs PR-pending distinction**: the audit explicitly verified that MCPA3 (Annex A), MCPA4 (S3 truth flag), and MCPA5 (manager discovery) are NOT yet merged on main. The drift table reflects current on-main state. The "Merge Gate 0" line item is the truthful trunk: many drifts close on PR merge with no new code.
2. **Annex A as canonical contract**: even though Annex A is not yet on main, it is the canonical contract per 012's MCPA3 acceptance and PR #517. The audit treats it as the spec while noting the current main lacks it.
3. **No false conformance claims**: every ✅ in the conformance matrix is tied to specific lines in the surface source. No surface gets ✅ for "intent" or "documentation" — only for runtime behavior matching the spec.

WSP 50: every quoted file:line was confirmed against the working tree. WSP 15: MPS scored on all drift items. WSP 00: identity locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA6_MCP_CONFORMANCE_AUDIT.md` (NEW)

No runtime code edits. No commits made.
