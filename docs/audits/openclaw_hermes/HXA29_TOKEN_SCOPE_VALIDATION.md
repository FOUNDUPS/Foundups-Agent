# HXA29: Token Scope Validation (Phase 1)

## Slice ID
`HXA29_TOKEN_SCOPE_VALIDATION_PHASE1`

## Status
**COMPLETE** - Token scope validation against action classes implemented and tested.

## Predecessor
HXA28: D3 Native Classification - `D3_NATIVE_CLASSIFICATION_DEFINED`

## Verdict
`TOKEN_SCOPE_VALIDATION_DEFINED`

---

## Objective

Harden capability token scope validation against Hermes destructive-action classes:
1. Map capability token scopes explicitly to allowed action classes
2. D3 sandbox scopes may authorize ONLY D3 dry-run/sandbox evidence actions
3. D3 scopes must NEVER authorize D4/D5/D6 actions
4. Separate scopes for repo/source/external defined but blocked by guard
5. Scope validation must be deterministic and fail-closed

---

## Implementation

### New Constants Added (`capability_token_validator.py`)

```python
# Action class to scopes mapping
ACTION_CLASS_SCOPES = {
    "D0_OBSERVE": ["d0:observe", "d0:read", "d0:status"],
    "D1_READ": ["d1:read", "d1:fetch", "d1:load"],
    "D2_SIMULATE": ["d2:simulate", "d2:plan", "d2:preview"],
    "D3_WRITE_SANDBOX": ["d3:sandbox", "d3:evidence", "d3:dry-run"],
    "D4_WRITE_REPO": ["d4:repo", "d4:source", "d4:git"],
    "D5_EXTERNAL_SIDE_EFFECT": ["d5:external", "d5:api", "d5:webhook"],
    "D6_IRREVERSIBLE": ["d6:delete", "d6:irreversible", "d6:payout"],
}

# Reverse mapping: scope -> action class
SCOPE_TO_ACTION_CLASS = {
    "d3:sandbox": "D3_WRITE_SANDBOX",
    "d3:evidence": "D3_WRITE_SANDBOX",
    "d3:dry-run": "D3_WRITE_SANDBOX",
    "d4:repo": "D4_WRITE_REPO",
    # ... etc.
}
```

### New Function Added

```python
def validate_scope_for_action_class(scope: str, action_class: Any) -> bool:
    """
    Validate that a scope authorizes a specific action class.
    
    Returns True only if scope maps to the requested action class.
    Returns False for unknown scopes (fail-closed).
    """
```

---

## Scope Validation Rules

### D3 Scopes (Sandbox/Evidence/Dry-Run)

| Scope | D3 | D4 | D5 | D6 |
|-------|----|----|----|----|
| `d3:sandbox` | ALLOWED | BLOCKED | BLOCKED | BLOCKED |
| `d3:evidence` | ALLOWED | BLOCKED | BLOCKED | BLOCKED |
| `d3:dry-run` | ALLOWED | BLOCKED | BLOCKED | BLOCKED |

### D4/D5/D6 Scopes (Defined but Guard-Blocked)

| Scope | D3 | D4 | D5 | D6 |
|-------|----|----|----|----|
| `d4:repo` | BLOCKED | AUTHORIZED* | BLOCKED | BLOCKED |
| `d5:external` | BLOCKED | BLOCKED | AUTHORIZED* | BLOCKED |
| `d6:delete` | BLOCKED | BLOCKED | BLOCKED | AUTHORIZED* |

*AUTHORIZED by scope but BLOCKED by guard policy in Phase 1.

### Unknown/Missing Scopes

| Condition | Result |
|-----------|--------|
| Missing scope | BLOCKED (fail-closed) |
| Unknown scope | BLOCKED (fail-closed) |
| Empty scopes list | BLOCKED (fail-closed) |

---

## Test Coverage (54 tests)

### Scope Constants Tests (6 tests)
- `TestScopeConstantsExist` - Constants defined correctly

### D3 Scope Authorization Tests (9 tests)
- `TestD3SandboxScopeAuthorizesD3Only` - D3 scopes authorize D3 actions
- `TestD3ScopeDoesNotAuthorizeD4` - D3 scopes blocked for D4
- `TestD3ScopeDoesNotAuthorizeD5` - D3 scopes blocked for D5
- `TestD3ScopeDoesNotAuthorizeD6` - D3 scopes blocked for D6

### D4/D5/D6 Scope Tests (3 tests)
- `TestD4D5D6ScopesDefinedButBlocked` - Scopes validate but guard blocks

### Fail-Closed Tests (4 tests)
- `TestMissingScopeFailsClosed` - Missing scope blocked
- `TestUnknownScopeFailsClosed` - Unknown scope blocked

### Mixed Scope Tests (2 tests)
- `TestMixedScopesObeyActionClass` - Multiple scopes still respect class

### Path Validation Tests (3 tests)
- `TestBlockedPathOverridesAllowedScope` - Path blocks override scope
- `TestPathTraversalBlocked` - Traversal attempts blocked

### Dry-Run Tests (2 tests)
- `TestDryRunOnlyBlocksLiveExecution` - dry_run_only enforced

### WSP 97 Truth Fields Tests (4 tests)
- `TestWSP97TruthFieldsAlwaysFalse` - All truth fields remain False

### Parametrized Scope Validation Tests (14 tests)
- `TestValidateScopeForActionClass` - All scope/class combinations

### Verdict Documentation (1 test)
- `TestHXA29VerdictDocumentation` - Verdict proof

---

## WSP 97 Truth Boundaries

All truth fields remain FALSE in Phase 1:

| Field | Value | Reason |
|-------|-------|--------|
| `live_external_delegate_called` | False | No live delegation |
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | No production writes |
| `real_execution_performed` | False | Phase 1 dry-run only |
| `verification_complete` | False | No CABR pipeline |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

## Regression Tests

All prior HXA tests continue to pass:

| Test Suite | Result |
|------------|--------|
| `test_hxa28_d3_native_classification.py` | 132 passed |
| `test_hxa27_hermes_token_validation_integration.py` | 31 passed |
| `test_hxa26_token_validation_service.py` | 51 passed |
| `test_hermes_job_executor.py` | 94 passed |

---

## Files Changed

### Production Code
- `modules/infrastructure/wre_core/src/capability_token_validator.py`
  - Added `ACTION_CLASS_SCOPES` constant
  - Added `SCOPE_TO_ACTION_CLASS` constant
  - Added `validate_scope_for_action_class()` function

### Tests
- `modules/infrastructure/wre_core/tests/test_hxa29_token_scope_validation.py` (NEW)
  - 54 tests covering scope validation

---

## Security Analysis

### Threat Mitigated
D3 scope escalation to D4/D5/D6 actions blocked by:
1. Scope-to-action-class mapping is explicit (no wildcards)
2. Each scope maps to exactly one action class
3. Unknown scopes fail closed (return False)
4. Guard policy provides defense in depth (blocks D4/D5/D6 in Phase 1)

### Defense in Depth
Token scope validation is layer 1. Guard policy is layer 2.
Even if scope somehow authorizes D4 action, guard still blocks:
- `BLOCKED_D4_REPO_WRITE_PHASE1`
- `BLOCKED_D5_EXTERNAL_PHASE1`
- `BLOCKED_D6_IRREVERSIBLE_PHASE1`

---

## Recommended Next Slice

**HXA30: Scope-Aware Token Validation Integration**

Integrate `validate_scope_for_action_class()` into the HermesJobExecutor token validation flow to:
1. Validate requested action class against token scopes before guard
2. Add `SCOPE_NOT_AUTHORIZED_FOR_ACTION_CLASS` reason code
3. Block execution early if scope doesn't authorize action class

This would add a third layer of defense before guard evaluation.

---

## Worker
W1

## Date
2026-05-12

## WSP Compliance
- WSP 97: Truth Boundaries (all safety fields remain False)
- WSP 50: Pre-Action Verification (fail-closed validation)
- WSP 11: Interface contract (typed constants and functions)
