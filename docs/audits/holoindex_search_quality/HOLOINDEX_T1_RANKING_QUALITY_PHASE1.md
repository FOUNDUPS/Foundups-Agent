# HoloIndex T1 Ranking Quality -- Phase 1

**Slice**: `HOLOINDEX_T1_RANKING_QUALITY_PHASE1`
**Decision**: RESUME_AND_REPAIR
**Worker-Lane**: W6
**Agent**: 0102
**Date**: 2026-05-30
**Mode**: Search-time ranking tuning (no reindex, no indexer change)
**Branch**: `main` (working tree, dirty)
**Base commit**: `3dc26e6f9` (origin/main HEAD, post-PR #730)
**Lineage**: Resumes the abandoned W7 slice originally based at `d86450997`
(post-#701). Re-validated against current main after #728 (full-body
chunking) and #730 (cold-process timeout).
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_T1_RANKING_QUALITY_ONLY | YES | Single-function tier added to `_slice_id_match_boost`; no other behavior change. |
| 2 | SEARCH_TIME_ONLY | YES | No indexing-engine touch; no Chroma writes; no reindex run. |
| 3 | NO_INDEXING_ENGINE_CHANGE | YES | `holo_index/core/indexing_engine.py` untouched (`git status` confirms). |
| 4 | NO_REINDEX | YES | Fix takes effect at search time against the existing `navigation_docs` collection. |
| 5 | NO_LIVE_CHROMA_MUTATION | YES | No writes; no reindex executed. |
| 6 | NO_DOCS_INDEX_MUTATION | YES | No artifacts written under any index path. |
| 7 | NO_TIMEOUT_DEFAULT_CHANGE | YES | `holo_index/core/holo_index.py` timeouts untouched (still 120 from #730). |
| 8 | NO_KNOWLEDGE_CHUNKING_CHANGE | YES | Indexer chunking logic untouched (#728 behavior preserved). |
| 9 | NO_SEARCH_ALGORITHM_REWRITE | YES | Single-function tier inside `_slice_id_match_boost`; cosine + lexical pipelines unchanged. |
| 10 | NO_TRADE_SPECIFIC_SPECIAL_CASE | YES | Rule contains no Trade-specific text, slice prefix, or filename. Proven by `TestNoTradeOrPathSpecialCase` and `TestGenericMetadataPrecedenceProperty`. |
| 11 | NO_PATH_SPECIFIC_SPECIAL_CASE | YES | Rule references no path string; behavior is uniform across slice prefixes. |
| 12 | EXACT_SLICE_ID_METADATA_PRECEDENCE | YES | Tier-1 boost gated on `meta_slice_id.upper() == query_slice`. |
| 13 | NON_SLICE_TRADE_QUERY_BEHAVIOR_PRESERVED | YES | Proven by `TestNonSliceTradeQueryBehaviorPreserved`; analyst-language queries still get path+alias cascade. |
| 14 | NO_PUBLIC_SURFACE_MUTATION | YES | `_slice_id_match_boost` signature unchanged; two new module-private constants added. |
| 15 | NO_WSP_MUTATION | YES | No file under `WSP_framework/` or `WSP_knowledge/` modified. |
| 16 | NO_DEPENDENCY_CHANGE | YES | `requirements*.txt` and `pyproject.toml` untouched. |
| 17 | NO_CI_CHANGE | YES | No file under `.github/workflows/` modified. |
| 18 | RUNTIME_OUTPUT_UNTOUCHED | YES | `holo_index/holo_index/output/holo_output_history.jsonl` left alone (separate hygiene slice). |
| 19 | T2_AUDIT_DOC_RANK_LIFTED | YES | Pre-fix CLI [DOCS] rank=2 (INTERFACE.md=1); post-fix CLI [DOCS] rank=1 (INTERFACE.md=2). |
| 20 | T1_T3_NO_REGRESSION | YES | T1 and T3 audit docs remained at [DOCS] rank=1 (verified via `python holo_index.py --search ...`). |

**WSP_97 VERDICT**: PASS (20/20)

---

## 1. Mission

Apply a generic search-time ranking rule that lifts audit/spec docs to
[DOCS] rank #1 for their exact slice-ID queries when they carry the
correct `slice_id` metadata, without special-casing any individual
slice, file path, or Trade-only terms. T1/T2/T3 must all rank #1 on
their respective slice-ID queries.

Non-slice-ID analyst queries (e.g., "trade due diligence scoring") must
continue to benefit from the Trade alias/path boost cascade. No reindex,
no indexer change.

---

## 2. Lineage and resume context

The original W7 slice (2026-05-24, base `d86450997` post-#701) wrote:

- `docs/audits/holoindex_search_quality/HOLOINDEX_T1_RANKING_QUALITY_PHASE1.md` (this audit)
- `holo_index/tests/test_t1_ranking_quality.py` (15 tests)

but never landed the actual code patch to
`holo_index/core/search_engine.py`. The patch and the four sibling
test-assertion updates were missing from the worktree.

Between then and this resume, two HoloIndex fixes landed:

- PR #728: full-body paper chunking (1451 chunks across 47 papers).
- PR #730: cold-process model import/load timeout raised to 120s.

Neither touched the ranking math; the T2 defect described below was
re-verified on `3dc26e6f9` and is unchanged.

---

## 3. WSP_97 CoT / CoA / CoE

### 3.1 CoT -- hypothesis and rank-factor analysis

For T2's exact slice-ID query `TRADE_ADAPTER_INTEGRATION_PHASE1` on the
post-#730 baseline, the keyword-score composition at
`holo_index/core/search_engine.py:_compute_keyword_score` is:

```
keyword_score = (
    _wsp_number_match_boost +    # 0 for non-WSP queries
    _wsp_alias_match_boost +     # 0 for non-WSP queries
    _slice_id_match_boost +      # 5.0 (flat) on exact slice-ID match (pre-fix)
    _work_ledger_combined_boost +
    _trade_path_boost +          # 8.0 for Trade target docs
    _trade_alias_keyword_boost   # up to 6.0
)
```

For T2's exact slice-ID query:

| Doc | slice_id | trade_path | trade_alias | Total |
|---|---|---|---|---|
| `docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md` | 5.0 | 0 | ~6.0 | ~11.0 |
| `modules/foundups/trade/INTERFACE.md` | 0 | 8.0 | ~6.0 | ~14.0 |

INTERFACE.md outranks the audit doc on its own slice-ID query because
the flat `_slice_id_match_boost` (5.0) cannot exceed the
`_trade_path_boost` + `_trade_alias_keyword_boost` cascade (up to 14.0).

The fix tiers the existing `_slice_id_match_boost` so an exact
`meta_slice_id` match returns 20.0 (strictly greater than 14.0). The
rule:

- Refers to no specific slice ID, filename, or module.
- Triggers only when (a) the query contains a literal slice-ID token AND
  (b) the document's `meta_slice_id.upper()` exactly equals that token.
- Leaves the path/title-only fallback at 5.0 so docs without populated
  `slice_id` metadata are not regressed.
- Returns 0.0 unchanged for queries that contain no slice-ID literal --
  so analyst-language queries still ride the Trade path/alias cascade.

### 3.2 CoA -- exact change

Single-function edit in `holo_index/core/search_engine.py`:

| Before | After |
|--------|-------|
| `_slice_id_match_boost` returned flat `5.0` for any slice-ID match across path, title, OR metadata. | Two module-private constants `_SLICE_ID_METADATA_PRECEDENCE_BOOST = 20.0` (tier 1) and `_SLICE_ID_PATH_OR_TITLE_BOOST = 5.0` (tier 2). The function checks metadata first; returns 20.0 when `meta_slice_id.upper()` matches a query-extracted slice ID, else returns 5.0 on path/title match, else 0.0. |

No other code path changed. No new file added under `holo_index/core/`.
No indexer touch. No Chroma writes. No reindex.

The lexical-fallback path (`_lexical_search_collection`) automatically
benefits from the same fix because it imports and calls the same
function.

### 3.3 CoE -- before / after evidence (post-#730 CLI)

CLI command used for each row:
`python holo_index.py --search "<slice_id>" --limit 10`

| Target | Slice ID | BEFORE [DOCS] rank-1 | T-doc rank | AFTER [DOCS] rank-1 | T-doc rank |
|--------|----------|----------------------|-----------:|---------------------|-----------:|
| T1 | `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` | T1 audit | 1 | T1 audit | 1 (unchanged) |
| T2 | `TRADE_ADAPTER_INTEGRATION_PHASE1` | `modules/foundups/trade/INTERFACE.md` | 2 | T2 audit | **1 (lifted)** |
| T3 | `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1` | T3 audit | 1 | T3 audit | 1 (unchanged) |

Architect success bar (T1/T2/T3 all [DOCS] rank #1): **MET**.

**No-reindex proof**: this slice did not invoke `python holo_index.py
--index-docs` nor any indexer entrypoint. The same persistent Chroma
collection at `E:/HoloIndex/vectors` is queried before and after.

---

## 4. DESIGN -- the rule

For any slice-ID `S` extracted from the query, a document whose
`metadata.slice_id.upper() == S` receives the tier-1 precedence boost
`_SLICE_ID_METADATA_PRECEDENCE_BOOST` (20.0). Otherwise, if `S` appears
in the document's path or title, the tier-2 fallback
`_SLICE_ID_PATH_OR_TITLE_BOOST` (5.0) applies. Otherwise 0.0.

**Why 20.0**: it must strictly exceed the maximum sum of all current
non-slice-id keyword boosts. The dominant non-slice-id stack is
`_trade_path_boost.cap (8.0) + _trade_alias_keyword_boost.cap (6.0) =
14.0`. 20.0 leaves a 6-point margin against accidental escalation. This
invariant is pinned by
`TestSliceIdPrecedenceConstants::test_metadata_precedence_exceeds_max_trade_combination`,
which reads the caps directly from the boost helpers and asserts strict
inequality -- so any future cap increase will fail loudly before
causing a silent regression.

**Why path/title fallback stays at 5.0**: docs whose `slice_id`
metadata is empty (e.g., older docs that have not been re-indexed under
the HXA fix) still receive the original 5.0 boost. The fix is strictly
additive to the existing tier; no doc loses a boost.

---

## 5. IMPLEMENTATION -- files changed

| File | Change | Reason |
|------|--------|--------|
| `holo_index/core/search_engine.py` | MODIFIED -- two module-private constants (`_SLICE_ID_METADATA_PRECEDENCE_BOOST`, `_SLICE_ID_PATH_OR_TITLE_BOOST`); `_slice_id_match_boost` tiered into metadata-precedence vs. path/title tiers. | The fix itself. |
| `holo_index/tests/test_t1_ranking_quality.py` | NEW (resumed from W7) -- 15 tests pinning the precedence constants, per-target metadata-wins property, and anti-overfit / no-Trade-special-case / non-slice-id-query-behavior-preserved invariants. | Slice scope item 2. |
| `holo_index/tests/test_audit_spec_slice_id_indexing.py` | MODIFIED -- 4 assertion-only updates to reference the new tier constants; docstrings updated to record the tiered semantics. | Reflect tiered policy; no behavioral change to those tests. |
| `holo_index/tests/test_hxa_retrieval_fix.py` | MODIFIED -- 2 assertion-only updates to reference the new tier constants. | Reflect tiered policy. |
| `docs/audits/holoindex_search_quality/HOLOINDEX_T1_RANKING_QUALITY_PHASE1.md` | NEW (this audit -- W6 resume) | Slice scope item 3; W7 dirty file repaired. |
| `holo_index/ModLog.md` | MODIFIED -- W6 resume entry. | WSP 22. |

Files **not** touched (boundary preserved):

- `holo_index/core/indexing_engine.py`
- `holo_index/core/holo_index.py` (no timeout-default change)
- Any Chroma collection / persisted vector
- `modules/foundups/trade/**`
- `modules/foundups/registry/**`, `manifest/**`, `projection/**`, `catalog/**`
- `WSP_framework/**`, `WSP_knowledge/**`
- CI workflow files
- `holo_index/holo_index/output/holo_output_history.jsonl` (runtime output -- separate hygiene slice)

---

## 6. VERIFICATION

### 6.1 Targeted ranking-quality suites

```
$ python -m pytest holo_index/tests/test_t1_ranking_quality.py \
                   holo_index/tests/test_hxa_retrieval_fix.py \
                   holo_index/tests/test_audit_spec_slice_id_indexing.py -q
65 passed in 2.64s
```

Per-suite breakdown:

| Suite | Status |
|-------|--------|
| `test_t1_ranking_quality.py` (resumed) | PASS (15 tests) |
| `test_hxa_retrieval_fix.py` (2 assertions updated) | PASS |
| `test_audit_spec_slice_id_indexing.py` (4 assertions updated) | PASS |

### 6.2 CLI ranking proof

```
$ python holo_index.py --search "TRADE_ADAPTER_INTEGRATION_PHASE1" --limit 10
[DOCS] docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md   <- rank 1 (lifted)
[DOCS] modules/foundups/trade/INTERFACE.md                            <- rank 2

$ python holo_index.py --search "TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1" --limit 10
[DOCS] docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md   <- rank 1

$ python holo_index.py --search "HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1" --limit 10
[DOCS] docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md   <- rank 1
```

### 6.3 HoloIndex retrieval evaluation (WSP 87)

| Query | Surfaced expected docs? | Quality |
|-------|-------------------------|---------|
| `slice id metadata precedence ranking boost HoloIndex` | YES -- HOLOINDEX audit docs in [DOCS]; `holoindex_plugin.py` in [CODE]. | OK |
| `TRADE_ADAPTER_INTEGRATION_PHASE1 ranking interface outranks audit` | YES -- T2 audit doc in [DOCS]; HIA_AGENTIC_RAG_RANKING_QUALITY_PHASE6 surfaced (relevant prior ranking work). | OK |
| `HOLOINDEX_T1_RANKING_QUALITY_PHASE1` | NO (pre-fix) -- this audit doc had not yet been indexed; sibling HOLOINDEX_* audit docs surfaced instead. | EXPECTED (no reindex run) |

The third query's gap is expected: this audit doc is freshly written
this slice and not yet in the `navigation_docs` collection. A future
docs-reindex slice will pick it up; that is out of scope here per
`NO_REINDEX`.

---

## 7. Anti-overfit guarantees

Pinned by `holo_index/tests/test_t1_ranking_quality.py`:

- `TestNoTradeOrPathSpecialCase::test_non_slice_id_query_returns_zero` --
  analyst-language queries (no slice-ID literal) get 0.0 from
  `_slice_id_match_boost`, so Trade alias/path boosts still control
  ranking on those queries.
- `TestNoTradeOrPathSpecialCase::test_metadata_match_works_for_non_trade_slice` --
  a HOLOINDEX-domain slice (no Trade content) gets the tier-1 boost --
  the rule is not Trade-specific.
- `TestNoTradeOrPathSpecialCase::test_unrelated_slice_id_no_boost` -- a
  doc with a different `meta_slice_id` than the query gets 0.0 -- not
  a blanket "all audit docs win" lever.
- `TestNoTradeOrPathSpecialCase::test_path_only_slice_match_keeps_original_5point0` --
  backward-compatible: docs with empty `meta_slice_id` still get the
  tier-2 (5.0) boost from path/title match.
- `TestNonSliceTradeQueryBehaviorPreserved::test_trade_path_boost_still_fires_for_trade_target_docs` --
  `_trade_path_boost` still returns 8.0 for Trade target docs on
  analyst queries.
- `TestNonSliceTradeQueryBehaviorPreserved::test_trade_alias_boost_still_fires_for_alias_match` --
  `_trade_alias_keyword_boost` still fires for alias queries.
- `TestGenericMetadataPrecedenceProperty::test_arbitrary_holoindex_slice_id_metadata_wins`,
  `..._foundups_slice_id_metadata_wins`,
  `..._short_form_slice_id_metadata_wins` -- the rule applies uniformly
  to any slice ID, any prefix (HOLOINDEX_, FOUNDUPS_, HXA*), any path.

---

## 8. Completion Summary

| Item | Value |
|------|-------|
| Decision | RESUME_AND_REPAIR |
| Branch | `main` (working tree -- this audit + sibling files) |
| Worker-Lane | W6 |
| Slice | `HOLOINDEX_T1_RANKING_QUALITY_PHASE1` |
| Base commit | `3dc26e6f9` (origin/main, post-PR #730) |
| Files changed | 6 (1 src tier, 1 new test file resumed, 2 sibling test-assertion updates, 1 audit doc rewrite, 1 ModLog entry) |
| Dirty files resolved | both (audit doc repaired + lineage updated; tests reconciled with code) |
| Runtime output untouched | YES (`holo_index/holo_index/output/holo_output_history.jsonl` not modified) |
| Reindex executed | NO |
| T1 [DOCS] rank (BEFORE -> AFTER) | 1 -> 1 (unchanged) |
| T2 [DOCS] rank (BEFORE -> AFTER) | 2 -> **1 (lifted)** |
| T3 [DOCS] rank (BEFORE -> AFTER) | 1 -> 1 (unchanged) |
| Architect success bar (T1/T2/T3 all #1) | MET |
| Tests run | `test_t1_ranking_quality.py` + `test_hxa_retrieval_fix.py` + `test_audit_spec_slice_id_indexing.py` -- 65 passed |
| WSP_97 truth boundary | PASS (20/20) |

---

**Worker-Lane**: W6
**Slice**: `HOLOINDEX_T1_RANKING_QUALITY_PHASE1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22
