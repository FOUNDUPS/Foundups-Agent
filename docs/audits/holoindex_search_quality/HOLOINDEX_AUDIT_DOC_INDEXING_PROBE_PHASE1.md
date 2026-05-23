# HoloIndex Audit Doc Indexing Probe — Phase 1

**Slice**: `HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1`
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: DIAGNOSTIC (read-only probe)
**Branch**: `feat/holoindex-audit-doc-indexing-probe-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_DIAGNOSTIC_PROBE_ONLY | YES |
| READ_ONLY_CHROMA_ACCESS | YES |
| NO_CHROMA_MUTATION | YES |
| NO_REINDEX | YES |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_TRADE_MUTATION | YES |
| NO_WSP_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| REPORT_ONLY | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Diagnostic-only probe of the `navigation_docs` Chroma collection to classify WHY three target audit docs fail to surface for their slice-ID queries. This slice does NOT reindex, does NOT mutate Chroma, and does NOT add boost or alias code. It only READS the collection state and classifies.

---

## 2. HoloIndex WSP_50 Retrieval Assessment

### Queries Run

| Query | Quality | Notes |
|-------|---------|-------|
| `navigation_docs chroma collection metadata probe` | WEAK | Top hits: test_member_foundup_entry.py, doc_dae.py, pqn_portal/docs.py — not HoloIndex internals |
| `slice_id metadata indexing engine` | MODERATE | Found HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md |
| `HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1` | MODERATE | Target doc surfaced in top 3 |
| `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1` | WEAK | Target doc NOT surfaced |
| `HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1` | WEAK | Target doc NOT surfaced |

### Assessment

Retrieval for exact slice IDs remains inconsistent. The prior fix (PR #675 `_AUDIT_SPEC_SLICE_ID_PATTERN`) helps for some queries but target audit docs from recent PRs do not surface because they are not in the index.

---

## 3. Probe Methodology

### Target Documents

| ID | Path | Expected slice_id |
|----|------|-------------------|
| T1 | `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` | TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 |
| T2 | `docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md` | TRADE_ADAPTER_INTEGRATION_PHASE1 |
| T3 | `docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` | HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1 |

### Probe Steps (per target)

1. **Presence check**: Search `navigation_docs` collection for document by path/filename
2. **Metadata inspection**: If found, read `slice_id` metadata field
3. **Query ranking**: Run slice-ID query, capture target rank and cosine distance
4. **Classification**: Map to A/B/C/D/E category

### Classification Space

| Code | Classification | Meaning |
|------|---------------|---------|
| A | NOT_INDEXED | No document for target path exists in navigation_docs |
| B | INDEXED_NO_SLICE_ID | Present but slice_id metadata absent or mismatched |
| C | INDEXED_WITH_SLICE_ID_OUTRANKED | Present with correct slice_id but outranked |
| D | INDEXED_BUT_BOOST_NOT_APPLIED | Present with correct slice_id but boost not firing |
| E | INDEXED_METADATA_UNKNOWN_OR_PATH_SCHEMA_MISMATCH | Metadata path fields don't allow reliable matching |

---

## 4. Probe Execution

### Collection Stats

```
navigation_docs collection: 3309 documents
docs/audits/** subset: 290 documents
docs/audits/architecture/** subset: 36 documents
```

### Verification: Files Exist on Disk

```bash
$ ls -la docs/audits/architecture/TRADE*.md
-rw-r--r-- 1 user 197121  6139 May 23 20:01 docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md
-rw-r--r-- 1 user 197121  8767 May 23 21:12 docs/audits/architecture/TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.md
-rw-r--r-- 1 user 197121  7558 May 24 01:31 docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md
-rw-r--r-- 1 user 197121 21868 May 23 21:12 docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md
...
```

All target files exist on disk.

### Search in navigation_docs

```python
# Direct search in Chroma for TRADE docs
TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1: 0 matches -> NOT FOUND
TRADE_ADAPTER_INTEGRATION_PHASE1: 0 matches -> NOT FOUND
HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1: 0 matches -> NOT FOUND
```

All three targets are ABSENT from the collection despite existing on disk.

---

## 5. Per-Target Classification

### T1: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md

| Field | Value |
|-------|-------|
| Disk status | EXISTS at `docs/audits/architecture/` |
| Collection status | NOT FOUND |
| **Classification** | **A** |
| Reason | NOT_INDEXED: Document not found in navigation_docs collection |

### T2: TRADE_ADAPTER_INTEGRATION_PHASE1.md

| Field | Value |
|-------|-------|
| Disk status | EXISTS at `docs/audits/architecture/` |
| Collection status | NOT FOUND |
| **Classification** | **A** |
| Reason | NOT_INDEXED: Document not found in navigation_docs collection |

### T3: HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md

| Field | Value |
|-------|-------|
| Disk status | EXISTS at `docs/audits/holoindex_search_quality/` |
| Collection status | NOT FOUND |
| **Classification** | **A** |
| Reason | NOT_INDEXED: Document not found in navigation_docs collection |

### Summary Table

| Target | Classification | Reason |
|--------|---------------|--------|
| T1 | **A** | NOT_INDEXED |
| T2 | **A** | NOT_INDEXED |
| T3 | **A** | NOT_INDEXED |

---

## 6. Root Cause Analysis

### Finding

All three target documents have classification **A (NOT_INDEXED)**. They exist on disk but are not present in the `navigation_docs` Chroma collection.

### Critical Contradiction with PR #688

PR #688 (HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1) ran `python holo_index.py --index-docs` with:
- Exit code: **0**
- Duration: **15.596 s**
- stdout marker: `[POINTS] Session Summary: +5 Refreshed indexes`
- Target files: **EXISTED** in the worktree at time of reindex (verified via `git ls-tree`)

Yet targets were STILL ABSENT in the AFTER snapshot. This means **`--index-docs` reported success but did NOT index these files**.

### Evidence

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Files on disk in `docs/audits/architecture/` | — | 42 | EXISTS |
| Files in collection for that path | 42 | 33 | **9 MISSING** |
| Target T1 in collection | YES | NO | **FAIL** |
| Target T2 in collection | YES | NO | **FAIL** |
| Target T3 in collection | YES | NO | **FAIL** |
| File discovery simulation finds targets | — | YES | **DISCOVERY OK** |

### Hypothesis Space

| Hypothesis | Evidence |
|------------|----------|
| 1. Stale index (files added after reindex) | RULED OUT — files existed before #688 ran |
| 2. Worktree didn't have files | RULED OUT — `git ls-tree` confirms files present at base commit |
| 3. `project_root` mismatch in worktree | POSSIBLE — worktree path may affect resolution |
| 4. Embedding model failure | POSSIBLE — silent fallback could cause partial index |
| 5. `collection.add` failed silently | POSSIBLE — 3309 docs but 9 architecture docs missing |
| 6. Probe bug | RULED OUT — direct Chroma query confirms absence |

### Collection Discrepancy

```
docs/audits/architecture/ on disk:  42 files
docs/audits/architecture/ in index: 33 files
Gap:                                 9 files (all recent)
```

---

## 7. Implication for Next Slice

### DO NOT Simply Rerun `--index-docs`

PR #688 already ran `--index-docs` with exit 0 and targets remained absent. Blindly rerunning will likely produce the same result.

### Recommended Investigation Path

1. **Verify Chroma path consistency**: Confirm worktree and main repo both use `E:/HoloIndex/vectors`
2. **Check `project_root` resolution**: Run `--index-docs` from main repo (not worktree) and compare file discovery
3. **Inspect indexing logs**: Add verbose logging to `index_docs_entries()` to trace file count
4. **Check embedding model state**: If model fails to load, indexing may silently skip files

### Next Slice Classification

Based on the evidence, this is NOT a simple "stale index" issue. The recommended next slice is:

**HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1**

Purpose: Investigate why `--index-docs` reports success but misses files.

### Alternative Diagnoses Ruled Out

| Classification | Ruled Out Because |
|---------------|-------------------|
| B (INDEXED_NO_SLICE_ID) | Documents not in collection at all |
| C (OUTRANKED) | Documents not in collection at all |
| D (BOOST_NOT_APPLIED) | Documents not in collection at all |
| E (METADATA_MISMATCH) | Documents not in collection at all |

---

## 8. Static Safety Verification

### Probe Script Mutation Scan

```bash
$ grep -v '^#' probe_audit_doc_indexing.py | grep -E '\.(add|update|delete|persist)\s*\('
(no output)
```

**Result**: PASS — No mutation methods in probe script.

### Determinism Verification

```bash
$ python holo_index/scripts/probe_audit_doc_indexing.py 2>/dev/null | md5sum
49c02f005a4a608eee3cbcf023355b6f
$ python holo_index/scripts/probe_audit_doc_indexing.py 2>/dev/null | md5sum
49c02f005a4a608eee3cbcf023355b6f
```

**Result**: PASS — Two runs produce identical JSON output.

### Git Status Artifact Guard

```bash
$ git status --porcelain
M docs/audits/holoindex_search_quality/HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1.md
?? holo_index/scripts/probe_audit_doc_indexing.py
```

**Result**: PASS — Only expected files (this audit + probe script). No generated index artifacts.

---

## 9. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex diagnostic probe only | PASS |
| Read-only Chroma access | PASS |
| No Chroma mutation | PASS |
| No reindex | PASS |
| No HoloIndex core mutation | PASS |
| No generated index artifacts | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No Trade mutation | PASS |
| No WSP mutation | PASS |
| No CI change | PASS |
| No dependency install | PASS |
| Report only | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS (18/18)

---

## 10. Files Changed

| File | Change |
|------|--------|
| `holo_index/scripts/probe_audit_doc_indexing.py` | NEW (probe script, ~300 lines) |
| `docs/audits/holoindex_search_quality/HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1.md` | NEW (this file) |

---

## 11. Probe Output (JSON)

```json
{
  "classification_summary": {
    "T1": "A",
    "T2": "A",
    "T3": "A"
  },
  "collection_name": "navigation_docs",
  "collection_stats": {
    "total_documents": 3309,
    "docs_audits_architecture_on_disk": 42,
    "docs_audits_architecture_in_index": 33,
    "gap": 9
  },
  "next_slice_recommendation": "HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1",
  "probe_version": "1.0.0",
  "slice": "HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1"
}
```

---

## 12. Next Slice (Do Not Start)

| Recommendation | Description |
|----------------|-------------|
| `HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1` | Investigate why `--index-docs` reports success but misses files |

**DO NOT** simply rerun `--index-docs`. PR #688 already did that and targets remained absent.

### Investigation checklist for next slice

1. Run `--index-docs` from **main repo** (not worktree) with verbose logging
2. Compare `project_root` resolution between worktree and main repo
3. Verify file discovery count matches expected (~3300+)
4. Check embedding model load status during indexing
5. Trace `collection.add()` to confirm all files are actually added

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_22.*
*Slice: HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1*
