# HoloIndex Indexer Project Root Worktree Safety — Phase 1

**Slice**: `HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Bug Fix (path filter)
**Branch**: `feat/holoindex-indexer-project-root-worktree-safety-phase1`
**Base commit**: `6f9ba8c14` (origin/main, post-PR #690)
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_INDEXER_PATH_FILTER_FIX_ONLY | YES |
| HOLOINDEX_CORE_MUTATION_AUTHORIZED_FOR_WORKTREE_SAFETY | YES |
| WORKTREE_PATH_SAFETY_ONLY | YES |
| INTENT_PRESERVED_DOTFILES_INSIDE_DOCS_STILL_REJECTED | YES |
| NO_CLI_REWARD_CHANGE | YES |
| NO_EMBEDDING_MODEL_CHANGE | YES |
| NO_BULK_INSERT_CHANGE | YES |
| NO_RESET_COLLECTION_CHANGE | YES |
| NO_LIVE_REINDEX | YES |
| NO_CHROMA_MUTATION_IN_TESTS | YES |
| NO_GENERATED_INDEX_ARTIFACTS_COMMITTED | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_TRADE_MUTATION | YES |
| NO_WSP_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Fix the docs-index file filter in `holo_index/core/indexing_engine.py` so that
worktree parent directories like `.claude` do not cause every docs file to be
rejected. The fix is a narrow path-filter change plus regression tests.

---

## 2. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### 2.1 Chain-of-Thought (Assumptions / Root Cause Summary)

PR #690 confirmed root cause H1+H4 interlock:
- `project_root = Path(__file__).parent.parent.parent` resolves to worktree path
- Line 650: `not any(part.startswith('.') for part in f.parts)` checks **absolute** path parts
- When running from `.claude/worktrees/X/`, every absolute path contains `.claude`
- The `.claude` component starts with `.`, so the filter rejects **ALL** files
- Result: 387/387 docs rejected, empty list short-circuits, CLI reports success

### 2.2 Chain-of-Action

| Step | Action | Mutates Core? |
|------|--------|---------------|
| 1 | Confirm root cause from PR #690 audit | NO |
| 2 | Locate exact filter clause at L650 and redundant clauses at L655-656 | NO |
| 3 | Add helper `_has_dotfile_in_relative_path()` | YES (authorized) |
| 4 | Replace absolute-path check with relative-path check | YES (authorized) |
| 5 | Remove redundant `.claude/worktrees` clauses | YES (authorized) |
| 6 | Add regression tests A-E (synthetic paths, no Chroma) | NO |
| 7 | Run required HoloIndex test suites | NO |

### 2.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Root cause confirmed | PR #690 audit §6.2 | 387/387 files rejected by dot-prefix clause |
| Filter location | `indexing_engine.py:650` | `not any(part.startswith('.') for part in f.parts)` |
| Redundant clauses | `indexing_engine.py:655-656` | `.claude/worktrees` substring checks |
| Fix applied | `indexing_engine.py:650` | `not _has_dotfile_in_relative_path(f, base)` |
| Helper added | `indexing_engine.py:100-131` | `_has_dotfile_in_relative_path()` function |
| Tests pass | pytest output | 7 new tests + 183 existing = 190 pass |

---

## 3. HoloIndex WSP_50 Retrieval Assessment

As documented in PR #690 audit §3, HoloIndex retrieval for recent audit docs
remains degraded because `navigation_docs` has not been refreshed. The slice ID
queries `HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1` and
`HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1` return weak/no results.

| Query | Quality | Notes |
|-------|---------|-------|
| `HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1` | WEAK | Audit doc not surfaced by slice ID |
| `indexing_engine docs file filter dotfile` | WEAK | Core file not in top hits |
| `project_root worktree path resolution` | WEAK | Generic results |

**Fallback**: Direct file reads via `Read` tool. This is expected given the
collection state — the fix in this slice will enable the operator-gated
reindex in the follow-on slice.

---

## 4. Before/After Diff of Filter Logic

### 4.1 BEFORE (L645-657)

```python
filtered_files = [
    f for f in all_doc_files
    if 'node_modules' not in str(f)
    and 'CHANGELOG' not in f.name.upper()
    and 'package-lock' not in f.name.lower()
    and not any(part.startswith('.') for part in f.parts)  # L650: BUG
    and '_backup' not in str(f).lower()
    and '/archive/' not in str(f).lower()
    and '\\archive\\' not in str(f).lower()
    # HXA Audit Fix: Exclude worktrees to prevent duplicates
    and '.claude/worktrees' not in str(f).replace("\\", "/").lower()  # L655: redundant
    and '.worktrees' not in str(f).replace("\\", "/").lower()  # L656: redundant
]
```

### 4.2 AFTER (L645-656)

```python
filtered_files = [
    f for f in all_doc_files
    if 'node_modules' not in str(f)
    and 'CHANGELOG' not in f.name.upper()
    and 'package-lock' not in f.name.lower()
    # Worktree safety fix: Check dot-prefix relative to base, not absolute path.
    # This prevents rejecting all files when project_root is under .claude/worktrees/.
    and not _has_dotfile_in_relative_path(f, base)
    and '_backup' not in str(f).lower()
    and '/archive/' not in str(f).lower()
    and '\\archive\\' not in str(f).lower()
    # Note: The .claude/worktrees clauses previously here are now redundant
    # because the relative-path check ignores parent directories above base.
]
```

### 4.3 New Helper Function (L100-131)

```python
def _has_dotfile_in_relative_path(file_path: Path, base: Path) -> bool:
    """Check if any component of the relative path starts with a dot.

    This replaces the absolute-path dot-prefix check to fix worktree safety:
    when project_root is under .claude/worktrees/, the absolute path contains
    .claude as a component, which would incorrectly reject ALL files.

    By checking only the path relative to the discovery base, we skip dotfiles
    INSIDE the docs tree (e.g., .draft/, .DS_Store) while accepting files
    whose absolute path happens to traverse a dot-prefixed parent directory.

    Args:
        file_path: Absolute path to the file
        base: Discovery base directory (e.g., project_root / "docs")

    Returns:
        True if any relative path component starts with '.', False otherwise.
        Also returns True if file_path is not under base (fail-closed).
    """
    try:
        relative_parts = file_path.relative_to(base).parts
        return any(part.startswith('.') for part in relative_parts)
    except ValueError:
        # file_path is not under base — reject (fail-closed)
        return True
```

---

## 5. Intent Preservation

The original intent of the dot-prefix filter was to skip dotfiles **inside**
the docs tree (e.g., `.git/`, `.cache/`, `.DS_Store`). This intent is preserved:

| Test | Path Pattern | Expected | Actual |
|------|--------------|----------|--------|
| C | `<base>/.draft/foo.md` | REJECTED | REJECTED |
| D | `<base>/.DS_Store` | REJECTED | REJECTED |
| Extra | `<base>/audits/.hidden/file.md` | REJECTED | REJECTED |

The fix only changes behavior for paths where the dot-prefix component is
**above** the discovery base (e.g., in `.claude/worktrees/`), which was never
the intended exclusion target.

---

## 6. Out-of-Scope Items (Deliberately Deferred)

### 6.1 CLI Reward Issue

The CLI awards `+5 Refreshed indexes` on flag completion regardless of
inserted count. When zero files are indexed, the user sees no warning and
the exit code is 0.

**Follow-up slice**: `HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1`

This is explicitly out of scope for this slice per the task prompt.

### 6.2 `index_knowledge_entries` Same Pattern

Line 762 in `index_knowledge_entries()` has the same absolute-path dot-prefix
check. Per scope constraint "DO NOT touch any other function in this module",
this is deferred to a follow-on slice.

---

## 7. Post-Merge Plan

After this PR merges, an operator-gated `--index-docs` observation slice
should be run from the **main repo** (not a worktree) to verify that:
1. All 387+ docs are discovered
2. All 9 missing architecture audit docs surface in `navigation_docs`
3. Before/after gap closes (42 = 42 for architecture docs)

**Follow-up slice**: `HOLOINDEX_DOCS_REINDEX_POST_FIX_OBSERVATION_PHASE1`

This PR does NOT itself run reindex.

---

## 8. Test Results

### 8.1 New Tests (7 pass)

```
python -m pytest holo_index/tests/test_indexer_project_root_worktree_safety.py -v
7 passed in 3.51s
```

| Test | Purpose | Result |
|------|---------|--------|
| test_a_worktree_path_not_rejected | Worktree path with clean relative path | PASS |
| test_b_main_repo_path_not_rejected | Main repo path | PASS |
| test_c_dotfile_inside_docs_tree_rejected | `.draft/foo.md` rejected | PASS |
| test_d_hidden_file_rejected | `.DS_Store` rejected | PASS |
| test_e_path_outside_base_rejected | Path outside base (fail-closed) | PASS |
| test_nested_dotfile_directory_rejected | Nested `.hidden/` rejected | PASS |
| test_deep_worktree_path_not_rejected | Deep worktree path | PASS |

### 8.2 Required HoloIndex Test Suites (183 pass)

```
python -m pytest holo_index/tests/test_audit_spec_slice_id_indexing.py \
    holo_index/tests/test_hxa_retrieval_fix.py \
    holo_index/tests/test_work_ledger_indexing.py \
    holo_index/tests/test_search_quality_baseline.py \
    holo_index/tests/test_cfz4_collection_separation.py \
    holo_index/tests/test_trade_query_alias_retrieval.py -q
183 passed in 12.74s
```

**Total**: 190 tests pass, 0 regressions.

---

## 9. Files Changed

| File | Change |
|------|--------|
| `holo_index/core/indexing_engine.py` | Add helper + fix filter (~35 lines) |
| `holo_index/tests/test_indexer_project_root_worktree_safety.py` | NEW (7 tests, ~180 lines) |
| `docs/audits/holoindex_search_quality/HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1.md` | NEW (this file) |

---

## 10. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex indexer path filter fix only | PASS |
| HoloIndex core mutation authorized for worktree safety | PASS |
| Worktree path safety only | PASS |
| Intent preserved (dotfiles inside docs still rejected) | PASS |
| No CLI reward change | PASS |
| No embedding model change | PASS |
| No bulk insert change | PASS |
| No reset collection change | PASS |
| No live reindex | PASS |
| No Chroma mutation in tests | PASS |
| No generated index artifacts committed | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No Trade mutation | PASS |
| No WSP mutation | PASS |
| No CI change | PASS |
| No dependency install | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS (22/22)

---

## 11. W10 Readiness

| Gate | Status |
|------|--------|
| Branch created from origin/main | YES |
| Scope is path-filter-only | YES |
| Helper function added for testability | YES |
| Redundant `.claude/worktrees` clauses removed | YES |
| 7 regression tests pass (A-E + extras) | YES |
| 183 existing HoloIndex tests pass | YES |
| No live `--index-docs` invocation | YES |
| No Chroma writes in tests | YES |
| No generated artifacts committed | YES |
| Audit doc complete with WSP_97 verdict | YES |
| Out-of-scope items documented | YES |
| Post-merge plan documented | YES |
| **Ready for PR** | **YES** |

---

## 12. Completion Summary

| Item | Value |
|------|-------|
| Branch | `feat/holoindex-indexer-project-root-worktree-safety-phase1` |
| Base commit | `6f9ba8c14` |
| Files changed | 3 (indexing_engine.py, test file, audit doc) |
| Lines changed | ~35 in core + ~180 in tests |
| Tests added | 7 |
| Tests total | 190 (7 new + 183 existing) |
| Scope | Path filter fix only |
| Live reindex | NO |
| WSP_97 | PASS (22/22) |

---

**Worker**: W6
**Slice**: HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22
