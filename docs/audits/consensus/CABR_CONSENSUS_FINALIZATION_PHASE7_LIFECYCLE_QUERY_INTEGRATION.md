# CABR Consensus Finalization Phase 7: Lifecycle Query Integration

**Slice**: CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION
**Worker**: W1
**Date**: 2026-05-13

## Summary

Phase 7 integrates lifecycle correlation (Phase 6) with CABRConsensusStore queries
for end-to-end read-only tracing of CABR consensus pipeline stages.

## WSP 97 Compliance Statement

**Lifecycle query integration is OBSERVABILITY ONLY.** It does NOT mean:
- automatic state progression
- verification_complete=True
- cabr_ready=True
- payout_ready=True
- payout approval
- DAO activation
- token issuance
- external settlement

## Architecture

```
Phase 1 -> CABRConsensusRecord (in-memory decision)
Phase 2 -> CABRConsensusStore (SQLite persistence)
Phase 3 -> Auto-persist integration (optional persistence)
Phase 4 -> CABRConsensusReporting -> read-only aggregation
Phase 5 -> Time-range and receipt correlation
Phase 6 -> Lifecycle correlation (full pipeline tracing)
Phase 7 -> Lifecycle Query (this) -> store + lifecycle integration
```

## New Module

**File**: `modules/communication/moltbot_bridge/src/cabr_lifecycle_query.py`

### Public API

```python
# Query Filter
@dataclass
class CABRLifecycleQueryFilter:
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = None
    decision_filter: Optional[str] = None
    
    def validate(self) -> bool: ...
    def to_dict(self) -> Dict[str, Any]: ...

# Query Result
@dataclass
class CABRLifecycleQueryResult:
    query_filter: Optional[CABRLifecycleQueryFilter] = None
    persisted_record_count: int = 0
    correlation_result: Optional[CABRLifecycleCorrelationResult] = None
    gap_summary: Optional[CABRLifecycleGapSummary] = None
    generated_at: datetime
    wsp97_compliance_note: str

# Functions
def query_lifecycle_from_store(
    store: CABRConsensusStore,
    receipts: Optional[List[Dict]] = None,
    pavs_results: Optional[List[Dict]] = None,
    score_results: Optional[List[Dict]] = None,
    quorum_results: Optional[List[Dict]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> CABRLifecycleQueryResult: ...

def query_lifecycle_gaps_from_store(
    store: CABRConsensusStore,
    receipts: Optional[List[Dict]] = None,
    pavs_results: Optional[List[Dict]] = None,
    score_results: Optional[List[Dict]] = None,
    quorum_results: Optional[List[Dict]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> CABRLifecycleGapSummary: ...

def export_lifecycle_query_json(
    result: CABRLifecycleQueryResult,
    indent: int = 2,
) -> str: ...
```

## Behavior

1. **Read-only**: No mutations to store or supplied data
2. **Store path**: Caller-provided (no default DB path)
3. **Query**: Read persisted CABRConsensusRecords from store
4. **Time range**: Apply optional start/end filtering deterministically
5. **Limit**: Applied after time filtering for deterministic results
6. **Correlation**: Use Phase 6 correlation logic with supplied receipt/pAVS/score/quorum data
7. **Gap reporting**: Missing supplemental data reported as gaps, not inferred
8. **Invalid time range**: Fails closed (raises ValueError)
9. **Truth boundary**: Anomalies propagated from Phase 6
10. **No payout/DAO inference**: Query results never imply readiness

## Test Coverage

**File**: `modules/communication/moltbot_bridge/tests/test_cabr_lifecycle_query.py`

**45 tests covering**:
- empty store query
- store with persisted records query
- time range query (start, end, both)
- invalid time range fails closed
- limit applied deterministically
- persisted records correlate with supplied receipts
- missing supplied receipt data produces gaps
- lifecycle gap summary from store
- truth-boundary anomalies propagated
- JSON export deterministic
- no store mutation
- no payout readiness inferred
- no DAO activation inferred
- no default DB path
- tmp_path only

## Regression Tests

All existing tests pass:
- `test_cabr_lifecycle_correlation.py`: 43 passed
- `test_cabr_consensus_store.py`: 35 passed  
- `test_cabr_consensus_reporting_time_correlation.py`: 46 passed
- `test_cabr_lifecycle_query.py`: 45 passed

**Total**: 169 tests passed

## WSP 97 Verdict

**PASS** - All truth boundary constraints enforced:
- No automatic state progression
- No verification_complete/cabr_ready/payout_ready inference
- No payout approval
- No DAO activation
- No token issuance
- No external settlement
- Read-only queries only
- Store path caller-provided (no default)
- No filesystem writes
- No network calls
- Scoring/quorum/finalization semantics unchanged

## Files Changed

1. `modules/communication/moltbot_bridge/src/cabr_lifecycle_query.py` (NEW)
2. `modules/communication/moltbot_bridge/tests/test_cabr_lifecycle_query.py` (NEW)
3. `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION.md` (NEW)
4. `modules/communication/moltbot_bridge/ModLog.md` (UPDATE)
5. `modules/communication/moltbot_bridge/tests/TestModLog.md` (UPDATE)

## Recommended Next Slice

Phase 8: Lifecycle Report Export Integration
- Combine lifecycle query with consensus reporting for unified export
- Add batch query support for large stores
- Add aggregation statistics to lifecycle query results
