# W8 — HOLO_TEST_COVERAGE_IMPROVEMENT_PHASE1

```text
Window: W8
Slice: W8
Lane: HoloIndex Test Coverage
Branch: main
Mode: implementation
Status: in-progress
```

## Objective

Improve HoloIndex test coverage on core modules targeting 80% coverage on `holo_index/core/`. Tests must work in `HOLO_SKIP_MODEL=1` mode (no model download required).

## Baseline

Initial coverage on `holo_index/core/`: **14%** (limited test files ran against core modules)

## Progress

### New Test Files Created

| File | Tests | Coverage Impact |
|------|-------|-----------------|
| `test_circuit_breaker.py` | 23 | circuit_breaker.py: 0% → 98% |
| `test_mps_m_scorer.py` | 40 | mps_m_scorer.py: 0% → 96% |
| `test_comment_search.py` | 10 | comment_search.py: 0% → 100% |
| `test_turboquant_backend.py` | 6 | turboquant_backend.py: 0% → 100% |
| `test_module_scoring_subroutine.py` | 21 | module_scoring_subroutine.py: 16% → 87% |

### Current Coverage Summary

| Module | Coverage | Notes |
|--------|----------|-------|
| comment_search.py | 100% | Complete |
| turboquant_backend.py | 100% | Complete |
| circuit_breaker.py | 98% | Near-complete |
| mps_m_scorer.py | 96% | Near-complete |
| module_scoring_subroutine.py | 87% | Good |
| __init__.py | 67% | - |
| holo_index.py | 48% | Model-dependent paths |
| search_cache.py | 46% | - |
| search_engine.py | 44% | Model-dependent |
| introspection_engine.py | 40% | - |
| video_search.py | 33% | Database-dependent |
| indexing_engine.py | 26% | ChromaDB-dependent |
| intelligent_subroutine_engine.py | 9% | Complex dependencies |
| vocabulary_indexer.py | 0% | Requires HoloIndex instance |

**Total: 43%** (up from 14% baseline)

## Test Run Command

```bash
HOLO_SKIP_MODEL=1 python -m pytest holo_index/tests/test_circuit_breaker.py \
  holo_index/tests/test_mps_m_scorer.py holo_index/tests/test_comment_search.py \
  holo_index/tests/test_turboquant_backend.py holo_index/tests/test_module_scoring_subroutine.py \
  --cov=holo_index/core --cov-report=term-missing --tb=no
```

## Challenges

1. **Model-dependent code**: Many core modules (`holo_index.py`, `search_engine.py`, `indexing_engine.py`) require SentenceTransformer/ChromaDB initialization that can't be easily bypassed in tests.

2. **pytest capture error**: Some test files cause `ValueError: I/O operation on closed file` when run together with the full test suite. Individual test files work correctly.

3. **Windows file handling**: Temporary file cleanup requires using `TemporaryDirectory` context manager instead of `NamedTemporaryFile` due to Windows file locking.

## Recommendations for Phase 2

1. **Mock model initialization**: Create pytest fixtures that mock `SentenceTransformer` and `chromadb.Client` for testing `holo_index.py` and `search_engine.py`.

2. **Add vocabulary_indexer tests**: Test with mocked HoloIndex instance.

3. **Increase introspection_engine coverage**: Test file parsing logic with sample files.

4. **Add integration tests**: Create tests that verify the full search pipeline with mocked models.

## Test Summary

**New tests added**: 100 tests across 5 new test files
- test_circuit_breaker.py: 23 tests
- test_mps_m_scorer.py: 40 tests
- test_comment_search.py: 10 tests
- test_turboquant_backend.py: 6 tests
- test_module_scoring_subroutine.py: 21 tests

**All new tests pass** in HOLO_SKIP_MODEL=1 mode.

## WSP 97 Statement

This report documents coverage improvement work. The 43% combined coverage figure is measured against the existing test suite plus new tests. Target 80% coverage requires additional work on model-dependent modules (search_engine.py, indexing_engine.py, holo_index.py).

---

**Generated**: 2026-04-17
**Window**: W8
**Agent**: 0102 (Claude Opus 4.5)
