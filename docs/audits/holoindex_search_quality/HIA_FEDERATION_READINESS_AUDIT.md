# HIA_FEDERATION_READINESS_AUDIT_PHASE1

**Date**: 2026-05-06
**Slice**: HIA_FEDERATION_READINESS_AUDIT_PHASE1
**Status**: COMPLETE - AUDIT ONLY
**Author**: 0102 W1
**Base**: main @ `4d86b9fae` (PR #508 merged)
**WSP References**: WSP 97, WSP 103, WSP 104, WSP 15

---

## Purpose

Audit HoloIndex readiness for federated/external FoundUps after HIA Agentic
RAG baseline completion (27/27, 0 failures). Determine what must exist before
HoloIndex can safely support external repos, tenant-scoped retrieval, and
federation flows.

---

## 1. Preflight Results

### WSP_103/WSP_104 Retrieval

| Query | Expected | Bucket | Position | Verdict |
|-------|----------|--------|----------|---------|
| "WSP 103 FoundUp Federation pAVS MCP" | WSP_103 | wsps | TOP-1 | PASS |
| "WSP 104 FoundUp route namespace tenant isolation" | WSP_104 | wsps | TOP-1 | PASS |

### Federation Infrastructure Retrieval

| Query | Top Hits | Verdict |
|-------|----------|---------|
| Agent Workspace external repo gateway adapter | dae_gateway.py, WRE_GATEWAY_ADAPTER_DESIGN.md, FORK_PLAN.md | PASS |
| Trade FoundUp manifest routing | trade/INTERFACE.md, trade/README.md, WSP_104 | PASS |
| HoloIndex metadata filters foundup_id | holo_index.py, search_engine.py | PASS (returns core files, not filter implementations) |

---

## 2. Current HoloIndex Federation Capability

### What Exists

| Capability | Status | Evidence |
|-----------|--------|----------|
| Single-repo indexing | YES | All 7 collections index from `holo.project_root` |
| WSP 103/104 discoverable | YES | Both at TOP-1 |
| Trade FoundUp docs discoverable | YES | INTERFACE.md, README.md in docs bucket |
| Agent Workspace docs discoverable | YES | FORK_PLAN.md, GATEWAY_ADAPTER_DESIGN.md |
| ChromaDB `where=` filter available | YES | Used in `video_search.py` line 497 |
| `foundup_manifest.json` schema exists | YES | 7 manifests across the repo |
| pAVS MCP `holo_search` tool defined | YES | `pavs_mcp/src/server.py` (stub) |
| pAVS MCP `foundup_register` tool defined | YES | `pavs_mcp/src/server.py` (stub) |

### What Does NOT Exist

| Capability | Status | Risk |
|-----------|--------|------|
| `foundup_id` in index metadata | NOT PRESENT | Cross-tenant leakage |
| `tenant_id` in index metadata | NOT PRESENT | No query isolation |
| `source_repo` / `repo_url` in metadata | NOT PRESENT | No provenance tracking |
| `execute_search()` tenant filter param | NOT PRESENT | Global results to all callers |
| `_search_collection()` `where=` filter | NOT PRESENT | ChromaDB can filter; HoloIndex doesn't |
| `HoloIndex.search()` scoped to foundup | NOT PRESENT | Singleton serves all |
| External repo indexing | NOT PRESENT | Only indexes `project_root` |
| Manifest-driven collection routing | NOT PRESENT | `holo_collections: []` in Trade |
| Signature/auth gate on `holo_search` | NOT PRESENT | `signature: ""` in Trade manifest |

---

## 3. Tenant/FoundUp Isolation Gaps

### Gap 1: No Metadata Provenance

**Current state**: All 7 index collections write metadata without any source
identity. A document indexed from `modules/foundups/trade/` is
indistinguishable from `modules/foundups/kosei/` in search results.

**Fields written per collection**:

| Collection | Metadata Fields |
|-----------|----------------|
| navigation_code | need, type, source, cube |
| navigation_symbols | symbol, path, line, type |
| navigation_wsp | wsp, title, path, summary, type, priority |
| navigation_docs | title, path, summary, type, priority |
| navigation_knowledge | title, path, summary, type, priority |
| navigation_tests | test_id, path, description, capabilities, type, priority |
| navigation_skills | skill_name, description, agents, primary_agent, path, type, priority |

**None include**: `foundup_id`, `tenant_id`, `source_repo`, `repo_url`.

### Gap 2: No Query-Time Filtering

ChromaDB supports `where={"foundup_id": "trade"}` on `collection.query()`.
This is proven working in `video_search.py` (filters by `channel`). But
`_search_collection()` in `search_engine.py` does not pass any `where=`
clause. All searches return global results.

### Gap 3: Singleton HoloIndex

`HoloIndex` uses a shared-state singleton pattern (`_shared_state`). All
callers share one instance, one `project_root`, one set of collections.
There is no mechanism to instantiate a HoloIndex scoped to a specific
FoundUp's repo or namespace.

### Gap 4: No External Repo Indexing Path

`index_code_entries()` reads from NAVIGATION.py in the current project root.
`index_symbol_entries()` scans hardcoded directories (`holo_index/core`,
`modules/`). There is no API to index an external repo's files into a
separate or tagged collection.

---

## 4. External Repo Indexing Risks

### Risk: Cross-Tenant Leakage

If an external FoundUp's code were indexed into the existing `navigation_code`
collection without a `foundup_id` tag, its content would appear in ALL search
results for ALL users/agents. A query from the Trade FoundUp context would
return Kosei's private code and vice versa.

**Severity**: HIGH — violates WSP 104 tenant isolation.

### Risk: Index Pollution

External repos may contain large codebases. The symbol index is already at
its 20,000 entry cap. Indexing external FoundUp code into the same collection
would displace existing entries.

**Severity**: MEDIUM — degrades existing recall quality.

### Risk: Unsigned Manifests

All `foundup_manifest.json` files have `"signature": ""`. Without
cryptographic verification of manifest identity, a malicious external repo
could claim any `foundup_id` and poison the index.

**Severity**: HIGH — blocked until signature/auth gate exists.

### Risk: No Collection Isolation

WSP 104 mandates `data_namespace = idb_{foundup_id}`. Applied to HoloIndex,
this implies per-FoundUp collections (e.g., `trade_code`, `trade_docs`).
Currently all FoundUps share 7 global collections.

**Severity**: HIGH — violates WSP 104 data namespace isolation.

---

## 5. Metadata/Filter Requirements

### Minimum Metadata Fields for Federation

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `foundup_id` | string | `foundup_manifest.json` | Tenant isolation at query time |
| `source_repo` | string | Git remote URL | Provenance tracking |
| `indexed_at` | ISO datetime | Indexing timestamp | Staleness detection |

### Minimum Query Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `foundup_id` | Optional[str] | Scope results to one FoundUp |
| `include_shared` | bool | Whether to include shared/core results |

### Implementation Path (ChromaDB `where=`)

```python
# In _search_collection(), add optional where filter:
where_filter = None
if foundup_id:
    where_filter = {"foundup_id": foundup_id}

results = collection.query(
    query_embeddings=[embedding],
    n_results=limit,
    where=where_filter,  # <-- Currently missing
)
```

---

## 6. WSP_103/WSP_104 Retrieval Status

| WSP | Query | Position | Discoverable |
|-----|-------|----------|-------------|
| WSP 103 | "FoundUp Federation Protocol" | TOP-1 | YES |
| WSP 104 | "FoundUp route namespace tenant isolation" | TOP-1 | YES |
| WSP 103 | "pAVS MCP external FoundUps" | TOP-1 | YES |
| WSP 104 | "foundup_id routing_prefix" | TOP-1 | YES |

Both protocols are fully discoverable. No alias registry expansion needed.

---

## 7. Trade FoundUp Retrieval Status

| Query | Expected | Found | Position |
|-------|----------|-------|----------|
| "Trade FoundUp manifest routing" | trade/ docs | trade/INTERFACE.md | TOP-1 (docs) |
| "Trade FoundUp manifest routing" | WSP_104 | WSP_104 | TOP-1 (wsps) |
| "Trade FoundUp manifest routing" | trade/README.md | trade/README.md | TOP-2 (docs) |

Trade docs are discoverable in the docs bucket. The manifest itself
(`foundup_manifest.json`) is NOT in any index (it's JSON, not Python or
Markdown). This is acceptable — the manifest schema is documented in
PFMALL_FOUNDUP_MANIFEST_SCHEMA.md which IS discoverable.

---

## 8. FoundUps Agent Workspace Retrieval Status

| Query | Expected | Found | Position |
|-------|----------|-------|----------|
| "Agent Workspace external repo gateway" | FORK_PLAN.md | FORK_PLAN.md | TOP-2 (docs) |
| "Agent Workspace external repo gateway" | GATEWAY_ADAPTER.md | GATEWAY_ADAPTER.md | TOP-1 (docs) |
| "Agent Workspace external repo gateway" | dae_gateway.py | dae_gateway.py | TOP-1 (code) |

All workspace architecture docs are discoverable. The gateway adapter design
references `tenant_id` in WebSocket envelopes and `foundup_id` in task packet
identity blocks — but these are design docs, not implemented code.

---

## 9. WSP 97 Truth Boundaries

| Statement | Status |
|-----------|--------|
| HoloIndex has zero tenant isolation today | TRUE |
| ChromaDB supports where= filters (proven in video_search.py) | TRUE |
| No foundup_id/tenant_id in any index metadata | TRUE |
| All 7 collections are globally queried | TRUE |
| External repo indexing does not exist | TRUE |
| WSP_103/WSP_104 are discoverable | TRUE |
| Trade docs are discoverable | TRUE |
| Workspace docs are discoverable | TRUE |
| Manifest signatures are empty | TRUE |
| No runtime execution claims in this audit | TRUE |

---

## 10. WSP 15 Recommendation

### BLOCK: External Repo Indexing

External FoundUp code MUST NOT be indexed into HoloIndex until:

1. **Per-document `foundup_id` metadata** is written during indexing
2. **Query-time `where={"foundup_id": ...}` filtering** is implemented
3. **Manifest signature verification** prevents identity spoofing
4. **Collection isolation** (per-FoundUp collections OR `foundup_id` tags
   on shared collections) prevents cross-tenant leakage

### ALLOW: Internal FoundUp Retrieval

Current monorepo FoundUps (Trade, Kosei, GotJunk, etc.) are safe to
retrieve via HoloIndex because:

- They share a single `project_root` and single operator (012)
- No external party has query access
- pAVS MCP `holo_search` is a stub (not live)
- All access is via the local CLI, not a network API

### ALLOW: Federation Protocol Discovery

WSP_103 and WSP_104 are discoverable. Agents can retrieve federation
requirements without implementing federation indexing.

### SEQUENCE

```
1. [SAFE NOW]     Internal FoundUp retrieval (current state)
2. [NEXT SLICE]   Add foundup_id metadata to indexing (tag, don't filter yet)
3. [THEN]         Add where= filter to execute_search/search_collection
4. [THEN]         Per-FoundUp collection isolation (idb_{foundup_id} pattern)
5. [BLOCKED]      External repo indexing (requires 2+3+4 + signature gate)
6. [BLOCKED]      pAVS MCP holo_search live (requires 2+3 + auth)
```

---

## 11. Next Atomic Implementation Prompt

```
HIA_FEDERATION_METADATA_TAGGING_PHASE2

Objective:
Add foundup_id metadata field to HoloIndex indexing pipeline.

Scope:
- Add foundup_id to metadata in all index_* functions in indexing_engine.py
- Read foundup_id from foundup_manifest.json at project root (or default "core")
- Do NOT add query filtering yet (Phase 3)
- Do NOT add external repo indexing (blocked)
- Do NOT change search ranking

Deliverables:
- Modified indexing_engine.py (all index_* functions write foundup_id)
- Test: verify foundup_id appears in ChromaDB metadata after re-index
- Audit doc update
- ModLog entry

Gate:
All existing tests must pass with no regression.
```

---

## HIA Agentic RAG + Federation Pipeline Status

| Phase | Status |
|-------|--------|
| HIA Phase 1: Baseline gate | DONE (PR #503) |
| HIA Phase 2: Collection health | DONE (PR #504) |
| HIA Phase 3: Sentinel sufficiency | DONE (PR #505) |
| HIA Phase 4/4B: Docs/knowledge recall | DONE (PR #506) |
| HIA Phase 5: WSP_97 alias recall | DONE (PR #507) |
| HIA Phase 6/7: Ranking quality + index refresh | DONE (PR #508) |
| HIA Federation Phase 1: Readiness audit | DONE (this slice) |
| HIA Federation Phase 2: Metadata tagging | NEXT |
| HIA Federation Phase 3: Query filtering | BLOCKED on Phase 2 |
| HIA Federation Phase 4: Collection isolation | BLOCKED on Phase 3 |
| HIA Federation Phase 5: External repo indexing | BLOCKED on Phase 4 + signature gate |
