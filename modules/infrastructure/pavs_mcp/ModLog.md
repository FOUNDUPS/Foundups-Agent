# pAVS MCP Server - ModLog

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
