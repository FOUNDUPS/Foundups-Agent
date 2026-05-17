# HOLOINDEX_HXA_AUDIT_RETRIEVAL_IMPROVEMENT_AUDIT_PHASE1

**Slice**: HOLOINDEX_HXA_AUDIT_RETRIEVAL_IMPROVEMENT_AUDIT_PHASE1
**Worker**: W9
**Date**: 2026-05-14
**Mode**: DOCS_ONLY (No code changes, no reindexing)
**WSP Lock**: WSP_00 -> WSP_97 -> WSP_87 -> WSP_50

---

## 1. Retrieval Summary

### HoloIndex Query Results Assessment

| Query | Expected Result | Actual Result | Verdict |
|-------|-----------------|---------------|---------|
| "destructive action guard path validation" | HXA22, destructive_action_guard.py | WRE_DESTRUCTIVE_ACTION_GUARD.md (docs), no HXA22 | **PARTIAL** |
| "HXA22 destructive action guard runtime" | HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md | HXA1, HXA2 (wrong slices), WRE_DESTRUCTIVE_ACTION_GUARD.md | **MISS** |
| "HXA23 Hermes guard integration" | HXA23_HERMES_GUARD_INTEGRATION.md | HXA1, hermes_job_executor.py | **MISS** |
| "HXA28 D3 native classification" | HXA28_D3_NATIVE_CLASSIFICATION.md | Unrelated files (gemma_segment_classifier.py) | **MISS** |
| "HXA30 scope action class integration" | HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION.md | 5 "Unknown" (43-45% relevance), WSP 29 | **FAIL** |
| "Gemini architectural feedback destructive guard" | GEMINI_ARCHITECTURE_RECONCILIATION.md | pqn_alignment/guardrail.py, GEMINI.md | **PARTIAL** |

### rg Fallback Verification

**Actual HXA files in docs/audits/openclaw_hermes/**:
- HXA1, HXA2, HXA5-8, HXA11, HXA13, HXA15, HXA17-30 (23 files total)

**Actual guard files in modules/infrastructure/wre_core/**:
- `src/destructive_action_guard.py`
- `tests/test_destructive_action_guard_edge_cases.py`
- `tests/test_hxa22_destructive_action_guard_runtime.py`
- `tests/test_hxa23_hermes_guard_integration.py`
- `tests/test_hxa28_d3_native_classification.py`
- `tests/test_hxa30_scope_to_action_class_integration.py`

---

## 2. Missed Files Table

| File | Expected Query | Should Match | Actually Matched |
|------|----------------|--------------|------------------|
| HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md | "HXA22 destructive action guard runtime" | Yes (exact slice ID) | No |
| HXA23_HERMES_GUARD_INTEGRATION.md | "HXA23 Hermes guard integration" | Yes (exact slice ID) | No |
| HXA28_D3_NATIVE_CLASSIFICATION.md | "HXA28 D3 native classification" | Yes (exact slice ID) | No |
| HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION.md | "HXA30 scope action class" | Yes (exact slice ID) | No |
| destructive_action_guard.py | "destructive action guard" | Yes | No (only doc returned) |
| test_hxa22_destructive_action_guard_runtime.py | "HXA22 test" | Yes | No |
| test_hxa23_hermes_guard_integration.py | "HXA23 test" | Yes | No |
| test_hxa28_d3_native_classification.py | "HXA28 test" | Yes | No |
| test_hxa30_scope_to_action_class_integration.py | "HXA30 test" | Yes | No |

---

## 3. Noisy Results Table

| Query | Noise Result | Relevance | Why Noise |
|-------|--------------|-----------|-----------|
| "HXA30 scope action class" | "Unknown" (5 results) | 42-45% | No file path preserved in metadata |
| "HXA22 destructive action" | HXA1, HXA2 | ~50% | Semantically similar but wrong slice |
| "Gemini architectural feedback" | pqn_alignment/guardrail.py | ~48% | "Guardrail" semantic match but wrong domain |
| "HXA28 D3 native" | gemma_segment_classifier.py | ~47% | "Classification" semantic match but wrong domain |

---

## 4. Root Cause Hypotheses

### H1: docs/audits/ Not Fully Indexed in navigation_docs

**Evidence**:
- `index_docs_entries()` scans: `modules/`, `docs/`, `holo_index/docs/`, `WSP_framework/docs/`
- `docs/` is included, BUT audits under `docs/audits/openclaw_hermes/` may be filtered
- Filter excludes: `CHANGELOG`, `package-lock`, hidden dirs, `_backup`, `/archive/`
- **HXA files should pass these filters** - hypothesis partially ruled out

**Root cause likelihood**: 30%

### H2: Slice IDs (HXA22, HXA23, etc.) Not Tokenized/Weighted

**Evidence**:
- Embedding is generated from `f"{title}\n{summary}"` (first 6 lines, 400 chars)
- Title like "HXA22 - Destructive Action Guard Runtime" should embed "HXA22"
- BUT: Semantic embedding treats "HXA22" as an unknown token (no pre-training)
- Sentence-transformers `all-MiniLM-L6-v2` has no HXA vocabulary

**Root cause likelihood**: 70%

### H3: File Path Not Preserved in Search Results

**Evidence**:
- Query "HXA30 scope action class" returned 5 "Unknown" locations
- Metadata includes `path` field but display layer shows "Unknown"
- This is a **result formatting bug**, not indexing bug

**Root cause likelihood**: 90% (for Unknown results)

### H4: Test Files Not Indexed

**Evidence**:
- `index_symbol_entries()` scans `modules/` including test files
- BUT: Scans for functions/classes, not test file names
- `test_hxa22_destructive_action_guard_runtime.py` filename not indexed as document
- Test docstrings/class names not boosted

**Root cause likelihood**: 80%

### H5: Worktree Duplicates Creating Noise

**Evidence**:
- 45 worktrees in `.claude/worktrees/`
- Each worktree is a full repo copy
- If worktrees are indexed, duplicate HXA files could dilute relevance

**Root cause likelihood**: 20% (glob pattern unlikely to hit worktrees)

---

## 5. Required Indexing Coverage

### Priority 1: Explicit Audit Doc Indexing

```yaml
Collection: navigation_docs (or new navigation_audits)
Paths:
  - docs/audits/**/*.md
  - docs/audits/openclaw_hermes/HXA*.md (explicit)
  - docs/audits/holoindex/*.md
  - docs/audits/softproto/**/*.md
  - docs/audits/security/**/*.md
```

### Priority 2: Slice ID Keyword Extraction

```yaml
Pattern: Extract slice IDs from filenames and titles
Examples:
  - HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md -> keywords: ["HXA22", "HXA", "destructive", "action", "guard", "runtime"]
  - test_hxa30_scope_to_action_class_integration.py -> keywords: ["HXA30", "scope", "action", "class"]
Storage: metadata.slice_id, metadata.keywords
```

### Priority 3: Test File Indexing

```yaml
Collection: navigation_tests (expand from registry-only)
Paths:
  - modules/**/tests/test_*.py
  - holo_index/tests/test_*.py
Extract:
  - Filename tokens (test_hxa22 -> HXA22)
  - Docstrings mentioning slice IDs
  - Test class names (TestHXA22DestructiveActionGuardRuntime)
```

### Priority 4: Worktree Exclusion

```yaml
Skip_Dirs:
  - .claude/worktrees
  - .git
  - __pycache__
  - node_modules
Prevent: Duplicate indexing of agent worktree copies
```

---

## 6. Ranking/Weighting Recommendations

### R1: Exact Slice ID Match Boost

```python
def boost_slice_id_match(query: str, metadata: dict) -> float:
    """Boost documents where query contains exact slice ID."""
    slice_id = metadata.get("slice_id", "")
    if slice_id and slice_id.upper() in query.upper():
        return 1.5  # 50% boost
    return 1.0
```

### R2: Recent Audit Doc Priority

```python
def boost_recent_audits(file_path: Path) -> float:
    """Boost audits modified within last 30 days."""
    if "/audits/" in str(file_path):
        mtime = file_path.stat().st_mtime
        if time.time() - mtime < 30 * 86400:
            return 1.3
    return 1.0
```

### R3: Audit Path Priority Map

```python
priority_map = {
    "docs/audits/openclaw_hermes": 9,  # HXA series
    "docs/audits/holoindex": 9,
    "docs/audits/security": 8,
    "docs/audits/softproto": 7,
    "docs/architecture": 7,
}
```

### R4: Preserve File Path in Results

```python
# Current: returns "Unknown" when path missing
# Fix: Ensure metadata["path"] always populated and returned
result["location"] = metadata.get("path", str(file_path))
```

---

## 7. Minimal Fix Proposal

### Phase 1: Docs-Only Spec (This Slice)

1. Document root causes (DONE in this file)
2. Specify indexing changes (DONE above)
3. Define acceptance criteria for next slice

### Phase 2: Indexing Fix (Next Slice - HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1)

**Minimal code changes**:

1. **indexing_engine.py** `index_docs_entries()`:
   - Add explicit `docs/audits/**/*.md` scan
   - Extract slice IDs from filenames (regex: `(HXA\d+|FX\d+|CFZ\d+)`)
   - Store in `metadata.slice_id`

2. **indexing_engine.py** `_calculate_document_priority()`:
   - Add audit path priority boost (see R3 above)

3. **search_engine.py** `_search_collection()`:
   - Ensure `path` metadata always returned (fix "Unknown")

4. **indexing_engine.py** global:
   - Add `.claude/worktrees` to `skip_dirs`

**Test criteria**:
- Query "HXA22 destructive action guard" returns HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md as top result
- Query "HXA30 scope action class" returns file path, not "Unknown"
- No worktree duplicates in results

---

## 8. WSP_87 Impact

### Current State

- HoloIndex fails to retrieve exact-match audit documents
- Agents must fall back to `rg` for ground truth verification
- WSP 87 anti-vibecoding principle violated when HoloIndex misses existing code

### Required WSP 87 Compliance

- HoloIndex MUST return audit docs when queried with slice ID
- HoloIndex MUST return implementation files when queried with guard name
- HoloIndex MUST NOT return "Unknown" for indexed files

### Audit Trail

```yaml
Query: "HXA22 destructive action guard runtime"
Expected: HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md (top-1)
Current: HXA1, HXA2 (wrong slices)
WSP_87_VIOLATION: Search before create pattern broken
```

---

## 9. WSP_15 Next-Slice Recommendation

### Recommended Next Slice

**ID**: HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1
**Objective**: Implement minimal indexing fixes per Section 7.2
**Scope**: 
- Modify `holo_index/core/indexing_engine.py` (audit path scanning, slice ID extraction)
- Modify `holo_index/core/search_engine.py` (fix "Unknown" path display)
- Add test cases for HXA query retrieval

**Preconditions**:
- This spec approved by 012/W10
- No runtime changes (index mutation only after approval)

**WSP 97 Labels for Next Slice**:
```yaml
- INDEXING_CHANGE_ALLOWED
- NO_RUNTIME_CHANGE
- NO_LIVE_REINDEX_WITHOUT_APPROVAL
- TEST_COVERAGE_REQUIRED
```

---

## 10. WSP 97 Truth Table (This Slice)

| Claim | Status | Evidence |
|-------|--------|----------|
| DOCS_ONLY | **COMPLIANT** | No code modified |
| HOLOINDEX_AUDIT_ONLY | **COMPLIANT** | Audit/spec document only |
| NO_INDEX_MUTATION | **COMPLIANT** | No reindex executed |
| NO_RUNTIME_CHANGE | **COMPLIANT** | No runtime files modified |
| NO_REINDEX_WITHOUT_APPROVAL | **COMPLIANT** | Reindex deferred to next slice |
| NO_CABR_READY | **COMPLIANT** | Not production |
| NO_PAYOUT_READY | **COMPLIANT** | Not production |
| NO_DAO_ACTIVATION | **COMPLIANT** | Not production |

---

## Appendix A: Raw Query Output Samples

### Query 1: "destructive action guard path validation"
```
[DOCS] O:\Foundups-Agent\docs\architecture\WRE_DESTRUCTIVE_ACTION_GUARD.md
[CODE] O:\Foundups-Agent\public\member\js\mall-state-restore.js (NOISE)
```

### Query 5: "HXA30 scope action class integration"
```
[INTENT: CODE_LOCATION]
[FINDINGS]
  1. Unknown (relevance: 43.3%)
  2. Unknown (relevance: 44.7%)
  3. Unknown (relevance: 43.7%)
  4. Unknown (relevance: 44.7%)
  5. Unknown (relevance: 42.6%)
[BOOKS] WSP 29: CABR Engine Framework
```

### rg Verification
```bash
rg "HXA22|HXA23|HXA28|HXA30" docs/audits/openclaw_hermes
# 11 files found with exact slice IDs
```

---

## Appendix B: File Counts

| Path | File Count | Indexed Collection |
|------|------------|-------------------|
| docs/audits/openclaw_hermes/ | 23 HXA files | navigation_docs (expected) |
| modules/infrastructure/wre_core/tests/ | 24 test files with HXA refs | navigation_tests (partial) |
| .claude/worktrees/ | 45 worktrees | Should be EXCLUDED |

---

**END OF AUDIT**

Worker: W9
Slice: HOLOINDEX_HXA_AUDIT_RETRIEVAL_IMPROVEMENT_AUDIT_PHASE1
WSP 97 Verdict: COMPLIANT (DOCS_ONLY)
Next Slice: HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1
