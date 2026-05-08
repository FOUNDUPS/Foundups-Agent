# foundups_mcp_bridge - ModLog

## 2026-05-08 - S63: S2 holo_search → WSP 96 Annex A request/meta conformance

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.2/A.3)
**Slice**: `S63_S2_ANNEX_A_RENAME_AND_META_PHASE1`
**Closes (MCPA6 audit drift)**: D12, D13, D14, D15, D16, D17, D18

### Why

Per MCPA6 conformance audit (`docs/audits/mcp_system/MCPA6_MCP_CONFORMANCE_AUDIT.md`),
S2 was the closest of the three `holo_search` surfaces to the WSP 96 Annex A
canonical contract — but still drifted on field naming (`scope` vs
`doc_type_filter`, `top_k` vs `limit`), lacked the federation request fields
(`foundup_id`, `include_shared`), did not tag responses with `meta.surface`,
returned a flat string error instead of the canonical `error.code` object,
and used a hardcoded `0.5` relevance for ripgrep fallback instead of the
Annex A.3 0.6 cap policy. This slice closes those gaps without rewriting
S2 architecture.

### Changes

- `src/holo_tools.py`:
  - Added module-level constants `S2_SURFACE_ID`, `ANNEX_A_LIMIT_MAX`,
    `ANNEX_A_LIMIT_DEFAULT`, `ANNEX_A_FALLBACK_RELEVANCE_CAP`.
  - Added `_build_s2_error_envelope()` helper producing the Annex A.3
    `{code, message, details?}` error shape (the generic `error_response()`
    keeps returning a flat string for the other tools — no cross-tool drift).
  - Added `_build_s2_ok_envelope()` helper producing the canonical Annex A.3
    ok envelope with `data.metadata.retrieval_mode`, `data.metadata.warnings`,
    `meta.surface = "S2"`, etc.
  - Rewrote `holo_search` signature to accept the five canonical Annex A.2
    request fields (`query`, `limit`, `doc_type_filter`, `foundup_id`,
    `include_shared`). Legacy `scope` and `top_k` retained as deprecated
    aliases; canonical names win when both are supplied.
  - Empty-query rejection now returns `error.code = "EMPTY_QUERY"` with a
    truthful message naming Annex A.2.
  - Limit is clamped to Annex A.2 [1..50] with a truthful warning when the
    clamp applies; invalid types fall back to default 10 with a warning.
  - Lexical fallback path now caps every hit's `relevance` at
    `ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6` per Annex A.3.
  - `data.metadata` block now always carries `retrieval_mode`,
    `engine_version`, `collections_searched`, and `warnings`. Engine
    metadata is merged in without overriding canonical keys.
  - `meta.surface = "S2"` and `meta.tool = "holo_search"` emitted on both
    ok and error responses.
  - Federation field acceptance is truthful: `foundup_id` is echoed but
    surfaces an Annex A.2/Slice-6 "tenant scoping not yet enforced" warning;
    `include_shared` is echoed as `None` when `foundup_id` is null so callers
    cannot infer a scope decision was made.
  - Imports `MCPResponse` from `response_schema` (was importing
    `ok_response`/`error_response` only).

- `tests/test_mcp_bridge.py`:
  - Updated `test_holo_search_empty_query_error` to assert the canonical
    `error.code = "EMPTY_QUERY"` shape and `meta.surface = "S2"`.
  - Added `TestS2HoloSearchAnnexAConformance` class with 22 focused tests
    covering: canonical field names accepted, foundup_id/include_shared
    echo semantics, legacy aliases (`scope`, `top_k`) still work with
    truthful warnings, canonical wins over alias when both supplied,
    Annex A.2 limit bounds (clamp warnings), `meta.surface`, `meta.tool`,
    `meta.source` truthfulness, `data.metadata` canonical keys, empty-query
    canonical error, whitespace-query rejection, foundup_id unenforced
    warning, fallback relevance ≤ 0.6 cap, BACKEND_UNAVAILABLE error
    envelope, and direct `holo_tools.holo_search()` invocation.

- `ModLog.md` (NEW): this entry.

### Behavior boundaries (what did NOT change)

- S1 (`foundups-mcp-p1/servers/holo_index/server.py`) untouched.
- S3 (`pavs_mcp/src/server.py`) untouched.
- MCP Manager untouched.
- `error_response()` and `ok_response()` helpers in `response_schema.py`
  unchanged — only `holo_search` builds the canonical structured error.
  Other bridge tools keep the legacy flat-string error shape.
- Other tools in `holo_tools.py` (`holo_related`, `holo_failure_memory`,
  `holo_pattern_search`, `holo_task_packet`) are untouched per slice scope
  (deferred until they have a canonical Annex A entry of their own).
- No federation auth implementation. `foundup_id` is accepted and echoed
  but tenant scoping is NOT enforced — explicitly tracked as MCPA1 Slice 6.
- No real-relevance computation change in the semantic path — Annex A's
  `1/(1+distance)` rule was already approximated by `_parse_similarity`
  which converts "85.1%" → 0.851. Only the fallback path needed the cap.

### Tests

```
PYTHONPATH=. python -m pytest \
  modules/infrastructure/foundups_mcp_bridge/tests/test_mcp_bridge.py \
  -k "holo_search or AnnexAConformance" -q
-> 26 passed, 87 deselected
```

### Tracked follow-ups

- MCPA1 Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`) — actually
  enforce `foundup_id` tenant scoping. The truthful "not yet enforced"
  warning surfaced by this slice will flip to a real authority check.
- MCPA6 Slice 6.2 — bring S1 (`semantic_code_search`) into the same
  envelope conformance applied here to S2.
- The four other holo_* tools in this module (`holo_related`,
  `holo_failure_memory`, `holo_pattern_search`, `holo_task_packet`)
  remain on the legacy `ok_response` envelope. WSP 96 Annex A only
  defines `holo_search` today; those tools get their own annex when
  they have a canonical contract.
