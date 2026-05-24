# Trade Due Diligence Scoring Engine Deterministic Clock Fix — Phase 1

**Slice**: `TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1`
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Bug Fix (determinism enforcement)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
**Branch**: `feat/trade-due-diligence-scoring-engine-deterministic-clock-fix-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| Label | Status |
|-------|--------|
| TRADE_SCORING_ENGINE_CLOCK_FIX_ONLY | YES |
| DETERMINISTIC_BYTE_IDENTICAL_REQUIRED | YES |
| EXPLICIT_EVALUATION_TIME_REQUIRED | YES |
| TIMEZONE_AWARE_DATETIME_REQUIRED | YES |
| NO_IMPLICIT_WALL_CLOCK_IN_SCORING | YES |
| NO_ROUNDED_DETERMINISM_MASK | YES |
| NO_WEIGHT_CHANGE | YES |
| NO_BAND_CHANGE | YES |
| NO_DISQUALIFIER_CHANGE | YES |
| NO_LIVE_FEEDS | YES |
| NO_NETWORK_CALLS | YES |
| NO_WALLET | YES |
| NO_WALLET_SIGNING | YES |
| NO_KEY_MATERIAL | YES |
| NO_ORDER_PLACEMENT | YES |
| NO_REAL_TRADING | YES |
| NO_EXCHANGE_SDK_IMPORT | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_PORTFOLIO_PROMOTION | YES |
| NO_PUBLIC_SURFACE_CLAIM | YES |
| NO_CI_GATE_ACTIVATION | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Remove implicit `datetime.now()` from scoring path to ensure true byte-identical determinism. Two runs with identical inputs must produce identical JSON output regardless of wall-clock time.

---

## 2. Problem Statement

### Previous State

Line 44-45 of `due_diligence_scoring.py`:
```python
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

Line 66 in `score_launch_timing()`:
```python
now = _utc_now()
age_seconds = (now - candidate.timestamp).total_seconds()
```

**Impact**: Two runs with identical inputs at different wall-clock times produced different `launch_timing` scores and therefore different `total_score` values. Not byte-identical.

### Fix Applied

1. Removed `_utc_now()` function entirely
2. Added explicit `evaluation_time: datetime` parameter to `score()` method (required, keyword-only)
3. Validation: naive datetimes rejected with `ValueError`
4. Normalization: non-UTC aware datetimes normalized to UTC via `astimezone(timezone.utc)`

---

## 3. Code Changes

### 3.1 Removed Function

```python
# REMOVED (was line 44-45):
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

### 3.2 Updated score_launch_timing()

```python
# BEFORE:
def score_launch_timing(candidate: LaunchpadTokenCandidate) -> float:
    now = _utc_now()
    age_seconds = (now - candidate.timestamp).total_seconds()

# AFTER:
def score_launch_timing(candidate: LaunchpadTokenCandidate, evaluation_time: datetime) -> float:
    age_seconds = (evaluation_time - candidate.timestamp).total_seconds()
```

### 3.3 Updated DueDiligenceScoringEngine.score()

```python
def score(
    self,
    candidate: LaunchpadTokenCandidate,
    *,
    evaluation_time: datetime,  # NEW - required, keyword-only
    issuer_report: Optional[EntityHistoryReport] = None,
    # ... other params unchanged
) -> TradeDueDiligenceScore:
    # Validation
    if evaluation_time.tzinfo is None:
        raise ValueError(
            "evaluation_time must be timezone-aware (use datetime with tzinfo). "
            "Naive datetimes are rejected to ensure deterministic scoring."
        )

    # Normalization to UTC
    evaluation_time = evaluation_time.astimezone(timezone.utc)

    # ... rest of scoring
    launch_timing = score_launch_timing(candidate, evaluation_time)
```

---

## 4. Static Scan Proof

### Forbidden Clock Patterns

```bash
grep -E "datetime\.now|date\.today|time\.time|time\.monotonic|_utc_now" \
    modules/foundups/trade/src/due_diligence_scoring.py
# (no output)
```

**Result**: PASS — Zero hits for forbidden clock patterns.

---

## 5. Test Results

### 5.1 New Tests (8)

| Test | Purpose |
|------|---------|
| `test_naive_datetime_raises_valueerror` | Naive evaluation_time raises ValueError |
| `test_non_utc_timezone_normalizes_to_utc` | JST and UTC same instant -> byte-identical output |
| `test_no_forbidden_clock_patterns_in_source` | Static scan for forbidden patterns |
| `test_component_weights_sum_to_one` | Weights unchanged (sum to 1.0) |
| `test_decision_bands_unchanged` | All 4 bands present |
| `test_hard_disqualifier_thresholds_unchanged` | <20 threshold unchanged |
| `test_low_evidence_threshold_unchanged` | <0.5 threshold unchanged |
| `test_byte_identical_determinism` | Explicit byte-identical JSON test |

### 5.2 Modified Tests (50)

All 50 existing tests updated to pass explicit `evaluation_time=FIXED_EVAL_TIME`:
- `FIXED_EVAL_TIME = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)`
- `fresh_candidate` fixture: timestamp = FIXED_EVAL_TIME - 2 minutes
- `old_candidate` fixture: timestamp = FIXED_EVAL_TIME - 8 hours

### 5.3 Test Counts

```
python -m pytest modules/foundups/trade/tests/test_due_diligence_scoring.py -q
58 passed in 0.25s

python -m pytest modules/foundups/trade/tests/ -q
350 passed in 1.91s
```

---

## 6. Invariants Verified Unchanged

| Invariant | Verified |
|-----------|----------|
| Component weights sum to 1.0 | YES |
| 10 components present | YES |
| 4 decision bands present | YES |
| Hard disqualifier threshold < 20 | YES |
| Low evidence threshold < 0.5 | YES |
| No real trading authorization | YES |

---

## 7. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/trade/src/due_diligence_scoring.py` | Remove `_utc_now()`, add `evaluation_time` param |
| `modules/foundups/trade/tests/test_due_diligence_scoring.py` | Add 8 new tests, update 50 existing tests |
| `modules/foundups/trade/tests/TestModLog.md` | Add v0.6.1 entry |
| `docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1.md` | NEW (this file) |

---

## 8. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Trade scoring engine clock fix only | PASS |
| Deterministic byte-identical required | PASS |
| Explicit evaluation_time required | PASS |
| Timezone-aware datetime required | PASS |
| No implicit wall-clock in scoring | PASS |
| No rounded determinism mask | PASS |
| No weight change | PASS |
| No band change | PASS |
| No disqualifier change | PASS |
| No live feeds | PASS |
| No network calls | PASS |
| No wallet | PASS |
| No wallet signing | PASS |
| No key material | PASS |
| No order placement | PASS |
| No real trading | PASS |
| No exchange SDK import | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No portfolio promotion | PASS |
| No public surface claim | PASS |
| No CI gate activation | PASS |
| No dependency install | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS (28/28)

---

## 9. W10 Readiness

This slice removes the implicit wall-clock dependency. W10 can verify:
- Static scan shows zero forbidden clock patterns
- Naive datetime raises ValueError
- Non-UTC aware normalizes to UTC with byte-identical output
- All scoring invariants unchanged
- 350/350 tests pass

---

## 10. Next Slice (Do Not Start)

| Slice | Purpose |
|-------|---------|
| `TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1` | Synthetic test data for scoring validation |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1*
