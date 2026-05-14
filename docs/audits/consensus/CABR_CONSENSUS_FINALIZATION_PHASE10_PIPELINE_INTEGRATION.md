# CABR Consensus Finalization Phase 10: Pipeline Integration

**Date**: 2026-05-13
**Slice**: CABR_CONSENSUS_FINALIZATION_PHASE10_PIPELINE_INTEGRATION
**Worker**: W1
**WSP Compliance**: WSP 11, WSP 91, WSP 97

## Summary

Phase 10 adds a caller-driven CABR consensus pipeline composer that runs the
existing review-only pipeline stages in deterministic order:

```
ProofOfComputeReceipt -> pAVS -> CABR scoring -> quorum -> consensus
finalization -> optional persistence -> lifecycle query/export
```

## WSP 97 Critical Constraints

Pipeline integration is **explicit/caller-driven observability and review flow only**.

It does **NOT** mean:
- automatic state progression
- verification_complete=True
- cabr_ready=True
- payout_ready=True
- payout approval
- DAO activation
- token issuance
- final consensus readiness
- external settlement

## Files Created

### Implementation

**`modules/communication/moltbot_bridge/src/cabr_consensus_pipeline.py`**

Defines:
- `CABRConsensusPipelineInput` - Input with receipts, attestations, optional pre-computed results
- `CABRConsensusPipelineResult` - Result with stage results, consensus records, exports
- `CABRConsensusPipelineStageStatus` - Stage execution status enum
- `CABRConsensusPipelineStage` - Pipeline stage identifier enum
- `run_cabr_consensus_pipeline(...)` - Main pipeline composer function
- `export_cabr_consensus_pipeline_json(...)` - Deterministic JSON export
- `export_cabr_consensus_pipeline_markdown(...)` - Deterministic Markdown export

### Tests

**`modules/communication/moltbot_bridge/tests/test_cabr_consensus_pipeline.py`**

35 tests covering:
- Minimal receipt pipeline returns review-only result
- Missing evidence fails closed
- pAVS reject blocks scoring/finalization path
- Quorum not met returns pending/review-only state
- Quorum met + score accepted returns accepted-for-review only
- Optional store persists record when provided
- No store creates no DB/file writes
- Export JSON/Markdown deterministic
- Required WSP_97 labels present
- No payout readiness inferred
- No DAO activation inferred
- No CABR readiness inferred
- Stage failure explicit
- Batch pipeline deterministic

## Pipeline API

### Input

```python
CABRConsensusPipelineInput(
    receipts=[receipt_dict],           # Required: At least one receipt
    attestations=[VerifierAttestation(...)],  # Required: Verifier attestations
    pavs_results=None,                 # Optional: Pre-computed pAVS results
    score_results=None,                # Optional: Pre-computed score results
    quorum_results=None,               # Optional: Pre-computed quorum results
    store=None,                        # Optional: CABRConsensusStore for persistence
    min_validators=3,                  # WSP 29 default
    consensus_threshold=0.382,         # WSP 29 default
    include_lifecycle_export=False,    # Generate lifecycle export
)
```

### Running the Pipeline

```python
result = run_cabr_consensus_pipeline(pipeline_input)

# Result contains:
result.success                # True if pipeline completed
result.stage_results          # List of stage results
result.consensus_records      # List of CABRConsensusRecord
result.persistence_attempted  # True if store was provided
result.persistence_success    # True if all persisted
result.json_export           # JSON string (if lifecycle export requested)
result.markdown_export       # Markdown string (if lifecycle export requested)
```

## Stage Failure Behavior

The pipeline **fails closed** on stage errors:

1. Input validation failure -> RECEIPT stage FAILED
2. pAVS verification exception -> PAVS stage FAILED
3. CABR scoring exception -> SCORING stage FAILED
4. Quorum evaluation exception -> QUORUM stage FAILED
5. Consensus finalization exception -> FINALIZATION stage FAILED

When a stage fails:
- `result.success = False`
- `result.failed_stage` = the failed stage
- All downstream stages marked as `BLOCKED`
- Explicit error message in stage result

**Note**: Persistence and export failures do NOT fail the pipeline - records are
still returned. Caller must check `persistence_success` if storage is required.

## Export Behavior

### JSON Export

```python
json_str = export_cabr_consensus_pipeline_json(result, indent=2)
```

- Deterministic output (sorted keys)
- Contains all WSP 97 required labels
- Contains truth boundary fields (all False)
- Contains compliance note

### Markdown Export

```python
md_str = export_cabr_consensus_pipeline_markdown(result)
```

- Human-readable format
- Contains WSP 97 compliance notice header
- Contains truth boundary table
- Contains stage results table
- Contains consensus records summary

## WSP 97 Required Labels

All exports include:
- REVIEW_ONLY
- OBSERVABILITY_ONLY
- NOT_CABR_READY
- NOT_PAYOUT_READY
- NO_DAO_ACTIVATION
- NO_EXTERNAL_ATTESTATION_REQUIRED

## Truth Boundary Fields

All results enforce:
- verification_complete = False
- cabr_ready = False
- payout_ready = False

## Test Results

```
35 passed in 0.64s
```

## Regression Tests

All existing module tests pass:
```
287 passed in 3.09s
```

Including:
- test_cabr_store_export.py
- test_cabr_lifecycle_report_export.py
- test_cabr_consensus_finalizer.py
- test_quorum_verification_engine.py
- test_cabr_scoring_engine.py
- test_pavs_verification_seam.py

## WSP 97 Verdict

**COMPLIANT**

- No automatic state progression
- No default DB path
- No filesystem writes without caller-provided store
- No network calls
- No secrets
- No payout inference
- No DAO activation inference
- No CABR readiness inference
- All required labels present
- All truth boundary fields False
- Stage failures explicit and fail-closed
- Exports deterministic

## Recommended Next Slice

Phase 11 options:
1. **Batch pipeline optimization** - Parallel stage execution for multiple receipts
2. **Pipeline metrics** - Observability for pipeline execution timing/counts
3. **Pipeline resumption** - Resume from checkpoint on failure
4. **CLI integration** - Command-line interface for manual pipeline runs
