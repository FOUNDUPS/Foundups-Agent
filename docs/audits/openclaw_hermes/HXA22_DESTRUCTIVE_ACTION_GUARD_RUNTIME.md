# HXA22 - Destructive Action Guard Runtime (Phase 1)

**Slice**: `HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - minimal production code + tests
**Branch**: `feat/hxa22-destructive-action-guard-runtime`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED**

A fail-closed runtime destructive action guard has been defined and tested without:
- Enabling live delegation
- Creating repos
- Modifying production source
- Using real credentials or capability tokens
- Initiating external federation
- Production readiness claims

**HXA19 proved the repo creation approval gate contract.**
**HXA20 proved the production source modification gate contract.**
**HXA21 proved the capability token infrastructure contract.**
**HXA22 provides the runtime guard seam that integrates these contracts.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| DestructiveActionClass enum defined | **PROVEN** | D0-D6 enum values |
| DestructiveActionRequest model defined | **PROVEN** | Dataclass with all gate fields |
| DestructiveActionGuardResult model defined | **PROVEN** | Dataclass with all WSP 97 fields |
| DestructiveActionGuard evaluator defined | **PROVEN** | Fail-closed evaluate() method |
| D0 observe dry-run allowed | **PROVEN** | Test case passes |
| D1 read dry-run allowed | **PROVEN** | Test case passes |
| D2 simulate allowed | **PROVEN** | Test case passes |
| D3 sandbox blocked without workspace binding | **PROVEN** | Test case passes |
| D3 sandbox blocked without path validation | **PROVEN** | Test case passes |
| D3 sandbox blocked without capability token | **PROVEN** | Test case passes |
| D3 sandbox blocked without security gate | **PROVEN** | Test case passes |
| D3 sandbox allowed when all gates pass | **PROVEN** | Test case passes |
| D4 repo write blocked | **PROVEN** | Test case passes |
| D5 external side effect blocked | **PROVEN** | Test case passes |
| D6 irreversible blocked | **PROVEN** | Test case passes |
| live_execution_allowed | **False** | All tests assert False |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. Destructive Action Classification

### 3.1 DestructiveActionClass Enum

| Class | Severity | Phase 1 Behavior |
|-------|----------|------------------|
| D0_OBSERVE | 0 | Allowed (dry-run only) |
| D1_READ | 1 | Allowed (dry-run only) |
| D2_SIMULATE | 2 | Allowed (dry-run only) |
| D3_WRITE_SANDBOX | 3 | Allowed when all gates pass |
| D4_WRITE_REPO | 4 | BLOCKED |
| D5_EXTERNAL_SIDE_EFFECT | 5 | BLOCKED |
| D6_IRREVERSIBLE | 6 | BLOCKED |

### 3.2 Guard Decision Types

| Decision | Meaning |
|----------|---------|
| ALLOW_DRY_RUN | Action allowed as dry-run only |
| BLOCKED | Action blocked by guard |
| REQUIRES_APPROVAL | Action requires human approval (future) |

---

## 4. Fail-Closed Rules

### 4.1 D0/D1/D2 Rules

- Allowed only if `dry_run_mode=True`
- No live execution in Phase 1

### 4.2 D3 Sandbox Write Rules

All gates must pass:
1. `workspace_binding_enforced=True`
2. `path_constraints_validated=True`
3. `capability_token_present=True`
4. `security_gate_passed=True`

If any gate fails, action is BLOCKED.

### 4.3 D4/D5/D6 Rules

- BLOCKED in Phase 1 (no live execution)
- Human approval required (future)
- Two-party approval for D6 (future)

---

## 5. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestDestructiveActionClassEnum` | 3 | Enum definition and severity |
| `TestDestructiveActionRequest` | 3 | Request model fields and defaults |
| `TestDestructiveActionGuardResult` | 2 | Result model WSP 97 fields |
| `TestD0ObserveDryRunAllowed` | 1 | D0 observe allowed |
| `TestD1ReadDryRunAllowed` | 1 | D1 read allowed |
| `TestD2SimulateAllowed` | 1 | D2 simulate allowed |
| `TestD3SandboxWriteGates` | 5 | D3 gate requirements |
| `TestD4RepoWriteBlocked` | 1 | D4 blocked |
| `TestD5ExternalSideEffectBlocked` | 1 | D5 blocked |
| `TestD6IrreversibleBlocked` | 1 | D6 blocked |
| `TestLiveExecutionAlwaysFalse` | 2 | live_execution_allowed=False |
| `TestRepoCreatedAlwaysFalse` | 2 | repo_created=False |
| `TestProductionSourceModifiedAlwaysFalse` | 2 | production_source_modified=False |
| `TestExternalFederationInitiatedAlwaysFalse` | 2 | external_federation_initiated=False |
| `TestVerificationCompleteAlwaysFalse` | 2 | verification_complete=False |
| `TestCABRReadyAlwaysFalse` | 2 | cabr_ready=False |
| `TestPayoutReadyAlwaysFalse` | 2 | payout_ready=False |
| `TestConvenienceFunctions` | 2 | Singleton and convenience |
| `TestWSP97TruthFieldsPreserved` | 2 | All truth fields preserved |
| `TestHXA22CompleteGuardFlow` | 2 | Integration proof |
| `TestHXA22VerdictDocumentation` | 1 | Verdict documented |

**Total**: 40 tests, all passing

---

## 6. What HXA22 Proves

| Proof Point | Evidence |
|-------------|----------|
| D0-D6 classification defined | Enum with severity ordering |
| Request model captures all gates | 10 gate/mode fields |
| Result model captures all truth fields | 7 WSP 97 fields |
| Guard evaluator is fail-closed | All blocking conditions tested |
| D0/D1/D2 allowed only in dry-run | 3 test cases pass |
| D3 requires all gates | 4 blocking conditions tested |
| D4/D5/D6 blocked in Phase 1 | 3 test cases pass |
| All WSP 97 fields remain False | All assertions pass |

---

## 7. What HXA22 Does NOT Prove

| Gap | Reason |
|-----|--------|
| Live execution capability | Phase 1 blocks all live execution |
| Real capability token validation | Uses fake tokens (HXA21) |
| Real human approval flow | Requires approval UI/API |
| Two-party approval for D6 | Phase 2+ feature |
| Delayed delete queue | Phase 2+ feature |
| Hermes runtime integration | No-op validation only |

---

## 8. Guard API Summary

### 8.1 Request Model

```python
@dataclass
class DestructiveActionRequest:
    action_id: str
    action_type: str
    target_path: str
    requested_class: DestructiveActionClass
    dry_run_mode: bool = True
    human_approval: bool = False
    capability_token_present: bool = False
    security_gate_passed: bool = False
    workspace_binding_enforced: bool = False
    path_constraints_validated: bool = False
```

### 8.2 Result Model

```python
@dataclass
class DestructiveActionGuardResult:
    allowed: bool
    decision: GuardDecision
    reason_code: GuardBlockReasonCode
    destructive_class: DestructiveActionClass
    dry_run_only: bool = True
    # WSP 97 Truth Fields (ALWAYS False)
    live_execution_allowed: bool = False
    repo_created: bool = False
    production_source_modified: bool = False
    external_federation_initiated: bool = False
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False
```

### 8.3 Usage

```python
from modules.infrastructure.wre_core.src.destructive_action_guard import (
    DestructiveActionClass,
    DestructiveActionRequest,
    evaluate_destructive_action,
)

request = DestructiveActionRequest(
    action_id="act_001",
    action_type="sandbox_write",
    target_path="/tmp/test/file.txt",
    requested_class=DestructiveActionClass.D3_WRITE_SANDBOX,
    dry_run_mode=True,
    workspace_binding_enforced=True,
    path_constraints_validated=True,
    capability_token_present=True,
    security_gate_passed=True,
)

result = evaluate_destructive_action(request)
assert result.allowed is True
assert result.live_execution_allowed is False
```

---

## 9. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA23_HERMES_GUARD_INTEGRATION_PHASE1` | Integrate guard into Hermes executor | **P0** |
| 2 | `HXA24_HUMAN_APPROVAL_QUEUE_PHASE1` | Approval queue for D4+ | P1 |
| 3 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |

---

## 10. Files Changed

| File | Type | Lines |
|------|------|-------|
| `wre_core/src/destructive_action_guard.py` | NEW | 450+ |
| `wre_core/tests/test_hxa22_destructive_action_guard_runtime.py` | NEW | 700+ |
| `wre_core/ModLog.md` | UPDATED | +65 |
| `wre_core/tests/TestModLog.md` | UPDATED | +55 |
| `docs/audits/openclaw_hermes/HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md` | NEW | This file |

---

## 11. Production Code Changes

**YES - Minimal production code added.**

New file: `modules/infrastructure/wre_core/src/destructive_action_guard.py`

This is the first HXA slice to add production code (as specified in the slice requirements).
The code is:
- Pure validation (no side effects)
- Fail-closed by design
- Uses no external dependencies
- Uses no real credentials
- Does not integrate into live Hermes execution yet

---

## 12. WSP 97 Closing Statement

This implementation provides a runtime destructive action guard seam for WRE/Hermes flow.

**What is confirmed**:
- DestructiveActionClass enum with D0-D6 classification
- DestructiveActionRequest with all gate requirements
- DestructiveActionGuardResult with all WSP 97 truth fields
- DestructiveActionGuard with fail-closed evaluation
- D0/D1/D2 allowed only in dry-run mode
- D3 requires all four gates to pass
- D4/D5/D6 blocked in Phase 1
- All WSP 97 safety fields remain False

**What is NOT confirmed**:
- Live execution capability
- Real capability token validation
- Real human approval flow
- Hermes runtime integration (future slice)
- Delayed delete queue (future slice)
- Two-party approval for D6 (future slice)

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1.
