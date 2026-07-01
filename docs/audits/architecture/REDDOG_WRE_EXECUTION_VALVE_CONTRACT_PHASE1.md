# REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1

**Retrieval tags:** RedDog execution valve | WRE worktree valve | OpenClaw execution gate | closed by default

**Slice:** Closed-by-default execution valve evaluator (pure evaluation)  
**Type:** Module + contract -- **no execution, no worktree, no worker launch**  
**Date:** 2026-06-28  
**Base:** `2c8df23dd` (post-#901 OpenClaw adapter contract land)  
**Status:** PR-READY -- draft PR only  
**WSP lock:** WSP_00, WSP_15, WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

---

## Purpose

Provide an explicit **closed-by-default execution valve** between the landed RedDog spine
(#889-#898) and any future OpenClaw intake, adapter dry-run, or worktree-create slices.

Default: `VALVE_CLOSED`. No implicit open path.

---

## Module

| Symbol | Path |
|--------|------|
| `evaluate_reddog_execution_valve()` | `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py` |

---

## Valve states

| State | Meaning | Required environment |
|-------|---------|---------------------|
| `VALVE_CLOSED` | Hard default; reject or hold | No flag, failed checks, or missing token |
| `VALVE_OPEN_DRYRUN_ONLY` | Adapter/planner dry-run only | `valve_dryrun_enabled=true` + full spine |
| `VALVE_OPEN_WORKTREE_CREATE` | First real worktree slice may proceed | `valve_worktree_create_enabled=true` + `sovereign_worktree_token` + full spine |

---

## Mandatory spine prerequisites

All must pass before any non-`VALVE_CLOSED` state:

1. `PolicyGateReceipt.decision == POLICY_ACCEPT`
2. `RedDogWorkOrderReceipt` present with matching policy digest
3. `WorkOrderDryRunInvocationResult.decision == INVOCATION_ACCEPT`
4. `WREExecutorDryRunResult.decision == EXECUTOR_PLAN_ACCEPT` with plan
5. Fresh permission snapshot digest
6. #901 canonical intake target: `foundup_job` or `autonomous_task`
7. Reject `assignment_dispatcher` target

---

## Forbidden paths (fail closed)

| Code | Condition |
|------|-----------|
| V1 | Direct worker launch |
| V2 | Direct model / OpenRouter worker launch |
| V3 | Direct WRE executor call |
| V4 | Protected branch mutation request |
| V5 | Missing or mismatched receipt chain |
| V6 | Stale permission snapshot |
| V7 | INDEX_GAP on write-sensitive operation |
| V8 | AssignmentDispatcher intake target |

---

## Gate ordering (spine + valve)

```text
1. RedDog advisory (extension) -- no execution
2. #890 dry-run validation
3. #892 permission snapshot
4. #893 policy gate
5. #894 receipt
6. #896 invocation dry-run
7. #898 executor plan dry-run
8. THIS VALVE (evaluate only)
9. #901 adapter dry-run (future)
10. OpenClaw intake (future)
11. Worktree create (future; valve OPEN_WORKTREE_CREATE only)
```

---

## WSP_97 truth table

| # | Claim | Label |
|---|-------|-------|
| 1 | Default valve state is CLOSED | **OBSERVED** |
| 2 | Evaluator performs no git/subprocess/worktree mutation | **OBSERVED** |
| 3 | AssignmentDispatcher is forbidden intake target | **OBSERVED** |
| 4 | FoundUpJob / autonomous_task are canonical targets per #901 | **OBSERVED** |
| 5 | Adapter implementation remains future slice | **SPECIFIED_NOT_IMPLEMENTED** |
| 6 | Worktree create remains future slice | **SPECIFIED_NOT_IMPLEMENTED** |

---

## WSP_15 next slices (ordered)

| Order | Slice | Depends on |
|-------|-------|------------|
| 1 | `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1` | This valve + #901 contract |
| 2 | `REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1` | Valve OPEN_WORKTREE_CREATE |
| 3 | `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_POC_PHASE1` | Adapter dry-run |

---

## Explicit non-goals

| Non-goal | Status |
|----------|--------|
| Worktree / branch creation | **FORBIDDEN** |
| File edits / PR / merge | **FORBIDDEN** |
| OpenClaw / Hermes runtime dispatch | **FORBIDDEN** |
| Extension runtime wiring | **SPECIFIED_NOT_IMPLEMENTED** |

**No runtime mutation performed in authoring this contract or module.**
