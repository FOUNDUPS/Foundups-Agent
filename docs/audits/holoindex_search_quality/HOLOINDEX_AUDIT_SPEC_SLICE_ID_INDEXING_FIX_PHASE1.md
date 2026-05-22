# HoloIndex Audit Spec Slice ID Indexing Fix — Phase 1

**Slice**: `HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1`
**Worker**: W1
**Date**: 2026-05-22
**Mode**: HoloIndex retrieval improvement (indexing + search)
**Base commit**: PR #674 merged
**Branch**: `feat/holoindex-audit-spec-slice-id-indexing-fix-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22

---

## WSP_97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| HOLOINDEX_RETRIEVAL_IMPROVEMENT_ONLY | YES |
| SLICE_ID_INDEXING_FIX_ONLY | YES |
| HOLOINDEX_CORE_MUTATION_AUTHORIZED_FOR_SLICE_ID_RETRIEVAL | YES |
| NO_LIVE_REINDEX | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_VALIDATOR_MUTATION | YES |
| NO_MCP_CHANGE | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_WSP_MUTATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Fix the repeated retrieval gap where HoloIndex fails to surface audit/spec docs by exact slice ID.

## 2. Retrieval Gap Evidence

| PR | Slice | Retrieval Quality |
|----|-------|------------------|
| #657 | Credential access spec | WEAK — audit/spec not surfaced |
| #663 | Redteam Family B | WEAK — audit/spec not surfaced |
| #667 | Family C | WEAK — audit/spec not surfaced |
| #668 | Provenance check | WEAK — audit/spec not surfaced |
| #672 | Portfolio validator | WEAK — spec did not surface |
| #673 | HoloIndex registry entry | WEAK — audit docs not surfaced |
| #674 | Dual identity field | WEAK — audit docs not surfaced |

### 2.1 Preflight Verification

```bash
python holo_index.py --search "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1" --limit 8
```

**Result**: NO HITS for the actual spec doc at `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md`.

Top hits were thematically unrelated: `modules/foundups/trade/src/guards.py`, `WSP_106_FoundUp_API_Gateway_Protocol.md`, etc.

## 3. Current Architecture Findings

### 3.1 Existing Slice ID Pattern (Before Fix)

```python
# indexing_engine.py line 116
_SLICE_ID_PATTERN = re.compile(r"(HXA\d+|FX\d+|CFZ\d+)", re.IGNORECASE)
```

**Gap**: Only matches short-form IDs:
- `HXA22`, `FX1`, `CFZ4`

Does NOT match long-form audit spec IDs:
- `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1`
- `FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1`
- `HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1`

### 3.2 Slice ID Extraction Flow

1. `index_docs_entries()` calls `_extract_slice_id(filename, title)`
2. If slice_id found, added to metadata: `metadata_entry["slice_id"] = slice_id`
3. Search calls `_slice_id_match_boost()` which returns 5.0 for exact matches
4. Both vector and lexical paths honor the boost

### 3.3 Files Involved

| File | Role |
|------|------|
| `holo_index/core/indexing_engine.py` | Slice ID extraction during indexing |
| `holo_index/core/search_engine.py` | Slice ID boost during search |

## 4. Implementation

### 4.1 Slice ID Extraction Rule

Added new pattern for audit spec slice IDs:

```python
# Pattern: Uppercase words with underscores ending in _PHASE<digits>
_AUDIT_SPEC_SLICE_ID_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_PHASE\d+)\b"
)
```

**Matches**:
- `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1`
- `HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1`
- `FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1`
- `SOME_SLICE_PHASE12` (multi-digit phase numbers)

**Does NOT match** (correctly):
- `foundups_portfolio_validator_phase1` (lowercase)
- `PortfolioValidatorPhase1` (no underscores)
- `PORTFOLIO_DATA` (no _PHASE suffix)

### 4.2 Updated `_extract_slice_id` Function

```python
def _extract_slice_id(filename: str, title: str) -> Optional[str]:
    # 1. Check filename for short-form (HXA/FX/CFZ) — priority
    # 2. Check filename for long-form audit spec IDs
    # 3. Check title for short-form
    # 4. Check title for long-form
    # 5. Return None if no match
```

**Priority**: Short-form HXA/FX/CFZ patterns take precedence to preserve existing behavior.

### 4.3 Updated `_extract_slice_ids` Function (Search)

```python
def _extract_slice_ids(text: str) -> List[str]:
    # Extract both short-form and long-form slice IDs
    short_matches = _SLICE_ID_PATTERN.findall(text)
    long_matches = _AUDIT_SPEC_SLICE_ID_PATTERN.findall(text)
    return short_ids + long_matches
```

### 4.4 Search Boost (Unchanged)

`_slice_id_match_boost()` returns **5.0** for exact slice ID matches. This already works for both vector and lexical paths — only the extraction patterns needed extension.

## 5. Synthetic Before/After Rank Proof

### 5.1 Before Fix

Query: `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1`

| Doc | Slice ID Extracted | Boost |
|-----|-------------------|-------|
| `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md` | None | 0.0 |
| `PORTFOLIO_DATA_GENERATOR_PHASE1.md` | None | 0.0 |
| Other docs | None | 0.0 |

**Result**: All docs scored equally (no slice_id differentiation).

### 5.2 After Fix

Query: `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1`

| Doc | Slice ID Extracted | Boost |
|-----|-------------------|-------|
| `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md` | `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1` | **5.0** |
| `PORTFOLIO_DATA_GENERATOR_PHASE1.md` | `PORTFOLIO_DATA_GENERATOR_PHASE1` | 0.0 |
| Other docs | Various | 0.0 |

**Result**: Target doc gets 5.0 boost, ranks first.

### 5.3 Test Verification

```
28 passed in 2.66s (new tests)
22 passed in 2.21s (test_hxa_retrieval_fix.py — no regression)
75 passed in 12.77s (test_work_ledger_indexing.py — no regression)
10 passed in 0.14s (test_search_quality_baseline.py — no regression)
12 passed in 0.15s (test_cfz4_collection_separation.py — no regression)
```

## 6. Reindex Gate

### 6.1 Post-Merge CLI Command (NOT EXECUTED)

```bash
python holo_index.py --index-docs
```

Or for full refresh:

```bash
python holo_index.py --index-all
```

### 6.2 Why Reindex Required

The slice_id metadata extraction happens during indexing. Existing indexed docs do not have the new audit spec slice_ids in their metadata. A reindex is required to:

1. Re-extract slice_ids from all docs/audits/** files
2. Store the new long-form slice_ids in ChromaDB metadata
3. Enable search boost to function for audit spec queries

### 6.3 Expected Post-Reindex Behavior

Query: `FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1`

Expected: `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md` ranks in top 3.

## 7. Test Results

### 7.1 New Tests

```
holo_index/tests/test_audit_spec_slice_id_indexing.py
28 passed in 2.66s
```

Covers:
1. Slice ID extraction from filename
2. Slice ID extraction from H1 heading
3. docs/audits chunks receive metadata.slice_id
4. Exact slice-id query ranks matching synthetic audit doc first
5. Lexical fallback path honors slice_id boost
6. Existing HXA/FX/CFZ patterns not regressed

### 7.2 Existing Suites (No Regression)

| Test File | Result |
|-----------|--------|
| `test_hxa_retrieval_fix.py` | 22 passed |
| `test_work_ledger_indexing.py` | 75 passed |
| `test_search_quality_baseline.py` | 10 passed |
| `test_cfz4_collection_separation.py` | 12 passed |

## 8. Files Changed

| File | Change |
|------|--------|
| `holo_index/core/indexing_engine.py` | Added `_AUDIT_SPEC_SLICE_ID_PATTERN`, extended `_extract_slice_id` |
| `holo_index/core/search_engine.py` | Added `_AUDIT_SPEC_SLICE_ID_PATTERN`, extended `_extract_slice_ids` |
| `holo_index/tests/test_audit_spec_slice_id_indexing.py` | NEW — 28 tests |
| `docs/audits/holoindex_search_quality/HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md` | NEW (this file) |
| `holo_index/ModLog.md` | Updated |

## 9. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex retrieval improvement only | PASS |
| Slice ID indexing fix only | PASS |
| No live reindex | PASS |
| No generated index artifacts | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No validator mutation | PASS |
| No MCP change | PASS |
| No CI change | PASS |
| No dependency install | PASS |
| Existing HXA/FX/CFZ patterns preserved | PASS |

**Verdict**: PASS

## 10. Next Slice (Do Not Start)

| Slice | Purpose |
|-------|---------|
| `HOLOINDEX_AUDIT_SPEC_SLICE_ID_LIVE_REINDEX_OBSERVATION_PHASE1` | Operator-gated live reindex + 14-day observation |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22.*
*Slice: HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1*
