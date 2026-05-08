# MCPA6B — MCP `holo_search` Conformance Re-Audit (Phase 1)

**Slice**: `MCPA6B_MCP_CONFORMANCE_REAUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-08
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_15 → WSP_97 → WSP_50
**Anchor contract**: WSP 96 Annex A (`Canonical holo_search Contract`, MCPA3, PR #517 — now on main)
**Predecessor audit**: `docs/audits/mcp_system/MCPA6_MCP_CONFORMANCE_AUDIT.md` (PR #520)

---

## Precondition Check (verified live on `origin/main`)

| PR | Slice | Commit | Status |
|----|-------|--------|--------|
| #520 | MCPA6 conformance audit doc | `7faef740b` | ✓ merged |
| #521 | MCPA1 Slice 4 — S3 `not_implemented` envelope | `3efb1978c` | ✓ merged |
| #522 | S63 — S2 Annex A request/meta conformance | `153354689` | ✓ merged |
| #523 | S62 — S1 Annex A canonical envelope adapter | `eabf12242` | ✓ merged |
| #524 | S64 — S1/S2 federation-scope request parity | `9328a039f` | ✓ merged |

All four hard preconditions satisfied. Re-audit proceeds.

---

## HoloIndex Research

```bash
python holo_index.py --search "MCPA6B re-audit S1 S2 S3 conformance Annex A after S6.4" --limit 5
```

**Top WSP hit**: `WSP_framework/src/WSP_79_Module_SWOT_Analysis_Protocol.md` (false positive — module-audit term match)
**Top CODE hit**: `modules/infrastructure/wre_core/src/security_analysis_assistant.py` (false positive)
**Top DOCS hit**: `docs/audits/mobile_first_integration/INTEGRATION_CONFORMANCE_REPORT.md`

The retrieval was less specific than ideal for a re-audit query. Verified the canonical Annex A spec directly via the on-main file (`WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md` Annex A.2/A.3) and grep-confirmed every conformance invariant on each surface (see §1 below).

---

## 1. Per-Surface Conformance Checklist (A.2 + A.3)

Legend: ✅ conformant · ⚠️ partial · ❌ missing · n/a not applicable

### S1 — `foundups-mcp-p1/servers/holo_index/canonical_search.py`

Tool name: **`holo_search`** (canonical). Legacy `semantic_code_search` retained in `server.py` for back-compat.

| Annex A check | S1 reality | Verdict | Evidence |
|---------------|------------|---------|----------|
| Tool name `holo_search` | matches | ✅ | `server.py:holo_search` method delegates to `canonical_search.canonical_holo_search` |
| Request: `query` (required, non-empty) | accepted; rejected when empty | ✅ | `canonical_search.py:359-365` |
| Request: `limit` (1..50, default 10) | accepted; clamped with truthful warning | ✅ | `canonical_search.py:307-321` |
| Request: `doc_type_filter` (enum) | accepted, passed through to backend | ✅ | `canonical_search.py:264, 350` |
| Request: `foundup_id` | accepted, echoed in `data.foundup_id` | ✅ | `canonical_search.py:265, 119` |
| Request: `include_shared` (default True) | accepted; echoed null when no `foundup_id` | ✅ | `canonical_search.py:266, 121` |
| Empty-query rejection with `EMPTY_QUERY` code | structured error envelope | ✅ | `canonical_search.py:359-365` |
| Envelope: `status` / `data` / `meta` | full canonical shape | ✅ | `canonical_search.py:114-133` |
| Hits: unified `hits[]` with `type` discriminator | flattened across code/wsp/test/skill/docs/knowledge | ✅ | `canonical_search.py:188-231` |
| Hit fields: `type` / `path` / `preview` / `relevance` / `line_num`? / `summary`? | per Annex A.3 hit shape | ✅ | `canonical_search.py:191-231` |
| Relevance scale: `1/(1+distance)` formula | applied uniformly | ✅ | `canonical_search.py:62-86` |
| Relevance omitted when not computable | `None` returned, callers omit field | ✅ | `canonical_search.py:84-86, 200-203` |
| `meta.source = "holoindex"` (truthful) | set on success | ✅ | `canonical_search.py:158, 380` |
| `meta.surface = "S1"` | always set | ✅ | `canonical_search.py:159, 181` |
| `meta.tool = "holo_search"` | always set | ✅ | `canonical_search.py:158, 180` |
| `meta.confidence` | set | ✅ | `canonical_search.py:160` |
| `data.metadata.retrieval_mode` (enum) | `"semantic"` on success | ✅ | `canonical_search.py:104, 386` |
| `data.metadata.engine_version` | passed through from backend | ✅ | `canonical_search.py:105` |
| `data.metadata.collections_searched` | passed through | ✅ | `canonical_search.py:106` |
| `data.metadata.warnings` | populated truthfully | ✅ | `canonical_search.py:107` |
| `foundup_id` warning when supplied | byte-identical to S2 via shared template | ✅ | `canonical_search.py:355` (`federation_scope_warning(S1_SURFACE_ID)`) |
| Federation auth/scope enforcement | NOT enforced (truthful warning surfaces this) | ⚠️ deferred to Slice 6 | `canonical_search.py:355` |

**S1 score: 21/22 ✅, 1 ⚠️ (deferred federation enforcement)**

### S2 — `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py`

Tool name: **`holo_search`** ✅.

| Annex A check | S2 reality | Verdict | Evidence |
|---------------|------------|---------|----------|
| Tool name `holo_search` | matches | ✅ | `holo_tools.py:121` |
| Request: `query` (required, non-empty) | accepted; rejected when empty | ✅ | `holo_tools.py:238-247` |
| Request: `limit` (1..50, default 10) | canonical accepted; legacy `top_k` alias with warning | ✅ | `holo_tools.py:126, 196-211` |
| Request: `doc_type_filter` (enum) | canonical accepted; legacy `scope` alias with warning | ✅ | `holo_tools.py:127, 207-216` |
| Request: `foundup_id` | accepted, echoed | ✅ | `holo_tools.py:128, 397` |
| Request: `include_shared` (default True) | accepted; null when no `foundup_id` | ✅ | `holo_tools.py:129, 399` |
| Empty-query rejection with `EMPTY_QUERY` code | structured error envelope | ✅ | `holo_tools.py:238-247` |
| Envelope: `status` / `data` / `meta` | via `MCPResponse` wrapper | ✅ | `holo_tools.py:140-149`, `_build_s2_ok_envelope` |
| Hits: unified `hits[]` with `type` discriminator | already aligned from prior S63 | ✅ | `holo_tools.py:281-326` |
| Hit fields: per Annex A.3 hit shape | `type`/`path`/`preview`/`relevance`/`title`/`summary` | ✅ | `holo_tools.py:281-326` |
| Relevance scale: 0..1 | `_parse_similarity` produces unit interval | ✅ | `holo_tools.py:_parse_similarity` |
| Lexical fallback caps relevance at 0.6 | `ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6` enforced | ✅ | `holo_tools.py:93, 342` |
| `meta.source = "holoindex"|"fallback"` (truthful) | set per path | ✅ | `holo_tools.py:401` |
| `meta.surface = "S2"` | always set | ✅ | `holo_tools.py:144, 403` |
| `meta.tool = "holo_search"` | always set | ✅ | `holo_tools.py:144, 402` |
| `meta.confidence` | set | ✅ | `holo_tools.py:402` |
| `data.metadata.retrieval_mode` (enum) | `"semantic"`/`"lexical"` per path | ✅ | `holo_tools.py:380` |
| `data.metadata.warnings` | truthfully populated | ✅ | `holo_tools.py:386` |
| Legacy `scope`/`top_k` aliases preserved with truthful warnings | yes; canonical wins when both supplied | ✅ | `holo_tools.py:196-216` |
| `foundup_id` warning when supplied | byte-identical to S1 via shared template | ✅ | `holo_tools.py:235` (`federation_scope_warning(S2_SURFACE_ID)`) |
| Cross-surface template parity vs S1 | byte-identical `FEDERATION_SCOPE_WARNING_TEMPLATE` | ✅ | `holo_tools.py:99-110` (mirror of `canonical_search.py:59-71`); enforced by S64 parity tests |
| Federation auth/scope enforcement | NOT enforced (truthful warning surfaces this) | ⚠️ deferred to Slice 6 | `holo_tools.py:235` |

**S2 score: 21/22 ✅, 1 ⚠️ (deferred federation enforcement)**

### S3 — `modules/infrastructure/pavs_mcp/src/server.py`

Tool name: **`holo_search`** (returns `not_implemented` per Annex A.3 — placeholder surface).

| Annex A check | S3 reality | Verdict | Evidence |
|---------------|------------|---------|----------|
| Tool name `holo_search` | matches | ✅ | `pavs_mcp/server.py:302` |
| Request: `query` (accepts) | accepted (echoed in `data.query`) | ✅ | `pavs_mcp/server.py:304, 378` |
| Request: `limit` (1..50, default 10) | accepted; clamped per Annex A.2 | ✅ | `pavs_mcp/server.py:305-310, 350-357` |
| Request: `doc_type_filter` (enum) | accepted; legacy `domain` alias with warning | ✅ | `pavs_mcp/server.py:307, 339-348` |
| Request: `foundup_id` | accepted, echoed | ✅ | `pavs_mcp/server.py:308, 380` |
| Request: `include_shared` (default True) | accepted; null when no `foundup_id` | ✅ | `pavs_mcp/server.py:309, 384` |
| Envelope: `status = "not_implemented"` (Annex A.3 mandate for placeholder) | exact canonical shape | ✅ | `pavs_mcp/server.py:375` |
| `error.code = "NOT_IMPLEMENTED"` | structured error code | ✅ | `pavs_mcp/server.py:394` |
| `error.message` names canonical owners (S1/S2) | message points callers at S2 + S1 | ✅ | `pavs_mcp/server.py:395-399` |
| `error.delegate_to` hint | `"S2"` | ✅ | `pavs_mcp/server.py:400` |
| `data.hits = []` (no fabrication) | empty array; `hit_count = 0` | ✅ | `pavs_mcp/server.py:386-387` |
| `data.metadata.retrieval_mode = "none"` (truthful) | not "semantic"; honest | ✅ | `pavs_mcp/server.py:389` |
| No fabricated relevance/score/distance keys anywhere | tree-walk test enforces this | ✅ | `pavs_mcp/tests/test_server_holo_search.py` (forbidden-keys test) |
| `meta.surface = "S3"` | always set | ✅ | `pavs_mcp/server.py:405` |
| `meta.tool = "holo_search"` | always set | ✅ | `pavs_mcp/server.py:404` |
| `meta.implementation_status = "placeholder_stub"` | from MCPA4 truth meta | ✅ | merged via `_truth_meta()` |
| `meta.real_backend = False` | truthful | ✅ | merged via `_truth_meta()` |
| `meta.canonical_owner = False` | truthful (S3 has `no_authority`) | ✅ | merged via `_truth_meta()` |
| Authority role per Annex A.1: `no_authority` | code reflects via `meta.canonical_owner=False` + delegate hint | ✅ | per A.1 audit anchor |
| Federation auth (api_key validation) | accepted but NOT enforced | ⚠️ deferred to Slice 6 | `pavs_mcp/server.py:329` (TODO) |
| Real WebSocket transport | `start()` does not bind a port | ⚠️ deferred to Slice 6 | `pavs_mcp/server.py` (sleep-loop) |
| Cross-tenant ownership check | not enforced | ⚠️ deferred to Slice 6 | per MCPA1 R1 |

**S3 score: 18/21 ✅, 3 ⚠️ (deferred — auth, transport, cross-tenant enforcement)**

### Cross-surface parity (S64)

| Parity invariant | Verdict | Evidence |
|---|---|---|
| `FEDERATION_SCOPE_WARNING_TEMPLATE` byte-identical between S1 and S2 | ✅ | enforced by `test_s2_template_matches_s1_template` (S1 suite) and `test_s1_template_matches_s2_template` (S2 suite) |
| `foundup_id` echo semantics identical (S1 and S2): `null` when absent, value when present | ✅ | both call sites use the same conditional — S64 unified code path |
| `include_shared` echo semantics identical: `null` without `foundup_id`, request value when present | ✅ | identical in both modules per Annex A.2 |
| Federation warning emitted only when `foundup_id` is set (no silent emission) | ✅ | both surfaces guard the append on `if foundup_id is not None` |
| Runtime warning string matches `federation_scope_warning(SURFACE)` byte-for-byte | ✅ | enforced by per-surface `test_emitted_warning_matches_template_byte_for_byte` |

---

## 2. Updated Drift Table (Closed vs Remaining)

### Closed by merged PRs

| ID | Original drift | Closed by | Closure evidence |
|----|----------------|-----------|------------------|
| **D1** | S1 tool name was `semantic_code_search` | #523 | `canonical_search.canonical_holo_search()` exposes `holo_search` (legacy retained for back-compat). |
| **D2** | S1 returned flat dict, no envelope | #523 | `build_ok_envelope` produces `{status, data, meta}`. |
| **D3** | S1 hits split into `code_results`/`wsp_results` | #523 | `_unify_hits` flattens to `hits[]` with `type` discriminator. |
| **D4** | S1 used `file_types` not `doc_type_filter` | #523 | Canonical name accepted and passed through. |
| **D5** | S1 reported raw `distance` as relevance | #523 | `distance_to_similarity` applies `1/(1+d)` uniformly; no raw distance leaks. |
| **D6** | S1 emitted `quantum_coherence`/`bell_state_alignment` | #523 | Canonical envelope omits them; tests enforce absence. |
| **D7** | S1 missing `foundup_id` request field | #523 + #524 | Accepted, echoed; cross-surface parity enforced via shared template. |
| **D8** | S1 missing `include_shared` request field | #523 + #524 | Accepted with Annex A.2 semantics; null when no `foundup_id`. |
| **D9** | S1 no empty-query rejection | #523 | Returns `error.code = "EMPTY_QUERY"`. |
| **D10** | S1 default limit 5, no upper bound | #523 | Default 10, range 1..50, truthful clamp warning. |
| **D11** | S1 missing `meta.surface`/`meta.tool`/`meta.source` | #523 | All three set on every response. |
| **D12** | S2 used `scope` not `doc_type_filter` | #522 | Canonical accepted; legacy `scope` alias with warning. |
| **D13** | S2 used `top_k` not `limit` | #522 | Canonical accepted; legacy `top_k` alias with warning. |
| **D14** | S2 missing `foundup_id` request field | #522 + #524 | Accepted, echoed; cross-surface parity. |
| **D15** | S2 missing `include_shared` request field | #522 + #524 | Accepted with Annex A.2 semantics. |
| **D16** | S2 empty-query error lacked `error.code` | #522 | Returns `error.code = "EMPTY_QUERY"`. |
| **D17** | S2 fallback relevance hardcoded 0.5 | #522 | Now `ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6` policy. |
| **D18** | S2 missing `meta.surface = "S2"` | #522 | Set on every response. |
| **D19** | S2/S3 no `data.foundup_id` echo | #522 + #521 + #524 | All three surfaces echo; cross-surface parity verified. |
| **D20** | S3 returned hardcoded fake data | #521 | `status = "not_implemented"`, `hits = []`. |
| **D21** | S3 had no envelope at all | #521 | Full canonical envelope. |
| **D22** | S3 fabricated `score: 0.95` | #521 | Tree-walk test forbids any fabricated relevance/score/distance keys. |
| **D23** | S3 used `domain` not `doc_type_filter` | #521 | Canonical accepted; `domain` retained as deprecated alias with warning. |
| **D25** | S3 had no canonical envelope shape | #521 | Full Annex A.3 envelope. |
| **D26** | S3 had no truth flag on responses | #518 (MCPA4) | `_truth_meta()` injects `implementation_status: "placeholder_stub"` on every response. |
| **D27** | S3 README claimed auth enforcement | #518 (MCPA4) | README banner says `NO_AUTH_ENFORCEMENT`; runtime banner mirrors. |
| **D28** | S3 README claimed live endpoint | #518 (MCPA4) | README qualifies endpoint as `(planned, not deployed)`. |

**Total closed: 27 of 28 drift IDs**.

### Remaining (deferred to MCPA1 Slice 6)

| ID | Drift | Why still open | Lane |
|----|-------|----------------|------|
| **D24** | S3 missing federation field enforcement (cross-tenant blocking) | Tenant scoping deferred to federation auth slice | MCPA1 Slice 6 |
| **R1** (from MCPA1 audit) | S3 `handle_tool_call` accepts `api_key` but never validates it | Real auth deferred | MCPA1 Slice 6 |
| **R2** (from MCPA1 audit) | S3 `start()` does not bind a port; `wss://pavs.foundups.com/mcp` not deployed | Real transport deferred | MCPA1 Slice 6 |
| **R6** (from MCPA1 audit) | S3 `FoundUpRegistration` registry is in-memory; not persistent | Persistent registry deferred | MCPA1 Slice 6 |
| (parity dimension of D7/D8/D14/D15) | Federation field enforcement on S1 + S2 (not just acceptance) | All three surfaces accept and echo, none enforce | MCPA1 Slice 6 |

**Total remaining: 1 audit-numbered drift + 4 cross-surface enforcement items, all in the federation auth/scope lane**.

---

## 3. Final Decision

### **PARTIAL_CONFORMANCE**

All envelope/request/response field-level conformance is in place across S1, S2, and S3. The cross-surface parity contract (S64) is enforced by code (shared template) and tests (cross-import byte equality). The remaining work is exclusively in the **federation auth/scope enforcement lane** — accepting the request fields (`foundup_id`, `include_shared`, `api_key`) is complete; verifying caller authority and enforcing tenant scope is not.

**Live-flip readiness**:
- **S2 internal usage**: `READY` — canonical envelope, real backend, truthful fallback semantics, no auth implications because S2 is internal-only.
- **S1 external MCP exposure**: `READY` for unauthenticated holo_search (read-only semantic search over global corpus) — same as today, just with a conformant envelope.
- **S3 federation usage**: `NOT_READY` — surface emits `not_implemented` truthfully; no live federation traffic should be routed here until Slice 6 lands.

This is an upgrade from the prior **MCPA6 verdict of NON_CONFORMANT_BLOCKING** — at that time S1 and S3 failed >half of Annex A checks. After PRs #521-#524 merged, every field-level check on every surface passes. The remaining gap is enforcement, not contract shape.

---

## 4. Exact Remaining Blockers for Slice 6 (auth/enforcement lane)

The slice will be `MCPA1_SLICE_6_S3_FEDERATION_AUTH_AND_SCOPE_PHASE1` (already named in MCPA1 plan; explicit blockers listed here):

1. **API-key validation on S3** (`pavs_mcp/server.py:329`): replace `# TODO: Implement proper auth` with a real `api_key` → `foundup_id` lookup against a persistent registry. Reject calls without a registered key with `error.code = "TENANT_UNAUTHORIZED"` per Annex A.3.
2. **Persistent FoundUp registration** (`pavs_mcp/server.py:48`): replace the in-memory `self.registrations: dict` with a durable store (SQLite via existing `agent_market` patterns). The current registry is lost on every restart.
3. **Real WebSocket / SSE transport** (`pavs_mcp/server.py` `start()` body): bind to the documented `wss://pavs.foundups.com/mcp` (or correct the README if a different endpoint is chosen). Until then S3 cannot accept real federation traffic.
4. **Tenant-scope enforcement on S3 tools** (`pavs_mcp/server.py` per-tool bodies): when a tool accepts a `foundup_id` parameter (e.g. `fam_emit`, `pattern_store`), verify that the caller's `api_key` is authorized for that `foundup_id`. Currently any `api_key` can pass any `foundup_id` and the surface accepts it. Reject mismatches with `TENANT_UNAUTHORIZED`.
5. **Cross-tenant query semantics on S1/S2 `holo_search`** (canonical_search.py:355, holo_tools.py:235): replace the truthful "not yet enforced" warning with real enforcement — when `foundup_id` is set, scope the search to the tenant's collections (and respect `include_shared`). The shared `FEDERATION_SCOPE_WARNING_TEMPLATE` is the canonical insertion point: when enforcement lands, the warning becomes empty (or shifts to an enforced-mode confirmation).
6. **MCP Manager status reflection**: `mcp_manager.discover_all_surfaces()` returns S3 as `implementation_status = "PLACEHOLDER_STUB"`. After Slice 6 lands, S3 graduates to `RUNTIME_LIVE` with `holo_search_support = "real"` (currently `"placeholder"`); `KnownSurface` constants in `mcp_manager.py` need the corresponding flip.

These six items collectively close D24, R1, R2, R6, and the cross-surface enforcement dimension of D7/D8/D14/D15. After Slice 6, the verdict moves from `PARTIAL_CONFORMANCE` to `CONFORMANT`.

---

## Acceptance Criteria Verification

- ✓ Field-level evidence for S1/S2/S3 (Section 1, with line-anchored citations).
- ✓ Explicit closure mapping for prior drift IDs (Section 2 — 27/28 closed).
- ✓ No overclaims — every ✅ tied to an on-main file:line; every ⚠️ explicitly attributed to a deferred lane (Slice 6).
- ✓ Audit-only — no runtime code edits.

---

## WSP 97 Applied

Three truth boundaries enforced by this re-audit:

1. **Closed ≠ silent.** Every drift ID closed in §2 cites the merging PR AND the line of code that proves the closure on `origin/main`. This re-audit does not say "fixed in PR #523" without grep-confirming the artifact lives at the cited line on the current main.
2. **`PARTIAL_CONFORMANCE` is the truthful verdict — neither overclaim nor underclaim.** A `CONFORMANT` verdict would be false because federation enforcement is admittedly absent (the surfaces emit truthful "not yet enforced" warnings to say so). A `NON_CONFORMANT_BLOCKING` verdict would be false because every field-level Annex A.2/A.3 check passes today. The middle verdict is the only one consistent with the runtime state.
3. **Remaining blockers are listed by file:line, not by hand-wave.** Section 4 names the exact code locations Slice 6 must touch. This prevents the next slice from rediscovering the gap independently.

WSP 50 verification: every cited file:line was confirmed against the working tree (post-pull from `origin/main`). WSP 15: P0 narrow audit scope respected — single new doc, no runtime edits, no cross-slice broadening. WSP 00: identity locked as Worker W1 throughout.

---

## Files Touched This Slice

- `docs/audits/mcp_system/MCPA6B_MCP_CONFORMANCE_REAUDIT.md` (NEW)

No runtime code edits. No commits made.
