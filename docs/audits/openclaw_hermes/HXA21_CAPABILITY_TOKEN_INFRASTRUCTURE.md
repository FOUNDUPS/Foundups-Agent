# HXA21 - Capability Token Infrastructure (Phase 1)

**Slice**: `HXA21_CAPABILITY_TOKEN_INFRASTRUCTURE_PHASE1`
**Worker**: 0102
**Date**: 2026-05-12
**Mode**: Implementation - test-only capability token model and validation
**Branch**: `feat/hxa21-capability-token-infrastructure`
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15 -> WSP 50

---

## 1. Final Verdict

### **CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED**

A safe local capability token model and validation infrastructure has been defined and tested without:
- Production token issuance
- Real secrets or signing keys
- Repo creation
- Production source modification
- External network calls
- Live delegation
- External federation
- Production readiness claims

**HXA19 proved the repo creation approval gate requires `capability_token_present`.**
**HXA20 proved the production source gate requires `capability_token_present`.**
**HXA21 defines what a safe capability token looks like and how it is validated.**

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| CapabilityToken model defined | **PROVEN** | Test-local dataclass with all fields |
| token_id field | **PROVEN** | String field |
| issuer field | **PROVEN** | String field |
| subject field | **PROVEN** | String field |
| audience field | **PROVEN** | String field |
| scopes field | **PROVEN** | List[str] field |
| allowed_actions field | **PROVEN** | List[str] field |
| allowed_paths field | **PROVEN** | List[str] field |
| blocked_paths field | **PROVEN** | List[str] field |
| dry_run_only field | **PROVEN** | Boolean field, default True (safe) |
| issued_at field | **PROVEN** | datetime field |
| expires_at field | **PROVEN** | Optional datetime field |
| nonce field | **PROVEN** | String field for replay protection |
| signature_present field | **PROVEN** | Boolean field |
| signature_verified field | **PROVEN** | Boolean field |
| TokenValidationResult defined | **PROVEN** | Dataclass with all validation fields |
| FakeTokenIssuer available | **PROVEN** | Test fixture class (no real secrets) |
| FakeTokenValidator available | **PROVEN** | Test fixture class (in-memory nonce registry) |
| Token redaction works | **PROVEN** | redacted_repr() and to_dict() hide sensitive data |
| repo_created | **False** | All tests assert False |
| production_source_modified | **False** | All tests assert False |
| network_called | **False** | All tests assert False |
| live_external_delegate_called | **False** | All tests assert False |
| external_federation_initiated | **False** | All tests assert False |
| verification_complete | **False** | No CABR pipeline |
| cabr_ready | **False** | No CABR pipeline |
| payout_ready | **False** | No payout pipeline |

---

## 3. Capability Token Model

### 3.1 CapabilityToken Fields

```python
@dataclass
class CapabilityToken:
    # Identity
    token_id: str
    issuer: str
    subject: str
    audience: str

    # Authorization
    scopes: List[str] = field(default_factory=list)
    allowed_actions: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)

    # Execution Mode
    dry_run_only: bool = True  # Default True = SAFE

    # Temporal Validity
    issued_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None

    # Replay Protection
    nonce: str = field(default_factory=lambda: secrets.token_hex(16))

    # Signature (Fake for Testing)
    signature_present: bool = False
    signature_verified: bool = False
```

### 3.2 TokenValidationResult Fields

```python
@dataclass
class TokenValidationResult:
    token_valid: bool = False
    reason_code: TokenValidationReasonCode = MISSING_TOKEN
    missing_fields: List[str] = field(default_factory=list)
    denied_scopes: List[str] = field(default_factory=list)
    expired: bool = False
    replay_detected: bool = False
    action_allowed: bool = False
    path_allowed: bool = False
    dry_run_only_blocked_live: bool = False

    # WSP 97 Truth (ALWAYS False)
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False
```

---

## 4. Validation Failure Modes (Fail-Closed)

| Condition | Reason Code |
|-----------|-------------|
| Missing token | `MISSING_TOKEN` |
| Missing signature | `MISSING_SIGNATURE` |
| Signature not verified | `SIGNATURE_NOT_VERIFIED` |
| Token expired | `TOKEN_EXPIRED` |
| Token not yet valid | `TOKEN_NOT_YET_VALID` |
| Wrong audience | `WRONG_AUDIENCE` |
| Wrong issuer | `WRONG_ISSUER` |
| Nonce missing | `NONCE_MISSING` |
| Replayed nonce | `REPLAY_DETECTED` |
| Action not allowed | `ACTION_NOT_ALLOWED` |
| Scope not allowed | `SCOPE_NOT_ALLOWED` |
| Path outside allowed roots | `PATH_OUTSIDE_ALLOWED_ROOTS` |
| Path in blocked list | `PATH_IN_BLOCKED_LIST` |
| Dry-run-only blocks live | `DRY_RUN_ONLY_BLOCKS_LIVE` |

---

## 5. Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestCapabilityTokenModel` | 11 | Token model fields and validation |
| `TestTokenValidationResult` | 2 | Validation result fields |
| `TestFakeTokenIssuer` | 2 | Fake issuer behavior |
| `TestFakeTokenValidator` | 15 | All validation failure modes |
| `TestTokenRedaction` | 2 | Security: token string redaction |
| `TestWSP97TruthFieldsPreserved` | 10 | Truth fields always False |
| `TestHXA21CompleteCapabilityToken` | 2 | Integration proof |
| `TestHXA21VerdictDocumentation` | 1 | Verdict documented |

**Total**: 42 tests, all passing

---

## 6. What HXA21 Proves

| Proof Point | Evidence |
|-------------|----------|
| Token model has all required fields | 14 fields defined |
| Default values are safe | dry_run_only=True, signature_present=False |
| Validation blocks missing token | Test case passes |
| Validation blocks missing signature | Test case passes |
| Validation blocks unverified signature | Test case passes |
| Validation blocks expired token | Test case passes |
| Validation blocks wrong audience | Test case passes |
| Validation blocks replayed nonce | Test case passes |
| Validation blocks disallowed action | Test case passes |
| Validation blocks disallowed scope | Test case passes |
| Validation blocks path outside allowed | Test case passes |
| Validation blocks path in blocked list | Test case passes |
| Dry-run-only blocks live operation | Test case passes |
| Token redaction hides sensitive data | Test case passes |
| All WSP 97 truth fields remain False | All assertions pass |

---

## 7. What HXA21 Does NOT Prove

| Gap | Reason |
|-----|--------|
| Real JWT/OAuth token implementation | Test infrastructure only |
| Real signing key management | No real keys used |
| Real signature verification | Fake verification only |
| Production token issuance | Not implemented |
| External token federation | Not implemented |
| Real replay prevention persistence | In-memory only |

---

## 8. Validation Gates Tested

| Gate | Test Case | Status |
|------|-----------|--------|
| Missing token | `test_missing_token_fails` | PASS |
| Missing signature | `test_missing_signature_fails` | PASS |
| Unverified signature | `test_unverified_signature_fails` | PASS |
| Expired token | `test_expired_token_fails` | PASS |
| Wrong audience | `test_wrong_audience_fails` | PASS |
| Replayed nonce | `test_replayed_nonce_fails` | PASS |
| Action not allowed | `test_action_not_allowed_fails` | PASS |
| Scope not allowed | `test_scope_not_allowed_fails` | PASS |
| Path outside roots | `test_path_outside_allowed_roots_fails` | PASS |
| Blocked path | `test_blocked_path_fails` | PASS |
| Dry-run blocks live | `test_dry_run_only_blocks_live_operation` | PASS |
| Valid dry-run | `test_valid_dry_run_token_passes` | PASS |

---

## 9. Integration with HXA19 and HXA20

This capability token infrastructure is designed to satisfy the `capability_token_present` requirement from:

| Gate | Field | HXA21 Provides |
|------|-------|----------------|
| HXA19 RepoCreationApproval | `capability_token_present` | CapabilityToken model |
| HXA20 ProductionSourceGate | `capability_token_present` | CapabilityToken model |

Future phases can extend the token model with:
- Real JWT implementation (HXA22+)
- Real signature verification (HXA22+)
- Persistent nonce registry (HXA23+)
- External token federation (HXA24+)

---

## 10. Next Slice Recommendations

| Rank | Slice | Rationale | SCORE |
|------|-------|-----------|-------|
| **1** | `HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1` | Runtime integration | **P0** |
| 2 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | External readiness | P1 |
| 3 | `HXA23_TOKEN_PERSISTENCE_PHASE1` | Nonce registry persistence | P2 |

---

## 11. Files Changed

| File | Type | Lines |
|------|------|-------|
| `wre_core/tests/test_hxa21_capability_token_infrastructure.py` | NEW | 800+ |
| `wre_core/ModLog.md` | UPDATED | +50 |
| `wre_core/tests/TestModLog.md` | UPDATED | +35 |
| `docs/audits/openclaw_hermes/HXA21_CAPABILITY_TOKEN_INFRASTRUCTURE.md` | NEW | This file |

---

## 12. Production Code Changes

**None.** All capability token infrastructure is test-only. No production code was modified.

The token model, issuer, and validator are defined within the test file and do not affect:
- `hermes_job_executor.py`
- `foundup_job_router.py`
- `foundup_job_contract.py`
- Any other production source files

---

## 13. WSP 97 Closing Statement

This implementation defines a safe local capability token model for future repo creation and production source modification paths.

**What is confirmed**:
- CapabilityToken model with all required fields
- TokenValidationResult with all validation outputs
- FakeTokenIssuer creates test tokens (no real secrets)
- FakeTokenValidator validates all gates (fail-closed)
- In-memory nonce registry prevents replay
- Token redaction protects security logging
- All WSP 97 safety fields remain False
- No production code modified

**What is NOT confirmed**:
- Real JWT/OAuth token implementation
- Real signing key management
- Real signature verification
- Production token issuance capability
- External token federation readiness
- Persistent nonce registry

---

*Audit performed by 0102 under WSP 97 truth boundaries.*

Worker 0102 complete for HXA21_CAPABILITY_TOKEN_INFRASTRUCTURE_PHASE1.
