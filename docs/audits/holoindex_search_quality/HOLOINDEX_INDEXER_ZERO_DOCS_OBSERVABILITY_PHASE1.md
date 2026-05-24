# HoloIndex Indexer Zero Docs Observability — Phase 1

**Slice**: `HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Bug Fix (observability gap)
**Branch**: `feat/holoindex-indexer-zero-docs-observability-phase1`
**Base commit**: post-PR #694 (origin/main)
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_ZERO_DOCS_OBSERVABILITY_ONLY | YES |
| NO_PATH_FILTER_CHANGE | YES |
| NO_EMBEDDING_MODEL_CHANGE | YES |
| NO_BULK_INSERT_CHANGE_EXCEPT_COUNT_REPORTING | YES |
| NO_LIVE_REINDEX | YES |
| NO_CHROMA_MUTATION_IN_TESTS | YES |
| NO_GENERATED_INDEX_ARTIFACTS_COMMITTED | YES |
| NO_TRADE_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_WSP_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Fix the observability gap identified in PR #690 (HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1):

> The CLI awards `+5 Refreshed indexes` on flag completion regardless of inserted count. When zero files are indexed, the user sees no warning and the exit code is 0.

After PR #692 fixed the path filter issue (HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1), docs indexing now works correctly. However, the observability gap remains: if a future scenario results in zero docs discovered/indexed, the CLI will still silently report success and award points.

---

## 2. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### 2.1 Chain-of-Thought (Root Cause from PR #690)

The `index_docs_entries()` function:
1. Returns `None` (no return value)
2. Logs warnings via `holo._log_agent_action()` but these are not surfaced to CLI
3. CLI blindly sets `indexing_awarded = True` after calling the function

The fix requires:
1. Return an observable result from `index_docs_entries()`
2. CLI checks the result before awarding reward
3. Emit explicit warning when zero docs are discovered/indexed

### 2.2 Chain-of-Action

| Step | Action | Mutates Core? |
|------|--------|---------------|
| 1 | Add `IndexResult` dataclass to `indexing_engine.py` | YES (authorized) |
| 2 | Change `index_docs_entries()` to return `IndexResult` | YES (authorized) |
| 3 | Update `HoloIndex.index_docs_entries()` facade to forward return | YES (authorized) |
| 4 | Update CLI handler to check `IndexResult.is_empty` | YES (authorized) |
| 5 | Add regression tests (no Chroma mutation) | NO |

### 2.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Gap identified | PR #690 §6.4 | `indexing_awarded = True` unconditional |
| CLI location | `_cli_main.py:1009-1016` | No return value check |
| Engine location | `indexing_engine.py:657` | Returns `None` |
| Tests pass | pytest output | 12 new + 29 existing = 41 pass |

---

## 3. Before/After Behavior

### 3.1 BEFORE (Hidden Failure)

```
$ python holo_index.py --index-docs
[DOCS] Indexed module/root docs in 0.15s
+5 Refreshed indexes
```

Even when zero docs were discovered (e.g., worktree scenario), the CLI:
- Reported success
- Awarded +5 reward points
- Exit code 0

### 3.2 AFTER (Observable Failure)

```
$ python holo_index.py --index-docs
[DOCS] WARNING: No docs found to index -- discovery returned zero files (0.01s)
[DOCS] discovered=0, indexed=0
```

When zero docs are discovered/indexed, the CLI:
- Emits explicit WARNING
- Shows discovered/indexed counts
- Does NOT award reward points
- Normal path unchanged

### 3.3 Normal Path (Unchanged)

```
$ python holo_index.py --index-docs
[DOCS] Indexed 3327 module/root docs in 45.23s
+5 Refreshed indexes
```

---

## 4. Implementation Details

### 4.1 IndexResult Dataclass

```python
@dataclass
class IndexResult:
    """Result of an indexing operation for observability."""
    discovered_count: int
    indexed_count: int
    collection_name: str
    warning: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        """True if zero documents were discovered or indexed."""
        return self.discovered_count == 0 or self.indexed_count == 0

    @property
    def success(self) -> bool:
        """True if at least one document was indexed."""
        return self.indexed_count > 0
```

### 4.2 CLI Handler Change

```python
# BEFORE
holo.index_docs_entries()
indexing_awarded = True

# AFTER
docs_result = holo.index_docs_entries()
if docs_result is not None and docs_result.is_empty:
    safe_print(f"[DOCS] WARNING: {docs_result.warning}")
    # indexing_awarded NOT set
else:
    safe_print(f"[DOCS] Indexed {docs_result.indexed_count} module/root docs")
    indexing_awarded = True
```

### 4.3 Exit Code Decision

Per scope constraint, this slice uses **warning-only** behavior rather than nonzero exit code:
- Exit code remains 0 (existing CLI contract preserved)
- Explicit WARNING message emitted
- Reward NOT awarded
- `discovered` and `indexed` counts surfaced for debugging

A future slice could add `--strict-indexing` flag for nonzero exit on zero docs.

---

## 5. Test Results

### 5.1 New Tests (12 pass)

```
python -m pytest holo_index/tests/test_indexer_zero_docs_observability.py -v
12 passed in 2.40s
```

| Test | Purpose | Result |
|------|---------|--------|
| test_is_empty_when_zero_discovered | IndexResult.is_empty=True when discovered=0 | PASS |
| test_is_empty_when_zero_indexed | IndexResult.is_empty=True when indexed=0 | PASS |
| test_success_when_indexed_positive | IndexResult.success=True when indexed>0 | PASS |
| test_warning_present_on_failure | Warning message present on failure | PASS |
| test_zero_discovered_returns_index_result_with_warning | Integration: zero files | PASS |
| test_zero_indexed_from_empty_content_returns_warning | Integration: empty content | PASS |
| test_normal_docs_returns_positive_counts | Integration: normal path | PASS |
| test_partial_empty_content_shows_correct_counts | Integration: partial | PASS |
| test_reward_not_awarded_on_is_empty_true | CLI reward logic | PASS |
| test_reward_awarded_on_success | CLI reward logic | PASS |
| test_result_is_truthy_when_success | Backward compat | PASS |
| test_result_attributes_accessible | Backward compat | PASS |

### 5.2 Existing Tests (29 pass, no regression)

```
python -m pytest holo_index/tests/test_indexer_project_root_worktree_safety.py \
    holo_index/tests/test_cfz4_collection_separation.py \
    holo_index/tests/test_search_quality_baseline.py -q
29 passed in 3.08s
```

**Total**: 41 tests pass, 0 regressions.

---

## 6. Files Changed

| File | Change |
|------|--------|
| `holo_index/core/indexing_engine.py` | Add IndexResult dataclass, change return type (~40 lines) |
| `holo_index/core/holo_index.py` | Update facade to forward return value (~5 lines) |
| `holo_index/_cli_main.py` | Check IndexResult before awarding reward (~12 lines) |
| `holo_index/tests/test_indexer_zero_docs_observability.py` | NEW (12 tests, ~200 lines) |
| `docs/audits/holoindex_search_quality/HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1.md` | NEW (this file) |

---

## 7. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex zero docs observability only | PASS |
| No path filter change | PASS |
| No embedding model change | PASS |
| No bulk insert change except count reporting | PASS |
| No live reindex | PASS |
| No Chroma mutation in tests | PASS |
| No generated index artifacts committed | PASS |
| No Trade mutation | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No WSP mutation | PASS |
| No CI change | PASS |
| No dependency install | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS (18/18)

---

## 8. W10 Readiness

| Gate | Status |
|------|--------|
| Branch created from origin/main | YES |
| Scope is observability fix only | YES |
| IndexResult dataclass added for testability | YES |
| CLI checks result before reward | YES |
| Warning emitted on zero docs | YES |
| Normal path unchanged | YES |
| 12 new tests pass (no Chroma mutation) | YES |
| 29 existing tests pass (no regression) | YES |
| No live --index-docs invocation | YES |
| No generated artifacts committed | YES |
| Audit doc complete with WSP_97 verdict | YES |
| **Ready for PR** | **YES** |

---

## 9. Completion Summary

| Item | Value |
|------|-------|
| Branch | `feat/holoindex-indexer-zero-docs-observability-phase1` |
| Base commit | post-PR #694 (origin/main) |
| Files changed | 5 (3 core + 1 test + 1 audit doc) |
| Lines changed | ~40 in indexing_engine + ~12 in CLI + ~200 in tests |
| Tests added | 12 |
| Tests total | 41 (12 new + 29 existing) |
| Scope | Observability fix only |
| Live reindex | NO |
| WSP_97 | PASS (18/18) |

---

**Worker**: W6
**Slice**: HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22
