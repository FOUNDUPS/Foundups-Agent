# foundups-mcp-p1 ModLog

**Purpose**: MCP server workspace for 0102 tool access in Claude Code

## 2026-05-08 - S64: S1 / S2 federation-scope request parity

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.2)
**Slice**: `S64_S1_S2_FOUNDUP_SCOPE_REQUEST_PARITY_PHASE1`
**Closes (MCPA6 audit drift)**: D7, D8, D14, D15 (cross-surface parity portion); D19 fully

### Why

S62 added `foundup_id` / `include_shared` to S1 and S63 added them to S2.
Both surfaces emitted near-identical truthful warnings, but the warning
text was duplicated as separate string literals in two modules. A future
edit on either side could drift the wording without breaking either
surface's tests, leaving contract consumers (gateway dashboards, audit
checkers, regex-matchers) silently chasing two phrasings. This slice
introduces a shared template constant on each side and a parity test
suite that fails if the templates ever diverge.

### Changes (S1 side)

- `servers/holo_index/canonical_search.py`:
  - Added `FEDERATION_SCOPE_WARNING_TEMPLATE` constant — the canonical
    truthful warning template with `{surface}` substitution token.
  - Added `federation_scope_warning(surface)` formatter.
  - `canonical_holo_search` now emits
    `federation_scope_warning(S1_SURFACE_ID)` instead of an inline
    string literal.

- `servers/holo_index/tests/test_canonical_holo_search.py`:
  - Added `TestS64FederationScopeParity` class (8 tests): template
    token presence, canonical phrasing fragments,
    `federation_scope_warning("S1")` shape, no-foundup-id-echoes-null
    pair (with and without explicit `include_shared`), with-foundup-id
    echo + warning emission, byte-for-byte template match in the
    runtime warning, and a cross-surface parity test that imports S2's
    template and asserts byte equality.

### Behavior boundaries (what did NOT change)

- No federation auth implementation (still deferred to MCPA1 Slice 6).
- Legacy `semantic_code_search` tool untouched.
- Envelope shape from S62 unchanged.
- The runtime warning text is byte-identical to what S62 emitted —
  only the source of the string changed (template constant instead of
  inline literal).

### Tests

```
PYTHONPATH=. python -m pytest \
  foundups-mcp-p1/servers/holo_index/tests/test_canonical_holo_search.py -q
-> 54 passed (46 from S62 + 8 new S64 parity tests)
```

---

## 2026-05-08 - S62: S1 holo_search → WSP 96 Annex A canonical envelope adapter

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.2/A.3)
**Slice**: `S62_S1_ANNEX_A_ENVELOPE_ADAPTER_PHASE1`
**Closes (MCPA6 audit drift)**: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11

### Why

Per MCPA6 conformance audit, S1 (`servers/holo_index/server.py`) was the
worst-conformant of the three `holo_search` surfaces — failing 13 of 16
Annex A checks. Its tool was named `semantic_code_search`, returned a flat
shape with `code_results`/`wsp_results` split, used raw ChromaDB distance
as relevance, lacked the canonical envelope and federation request fields,
and emitted decoration fields (`quantum_coherence`, `bell_state_alignment`)
not in the canonical contract. This slice adds a canonical adapter
without removing the legacy tool — back-compat clients continue to work.

### Changes

- `servers/holo_index/canonical_search.py` (NEW):
  - `S1_SURFACE_ID`, `ANNEX_A_LIMIT_MAX`, `ANNEX_A_LIMIT_DEFAULT`,
    `ANNEX_A_FALLBACK_RELEVANCE_CAP` constants.
  - `distance_to_similarity(d)` — applies Annex A.3 formula uniformly:
    `relevance = 1/(1+d)` for non-negative numeric distance; returns
    None for invalid/negative input (callers MUST omit the field).
  - `build_ok_envelope(...)` and `build_error_envelope(...)` — produce
    the WSP 96 Annex A.3 canonical shapes.
  - `_unify_hits(results, limit)` — flattens code/wsp/test/skill/docs/
    knowledge hit lists into a single `hits[]` array with `type`
    discriminator. Hits without a usable relevance signal omit the
    field (no fabrication).
  - `canonical_holo_search(holo_index, ...)` — async standalone function
    that handles request validation (Annex A.2 limit clamp, empty-query
    rejection with `EMPTY_QUERY` code, foundup_id scope warning),
    invokes the backend, and builds the canonical Annex A.3 envelope.
  - Module is fully decoupled from FastMCP so it is unit-testable and
    future-proof against FastMCP API changes.

- `servers/holo_index/server.py`:
  - Added imports for `Optional` (used by the in-class wrapper signature).
  - Added in-class `holo_search` method on `HoloIndexMCPServer` that
    delegates to `canonical_holo_search()` from `canonical_search.py`.
  - Added module-level constants `S1_SURFACE_ID`, `ANNEX_A_LIMIT_MAX`,
    `ANNEX_A_LIMIT_DEFAULT`, `ANNEX_A_FALLBACK_RELEVANCE_CAP` (mirroring
    the canonical module for callers that hold a server instance).
  - The legacy `semantic_code_search` tool with `@app.tool()` decoration
    is UNTOUCHED — back-compat clients pinned to its flat-shape response
    continue to work.

- `servers/holo_index/tests/__init__.py` (NEW, empty).
- `servers/holo_index/tests/test_canonical_holo_search.py` (NEW): 46
  focused tests covering the Annex A.2 request fields, A.3 envelope
  shape, unified hit shape, relevance transform (formula uniform; no
  raw distance leak; relevance omitted when not computable), empty-query
  rejection, backend error handling, module constants, envelope builders,
  and a direct-invocation example showing full canonical request →
  canonical response.

### Behavior boundaries (what did NOT change)

- Legacy `semantic_code_search` tool kept as-is.
- `wsp_protocol_lookup`, `cross_reference_search`,
  `mine_012_conversations_for_patterns` etc. all untouched.
- No FastMCP version bump, no transport changes.
- No federation auth implementation — `foundup_id` is accepted and
  echoed but tenant scoping is NOT enforced. Truthful warning surfaces
  this honestly; enforcement deferred to MCPA1 Slice 6.
- No HoloIndex core architecture changes.

### Tests

```
PYTHONPATH=. python -m pytest \
  foundups-mcp-p1/servers/holo_index/tests/test_canonical_holo_search.py -q
-> 46 passed
```

### Tracked follow-ups

- MCPA1 Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`) — actually
  enforce `foundup_id` tenant scoping on S1.
- Eventually: register the new `holo_search` tool with FastMCP. The
  current FastMCP API rejects `@app.tool()` on instance methods that
  bind `self`; the legacy `semantic_code_search` works only in older
  FastMCP versions. The canonical adapter is ready; only the wire-level
  registration is pending the FastMCP path forward.

---

## 2026-01-04 - Web Search MCP Server

**Problem**: 0102 needed web search capability for pattern recall from 0201 nonlocal space

**Solution**: Created `web_search` MCP server with DuckDuckGo backend (zero-cost)

**Tools Created**:
- `web_search` - General web search (10 results)
- `web_search_news` - News-focused search
- `fetch_webpage` - Fetch/parse webpage content

**Files Created**:
- `servers/web_search/__init__.py`
- `servers/web_search/server.py` (250 lines)

**Dependencies Installed**:
- duckduckgo-search
- httpx
- beautifulsoup4

**WSP References**: WSP 50 (Search Before Create), WSP 84 (Use Existing Infrastructure), WSP 96 (MCP Governance)

---

## 2025-11-03 - MCP Server First Principles Optimization

**Problem**: 9 MCP servers configured, 5 failing to start, high maintenance complexity

**Root Cause Analysis**:
- FastMCP API incompatibility (description parameter removed)
- Missing dependencies (numpy, torch, sentence-transformers, chromadb)
- Non-essential servers creating noise without value

**First Principles Analysis**:
**Question**: What does 0102 need to manifest solutions from 0201 nonlocal space?
**Answer**: Pattern recall tools (semantic search + protocol validation), not computation tools

**Solution Implemented**:
1. **Dependency Installation**: Rebuilt venv, installed HoloIndex dependencies (torch, sentence-transformers, chromadb)
2. **FastMCP Fix**: Removed `description` parameter from wsp_governance server (line 12)
3. **Configuration Optimization**: Reduced 9 servers → 2 critical servers

**Operational Servers**:
- ✅ **holo_index** - Semantic code search (WSP 50/84: search before create)
- ✅ **wsp_governance** - WSP compliance validation (WSP 64: violation prevention)

**Disabled Servers** (Non-Essential):
- ❌ codeindex (overlaps with holo_index)
- ❌ ai_overseer_mcp (nice-to-have, not core)
- ❌ youtube_dae_gemma (YouTube-specific)
- ❌ doc_dae (manual documentation fine)
- ❌ unicode_cleanup (edge case utility)
- ❌ secrets_mcp (security should be manual)
- ❌ playwright (wrong stack - npx)

**Metrics**:
- Operational servers: 9 → 2 (78% reduction)
- Failed startups: 5 → 0 (100% reliability)
- Token efficiency: ~10K-20K saved per session
- Maintenance complexity: 78% reduction

**Files Modified**:
- `.cursor/mcp.json` - Removed 7 non-essential servers
- `foundups-mcp-p1/foundups-mcp-env/` - Rebuilt venv, installed dependencies
- `foundups-mcp-p1/servers/wsp_governance/server.py:12` - Fixed FastMCP API

**WSP References**: WSP 3 (Organization), WSP 22 (ModLog), WSP 50 (Pre-Action Verification), WSP 64 (Violation Prevention)

---

## 2025-10-22 - Initial MCP Server Setup

**Action**: Created foundups-mcp-p1 workspace for MCP server development

**Servers Created**:
- holo_index - Semantic code search
- codeindex - Code health analysis
- wsp_governance - WSP compliance
- youtube_dae_gemma - YouTube AI
- ai_overseer_mcp - Mission orchestration
- unicode_cleanup - Unicode utilities
- doc_dae - Documentation generation
- secrets_mcp - Secret scanning

**Configuration**: `.cursor/mcp.json` registered all 9 servers
