# HXA24 - Capability Token PolicyFlags (Phase 1)

**Slice**: `HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - capability token policy flags in FoundUpJob
**Branch**: `feat/hxa24-capability-token-policyflags`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **CAPABILITY_TOKEN_POLICYFLAGS_DEFINED**

Capability token policy flags have been added to PolicyFlags in foundup_job_contract.py and wired into HermesJobExecutor guard request construction without:
- Real token issuance
- Real token validation service
- Secrets or signing keys
- Network calls
- Live delegation
- Repo creation
- Production source modification
- External federation
- Changing HERMES_DELEGATE_ENABLED default

**HXA21 defined the capability token model (test-only).**
**HXA22 defined the destructive action guard runtime.**
**HXA23 integrated the guard into HermesJobExecutor.**
**HXA24 adds capability token policy flags to enable D3 gate control.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| PolicyFlags.capability_token_checked added | **PROVEN** | Field exists, default False |
| PolicyFlags.capability_token_present added | **PROVEN** | Field exists, default False |
| PolicyFlags.capability_token_validated added | **PROVEN** | Field exists, default False |
| PolicyFlags.capability_token_scope_authorized added | **PROVEN** | Field exists, default False |
| PolicyFlags.to_dict() includes all four | **PROVEN** | Test case passes |
| PolicyFlags.from_dict() restores all four | **PROVEN** | Test case passes |
| Missing fields default to False (backward compat) | **PROVEN** | Test case passes |
| Guard reads capability token flags | **PROVEN** | _build_destructive_action_request updated |
| Default flags block D3 | **PROVEN** | Test case passes |
| Partial flags block D3 | **PROVEN** | Test cases pass |
| All four True allows D3 dry-run | **PROVEN** | Test case passes |
| D4/D5/D6 still blocked with token | **PROVEN** | Test cases pass |
| live_execution_allowed | **False** | All tests assert False |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| real_execution_performed | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. PolicyFlags Changes

### 3.1 New Fields

```python
@dataclass(slots=True)
class PolicyFlags:
    # ... existing fields ...
    
    # HXA24: Capability token policy flags
    capability_token_checked: bool = False
    """Whether a capability token check was performed."""

    capability_token_present: bool = False
    """Whether a capability token was provided in the request."""

    capability_token_validated: bool = False
    """Whether the token signature and expiry were validated."""

    capability_token_scope_authorized: bool = False
    """Whether the token scope covers the requested action."""
```

### 3.2 Serialization

`to_dict()` and `from_dict()` updated to include all four fields with backward-compatible defaults.

---

## 4. Guard Request Construction Logic

### 4.1 Conservative Interpretation

For `capability_token_present` to be True in the guard request, ALL four PolicyFlags conditions must be True:

```python
capability_token_present_for_guard = (
    policy_flags.capability_token_checked
    and policy_flags.capability_token_present
    and policy_flags.capability_token_validated
    and policy_flags.capability_token_scope_authorized
)
```

### 4.2 Rationale

This conservative interpretation ensures D3+ operations remain blocked unless:
1. A token check was performed (auditable)
2. A token was actually provided (present)
3. The token passed signature/expiry validation (valid)
4. The token scope covers the requested action (authorized)

Any missing condition results in `capability_token_present=False` for the guard.

---

## 5. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestPolicyFlagsCapabilityTokenFields` | 5 | Default values and field existence |
| `TestPolicyFlagsSerialization` | 4 | to_dict/from_dict roundtrip |
| `TestJobSerializationWithCapabilityToken` | 2 | Job-level serialization |
| `TestDefaultPolicyFlagsBlockD3` | 1 | Default flags block D3 |
| `TestPartialCapabilityTokenFlagsBlockD3` | 3 | Partial flags block D3 |
| `TestAllFourTrueAllowsD3SandboxDryRun` | 2 | All four + security gate allows D3 |
| `TestD4D5D6StillBlockedEvenWithToken` | 3 | D4/D5/D6 blocked regardless |
| `TestWSP97TruthFieldsPreserved` | 7 | Truth fields remain False |
| `TestGuardRequestConstruction` | 3 | Guard request reads flags |
| `TestHXA24VerdictDocumentation` | 1 | Verdict documented |

**Total**: 31 tests, all passing

---

## 6. What HXA24 Proves

| Proof Point | Evidence |
|-------------|----------|
| PolicyFlags has capability_token_checked | Field exists with default False |
| PolicyFlags has capability_token_present | Field exists with default False |
| PolicyFlags has capability_token_validated | Field exists with default False |
| PolicyFlags has capability_token_scope_authorized | Field exists with default False |
| Serialization includes all four fields | to_dict/from_dict tested |
| Backward compatibility preserved | Missing fields default False |
| Guard reads flags correctly | _build_destructive_action_request updated |
| Default flags block D3 | Test case passes |
| Partial flags block D3 | Test cases pass |
| All four True allows D3 dry-run | Test case passes |
| D4/D5/D6 still blocked | Test cases pass |
| WSP 97 truth fields remain False | All assertions pass |

---

## 7. What HXA24 Does NOT Prove

| Gap | Reason |
|-----|--------|
| Real token issuance | Not implemented |
| Real token validation | Not implemented |
| Signing key management | Not implemented |
| Network token verification | Not implemented |
| Production token flow | Phase 1 is dry-run only |

---

## 8. Files Changed

| File | Type | Lines Changed |
|------|------|---------------|
| `moltbot_bridge/src/foundup_job_contract.py` | MODIFIED | +30 |
| `moltbot_bridge/tests/test_foundup_job_contract.py` | MODIFIED | +50 |
| `wre_core/src/hermes_job_executor.py` | MODIFIED | +25 |
| `wre_core/tests/test_hxa24_capability_token_policyflags.py` | NEW | 500+ |
| `docs/audits/openclaw_hermes/HXA24_CAPABILITY_TOKEN_POLICYFLAGS.md` | NEW | This file |

---

## 9. Production Code Changes

**YES - Production code modified.**

Modified files:
1. `modules/communication/moltbot_bridge/src/foundup_job_contract.py`
   - Added 4 capability token fields to PolicyFlags
   - Updated to_dict() to include new fields
   - Updated from_dict() to restore new fields (backward compat)

2. `modules/infrastructure/wre_core/src/hermes_job_executor.py`
   - Updated _build_destructive_action_request() to read capability token flags
   - Conservative logic: all four must be True for capability_token_present=True

The changes are:
- Safe default values (all False)
- Backward compatible (missing fields default False)
- Conservative interpretation (any missing flag blocks D3)
- No real tokens issued or validated
- No external calls

---

## 10. WSP 97 Closing Statement

This implementation adds capability token policy flags to PolicyFlags and wires them into the guard request construction.

**What is confirmed**:
- Four capability token fields added to PolicyFlags
- All fields default to False (safe)
- Serialization includes all fields
- Backward compatibility preserved
- Guard reads flags with conservative interpretation
- D3 blocked unless all four flags True
- D4/D5/D6 blocked regardless of flags
- All WSP 97 truth fields remain False

**What is NOT confirmed**:
- Real token issuance capability
- Real token validation capability
- Signing key management
- Network token verification
- Production token flow

---

## 11. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA25_D3_SANDBOX_EXECUTION_PHASE1` | Enable D3 sandbox dry-run with evidence | **P0** |
| 2 | `HXA26_TOKEN_VALIDATION_SERVICE_PHASE1` | Add token validation infrastructure | P1 |
| 3 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1.
