# REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1

**Retrieval tags:** RedDog OpenClaw adapter dryrun | FoundUpJob intake RedDog | AgentDB autonomous_task RedDog | adapter dryrun receipt

**Slice:** OpenClaw intake adapter dry-run planner (propose only, no enqueue)  
**Type:** Module + contract -- **no live OpenClaw intake, no execution**  
**Date:** 2026-06-28  
**Base:** `2761f2e65` (post-#903 execution valve land)  
**Status:** PR-READY -- draft PR only  
**WSP lock:** WSP_00, WSP_15, WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

---

## Purpose

Translate a fully gated RedDog spine plus `VALVE_OPEN_DRYRUN_ONLY` into a **proposed**
OpenClaw intake record (`FoundUpJob` or AgentDB `autonomous_task`).

**Key invariant:** propose the intake record; **do not enqueue it anywhere**.

Parent mapping: `REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md`

---

## Module

| Symbol | Path |
|--------|------|
| `plan_reddog_openclaw_adapter_dryrun()` | `modules/communication/moltbot_bridge/src/reddog_openclaw_adapter_dryrun.py` |

---

## Required inputs

| Input | Source |
|-------|--------|
| `RedDogGovernedWorkOrder` | #889/#890 |
| `PolicyGateReceipt` | #893 |
| `RedDogWorkOrderReceipt` | #894 |
| `WorkOrderDryRunInvocationResult` | #896 |
| `WREExecutorPlan` (via #898 result) | #898 |
| `ExecutionValveDecision` | #903 -- must be `VALVE_OPEN_DRYRUN_ONLY` |

---

## Required outputs

### `RedDogOpenClawAdapterDryRunResult`

- `decision`: `ADAPTER_DRYRUN_ACCEPT` | `ADAPTER_DRYRUN_REJECT`
- `proposed_intake`: `ProposedOpenClawIntakeRecord` or null
- `adapter_receipt`: `AdapterDryRunReceipt`
- `no_enqueue_performed: true`
- `no_execution_performed: true`

### Proposed intake record fields

| Field | Notes |
|-------|-------|
| `target_type` | `foundup_job` or `autonomous_task` |
| `proposed_job_id` | Deterministic when target is FoundUpJob |
| `proposed_task_id` | `reddog-wo-{work_order_id}` when autonomous_task |
| `work_order_id` | Correlation |
| `operation` | Normalized RedDog operation |
| `requested_action` | FoundUpJob canonical action when applicable |
| `repo_scope` | `repo_full_name` |
| `allowed_paths` / `denied_paths` | From executor plan / work order |
| `required_tests` | Propagated |
| `evidence_refs` | Digest-prefixed receipt refs |
| `policy_receipt_digest` | From #893 |
| `work_order_receipt_digest` | From #894 |
| `invocation_receipt_digest` | From #896 |
| `executor_plan_id` | From #898 |
| `valve_decision_digest` | From #903 |
| `no_enqueue_performed` | Always true |
| `no_execution_performed` | Always true |

---

## Rejection rules (fail closed)

| Code | Condition |
|------|-----------|
| A1 | Valve `VALVE_CLOSED` |
| A2 | Valve `VALVE_OPEN_WORKTREE_CREATE` (wrong authority for this slice) |
| A3 | Valve not `VALVE_OPEN_DRYRUN_ONLY` |
| A4 | AssignmentDispatcher target |
| A5 | Missing / mismatched receipt chain |
| A6 | Missing executor plan |
| A7 | Path outside allowed scope |
| A8 | Forbidden adapter operation (merge/pr/repo write) |

---

## Gate ordering

```text
1-7. RedDog spine (#890-#898)
8. Execution valve (#903) -- VALVE_OPEN_DRYRUN_ONLY
9. THIS ADAPTER DRY-RUN (propose only)
10. OpenClaw Supervisor enqueue (future)
11. Hermes / WRE execution (future)
```

---

## WSP_97 truth table

| # | Claim | Label |
|---|-------|-------|
| 1 | Adapter proposes intake only; no enqueue | **OBSERVED** |
| 2 | Requires VALVE_OPEN_DRYRUN_ONLY | **OBSERVED** |
| 3 | Rejects worktree-create valve authority | **OBSERVED** |
| 4 | AssignmentDispatcher forbidden | **OBSERVED** |
| 5 | Live OpenClaw enqueue remains future | **SPECIFIED_NOT_IMPLEMENTED** |
| 6 | AgentDB writes remain future | **SPECIFIED_NOT_IMPLEMENTED** |

---

## Explicit non-goals

| Non-goal | Status |
|----------|--------|
| OpenClaw Supervisor enqueue | **FORBIDDEN** |
| FoundUpJob queue append | **FORBIDDEN** |
| AgentDB writes | **FORBIDDEN** |
| Hermes / WRE execute | **FORBIDDEN** |
| Worktree / branch / file mutation | **FORBIDDEN** |

**No runtime mutation performed in authoring this contract or module.**
