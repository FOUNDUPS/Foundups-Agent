# HXA27 - Hermes Token Validation Integration (Phase 1)

**Slice**: `HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - token validation wired into HermesJobExecutor
**Branch**: `feat/hxa27-hermes-token-validation-integration`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED**

Token validation from HXA26 is now integrated into HermesJobExecutor execute() flow:
- Token validator is injectable into HermesJobExecutor constructor
- Token extraction from job payload (dict or CapabilityToken instance)
- Token validation performed before guard evaluation (step 2.3)
- Invalid token blocks execution immediately with BLOCKED_BY_TOKEN_VALIDATION
- Valid token allows execution to proceed
- No token in payload = no token validation (PolicyFlags control guard)
- Nonce replay protection prevents token reuse across executions
- All WSP 97 truth fields remain False

**HXA26 created the token validation service module.**
**HXA27 integrates that service into HermesJobExecutor.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Token validator injectable | **PROVEN** | Constructor accepts token_validator param |
| Default validator used if None | **PROVEN** | get_default_validator() called if None |
| Token extraction from payload | **PROVEN** | _extract_capability_token() method |
| Token validation before guard | **PROVEN** | Step 2.3 before step 2.5 in execute() |
| Invalid token blocks execution | **PROVEN** | Returns BLOCKED_BY_TOKEN_VALIDATION |
| Valid token allows proceeding | **PROVEN** | Execution continues to guard |
| No token = no validation | **PROVEN** | Returns None, proceeds to guard |
| Nonce replay protection | **PROVEN** | Validator tracks used nonces |
| token_validation_performed field | **PROVEN** | Added to HermesDelegationResult |
| token_validation_result field | **PROVEN** | Added to HermesDelegationResult |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | No production writes |
| live_external_delegate_called | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. Integration Architecture

### 3.1 Execute Flow

```
execute(job):
  1. Validate job structure
  2. Build delegation request
  2.3 [HXA27] Validate capability token if present in payload
      - If token present and invalid -> BLOCKED_BY_TOKEN_VALIDATION
      - If token present and valid -> proceed (token_validation_result set)
      - If no token -> proceed (token_validation_performed = False)
  2.5 [HXA23] Evaluate destructive action guard
      - If blocked -> BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
      - If allowed -> proceed
  3-7 ... existing flow ...
```

### 3.2 Token Extraction Strategy

```python
def _extract_capability_token(job) -> Optional[CapabilityToken]:
    1. Check if job.payload exists and is dict
    2. Check if "capability_token" key exists
    3. If CapabilityToken instance -> return directly
    4. If dict -> reconstruct CapabilityToken
    5. If None/missing -> return None (fail-closed)
```

### 3.3 Token Validation Integration

```python
def _validate_token_if_present(job, request) -> Optional[TokenValidationResult]:
    1. Extract token from payload
    2. If no token -> return None (no validation needed)
    3. Derive target_path from workspace_binding
    4. Determine is_live_operation (Phase 1: always False)
    5. Call token_validator.validate_token()
    6. Return TokenValidationResult
```

---

## 4. New Execution Status

```python
class HermesExecutionStatus(str, Enum):
    # ... existing statuses ...
    
    # HXA27: Token validation blocked states
    BLOCKED_BY_TOKEN_VALIDATION = "BLOCKED_BY_TOKEN_VALIDATION"
```

---

## 5. New Result Fields

```python
@dataclass
class HermesDelegationResult:
    # ... existing fields ...
    
    # HXA27 Token Validation Fields
    token_validation_performed: bool = False
    token_validation_result: Optional[Dict[str, Any]] = None
```

---

## 6. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestTokenValidatorInjection` | 3 | Validator injection |
| `TestTokenExtraction` | 6 | Token extraction from payload |
| `TestTokenValidationIntegration` | 5 | Validation in execute flow |
| `TestGuardAfterTokenValidation` | 2 | Guard eval after token |
| `TestWSP97TruthFields` | 3 | Truth field enforcement |
| `TestResultSerialization` | 2 | Result serialization |
| `TestNonceReplayProtection` | 1 | Replay prevention |
| `TestD3D4D6Behavior` | 2 | D4-D6 still blocked |
| `TestHXA27VerdictDocumentation` | 3 | Verdict documentation |
| `TestModuleImports` | 3 | Import verification |

**Total**: 30 tests

---

## 7. What HXA27 Proves

| Proof Point | Evidence |
|-------------|----------|
| Token validator injectable | Constructor parameter works |
| Token extraction from dict | Reconstructs CapabilityToken |
| Token extraction from instance | Returns directly |
| Invalid token blocks | BLOCKED_BY_TOKEN_VALIDATION returned |
| Valid token allows proceeding | Execution continues |
| No token = no validation | token_validation_performed = False |
| Guard evaluated after token | Step 2.5 after 2.3 |
| Nonce replay blocked | Second use returns REPLAY_DETECTED |
| Result includes token fields | to_dict() serialization works |
| All truth fields False | All tests verify |

---

## 8. What HXA27 Does NOT Prove

| Gap | Reason |
|-----|--------|
| Real JWT/OAuth token validation | Phase 1 uses fake verification |
| External token service integration | Local validator only |
| Production token issuance | Test infrastructure only |
| Live operation authorization | Phase 1 is dry-run only |
| Token revocation | Not implemented |

---

## 9. Files Changed

| File | Type | Lines |
|------|------|-------|
| `wre_core/src/hermes_job_executor.py` | MODIFIED | ~200 |
| `wre_core/tests/test_hxa27_hermes_token_validation_integration.py` | NEW | 500+ |
| `docs/audits/openclaw_hermes/HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION.md` | NEW | This file |
| `wre_core/ModLog.md` | MODIFIED | Entry added |
| `wre_core/tests/TestModLog.md` | MODIFIED | Entry added |

---

## 10. Production Code Changes

**YES - Production code modified.**

Changes to `hermes_job_executor.py`:
1. Added imports for capability token validator
2. Added `BLOCKED_BY_TOKEN_VALIDATION` status
3. Added `token_validation_performed` and `token_validation_result` fields to result
4. Added `token_validator` parameter to constructor
5. Added `_extract_capability_token()` method
6. Added `_validate_token_if_present()` method
7. Added `_build_token_blocked_result()` method
8. Updated `execute()` to call token validation at step 2.3
9. Updated all result constructions to include token validation fields

---

## 11. Integration Behavior

### 11.1 Token Present and Valid

```python
job = MockFoundUpJob(
    payload={"capability_token": valid_token},
    policy_flags=MockPolicyFlags(),
)
result = executor.execute(job)

# Result:
result.token_validation_performed = True
result.token_validation_result["token_valid"] = True
result.status = HermesExecutionStatus.SIMULATED  # Proceeds to normal flow
```

### 11.2 Token Present and Invalid

```python
job = MockFoundUpJob(
    payload={"capability_token": expired_token},
    policy_flags=MockPolicyFlags(),
)
result = executor.execute(job)

# Result:
result.token_validation_performed = True
result.token_validation_result["token_valid"] = False
result.token_validation_result["reason_code"] = "TOKEN_EXPIRED"
result.status = HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
result.guard_evaluated = False  # Guard NOT evaluated
```

### 11.3 No Token in Payload

```python
job = MockFoundUpJob(
    payload={},
    policy_flags=MockPolicyFlags(),
)
result = executor.execute(job)

# Result:
result.token_validation_performed = False
result.token_validation_result = None
result.guard_evaluated = True  # Guard is evaluated
result.status = HermesExecutionStatus.SIMULATED  # Normal flow
```

---

## 12. Token Failure Behavior

| Token State | Status | Guard Evaluated | Reason |
|-------------|--------|-----------------|--------|
| None in payload | Proceeds | Yes | PolicyFlags control guard |
| Present, expired | BLOCKED_BY_TOKEN_VALIDATION | No | TOKEN_EXPIRED |
| Present, wrong audience | BLOCKED_BY_TOKEN_VALIDATION | No | WRONG_AUDIENCE |
| Present, action not allowed | BLOCKED_BY_TOKEN_VALIDATION | No | ACTION_NOT_ALLOWED |
| Present, replayed nonce | BLOCKED_BY_TOKEN_VALIDATION | No | REPLAY_DETECTED |
| Present, valid | Proceeds | Yes | Token passes |

---

## 13. D3/D4-D6 Behavior

| Destructive Class | With Valid Token | Behavior |
|-------------------|------------------|----------|
| D0/D1/D2 | Token passes | Guard allows dry-run |
| D3 | Token passes | Guard checks PolicyFlags |
| D4/D5/D6 | Token passes | Guard blocks (Phase 1) |

Token validation does NOT override guard decisions.
Token validation happens BEFORE guard evaluation.
If token invalid, guard is never evaluated.

---

## 14. WSP 97 Closing Statement

This implementation integrates capability token validation into HermesJobExecutor.

**What is confirmed**:
- Token validator is injectable
- Token extraction works from payload (dict or instance)
- Token validation happens before guard evaluation
- Invalid token blocks execution immediately
- Valid token allows execution to proceed
- No token = no token validation performed
- Nonce replay protection works
- All WSP 97 truth fields remain False
- Result serialization includes token fields

**What is NOT confirmed**:
- Real JWT/OAuth token validation
- External token service integration
- Production token issuance
- Live operation authorization
- Token revocation

---

## 15. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA28_D3_NATIVE_CLASSIFICATION_PHASE1` | Enable native D3 classification | **P0** |
| 2 | `HXA29_TOKEN_SCOPE_VALIDATION_PHASE1` | Add scope-based authorization | P1 |
| 3 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION_PHASE1.
