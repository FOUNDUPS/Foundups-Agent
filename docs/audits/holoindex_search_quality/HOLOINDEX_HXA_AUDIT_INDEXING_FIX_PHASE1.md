# HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1

**Slice**: HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1
**Worker**: W1
**Date**: 2026-05-18
**Mode**: Code implementation (indexing logic changes)
**WSP Lock**: WSP_00, WSP_97, WSP_87, WSP_50

---

## WSP 97 Labels

| Label | Status |
|-------|--------|
| `INDEXING_CHANGE_ALLOWED` | Applied |
| `NO_RUNTIME_CHANGE` | ENFORCED |
| `NO_LIVE_REINDEX_WITHOUT_APPROVAL` | ENFORCED |
| `TEST_COVERAGE_REQUIRED` | VERIFIED (22/22 tests) |
| `NO_CABR_READY` | Applied |
| `NO_PAYOUT_READY` | Applied |
| `NO_DAO_ACTIVATION` | Applied |

---

## 1. Implementation Summary

This slice implements the minimal fixes specified in `HOLOINDEX_HXA_AUDIT_RETRIEVAL_IMPROVEMENT_AUDIT_PHASE1.md` Section 7.2:

| Fix | Description | Status |
|-----|-------------|--------|
| Slice ID extraction | Extract HXA/FX/CFZ patterns from filenames and titles | COMPLETE |
| Slice ID boost | +5.0 keyword boost for exact slice ID match in query | COMPLETE |
| Audit path priority | openclaw_hermes=9, holoindex=9, security=8 | COMPLETE |
| Worktree exclusion | Filter `.claude/worktrees` and `.worktrees` paths | COMPLETE |
| Path display fix | Never return "Unknown" for indexed files | COMPLETE |

---

## 2. Files Modified

### holo_index/core/indexing_engine.py

**Changes**:
1. Added `_SLICE_ID_PATTERN` regex: `(HXA\d+|FX\d+|CFZ\d+)`
2. Added `_extract_slice_id(filename, title)` function
3. Enhanced `_calculate_document_priority()` with audit path boosts
4. Updated `index_docs_entries()` to:
   - Exclude worktree paths
   - Extract and store slice_id in metadata

**Lines added**: ~55

### holo_index/core/search_engine.py

**Changes**:
1. Added `_SLICE_ID_PATTERN` regex with word boundaries
2. Added `_extract_slice_ids(text)` function
3. Added `_slice_id_match_boost(query, path, title, meta_slice_id)` function
4. Enhanced `_search_collection()` to apply slice ID boost
5. Enhanced `_lexical_search_collection()` to apply slice ID boost
6. Enhanced `_format_hit()` with docs/knowledge handler ensuring path is never None

**Lines added**: ~64

### holo_index/tests/test_hxa_retrieval_fix.py (NEW)

**Test classes**:
- `TestSliceIdExtraction` (6 tests)
- `TestSliceIdBoost` (4 tests)
- `TestSliceIdPatternExtraction` (2 tests)
- `TestAuditPathPriority` (3 tests)
- `TestWorktreeExclusion` (1 test)
- `TestDocsFormatHit` (2 tests)
- `TestSliceIdPattern` (4 tests)

**Total**: 22 tests, all passing

---

## 3. Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.0.3
collected 22 items

holo_index/tests/test_hxa_retrieval_fix.py ...................... [100%]

============================= 22 passed in 1.32s ==============================
```

---

## 4. Baseline vs Expected (Post-Reindex)

### Baseline (Before Fix)

| Query | Result | Verdict |
|-------|--------|---------|
| "HXA22 destructive action guard runtime" | HXA1, HXA2 (wrong slices) | MISS |
| "HXA23 Hermes guard integration" | HXA1, hermes_job_executor.py | MISS |
| "HXA28 D3 native classification" | gemma_segment_classifier.py | MISS |
| "HXA30 scope action class integration" | 5 "Unknown" paths | FAIL |

### Expected (After Reindex with Fix)

| Query | Expected Result | Reason |
|-------|-----------------|--------|
| "HXA22 destructive action guard runtime" | HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md | +5.0 slice ID boost |
| "HXA23 Hermes guard integration" | HXA23_HERMES_GUARD_INTEGRATION.md | +5.0 slice ID boost |
| "HXA28 D3 native classification" | HXA28_D3_NATIVE_CLASSIFICATION.md | +5.0 slice ID boost |
| "HXA30 scope action class integration" | HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION.md with path | +5.0 boost + path fix |

**Note**: Full verification requires reindex, which is deferred per `NO_LIVE_REINDEX_WITHOUT_APPROVAL`.

---

## 5. Algorithm Details

### Slice ID Extraction

```python
_SLICE_ID_PATTERN = re.compile(r"(HXA\d+|FX\d+|CFZ\d+)", re.IGNORECASE)

def _extract_slice_id(filename: str, title: str) -> Optional[str]:
    # Try filename first
    match = _SLICE_ID_PATTERN.search(filename)
    if match:
        return match.group(1).upper()
    # Fall back to title
    match = _SLICE_ID_PATTERN.search(title)
    if match:
        return match.group(1).upper()
    return None
```

### Slice ID Boost Scoring

```python
def _slice_id_match_boost(query, path, title, meta_slice_id) -> float:
    query_slices = _extract_slice_ids(query)
    if not query_slices:
        return 0.0
    
    # Check metadata slice_id (primary)
    if meta_slice_id and meta_slice_id.upper() in [s.upper() for s in query_slices]:
        return 5.0
    
    # Check path/title (fallback)
    combined = f"{path} {title}".upper()
    for slice_id in query_slices:
        if slice_id.upper() in combined:
            return 5.0
    
    return 0.0
```

### Audit Path Priority

```python
if "/audits/openclaw_hermes/" in path_str:
    base_priority = max(base_priority, 9)  # HXA series
elif "/audits/holoindex/" in path_str:
    base_priority = max(base_priority, 9)
elif "/audits/security/" in path_str:
    base_priority = max(base_priority, 8)
elif "/audits/" in path_str:
    base_priority = max(base_priority, 7)
```

---

## 6. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Indexing logic modified | **COMPLIANT** | indexing_engine.py, search_engine.py |
| No runtime changes | **COMPLIANT** | No execution flow changes |
| No live reindex | **COMPLIANT** | Index mutation deferred |
| Test coverage | **VERIFIED** | 22/22 tests passing |
| No CABR readiness | **COMPLIANT** | Not production |
| No payout readiness | **COMPLIANT** | Not production |
| No DAO activation | **COMPLIANT** | Not production |

---

## 7. Next Slice Recommendation

**ID**: HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE2
**Objective**: Execute reindex and verify query improvements
**Scope**:
- Run full reindex with new logic
- Execute baseline queries and compare results
- Document before/after metrics

**Preconditions**:
- This slice merged and approved
- W10 approval for live reindex

---

**END OF AUDIT**

Worker: W1
Slice: HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1
WSP 97 Verdict: COMPLIANT
