# HXA30: Scope-to-Action-Class Hermes Integration

**Slice**: HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_PHASE1
**Worker**: W1
**Base**: 18cbcad00d8503a472ff5e7d7633b6b2268200e8

## Objective

Integrate HXA29 scope-to-action-class validation into HermesJobExecutor token validation requests, creating defense-in-depth security layer.

## Implementation

### Token Validation Flow (Updated)

```
Job arrives → Classify action (HXA28/HXA30) → Validate token with action class → Guard evaluation
                    ↓                               ↓
              D0-D6 class                     Scope authorizes class?
                                                    ↓
                                              NO → BLOCKED_BY_TOKEN_VALIDATION
                                              YES → Continue to guard
```

### Key Changes

1. **HermesJobExecutor.execute()** (Step 2.2):
   - Classifies action into D0-D6 BEFORE token validation
   - Passes action_class to `_validate_token_if_present()`

2. **HermesJobExecutor._validate_token_if_present()**:
   - New parameter: `action_class: Optional[DestructiveActionClass]`
   - Passes action_class to token validator

3. **LocalCapabilityTokenValidator.validate_token()** (Gate 13):
   - New parameter: `action_class: Optional[Any]`
   - Calls `validate_scope_for_action_class()` if action_class provided
   - Returns `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` if mismatch

4. **TokenValidationResult** (HXA30 fields):
   - `scope_action_class_mismatch: bool`
   - `requested_action_class: Optional[str]`

### Decision Ordering

| Step | Component | Decision | Block Outcome |
|------|-----------|----------|---------------|
| 2.2 | Executor | Classify action | N/A (classification only) |
| 2.3 | Token Validator | Scope authorizes class? | BLOCKED_BY_TOKEN_VALIDATION |
| 2.5 | Guard | Policy allows action? | BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD |

### D3/D4/D5/D6 Behavior

| Token Scope | Action Class | Token Validation | Guard | Outcome |
|-------------|--------------|------------------|-------|---------|
| d3:sandbox | D3_WRITE_SANDBOX | PASS | Evaluated | SIMULATED (dry-run) |
| d3:sandbox | D4_WRITE_REPO | FAIL | NOT Evaluated | BLOCKED_BY_TOKEN_VALIDATION |
| d3:sandbox | D5_EXTERNAL | FAIL | NOT Evaluated | BLOCKED_BY_TOKEN_VALIDATION |
| d3:sandbox | D6_IRREVERSIBLE | FAIL | NOT Evaluated | BLOCKED_BY_TOKEN_VALIDATION |
| d4:repo | D4_WRITE_REPO | PASS | Evaluated | Blocked by guard (D4) |
| d5:external | D5_EXTERNAL | PASS | Evaluated | Blocked by guard (D5) |
| d6:delete | D6_IRREVERSIBLE | PASS | Evaluated | Blocked by guard (D6) |

### Defense-in-Depth

1. **Layer 1 (Token Scope)**: Token must have scope authorizing action class
2. **Layer 2 (Guard Policy)**: Guard independently blocks D4/D5/D6

Even if a token has `d4:repo` scope, the guard still blocks D4_WRITE_REPO actions.

## Test Coverage

**test_hxa30_scope_to_action_class_integration.py**: 24 tests

- D3 token + D3 action → token passes, guard allows dry-run
- D3 token + D4 action → BLOCKED_BY_TOKEN_VALIDATION before guard
- D3 token + D5 action → BLOCKED_BY_TOKEN_VALIDATION before guard
- D3 token + D6 action → BLOCKED_BY_TOKEN_VALIDATION before guard
- d4:repo scope + D4 action → token passes, guard blocks
- d5:external scope + D5 action → token passes, guard blocks
- d6:delete scope + D6 action → token passes, guard blocks
- Invalid token still blocks before guard
- No token follows existing guard behavior
- Valid token does not enable live delegate call

## WSP 97 Truth Fields

All unchanged and False:
- `real_execution_performed: False`
- `verification_complete: False`
- `cabr_ready: False`
- `payout_ready: False`
- `repo_created: False`
- `production_source_modified: False`
- `live_delegate_called: False`

## Regression Compatibility

Updated HXA27 tests with proper scopes:
- `valid_token` fixture: `scopes=["d3:sandbox"]`
- `test_same_token_blocked_on_replay`: `scopes=["d3:sandbox"]`
- `test_d4_blocked_even_with_valid_token`: `scopes=["d4:repo"]`

## Files Changed

| File | Changes |
|------|---------|
| hermes_job_executor.py | Step 2.2 classification, action_class param |
| capability_token_validator.py | Gate 13, action_class param, new result fields |
| test_hxa30_scope_to_action_class_integration.py | 24 new tests |
| test_hxa29_token_scope_validation.py | Updated expectations for HXA30 behavior |
| test_hxa27_hermes_token_validation_integration.py | Added proper scopes |

## Verdict

**SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED**

Token scope validation now integrated into Hermes execution flow as defense-in-depth layer before guard evaluation.
