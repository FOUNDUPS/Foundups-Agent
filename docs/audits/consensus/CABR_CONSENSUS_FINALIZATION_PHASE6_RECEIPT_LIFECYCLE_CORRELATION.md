# CABR Consensus Finalization Phase 6 - Receipt Lifecycle Correlation

**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION`
**Worker**: W1
**Date**: 2026-05-13
**WSP Compliance**: WSP 97 (System Execution Prompting), WSP 91 (Observability)

## Summary

Implemented read-only lifecycle correlation across all 7 CABR consensus pipeline stages:

| Stage | Item Type | Correlation Key |
|-------|-----------|-----------------|
| 1. RECEIPT_CREATED | ProofOfComputeReceipt | receipt_id, job_id |
| 2. PAVS_EVALUATED | PAVSVerificationResult | receipt_id, job_id |
| 3. CABR_SCORED | CABRScoreResult | receipt_id, job_id |
| 4. QUORUM_EVALUATED | QuorumVerificationResult | receipt_id, job_id |
| 5. CONSENSUS_FINALIZED | CABRConsensusRecord | receipt_id, job_id, record_hash |
| 6. PERSISTED | CABRConsensusRecord (stored) | receipt_id, job_id, record_hash |
| 7. REPORTED | CABRConsensusRecord (in report) | receipt_id, job_id, record_hash |

## WSP 97 Critical Constraint

Lifecycle correlation is **observability only**. It does NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement

## API Surface

### Enums

```python
class CABRLifecycleStage(str, Enum):
    RECEIPT_CREATED = "receipt_created"
    PAVS_EVALUATED = "pavs_evaluated"
    CABR_SCORED = "cabr_scored"
    QUORUM_EVALUATED = "quorum_evaluated"
    CONSENSUS_FINALIZED = "consensus_finalized"
    PERSISTED = "persisted"
    REPORTED = "reported"

LIFECYCLE_STAGE_ORDER: List[CABRLifecycleStage]  # 7 stages in order
```

### Dataclasses

```python
@dataclass
class CABRLifecycleItem:
    stage: CABRLifecycleStage
    receipt_id: Optional[str]
    job_id: Optional[str]
    record_hash: Optional[str]
    item_id: Optional[str]
    timestamp: Optional[datetime]
    decision: Optional[str]
    reason_code: Optional[str]
    verification_complete: bool = False  # WSP 97 truth field
    cabr_ready: bool = False             # WSP 97 truth field
    payout_ready: bool = False           # WSP 97 truth field

@dataclass
class CABRLifecycleGap:
    correlation_key: str
    correlation_value: str
    present_stage: CABRLifecycleStage
    missing_stage: CABRLifecycleStage
    gap_type: str = "missing_downstream"

@dataclass
class CABRLifecycleCorrelation:
    correlation_key: str
    correlation_value: str
    stages_present: List[CABRLifecycleStage]
    stages_missing: List[CABRLifecycleStage]
    items: Dict[str, CABRLifecycleItem]
    gaps: List[CABRLifecycleGap]
    has_truth_boundary_anomaly: bool
    anomaly_details: List[str]

@dataclass
class CABRLifecycleCorrelationResult:
    correlations: List[CABRLifecycleCorrelation]
    total_items: int
    items_by_stage: Dict[str, int]
    total_gaps: int
    total_anomalies: int
    generated_at: datetime
    wsp97_compliance_note: str

@dataclass
class CABRLifecycleGapSummary:
    total_gaps: int
    gaps_by_stage: Dict[str, int]
    correlations_with_gaps: int
    correlations_complete: int
```

### Functions

```python
def correlate_cabr_lifecycle(
    receipts: Optional[List[Dict]] = None,
    pavs_results: Optional[List[Dict]] = None,
    score_results: Optional[List[Dict]] = None,
    quorum_results: Optional[List[Dict]] = None,
    consensus_records: Optional[List[Dict]] = None,
    persisted_records: Optional[List[Dict]] = None,
    reported_records: Optional[List[Dict]] = None,
) -> CABRLifecycleCorrelationResult

def summarize_lifecycle_gaps(
    result: CABRLifecycleCorrelationResult
) -> CABRLifecycleGapSummary

def export_lifecycle_correlation_json(
    result: CABRLifecycleCorrelationResult,
    indent: int = 2
) -> str
```

## Behavior Specifications

### Correlation Key Priority

1. `receipt_id` (primary)
2. `job_id` (fallback)
3. `record_hash` (for consensus records only)

### Gap Detection

- Gaps are downstream from the highest present stage
- Missing intermediate stages are reported
- Gaps do NOT imply failure or retry needed
- Gap type is always `missing_downstream`

### Duplicate Handling

- First item at each stage wins (deterministic)
- `total_items` counts all inputs including duplicates
- Only one item per stage per correlation key

### Truth Boundary Anomaly Detection

- Flags any item with `verification_complete=True`
- Flags any item with `cabr_ready=True`
- Flags any item with `payout_ready=True`
- Anomaly details include stage and item_id

### JSON Export

- Deterministic output with sorted keys
- Datetime fields as ISO strings
- Includes WSP 97 compliance note
- No filesystem writes (pure string output)

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_lifecycle_correlation.py` | ~650 | Lifecycle correlation module |
| `tests/test_cabr_lifecycle_correlation.py` | ~700 | Test coverage (43 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION.md` | ~200 | This audit document |

## Test Coverage

43 tests covering:
- Stage enum ordering
- Receipt only -> downstream gaps
- Receipt + pAVS -> remaining gaps
- Full lifecycle correlation (no gaps)
- Correlation by receipt_id
- Correlation by job_id fallback
- Correlation by record_hash
- Duplicate handling (deterministic)
- Missing stage reporting (not inferred)
- Truth boundary anomaly detection
- Deterministic JSON export
- No store mutation
- No payout readiness inference
- No DAO activation inference
- No default DB path
- Gap summary statistics

## Regression Test Results

| Test Suite | Tests | Status |
|------------|-------|--------|
| test_cabr_lifecycle_correlation.py | 43 | PASS |
| test_cabr_consensus_reporting_time_correlation.py | 46 | PASS |
| test_cabr_consensus_reporting.py | 48 | PASS |
| test_cabr_consensus_finalizer.py | 48 | PASS |
| test_cabr_scoring_engine.py | 42 | PASS |
| test_quorum_verification_engine.py | 41 | PASS |
| test_pavs_verification_seam.py | 24 | PASS |
| test_proof_of_compute_receipt.py | 26 | PASS |

**Total**: 318 tests, 0 failures

## Usage Example

```python
from modules.communication.moltbot_bridge.src.cabr_lifecycle_correlation import (
    correlate_cabr_lifecycle,
    summarize_lifecycle_gaps,
    export_lifecycle_correlation_json,
)

# Correlate items across all stages
result = correlate_cabr_lifecycle(
    receipts=[...],           # ProofOfComputeReceipt dicts
    pavs_results=[...],       # PAVSVerificationResult dicts
    score_results=[...],      # CABRScoreResult dicts
    quorum_results=[...],     # QuorumVerificationResult dicts
    consensus_records=[...],  # CABRConsensusRecord dicts (in-memory)
    persisted_records=[...],  # CABRConsensusRecord dicts (from store)
    reported_records=[...],   # CABRConsensusRecord dicts (from report)
)

# Check for gaps
summary = summarize_lifecycle_gaps(result)
print(f"Total gaps: {summary.total_gaps}")
print(f"Complete correlations: {summary.correlations_complete}")

# Export as JSON
json_output = export_lifecycle_correlation_json(result)
```

## WSP 97 Compliance Verification

- [ ] No automatic state progression
- [ ] Truth fields remain False
- [ ] No payout readiness inference
- [ ] No DAO activation inference
- [ ] No token issuance
- [ ] No external settlement
- [ ] No default DB path
- [ ] No implicit filesystem writes
- [ ] No network calls
- [ ] Gaps reported, not inferred

**Verdict**: COMPLIANT
