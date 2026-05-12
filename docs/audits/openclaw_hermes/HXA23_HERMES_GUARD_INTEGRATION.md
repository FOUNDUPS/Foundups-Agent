# HXA23 - Hermes Guard Integration (Phase 1)

**Slice**: `HXA23_HERMES_GUARD_INTEGRATION_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - integration of HXA22 guard into HermesJobExecutor
**Branch**: `feat/hxa23-hermes-guard-integration`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **HERMES_GUARD_INTEGRATION_DEFINED**

The HXA22 destructive action guard has been integrated into HermesJobExecutor as a safe no-op validation seam without:
- Enabling live delegation
- Creating repos
- Modifying production source
- Using real credentials or capability tokens
- Initiating external federation
- Production readiness claims

**HXA22 proved the destructive action guard runtime contract.**
**HXA23 integrates that guard into the Hermes job execution flow.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Guard integrated into HermesJobExecutor | **PROVEN** | `execute()` calls `_evaluate_destructive_action_guard()` |
| Guard evaluated before delegation paths | **PROVEN** | Guard check is Step 2.5 before controlled harness |
| Guard result stored in HermesDelegationResult | **PROVEN** | `guard_evaluated` and `guard_result` fields |
| D0 validate allowed as dry-run | **PROVEN** | Test case passes |
| D1 queue allowed as dry-run | **PROVEN** | Test case passes |
| D2 simulate/extract/build allowed | **PROVEN** | Test case passes |
| D4 repo write blocked | **PROVEN** | Test case passes |
| D5 external side effect blocked | **PROVEN** | Test case passes |
| D6 irreversible blocked | **PROVEN** | Test case passes |
| Blocked guard does not call delegate | **PROVEN** | `controlled_delegate_invoked=False` |
| live_external_delegate_called | **False** | All tests assert False |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| real_execution_performed | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. Integration Architecture

### 3.1 Execution Flow

```
FoundUpJob
    ↓
HermesJobExecutor.execute()
    ↓
Step 1: Validate job structure
    ↓
Step 2: Build delegation request
    ↓
Step 2.5: *** HXA23 Guard Evaluation ***
    ├── _classify_destructive_action()  → D0/D1/D2 in Phase 1
    ├── _build_destructive_action_request()  → Guard request from job
    └── _evaluate_destructive_action_guard()  → Guard evaluation
        ├── If BLOCKED → Return BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
        └── If ALLOWED → Continue to Step 3
    ↓
Step 3: Controlled harness paths (HXA14/HXA16)
    ↓
Step 4: Feature flag check
    ↓
Step 5: Dry-run check → SIMULATED
    ↓
Step 6: Import check
    ↓
Step 7: Real delegation → BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED
```

### 3.2 Action Classification (Phase 1)

| Action Pattern | Destructive Class | Reason |
|----------------|-------------------|--------|
| `validate_*` | D0_OBSERVE | Read-only observation |
| `queue_*` | D0_OBSERVE | Read-only observation |
| `build_*` | D2_SIMULATE | Dry-run simulation (D3 deferred) |
| `extract_*` | D2_SIMULATE | Dry-run simulation |
| Other | D2_SIMULATE | Conservative default |

**Note**: D3_WRITE_SANDBOX classification deferred because it requires `capability_token_present` which is not yet implemented in PolicyFlags.

---

## 4. New Components

### 4.1 HermesDelegationResult Fields

```python
# HXA23 Destructive Action Guard Fields
guard_evaluated: bool = False
guard_result: Optional[Dict[str, Any]] = None
```

### 4.2 HermesExecutionStatus

```python
# HXA23: Destructive action guard blocked states
BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD = "BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD"
```

### 4.3 New Methods

```python
def _classify_destructive_action(
    self,
    job: "FoundUpJob",
    request: HermesDelegationRequest,
) -> DestructiveActionClass:
    """Classify job action into destructive action class (D0-D2 in Phase 1)."""

def _build_destructive_action_request(
    self,
    job: "FoundUpJob",
    request: HermesDelegationRequest,
) -> DestructiveActionRequest:
    """Build DestructiveActionRequest from job and delegation request."""

def _evaluate_destructive_action_guard(
    self,
    job: "FoundUpJob",
    request: HermesDelegationRequest,
) -> DestructiveActionGuardResult:
    """Evaluate destructive action guard for the job."""
```

---

## 5. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestHermesCallsDestructiveGuard` | 4 | Guard evaluation occurs |
| `TestD0D1D2D3AllowedAsDryRunOnly` | 5 | D0/D1/D2 allowed |
| `TestD4RepoWriteBlocked` | 2 | D4 blocked |
| `TestD5ExternalSideEffectBlocked` | 2 | D5 blocked |
| `TestD6IrreversibleBlocked` | 1 | D6 blocked |
| `TestBlockedGuardDoesNotWriteFiles` | 3 | Blocked = no files |
| `TestWSP97TruthFieldsPreserved` | 8 | Truth fields False |
| `TestEvidenceCheckpointFieldsPreserved` | 2 | Checkpoint preserved |
| `TestD3MissingGatesBlocked` | 2 | D3 gate failures |
| `TestGuardIntegrationFlow` | 2 | Complete flow |
| `TestExistingDryRunBehaviorPreserved` | 2 | Dry-run preserved |
| `TestHXA23VerdictDocumentation` | 1 | Verdict documented |

**Total**: 34 tests, all passing

---

## 6. What HXA23 Proves

| Proof Point | Evidence |
|-------------|----------|
| Guard integrated into executor | `execute()` method modified |
| Guard evaluated before delegation | Step 2.5 in flow |
| Guard result in HermesDelegationResult | New fields added |
| D0/D1/D2 allowed dry-run | 5 test cases pass |
| D4/D5/D6 blocked | 5 test cases pass |
| Blocked guard = no delegate call | Test case passes |
| WSP 97 truth fields remain False | 8 test cases pass |
| Existing dry-run preserved | 2 test cases pass |

---

## 7. What HXA23 Does NOT Prove

| Gap | Reason |
|-----|--------|
| D3 sandbox write gate | Requires capability tokens in PolicyFlags |
| Live execution capability | Phase 1 blocks all live execution |
| Real capability token validation | Uses fake tokens (HXA21) |
| Real human approval flow | Requires approval UI/API |
| Hermes runtime integration | No-op validation only |

---

## 8. Files Changed

| File | Type | Lines Changed |
|------|------|---------------|
| `wre_core/src/hermes_job_executor.py` | MODIFIED | +150 |
| `wre_core/tests/test_hxa23_hermes_guard_integration.py` | NEW | 800+ |
| `wre_core/tests/test_hermes_job_executor.py` | MODIFIED | +50 |
| `wre_core/ModLog.md` | UPDATED | +70 |
| `wre_core/tests/TestModLog.md` | UPDATED | +40 |
| `docs/audits/openclaw_hermes/HXA23_HERMES_GUARD_INTEGRATION.md` | NEW | This file |

---

## 9. Production Code Changes

**YES - Production code modified.**

Modified file: `modules/infrastructure/wre_core/src/hermes_job_executor.py`

Changes:
1. Imported guard types from `destructive_action_guard`
2. Added `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD` status
3. Added `guard_evaluated` and `guard_result` fields
4. Added classification, build, and evaluation methods
5. Modified `execute()` to evaluate guard before delegation

The changes are:
- Safe validation seam (no side effects)
- Fail-closed by design (blocks D4/D5/D6)
- Uses no external dependencies beyond HXA22 guard
- Uses no real credentials
- Does not enable live execution

---

## 10. WSP 97 Closing Statement

This implementation integrates the HXA22 destructive action guard into HermesJobExecutor as a validation seam.

**What is confirmed**:
- Guard is evaluated before any delegation paths
- Guard result is stored in execution result
- D0/D1/D2 actions allowed to continue (dry-run only)
- D4/D5/D6 actions blocked by guard
- Blocked actions do not call delegate adapter
- All WSP 97 truth fields remain False
- Existing dry-run behavior preserved

**What is NOT confirmed**:
- D3 sandbox write capability (requires capability tokens)
- Live execution capability
- Real capability token validation
- Real human approval flow
- External federation readiness

---

## 11. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1` | Add capability_token_present to PolicyFlags | **P0** |
| 2 | `HXA25_D3_SANDBOX_GATE_PHASE1` | Enable D3 sandbox write with tokens | P1 |
| 3 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA23_HERMES_GUARD_INTEGRATION_PHASE1.
