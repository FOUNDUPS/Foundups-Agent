# SACRDA - HXA Hermes Execution Safety Audit

**Slice**: `SACRDA_HXA_HERMES_EXECUTION_SAFETY_AUDIT_PHASE1`
**Worker**: W3
**Date**: 2026-05-14
**Mode**: Safety audit of HXA17-HXA30 Hermes execution infrastructure
**Base**: main (post PR #588 merge)
**WSP Lock**: WSP 00 -> WSP 97 -> WSP 15

---

## 1. Executive Summary

**VERDICT: SAFE - All critical safety constraints enforced**

The HXA17-HXA30 Hermes execution infrastructure implements defense-in-depth safety controls that prevent unauthorized live execution, repo creation, and production source modification. All WSP 97 truth fields remain `False` across the entire execution flow.

---

## 2. Specific Question Answers

### Q1: Does token validation run before guard?

**YES - CONFIRMED**

Evidence from `hermes_job_executor.py` execution flow (HXA27, HXA30):
```
Step 2.2: Classify action → D0-D6 class
Step 2.3: Token validation (if present) → BLOCKED_BY_TOKEN_VALIDATION if invalid
Step 2.5: Guard evaluation → BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD if D4+
```

Token validation at Step 2.3 runs BEFORE guard evaluation at Step 2.5. If token validation fails, the guard is NEVER evaluated (short-circuit).

### Q2: Is D3 dry-run only?

**YES - CONFIRMED**

Evidence from `destructive_action_guard.py` lines 517-524:
```python
# All D3 gates passed - allow as dry-run/sandbox only
return self._allow_dry_run_result(
    action_class=action_class,
    reason_code=GuardBlockReasonCode.OK_SANDBOX,
    reason_human="D3_WRITE_SANDBOX allowed (dry-run/sandbox only)",
    ...
)
```

D3_WRITE_SANDBOX actions:
- Require ALL gates: workspace_binding, path_constraints, capability_token, security_gate
- Return `ALLOW_DRY_RUN` decision (not `ALLOW_LIVE`)
- Set `dry_run_only=True` in result
- `live_execution_allowed=False` (ALWAYS)

### Q3: Are D4/D5/D6 blocked?

**YES - CONFIRMED**

Evidence from `destructive_action_guard.py` lines 527-563:
```python
# Gate 4: D4 - Repo write BLOCKED in Phase 1
if action_class == DestructiveActionClass.D4_WRITE_REPO:
    return self._blocked_result(
        reason_code=GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1,
        ...
    )

# Gate 5: D5 - External side effect BLOCKED in Phase 1
if action_class == DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT:
    return self._blocked_result(
        reason_code=GuardBlockReasonCode.BLOCKED_D5_EXTERNAL_PHASE1,
        ...
    )

# Gate 6: D6 - Irreversible BLOCKED in Phase 1
if action_class == DestructiveActionClass.D6_IRREVERSIBLE:
    return self._blocked_result(
        reason_code=GuardBlockReasonCode.BLOCKED_D6_IRREVERSIBLE_PHASE1,
        ...
    )
```

All D4/D5/D6 actions unconditionally return `BLOCKED` decision with explicit reason codes.

### Q4: Is live delegation still disabled by default?

**YES - CONFIRMED**

Evidence from `hermes_job_executor.py` lines 88-94:
```python
_HERMES_DELEGATE_ENABLED_KEY = "HERMES_DELEGATE_ENABLED"

def is_hermes_delegation_enabled() -> bool:
    """Check if Hermes delegation is enabled via environment flag."""
    value = os.environ.get(_HERMES_DELEGATE_ENABLED_KEY, "0")
    return value.strip().lower() in ("1", "true", "yes")
```

Default: `HERMES_DELEGATE_ENABLED=0` (disabled). Even if enabled, real delegation returns `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`.

### Q5: Can repo creation occur?

**NO - CONFIRMED**

Evidence from multiple layers:

1. **HermesDelegationResult** (line 455): `repo_created: bool = False`
2. **DestructiveActionGuardResult** (line 285): `repo_created: bool = False`
3. **TokenValidationResult** has no repo creation capability
4. All tests assert `repo_created=False`

The field is never set to `True` anywhere in the codebase.

### Q6: Can production source modification occur?

**NO - CONFIRMED**

Evidence from multiple layers:

1. **HermesDelegationResult** (line 456): `production_source_modified: bool = False`
2. **DestructiveActionGuardResult** (line 288): `production_source_modified: bool = False`
3. D4_WRITE_REPO (which covers production source) is blocked by guard
4. All tests assert `production_source_modified=False`

The field is never set to `True` anywhere in the codebase.

### Q7: Are runtime objects complete or still fixture/test-only?

**HYBRID - Production code exists but operates in dry-run mode**

| Component | Status | Evidence |
|-----------|--------|----------|
| `DestructiveActionGuard` | **Production code** | `destructive_action_guard.py` (670 lines) |
| `DestructiveActionClass` enum | **Production code** | D0-D6 enum values |
| `CapabilityToken` model | **Production code** | `capability_token_validator.py` (824 lines) |
| `LocalCapabilityTokenValidator` | **Production code** | Validates token structure |
| `HermesJobExecutor` | **Production code** | Integration of all HXA components |
| Signature verification | **Test-only (fake)** | `signature_verified=True` is fake in Phase 1 |
| JWT/OAuth tokens | **Not implemented** | Phase 1 uses local test tokens |
| External token service | **Not implemented** | No external calls |
| Real delegate_task call | **Not implemented** | Returns `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` |

### Q8: Any unsafe assumptions?

**NO CRITICAL UNSAFE ASSUMPTIONS FOUND**

However, documented limitations exist:

| Limitation | Risk Level | Mitigation |
|------------|------------|------------|
| Fake signature verification | LOW | All execution blocked anyway |
| In-memory nonce registry | LOW | Only matters for live ops (blocked) |
| No real human approval | LOW | D4+ blocked by guard before approval needed |
| No external token service | LOW | Local validation sufficient for dry-run |

---

## 3. Safety Matrix

### 3.1 WSP 97 Truth Fields (All False)

| Field | Guard | Token | Executor | Status |
|-------|-------|-------|----------|--------|
| `live_execution_allowed` | False | N/A | N/A | **SAFE** |
| `repo_created` | False | N/A | False | **SAFE** |
| `production_source_modified` | False | N/A | False | **SAFE** |
| `external_federation_initiated` | False | N/A | False | **SAFE** |
| `verification_complete` | False | False | False | **SAFE** |
| `cabr_ready` | False | False | False | **SAFE** |
| `payout_ready` | False | False | False | **SAFE** |
| `real_execution_performed` | N/A | N/A | False | **SAFE** |
| `live_external_delegate_called` | N/A | N/A | False | **SAFE** |

### 3.2 Destructive Action Classification

| Class | Allowed | Gates Required | Status |
|-------|---------|----------------|--------|
| D0_OBSERVE | Dry-run only | `dry_run_mode=True` | **SAFE** |
| D1_READ | Dry-run only | `dry_run_mode=True` | **SAFE** |
| D2_SIMULATE | Dry-run only | `dry_run_mode=True` | **SAFE** |
| D3_WRITE_SANDBOX | Dry-run only | All 4 gates | **SAFE** |
| D4_WRITE_REPO | **BLOCKED** | N/A | **SAFE** |
| D5_EXTERNAL_SIDE_EFFECT | **BLOCKED** | N/A | **SAFE** |
| D6_IRREVERSIBLE | **BLOCKED** | N/A | **SAFE** |

### 3.3 Token Validation (HXA26-HXA30)

| Gate | Fail-Closed | Evidence |
|------|-------------|----------|
| Missing token | INVALID | `MISSING_TOKEN` code |
| Missing signature | INVALID | `MISSING_SIGNATURE` code |
| Signature not verified | INVALID | `SIGNATURE_NOT_VERIFIED` code |
| Expired token | INVALID | `TOKEN_EXPIRED` code |
| Wrong audience | INVALID | `WRONG_AUDIENCE` code |
| Replayed nonce | INVALID | `REPLAY_DETECTED` code |
| Action not allowed | INVALID | `ACTION_NOT_ALLOWED` code |
| Scope not allowed | INVALID | `SCOPE_NOT_ALLOWED` code |
| Path outside allowed | INVALID | `PATH_OUTSIDE_ALLOWED_ROOTS` code |
| Blocked path | INVALID | `PATH_IN_BLOCKED_LIST` code |
| dry_run_only vs live | INVALID | `DRY_RUN_ONLY_BLOCKS_LIVE` code |
| Scope/class mismatch | INVALID | `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` code |

### 3.4 Defense-in-Depth Layers

```
Layer 1: Feature Flag ─────────────► HERMES_DELEGATE_ENABLED=0 (default disabled)
    │
    ▼
Layer 2: Token Validation ─────────► Invalid token → BLOCKED_BY_TOKEN_VALIDATION
    │
    ▼
Layer 3: Scope-Action Validation ──► Scope mismatch → BLOCKED_BY_TOKEN_VALIDATION
    │
    ▼
Layer 4: Guard Evaluation ─────────► D4/D5/D6 → BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
    │
    ▼
Layer 5: Real Delegation Block ────► BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED
```

---

## 4. HXA Audit Coverage

| Slice | Purpose | Safety Status |
|-------|---------|---------------|
| HXA17 | Real delegate runtime reaudit | **AUDITED** |
| HXA18 | Runtime fixture safe harness | **AUDITED** |
| HXA19 | Repo creation approval gate | **SAFE** - gate never passed |
| HXA20 | Production source gate | **SAFE** - gate never passed |
| HXA21 | Capability token infrastructure | **SAFE** - test tokens only |
| HXA22 | Destructive action guard runtime | **SAFE** - fail-closed |
| HXA23 | Hermes guard integration | **SAFE** - D4+ blocked |
| HXA24 | Capability token PolicyFlags | **SAFE** - dry_run_only default |
| HXA25 | D3 sandbox execution | **SAFE** - dry-run only |
| HXA26 | Token validation service | **SAFE** - 12 fail-closed gates |
| HXA27 | Hermes token validation integration | **SAFE** - blocks before guard |
| HXA28 | D3 native classification | **SAFE** - conservative default |
| HXA29 | Token scope validation | **SAFE** - scope-class mapping |
| HXA30 | Scope-to-action-class integration | **SAFE** - defense-in-depth |

---

## 5. Test Coverage Summary

| Test File | Tests | Purpose |
|-----------|-------|---------|
| test_hxa22_destructive_action_guard_runtime.py | 40 | Guard contract |
| test_hxa23_hermes_guard_integration.py | 34 | Guard in executor |
| test_hxa27_hermes_token_validation_integration.py | 30 | Token in executor |
| test_hxa29_token_scope_validation.py | 20+ | Scope validation |
| test_hxa30_scope_to_action_class_integration.py | 24 | Defense-in-depth |

**Total: 148+ tests covering safety boundaries**

---

## 6. Conclusion

### 6.1 Safety Confirmation

The HXA17-HXA30 Hermes execution infrastructure is **SAFE** for the following reasons:

1. **Token validation runs before guard** - Invalid tokens block execution before guard evaluation
2. **D3 is dry-run only** - All gates required, `live_execution_allowed=False` always
3. **D4/D5/D6 unconditionally blocked** - No path to enable in Phase 1
4. **Live delegation disabled by default** - `HERMES_DELEGATE_ENABLED=0`
5. **repo_created=False always** - Field never set to True
6. **production_source_modified=False always** - Field never set to True
7. **Runtime objects are production code** - But operate in dry-run mode only
8. **No unsafe assumptions** - All fail-closed, defense-in-depth

### 6.2 Remaining Gaps (Known, Documented)

| Gap | Status | Risk |
|-----|--------|------|
| Real JWT/OAuth tokens | Not implemented | None (blocked anyway) |
| External token service | Not implemented | None (local sufficient) |
| Real human approval | Not implemented | None (D4+ blocked) |
| Production delegate calls | Not implemented | None (blocked by design) |

### 6.3 Phase 2 Prerequisites

Before enabling any live execution:
1. Real signature verification (JWT/OAuth)
2. External token service integration
3. Human approval queue for D4+
4. Two-party approval for D6
5. CABR pipeline integration
6. Delayed delete queue for D6

---

*Audit performed by Worker W3 under WSP 97 truth boundaries.*

**SACRDA_HXA_HERMES_EXECUTION_SAFETY_AUDIT_PHASE1 COMPLETE**
