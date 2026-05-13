# CABR Consensus Finalization Phase 9: Store-Export Integration

**Slice**: CABR_CONSENSUS_FINALIZATION_PHASE9_STORE_EXPORT_INTEGRATION
**Worker**: W1
**Date**: 2026-05-13
**Status**: COMPLETE

## Overview

Phase 9 adds a caller-driven store-to-export integration helper that composes:
- CABRConsensusStore (Phase 2) - SQLite persistence
- Lifecycle Query (Phase 7) - store query with correlation
- Lifecycle Report Export (Phase 8) - unified JSON/Markdown export

## WSP 97 Critical Constraint

Store-export integration is **OBSERVABILITY ONLY**. It does NOT mean:
- automatic state progression
- verification_complete=True
- cabr_ready=True
- payout_ready=True
- payout approval
- DAO activation
- token issuance
- final consensus readiness
- external settlement

## Implementation

### Files Created

1. **`modules/communication/moltbot_bridge/src/cabr_store_export.py`**
   - `CABRStoreExportRequest` - Request dataclass
   - `CABRStoreExportResult` - Result dataclass with WSP 97 fields
   - `build_store_export()` - Main orchestration helper
   - `build_store_export_json()` - JSON-only convenience function
   - `build_store_export_markdown()` - Markdown-only convenience function

2. **`modules/communication/moltbot_bridge/tests/test_cabr_store_export.py`**
   - 65 test cases covering all required scenarios

### API

```python
from modules.communication.moltbot_bridge.src.cabr_store_export import (
    build_store_export,
    build_store_export_json,
    build_store_export_markdown,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import CABRConsensusStore

# Caller must provide store (no default DB path)
store = CABRConsensusStore(db_path="/path/to/db.sqlite")
store.initialize_schema()

# Full export with both formats
result = build_store_export(
    store=store,
    receipts=receipts,           # Optional supplemental data
    pavs_results=pavs_results,   # Optional supplemental data
    score_results=score_results, # Optional supplemental data
    quorum_results=quorum_results, # Optional supplemental data
    start=datetime(2026, 1, 1, tzinfo=timezone.utc),  # Optional time filter
    end=datetime(2026, 12, 31, tzinfo=timezone.utc),  # Optional time filter
    limit=100,                   # Optional record limit
    include_json=True,           # Default True
    include_markdown=True,       # Default True
)

# Access exports (strings only, no file writes)
json_export = result.json_export
markdown_export = result.markdown_export

# Or use convenience functions
json_str = build_store_export_json(store)
md_str = build_store_export_markdown(store)
```

### Behavior

1. Caller MUST provide store object (no default DB path)
2. No filesystem writes (returns strings only)
3. Composes existing lifecycle query and report export APIs
4. Returns JSON/Markdown strings only
5. Preserves all required WSP 97 labels:
   - REVIEW_ONLY
   - OBSERVABILITY_ONLY
   - NOT_CABR_READY
   - NOT_PAYOUT_READY
   - NO_DAO_ACTIVATION
   - NO_EXTERNAL_ATTESTATION_REQUIRED
6. Invalid query params fail closed (raises ValueError)
7. Missing supplemental data reported as gaps, not inferred
8. Truth-boundary anomalies flagged, not corrected
9. No payout/DAO/final consensus readiness inferred

## Test Coverage

### Test Results

```
test_cabr_store_export.py: 65 passed
test_cabr_lifecycle_report_export.py: 67 passed (regression)
test_cabr_lifecycle_query.py: 45 passed (regression)
test_cabr_consensus_store.py: 35 passed (regression)
```

### Test Categories

1. **No Store Provided Fails Closed** (4 tests)
   - build_store_export raises without store
   - build_store_export_json raises without store
   - build_store_export_markdown raises without store
   - Request validation fails without store

2. **Empty Store Exports** (5 tests)
   - Valid JSON output
   - Valid Markdown output
   - Deterministic JSON
   - Zero records reported
   - Sorted JSON keys

3. **Store With Records Exports** (6 tests)
   - Valid JSON output
   - Valid Markdown output
   - Correct record count
   - Correlations present
   - JSON convenience function
   - Markdown convenience function

4. **Include Toggles** (4 tests)
   - Both enabled by default
   - JSON only
   - Markdown only
   - Neither export

5. **Invalid Time Range** (4 tests)
   - ValueError on start > end
   - JSON function raises
   - Markdown function raises
   - Request validation fails

6. **Missing Receipts Produce Gaps** (5 tests)
   - No receipts produces gaps
   - Partial receipts produces gaps
   - Full receipts reduces gaps
   - Gap summary in JSON
   - Gap summary in Markdown

7. **WSP 97 Labels Present** (9 tests)
   - All required labels in result
   - All required labels in JSON
   - All required labels in Markdown
   - Individual label tests

8. **No Filesystem Writes** (4 tests)
   - Export does not create files
   - JSON function does not create files
   - Markdown function does not create files
   - Returns strings not paths

9. **No Default DB Path** (4 tests)
   - build_store_export requires store
   - JSON function requires store
   - Markdown function requires store
   - No db_path parameter

10. **No Payout Readiness Inferred** (3 tests)
    - payout_ready always False
    - No payout amount fields
    - NOT_PAYOUT_READY label present

11. **No DAO Activation Inferred** (3 tests)
    - cabr_ready always False
    - No DAO fields
    - NO_DAO_ACTIVATION label present

12. **No CABR Readiness Inferred** (2 tests)
    - verification_complete always False
    - NOT_CABR_READY label present

13. **Truth Anomaly Propagation** (6 tests)
    - Anomaly in pavs flagged
    - Anomaly in score flagged
    - Anomaly in quorum flagged
    - No anomalies by default
    - Anomaly section in JSON
    - Anomaly section in Markdown

14. **Request Dataclass** (3 tests)
    - Valid request
    - Request with time range
    - Request with all options

15. **Result Dataclass** (3 tests)
    - WSP 97 fields initialized
    - to_dict serialization
    - Sorted keys

## WSP Compliance

- **WSP 11**: Interface contract (explicit, typed)
- **WSP 91**: Observability (timestamps, audit fields)
- **WSP 97**: System Execution Prompting (truth boundaries)

## Architecture

```
Phase 2: CABRConsensusStore (SQLite persistence)
    |
Phase 7: query_lifecycle_from_store() (store + correlation)
    |
Phase 8: build_lifecycle_report_export() (unified export)
    |
Phase 9: build_store_export() (orchestration helper) <-- THIS PHASE
```

## Next Steps

Recommended next slice: CABR_CONSENSUS_FINALIZATION_PHASE10_CONSENSUS_REPORT_EXPORT_INTEGRATION

This would add consensus report integration to the store export, combining:
- Store export (Phase 9)
- Consensus reporting (Phase 4)
- Full end-to-end pipeline export
