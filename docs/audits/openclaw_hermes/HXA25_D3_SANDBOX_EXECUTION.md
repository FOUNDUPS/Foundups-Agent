# HXA25 - D3 Sandbox Execution (Phase 1)

**Slice**: `HXA25_D3_SANDBOX_EXECUTION_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - D3 sandbox dry-run execution with evidence
**Branch**: `feat/hxa25-d3-sandbox-execution`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **D3_SANDBOX_EXECUTION_DEFINED**

D3 sandbox dry-run execution with evidence has been proven functional without:
- Production source modification
- Repo creation
- Live external delegate calls
- Network calls
- Real credentials
- External federation
- D4/D5/D6 action enablement
- Changing HERMES_DELEGATE_ENABLED default

**HXA22 defined the destructive action guard runtime.**
**HXA23 integrated the guard into HermesJobExecutor.**
**HXA24 added capability token policy flags to enable D3 gate control.**
**HXA25 proves D3 sandbox dry-run execution works when all gates pass.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| D3 sandbox blocked by default | **PROVEN** | Test case passes |
| D3 sandbox blocked without capability token | **PROVEN** | Test case passes |
| D3 sandbox blocked if token not validated | **PROVEN** | Test case passes |
| D3 sandbox blocked if scope not authorized | **PROVEN** | Test case passes |
| D3 sandbox blocked without workspace binding | **PROVEN** | Test case passes |
| D3 sandbox blocked without path constraints | **PROVEN** | Test case passes |
| D3 sandbox allowed as dry-run when all gates true | **PROVEN** | Test case passes |
| Allowed D3 writes evidence only | **PROVEN** | Evidence files exist |
| Allowed D3 does not call live delegate | **PROVEN** | live_external_delegate_called=False |
| Allowed D3 does not create repo | **PROVEN** | repo_created=False |
| Allowed D3 does not modify production source | **PROVEN** | production_source_modified=False |
| Allowed D3 real_execution_performed=False | **PROVEN** | Test case passes |
| D4/D5/D6 blocked even with all gates | **PROVEN** | Test cases pass |
| Blocked result keeps truth fields false | **PROVEN** | Test cases pass |
| live_execution_allowed | **False** | All tests assert False |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| real_execution_performed | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. D3 Sandbox Execution Conditions

### 3.1 Required Gates (ALL must be True)

For D3 sandbox execution to be allowed:

```python
# Capability token flags (ALL four required)
policy_flags.capability_token_checked = True
policy_flags.capability_token_present = True
policy_flags.capability_token_validated = True
policy_flags.capability_token_scope_authorized = True

# Security gate
policy_flags.security_gate_passed = True

# Workspace constraints (automatic from job context)
workspace_binding_enforced = True  # From delegation request
path_constraints_validated = True  # From allowed_paths

# Execution mode
dry_run_mode = True  # ALWAYS in Phase 1
```

### 3.2 Guard Evaluation Flow

```
Job Created
    |
    v
_classify_destructive_action() -> D3_WRITE_SANDBOX
    |
    v
_build_destructive_action_request() -> DestructiveActionRequest
    |
    v
evaluate_destructive_action() -> DestructiveActionGuardResult
    |
    +-- All gates True? --> ALLOW_DRY_RUN --> Evidence written --> SIMULATED
    |
    +-- Any gate False? --> BLOCKED --> No evidence --> BLOCKED_BY_GUARD
```

---

## 4. Evidence Behavior

### 4.1 Evidence Directory

When D3 is allowed:
- Evidence directory: `.hermes_evidence/{job_id}/`
- Metadata file: `metadata.json` (job identity, timestamps)
- Checkpoint file: `checkpoint.json` (state, blockers)
- For build/extract: `poc_artifact_bundle.json` + scaffold files

### 4.2 Evidence Contents

```json
// metadata.json
{
  "job_id": "j_build_foundup_...",
  "foundup_id": "test_foundup",
  "dry_run": true,
  "execution_status": "SIMULATED"
}

// checkpoint.json
{
  "state": "SIMULATED",
  "files_changed": [],
  "exit_reason": "dry_run=True, job simulated"
}
```

---

## 5. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestD3SandboxBlockedByDefault` | 1 | Default flags block D3 |
| `TestD3SandboxBlockedWithoutCapabilityTokenFlags` | 1 | Missing token flags block |
| `TestD3SandboxBlockedIfNotValidated` | 1 | Unvalidated token blocks |
| `TestD3SandboxBlockedIfScopeNotAuthorized` | 1 | Unauthorized scope blocks |
| `TestD3SandboxBlockedWithoutWorkspaceBinding` | 1 | Missing workspace blocks |
| `TestD3SandboxBlockedWithoutPathConstraints` | 1 | Missing path constraints blocks |
| `TestD3SandboxAllowedAsDryRunWhenAllGatesTrue` | 2 | All gates allow D3 |
| `TestAllowedD3WritesEvidenceOnly` | 2 | Evidence written on allow |
| `TestAllowedD3DoesNotCallLiveDelegate` | 2 | No live delegate |
| `TestAllowedD3DoesNotCreateRepo` | 1 | No repo created |
| `TestAllowedD3DoesNotModifyProductionSource` | 1 | No production modification |
| `TestAllowedD3DoesNotSetRealExecutionPerformed` | 1 | No real execution |
| `TestD4D5D6BlockedEvenWithAllGatesTrue` | 3 | D4/D5/D6 remain blocked |
| `TestBlockedResultKeepsTruthFieldsFalse` | 2 | Blocked keeps truth false |
| `TestGuardResultContainsCorrectFields` | 1 | Guard result structure |
| `TestD3ClassificationWithCapabilityTokens` | 2 | D3 classification works |
| `TestHXA25VerdictDocumentation` | 1 | Verdict documented |

**Total**: 24 tests, all passing

---

## 6. What HXA25 Proves

| Proof Point | Evidence |
|-------------|----------|
| D3 blocked by default | Test passes |
| D3 blocked without capability token | Test passes |
| D3 blocked if token not validated | Test passes |
| D3 blocked if scope not authorized | Test passes |
| D3 blocked without workspace binding | Test passes |
| D3 blocked without path constraints | Test passes |
| D3 allowed when all gates true | Test passes |
| Allowed D3 writes evidence | Evidence files exist |
| Allowed D3 does not call live delegate | Assertion verified |
| Allowed D3 does not create repo | Assertion verified |
| Allowed D3 does not modify production | Assertion verified |
| Allowed D3 real_execution_performed=False | Assertion verified |
| D4/D5/D6 still blocked | Tests pass |
| Blocked keeps truth fields false | Tests pass |

---

## 7. What HXA25 Does NOT Prove

| Gap | Reason |
|-----|--------|
| Live D3 execution | Phase 1 is dry-run only |
| Real production writes | Not enabled |
| Live delegate calls | Blocked by design |
| D4/D5/D6 execution | Blocked in Phase 1 |
| Real token validation | Token infrastructure not live |

---

## 8. Files Changed

| File | Type | Lines Changed |
|------|------|---------------|
| `wre_core/tests/test_hxa25_d3_sandbox_execution.py` | NEW | 600+ |
| `docs/audits/openclaw_hermes/HXA25_D3_SANDBOX_EXECUTION.md` | NEW | This file |
| `wre_core/ModLog.md` | MODIFIED | Entry added |
| `wre_core/tests/TestModLog.md` | MODIFIED | Entry added |

---

## 9. Production Code Changes

**NO - No production code modified.**

This slice proves the existing D3 sandbox execution behavior is correct when all gates pass. The guard and executor logic from HXA22-24 already supports D3 dry-run execution with evidence. HXA25 adds comprehensive test coverage to prove this.

The tests use mocking to force D3 classification, demonstrating that:
1. The guard correctly blocks D3 when gates are missing
2. The guard correctly allows D3 when all gates pass
3. Evidence is written to `.hermes_evidence/` on allow
4. All WSP 97 truth fields remain False

---

## 10. D3 Allow Conditions Summary

D3 sandbox dry-run is allowed when ALL of:

1. **capability_token_checked** = True
2. **capability_token_present** = True
3. **capability_token_validated** = True
4. **capability_token_scope_authorized** = True
5. **security_gate_passed** = True
6. **workspace_binding_enforced** = True
7. **path_constraints_validated** = True
8. **dry_run_mode** = True

When allowed:
- Status: `SIMULATED`
- Guard decision: `ALLOW_DRY_RUN`
- Guard reason: `OK_SANDBOX`
- Evidence written: Yes (`.hermes_evidence/{job_id}/`)
- Live delegate called: No
- Repo created: No
- Production modified: No
- Real execution: No

---

## 11. Blocked Behavior

When any gate fails:
- Status: `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD`
- Guard decision: `BLOCKED`
- Reason code: `MISSING_*` or `BLOCKED_D*_PHASE1`
- Evidence written: No
- All truth fields: False

---

## 12. WSP 97 Closing Statement

This implementation proves D3 sandbox dry-run execution works correctly when all gates pass, without:
- Modifying production source
- Creating repositories
- Calling live external delegates
- Making network calls
- Using real credentials
- Initiating external federation
- Enabling D4/D5/D6 actions

**What is confirmed**:
- D3 blocked by default (missing gates)
- D3 blocked without capability token
- D3 blocked without workspace binding
- D3 allowed when all gates pass
- Evidence written only on allow
- No live execution on allow
- All WSP 97 truth fields remain False

**What is NOT confirmed**:
- Live D3 production execution
- Real capability token validation
- D4/D5/D6 execution paths

---

## 13. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA26_TOKEN_VALIDATION_SERVICE_PHASE1` | Add token validation infrastructure | **P0** |
| 2 | `HXA27_D3_NATIVE_CLASSIFICATION_PHASE1` | Enable native D3 classification | P1 |
| 3 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA25_D3_SANDBOX_EXECUTION_PHASE1.
