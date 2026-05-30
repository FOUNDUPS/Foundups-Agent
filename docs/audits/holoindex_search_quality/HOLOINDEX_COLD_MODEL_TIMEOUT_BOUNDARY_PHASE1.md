# HOLOINDEX_COLD_MODEL_TIMEOUT_BOUNDARY_PHASE1

**Date**: 2026-05-30
**Agent**: W6 (0102)
**Status**: COMPLETE
**PR**: (pending)

## Problem Statement

After PR #728 (full-body chunking), knowledge content was correctly indexed into
1451 body chunks across 47 papers. However, fresh-process search could still fail
to find content because SentenceTransformer import/load timed out with defaults:
- `HOLO_MODEL_IMPORT_TIMEOUT=20` (seconds)
- `HOLO_MODEL_LOAD_TIMEOUT=30` (seconds)

On this hardware, cold-process import can exceed 60 seconds. When timeout occurs,
HoloIndex silently degrades to lexical search, causing 0102 to incorrectly conclude
"content not found" when the semantic engine simply didn't load.

**Trust boundary issue**: False-negative search results lead to incorrect conclusions.

## Evidence

After #728:
- `--index-knowledge` successfully indexed 47 papers → 1451 chunks (with timeout=120s)
- First fresh `--search` with defaults returned no useful knowledge results
- Re-running with `HOLO_MODEL_IMPORT_TIMEOUT=120 HOLO_MODEL_LOAD_TIMEOUT=120` made rESP §4.4 retrieval work

## Solution

### A. Raised Defaults

| Timeout | Before | After |
|---------|--------|-------|
| `HOLO_MODEL_IMPORT_TIMEOUT` | 20s | 120s |
| `HOLO_MODEL_LOAD_TIMEOUT` | 30s | 120s |
| `HOLO_ENCODE_TIMEOUT` | 3s | 3s (unchanged) |
| `HOLO_SEARCH_TIMEOUT` | 15s | 15s (unchanged) |

### B. Improved Observability

**Timeout warning** (`_run_with_timeout`):
```
{error_msg} (>{timeout_sec}s). Semantic search will be unavailable. 
Raise HOLO_MODEL_IMPORT_TIMEOUT/HOLO_MODEL_LOAD_TIMEOUT or rerun after model warmup.
```

**Search degradation warning** (`_search_collection`):
```
Embedding model not available - semantic search degraded to lexical. 
Knowledge/paper results may be missing. Check HOLO_MODEL_IMPORT_TIMEOUT if cold-process.
```

## Files Changed

| File | Change |
|------|--------|
| `holo_index/core/holo_index.py` | Raised timeout defaults, improved warning |
| `holo_index/core/search_engine.py` | Improved degradation warning |
| `holo_index/tests/test_fx1_holoindex_truth.py` | Updated/added timeout default tests |
| `holo_index/ModLog.md` | Entry added |

## Test Coverage

| Test | Purpose |
|------|---------|
| `test_default_import_timeout_is_sufficient` | Assert >= 60s |
| `test_default_load_timeout_is_sufficient` | Assert >= 60s |
| `test_env_override_controls_import_timeout` | Env override works |
| `test_skip_model_still_produces_lexical` | HOLO_SKIP_MODEL=1 → lexical |

**Result**: 4/4 tests passing

## WSP_97 Truth Boundary Checklist

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | NO_RANKING_CHANGE | PASS | No search_engine.py ranking logic changed |
| 2 | NO_SEARCH_ALGORITHM_CHANGE | PASS | Only warning message changed |
| 3 | NO_KNOWLEDGE_CHUNKING_CHANGE | PASS | indexing_engine.py untouched |
| 4 | NO_DEPENDENCY_CHANGE | PASS | No requirements.txt change |
| 5 | NO_CI_CHANGE | PASS | No workflow files changed |
| 6 | NO_LIVE_MODEL_LOAD_IN_TESTS | PASS | Tests use module reload, not model load |
| 7 | NO_LIVE_CHROMA_MUTATION_IN_TESTS | PASS | No Chroma in timeout tests |
| 8 | NO_DOC_CONTENT_CHANGE | PASS | No WSP_knowledge changes |
| 9 | NO_WSP_MUTATION | PASS | No WSP_framework changes |
| 10 | NO_REGISTRY_MUTATION | PASS | No registry files changed |
| 11 | NO_PUBLIC_SURFACE_MUTATION | PASS | Env var interface unchanged |

## Manual Verification

Fresh process search (no env var override):
```bash
python holo_index.py --search "rESP null model comparison status forced nonlinear oscillators decoder tokenizer priors" --limit 6
```

Expected: `rESP_Quantum_Self_Reference.md` appears under `[KNOWLEDGE]` results.
