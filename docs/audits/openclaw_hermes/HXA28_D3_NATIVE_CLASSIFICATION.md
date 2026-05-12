# HXA28: D3 Native Classification Phase 1

**Slice**: HXA28_D3_NATIVE_CLASSIFICATION_PHASE1
**Date**: 2026-05-12
**Status**: COMPLETE
**Verdict**: PASS

## Executive Summary

This audit documents the hardening of HermesJobExecutor's native destructive-action classification to be deterministic and explicit. The implementation ensures:

- D0/D1/D2 dry-run behavior preserved for observe/read/simulate actions
- D3 for sandbox-local evidence/checkpoint writes with capability token gates
- D4 for repo creation, git operations, production source modification (BLOCKED)
- D5 for external API mutations (BLOCKED)
- D6 for delete, credential mutation, payout, irreversible actions (BLOCKED)
- Unknown/ambiguous actions fail-closed to D6 (blocking class)
- Valid tokens do NOT downgrade D4/D5/D6 classification

## Classification Hierarchy

| Class | Category | Behavior | Examples |
|-------|----------|----------|----------|
| D0 | Observe | Always allowed | validate_, check_, status_, observe_, read_, get_, list_ |
| D1 | Read | Always allowed | fetch_, load_, retrieve_, lookup_, search_ |
| D2 | Simulate | Allowed in dry_run=True | simulate_, plan_, dry_run_, preview_, analyze_ |
| D3 | Sandbox Write | Requires capability tokens | build_foundup, extract_foundup, write_evidence |
| D4 | Repo/Git Ops | BLOCKED in Phase 1 | create_repo, git_push, git_commit, modify_source |
| D5 | External API | BLOCKED in Phase 1 | send_, email_, notify_, webhook_, deploy_ |
| D6 | Irreversible | BLOCKED always | delete_, remove_, purge_, credential_, payout_ |

## Implementation Details

### File: `modules/infrastructure/wre_core/src/hermes_job_executor.py`

The `_classify_destructive_action()` method was enhanced from ~20 lines to ~100 lines with explicit prefix-based classification:

```python
# Classification prefixes (deterministic, explicit)
d0_prefixes = ("validate_", "queue_", "check_", "status_", "observe_", 
               "read_", "get_", "list_", "inspect_", "describe_", "info_")
d1_prefixes = ("fetch_", "load_", "retrieve_", "lookup_", "search_")
d2_prefixes = ("simulate_", "plan_", "dry_run_", "preview_", "analyze_",
               "estimate_", "calculate_", "compare_", "diff_")

# Exact match sets for special handling
d3_actions = {"build_foundup", "extract_foundup", "write_evidence", 
              "write_checkpoint", "save_evidence", "evidence_save", 
              "checkpoint_create", "sandbox_write_test"}
d4_actions = {"create_repo", "create_repository", "init_repo", "fork_repo",
              "git_push", "git_commit", "git_tag", "git_release", ...}

# D5 external API prefixes
d5_prefixes = ("send_", "email_", "notify_", "broadcast_", "publish_",
               "post_", "webhook_", "api_call_", "deploy_", ...)

# D6 irreversible prefixes  
d6_prefixes = ("delete_", "remove_", "purge_", "wipe_", "destroy_",
               "revoke_", "credential_", "token_", "key_", "secret_", 
               "payout_", "transfer_", "finalize_", "irreversible_")
```

### Fail-Closed Design

Unknown or ambiguous actions return `D6_IRREVERSIBLE`:

```python
# FAIL-CLOSED: Unknown actions classified as D6 (blocking)
return DestructiveActionClass.D6_IRREVERSIBLE
```

This ensures any unrecognized action patterns are blocked by default.

### Token Does Not Downgrade Classification

The implementation ensures that even with valid capability tokens, D4/D5/D6 actions remain blocked:

```python
# D4/D5/D6 are BLOCKED regardless of token validity
# Classification is immutable - tokens gate D3, not D4+
```

## Test Coverage

### New Test File: `test_hxa28_d3_native_classification.py`

132 tests covering all classification scenarios:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestD0ObserveValidateClassification | 16 | D0 prefix matching |
| TestD1ReadFetchClassification | 12 | D1 prefix matching |
| TestD2SimulatePlanClassification | 10 | D2 prefix matching |
| TestD3SandboxWriteClassification | 10 | D3 exact match + token gates |
| TestD4RepoGitOperationsBlocked | 24 | D4 blocking + no downgrade |
| TestD5ExternalAPIMutationsBlocked | 18 | D5 blocking + no downgrade |
| TestD6IrreversibleDeleteBlocked | 20 | D6 blocking + no downgrade |
| TestAmbiguousActionsFailClosed | 10 | Unknown action handling |
| TestTokenDoesNotDowngradeClassification | 3 | Token immutability |
| TestInvalidTokenStillBlocks | 1 | Invalid token rejection |
| TestWSP97TruthFieldsRemainFalse | 4 | Truth field invariants |
| TestClassificationDeterminism | 3 | Case/whitespace handling |
| TestHXA28VerdictDocumentation | 1 | Verdict constant |

### Updated Test Files

- `test_hxa23_hermes_guard_integration.py`: Updated expectations for build_foundup (D3)
- `test_hermes_job_executor.py`: Updated tests to use validate_foundup (D0) instead of build_foundup (D3) where token gates are not mocked

## Security Properties

### WSP 97 Truth Field Invariants

All four truth fields remain `False` regardless of classification:

```python
result.real_execution_performed = False  # Always
result.verification_complete = False     # Always  
result.cabr_ready = False                # Always
result.payout_ready = False              # Always
```

### Capability Token Gates

D3 sandbox writes require all four capability token gates:

- `policy_flags.d3_evidence_local_scoped = True`
- `policy_flags.allow_hermes_evidence_write = True`
- `policy_flags.d3_checkpoint_scoped = True`
- `policy_flags.allow_hermes_checkpoint_write = True`

### Phase 1 Blocking

D4/D5/D6 actions are unconditionally blocked in Phase 1:

- D4: Returns `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD` with reason "D4 blocked in Phase 1"
- D5: Returns `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD` with reason "D5 blocked in Phase 1"
- D6: Returns `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD` with reason "D6 blocked in Phase 1"

## Regression Test Results

```
modules/infrastructure/wre_core/tests/test_hermes_job_executor.py: 94 passed
modules/infrastructure/wre_core/tests/test_hxa23_hermes_guard_integration.py: 34 passed
modules/infrastructure/wre_core/tests/test_hxa28_d3_native_classification.py: 132 passed

Total: 260 tests, all passing
```

## Files Changed

| File | Change |
|------|--------|
| `wre_core/src/hermes_job_executor.py` | Enhanced _classify_destructive_action() |
| `wre_core/tests/test_hxa28_d3_native_classification.py` | NEW - 132 tests |
| `wre_core/tests/test_hxa23_hermes_guard_integration.py` | Updated D2/D3 expectations |
| `wre_core/tests/test_hermes_job_executor.py` | Changed build_foundup to validate_foundup |

## Verdict

**HXA28_D3_NATIVE_CLASSIFICATION_PHASE1: PASS**

All requirements met:
- [x] D0/D1/D2 observe/read/simulate allowed in dry_run
- [x] D3 sandbox writes gated by capability tokens
- [x] D4/D5/D6 unconditionally blocked
- [x] Unknown actions fail-closed to D6
- [x] Tokens do not downgrade classification
- [x] WSP 97 truth fields remain False
- [x] 260 tests passing

## References

- HXA23: Hermes Guard Integration
- HXA25: D3 Sandbox Execution
- HXA27: Hermes Token Validation Integration
- WSP 97: Truth Boundaries Protocol
