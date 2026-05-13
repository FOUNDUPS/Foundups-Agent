# CABR Runtime Scoring Engine Phase 1

**Implementation Date**: 2026-05-13  
**Slice**: `CABR_RUNTIME_SCORING_ENGINE_PHASE1`  
**Worker**: W1  
**WSP Lock**: WSP 00 -> WSP 50 -> WSP 97  
**Base Commit**: 255bf3fc0dc78bec465e7dc24c4e7848e2501e82

---

## 1. Mission Summary

Implement the first deterministic CABR runtime scoring seam for internal sovereign consensus per PR #574 gap analysis.

**Key Constraint**: Deterministic scoring only. No payouts, DAO activation, external attestation, network calls, secrets, or token issuance.

---

## 2. Implementation

### 2.1 Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `modules/communication/moltbot_bridge/src/cabr_scoring_engine.py` | ~750 | Core CABR scoring engine |
| `modules/communication/moltbot_bridge/tests/test_cabr_scoring_engine.py` | ~560 | Test coverage (42 tests) |
| `docs/audits/consensus/CABR_RUNTIME_SCORING_ENGINE_PHASE1.md` | This document | Audit trail |

### 2.2 API Surface

```python
# Enums
class CABRScoreDecision(str, Enum):
    NOT_EVALUATED
    ACCEPTED_FOR_REVIEW
    ACCEPTED_FOR_REVIEW_PENDING_QUORUM
    REJECTED_INSUFFICIENT_EVIDENCE
    REJECTED_TRUTH_BOUNDARY
    REJECTED_QUORUM_NOT_MET
    REJECTED_DUPLICATE_VERIFIERS
    REJECTED_PAVS_FAILED
    REJECTED_MISSING_IDENTITY

class CABRScoreReason(str, Enum):
    OK_EVIDENCE_PRESENT_QUORUM_MET
    OK_EVIDENCE_PRESENT_DRY_RUN
    OK_EVIDENCE_PRESENT_PENDING_QUORUM
    REJECTED_NO_EVIDENCE
    REJECTED_EMPTY_EVIDENCE
    REJECTED_VERIFICATION_COMPLETE_CLAIMED
    REJECTED_CABR_READY_CLAIMED
    REJECTED_PAYOUT_READY_CLAIMED
    REJECTED_BELOW_MIN_VALIDATORS
    REJECTED_DUPLICATE_VERIFIER_IDS
    REJECTED_PAVS_BLOCKED_MISSING_EVIDENCE
    REJECTED_PAVS_BLOCKED_UPSTREAM
    REJECTED_PAVS_FAILED_INPUT
    REJECTED_PAVS_REJECTED_IDENTITY
    REJECTED_PAVS_REJECTED_STATUS
    REJECTED_NO_RECEIPT_ID
    REJECTED_NO_JOB_ID
    REJECTED_NO_TENANT_ID
    NOT_EVALUATED

# Dataclasses
@dataclass
class CABRScoreInput:
    receipt_id: str
    job_id: str
    tenant_id: str
    evidence_refs: List[str]
    verifier_ids: List[str]
    pavs_decision: Optional[str]
    is_dry_run: bool
    is_simulated: bool
    verification_complete: bool  # WSP 97 input
    cabr_ready: bool            # WSP 97 input
    payout_ready: bool          # WSP 97 input
    foundup_id: Optional[str]
    intent_id: Optional[str]
    source_type: str

@dataclass
class CABRScoreResult:
    score_id: str
    receipt_id: str
    job_id: str
    tenant_id: str
    decision: CABRScoreDecision
    reason_code: CABRScoreReason
    reason_human: str
    verifier_count: int
    unique_verifier_count: int
    min_validators: int          # WSP 29 default: 3
    quorum_met: bool
    duplicate_verifiers_detected: bool
    evidence_count: int
    evidence_present: bool
    is_dry_run: bool
    is_simulated: bool
    verification_complete: bool  # WSP 97: Always False
    cabr_ready: bool            # WSP 97: Always False
    payout_ready: bool          # WSP 97: Always False
    pavs_decision: Optional[str]
    pavs_passed: bool
    scored_at: datetime
    scorer_version: str

# Core Functions
def score_cabr_receipt(
    score_input: CABRScoreInput,
    min_validators: int = 3,
    include_input_snapshot: bool = False,
) -> CABRScoreResult

def score_cabr_batch(
    inputs: List[CABRScoreInput],
    min_validators: int = 3,
) -> List[CABRScoreResult]

# Convenience
def score_from_receipt(receipt, verifier_ids, min_validators) -> CABRScoreResult
def score_from_pavs_result(result, verifier_ids, min_validators) -> CABRScoreResult
def build_score_input_from_receipt(receipt, verifier_ids) -> CABRScoreInput
def build_score_input_from_pavs_result(result, verifier_ids) -> CABRScoreInput
```

---

## 3. Scoring Decisions

### 3.1 Decision Tree

```
1. Validate identity (receipt_id, job_id, tenant_id)
   -> Missing: REJECTED_MISSING_IDENTITY

2. Validate WSP 97 truth boundaries
   -> verification_complete=True: REJECTED_TRUTH_BOUNDARY
   -> cabr_ready=True: REJECTED_TRUTH_BOUNDARY
   -> payout_ready=True: REJECTED_TRUTH_BOUNDARY

3. Validate evidence presence
   -> No evidence: REJECTED_INSUFFICIENT_EVIDENCE

4. Validate pAVS decision (if present)
   -> blocked_*: REJECTED_PAVS_FAILED
   -> failed_input: REJECTED_PAVS_FAILED

5. Evaluate verifier quorum
   -> Duplicate IDs: REJECTED_DUPLICATE_VERIFIERS
   -> Below min_validators: ACCEPTED_FOR_REVIEW_PENDING_QUORUM
   -> Met quorum: ACCEPTED_FOR_REVIEW

6. Check execution mode
   -> dry_run/simulated: ACCEPTED_FOR_REVIEW (reason=DRY_RUN)
   -> real execution + quorum: ACCEPTED_FOR_REVIEW (reason=QUORUM_MET)
```

### 3.2 Quorum Behavior

| Verifiers | Unique | Quorum (min=3) | Decision |
|-----------|--------|----------------|----------|
| 0 | 0 | No | ACCEPTED_FOR_REVIEW_PENDING_QUORUM |
| 2 | 2 | No | ACCEPTED_FOR_REVIEW_PENDING_QUORUM |
| 3 | 3 | Yes | ACCEPTED_FOR_REVIEW |
| 5 | 5 | Yes | ACCEPTED_FOR_REVIEW |
| 4 | 2 (duplicates) | N/A | REJECTED_DUPLICATE_VERIFIERS |

---

## 4. WSP 97 Compliance

### 4.1 Truth Fields (Always False in Phase 1)

| Field | Value | Rationale |
|-------|-------|-----------|
| `verification_complete` | `False` | No cryptographic verification performed |
| `cabr_ready` | `False` | No CABR consensus exists |
| `payout_ready` | `False` | No payout engine exists |

### 4.2 Input Rejection

If ANY of these input fields are `True`, the scoring is rejected with `REJECTED_TRUTH_BOUNDARY`:
- `verification_complete`
- `cabr_ready`
- `payout_ready`

This enforces fail-closed behavior: Phase 1 cannot accept inputs claiming completion.

---

## 5. Test Coverage

### 5.1 Test Results

```
pytest modules/communication/moltbot_bridge/tests/test_cabr_scoring_engine.py -q
42 passed in 3.70s
```

### 5.2 Coverage Matrix

| Category | Tests | Status |
|----------|-------|--------|
| Missing evidence rejects | 2 | PASS |
| Valid dry-run receipt accepted for review only | 3 | PASS |
| verification_complete=False never produces final consensus | 2 | PASS |
| cabr_ready=False preserved | 1 | PASS |
| payout_ready=False preserved | 1 | PASS |
| verifier_count below 3 fails quorum | 3 | PASS |
| 3 unique verifiers passes quorum eligibility | 2 | PASS |
| Duplicate verifiers do not count | 2 | PASS |
| Failed pAVS result rejects | 4 | PASS |
| Truth-boundary violation rejects | 3 | PASS |
| Batch scoring deterministic | 2 | PASS |
| No network calls | 1 | PASS |
| No token issuance | 1 | PASS |
| WSP 97 truth fields remain False | 1 | PASS |
| Missing identity rejects | 4 | PASS |
| Score ID generation | 2 | PASS |
| Serialization roundtrip | 2 | PASS |
| Convenience functions | 2 | PASS |
| min_validators configuration | 2 | PASS |
| Input builders | 2 | PASS |

### 5.3 Related Test Suites

All related test suites pass:
- `test_pavs_verification_seam.py`: 24 passed
- `test_proof_of_compute_receipt.py`: 26 passed
- `test_hermes_job_executor.py`: 94 passed

---

## 6. Architecture Integration

### 6.1 Position in Pipeline

```
ProofOfComputeReceipt (W6)
         |
         v
PAVSVerificationResult (W7)
         |
         v
CABRScoreResult (W1) <-- THIS SLICE
         |
         v
[Future: CABR Consensus Engine]
         |
         v
[Future: Payout Engine]
```

### 6.2 Dependencies

**Consumes**:
- `ProofOfComputeReceipt` (proof_of_compute_receipt.py)
- `PAVSVerificationResult` (pavs_verification_seam.py)

**Produces**:
- `CABRScoreResult` for future consensus/payout engines

**Does NOT Depend On**:
- Network services
- External attestation
- Token systems
- Wallet services
- FAM state mutation

---

## 7. WSP Compliance

| WSP | Requirement | Status |
|-----|-------------|--------|
| WSP 11 | Interface contract (explicit, typed) | COMPLIANT |
| WSP 29 | CABR Engine Framework (min_validators=3) | COMPLIANT |
| WSP 50 | Pre-Action Verification | COMPLIANT |
| WSP 91 | Observability (timestamps, audit fields) | COMPLIANT |
| WSP 97 | System Execution Prompting (truth boundaries) | COMPLIANT |

---

## 8. WSP 97 Verdict

| Claim | Status | Evidence |
|-------|--------|----------|
| Scoring is deterministic | TRUE | Pure function, no side effects |
| No network calls | TRUE | No imports of http/socket/requests |
| No token issuance | TRUE | No token-related fields in output |
| verification_complete=False always | TRUE | Hardcoded in all code paths |
| cabr_ready=False always | TRUE | Hardcoded in all code paths |
| payout_ready=False always | TRUE | Hardcoded in all code paths |
| No FAM/pAVS mutation | TRUE | Read-only input consumption |
| Quorum enforcement per WSP 29 | TRUE | min_validators=3 default |
| Duplicate verifier rejection | TRUE | Test coverage confirms |

**Verdict**: PHASE 1 COMPLIANT - Deterministic scoring seam operational.

---

## 9. Recommended Next Slice

```
QUORUM_VERIFICATION_ENFORCEMENT_PHASE1

Mission:
- Implement verifier attestation recording
- Connect CABR scoring to pAVS verification result storage
- Enforce quorum thresholds before state transition
- WSP 97: Do not claim verification_complete until quorum met

Deliverables:
- Verifier attestation model
- Quorum threshold enforcement logic
- pAVS -> CABR integration seam
```

---

## 10. Audit Trail

- **Worker**: W1
- **Slice**: CABR_RUNTIME_SCORING_ENGINE_PHASE1
- **Tests**: 42 passed
- **Related Tests**: 144 passed (24 + 26 + 94)
- **Files Created**: 3 (engine, tests, audit doc)

---

*Audit performed by Worker W1 under WSP 00/50/97 truth boundaries.*
