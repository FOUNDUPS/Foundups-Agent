# HIA4A: HoloIndex Index Refresh Audit

**Date**: 2026-05-01
**Status**: IN PROGRESS
**Branch**: feat/hia4a-holoindex-index-refresh

## Pre-Reindex State

### Collection Counts (Pre-Reindex)

| Collection | Count | Expected | Gap Analysis |
|------------|-------|----------|--------------|
| code | 296 | ~20,860 .py files | Intentional - code is module-level, not file-level |
| symbol | 20,000 | ? | Contains file symbols (functions, classes) |
| wsp | 117 | 118 WSP files | Match |
| test | 0 | ? | Not indexed |
| skill | 59 | 86 SKILLz.md files | 27 missing |
| docs | 3,120 | ? | Module docs |
| knowledge | 47 | ? | Research papers |

**Total**: ~23,639 documents

### Selenium Coverage Check

**Finding**: Selenium files ARE in the symbol_collection (19 paths with "selenium").

Sample paths:
- `modules/infrastructure/foundups_selenium/src/browser_manager.py`
- `modules/infrastructure/foundups_selenium/src/foundups_driver.py`
- `modules/infrastructure/wardrobe_ide/backends/selenium_backend.py`

**Issue**: Search for "browser automation selenium" returns `demurrage.py` instead of selenium files.
This is NOT an indexing issue - it's a ranking/semantic similarity issue.

### Baseline Metrics (Pre-Reindex)

From hia3_baseline_metrics.json:
- top_1_pass_rate: 54.5% (6/11)
- top_5_pass_rate: 54.5% (6/11)
- latency_p50: 85ms

### Key Diagnostic Findings

1. **All code results show 50.0% similarity** - suspicious constant value
2. **WSP direct queries work**: "WSP 97" finds WSP 97 at top
3. **WSP complex queries fail**: "WSP 97 truth distinction protocol" finds WSP 94 first
4. **Sentinel query mismatch**: "WSP 97 truth distinction protocol" describes wrong protocol
   - WSP 97 is actually "System Execution Prompting Protocol"
   - The query semantically matches WSP 94 "Agent Coordination Protocol" better

---

## Index Refresh

### Bug Found: index_wsp_entries() Signature Mismatch

```
TypeError: index_wsp_entries() takes 1 positional argument but 2 were given
```

**Root cause**: `holo_index.py:495-497` wrapper passes `paths` argument, but 
`indexing_engine.py:361` function signature only takes `holo`.

```python
# indexing_engine.py:361
def index_wsp_entries(holo: "HoloIndex") -> None:  # 1 arg

# holo_index.py:495-497
def index_wsp_entries(self, paths: Optional[List[Path]] = None) -> None:
    from .indexing_engine import index_wsp_entries as _idx_wsp
    _idx_wsp(self, paths)  # Passes 2 args!
```

**Impact**: `--index-all` partially fails - symbols reindex but WSP reindex crashes.

### Commands Executed

```bash
python holo_index.py --index-all
# Result: Symbols indexed in 338.87s, then TypeError on WSP indexing

python holo_index.py --index-symbols
# Result: In progress (running in background)
```

### Collection Counts (Post Reindex)

| Collection | Pre | Post | Delta |
|------------|-----|------|-------|
| code | 296 | 296 | 0 |
| symbol | 20,000 | 20,000 | 0 (restored) |
| wsp | 117 | 117 | 0 |
| test | 0 | 0 | 0 |
| skill | 59 | 59 | 0 |
| docs | 3,120 | 3,120 | 0 |
| knowledge | 47 | 47 | 0 |

**Symbol reindex completed**: 364.51s to index 20,000 symbols.

---

## Post-Reindex Baseline

| Metric | Pre-Audit | Post-Reindex |
|--------|-----------|--------------|
| top_1_pass_rate | 54.5% | 54.5% |
| top_5_pass_rate | 54.5% | 54.5% |

**Finding**: Baseline unchanged after reindex. Index freshness confirmed as NOT the issue.

---

## Key Findings

### 1. Index Bug Found
The `--index-all` command has a signature mismatch bug that prevents full reindex.
This should be fixed separately.

### 2. Selenium Files ARE Indexed
Confirmed 19 paths with "selenium" exist in the symbol_collection when populated.
The issue is NOT missing indexing - it's search ranking.

### 3. WSP Queries Work for Direct Numbers
- "WSP 97" → finds WSP 97 at top
- "WSP 97 truth distinction protocol" → finds WSP 94 (semantic mismatch)
- **Root cause**: Sentinel query describes wrong protocol topic

### 4. demurrage.py Over-Ranking
- Multiple unrelated queries return demurrage.py at 50.0% similarity
- All code results show constant 50.0% similarity - suspicious
- Suggests embedding model or scoring issue, not indexing issue

---

## Conclusions

**Index freshness is NOT the root cause of HIA3 failures.**

The three failure categories have different root causes:

| Failure | Root Cause | Fix Category |
|---------|------------|--------------|
| Selenium coverage | NOT indexing - files ARE indexed | Ranking (HIA4) |
| WSP 97 mismatch | Sentinel query describes wrong topic | Baseline fix |
| demurrage noise | Embedding similarity constant at 50% | Investigation needed |

**Recommendation**: Fix the `index_wsp_entries()` signature bug, but HIA4 ranking
fixes should proceed since indexing is not the problem.

## Action Items

1. ~~**CRITICAL**: Run `python holo_index.py --index-symbols`~~ **DONE** (364.51s)
2. Fix `index_wsp_entries()` signature mismatch (separate PR)
3. Proceed with HIA4 ranking fixes - indexing confirmed as not the problem
4. Update baseline sentinel query for WSP 97 to match actual topic
