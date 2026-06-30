# REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1

**Retrieval tags:** RedDog work order OpenClaw FoundUpJob | AssignmentDispatcher simulated dispatch | OpenClaw Supervisor autonomous tasks | Hermes WRE FoundUpJob receipt | RedDogGovernedWorkOrder adapter | OpenClaw worker loop intake

**Slice:** External RedDog lane — OpenClaw handoff **adapter contract only** (docs/audit)  
**Type:** Architecture contract / audit — **no runtime adapter implementation**  
**Date:** 2026-06-28  
**Base:** `c70433d7d` (post-#899 continuation memory land)  
**Status:** PR-READY — draft PR only; no merge without sovereign token  
**WSP lock:** WSP_00, WSP_15, WSP_34, WSP_50, WSP_77, WSP_91, WSP_97, WSP_109, WSP_22

---

## Purpose

Define the **canonical adapter contract** from landed RedDog governed work orders (#889–#898) to the **OpenClaw-owned worker loop** (`FoundUpJob`, AgentDB `autonomous_task`, future OpenClaw queue items).

This slice **settles ownership** and prevents RedDog from binding to `AssignmentDispatcher` (simulated scaffold).

```text
[LANDED RedDog spine — no execution]
  work order -> dry-run -> permission -> policy gate -> receipt -> invocation dry-run -> executor plan dry-run

[THIS SLICE — contract only]
  REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1

[FUTURE — not this slice]
  adapter implementation -> execution valve -> OpenClaw intake -> WRE/Hermes execution
```

---

## Direct-read evidence (WSP_50)

| Target | Path | Finding | Label |
|--------|------|---------|-------|
| RedDog spine termination | `reddog_work_order_runtime_invocation.py` | Chains #893 + #894; `no_execution_performed: true` | **OBSERVED** |
| Executor plan dry-run | `reddog_wre_executor_dryrun.py` | `plan_wre_isolated_worktree_execution_dryrun()`; no git/worktree | **OBSERVED** |
| AssignmentDispatcher | `worker_assignment_protocol.py` L403+ | Docstring: "scaffold only"; `SIMULATED_DISPATCH`; no real processes | **OBSERVED** |
| OpenClaw Supervisor | `openclaw_supervisor.py` | Canonical 24/7 state machine; polls AgentDB `autonomous_task` | **OBSERVED** |
| FoundUp orchestrator | `openclaw_foundup_orchestrator.py` | Genesis gate; `FoundUpJob` queue; build intent detection | **OBSERVED** |
| FoundUpJob contract | `foundup_job_contract.py` | Canonical job identity, lifecycle, `policy_flags`, `evidence_refs` | **OBSERVED** |
| OpenClaw execution routes | `openclaw_execution_routes.py` | Route dispatch (`fam_adapter`, `wre_orchestrator`, …) | **OBSERVED** |
| Hermes job executor (WRE) | `hermes_job_executor.py` | FoundUpJob → delegation adapter; `HERMES_DELEGATE_ENABLED=0` default | **OBSERVED** |
| Hermes FoundUp executor (agent) | `hermes_foundup_job_executor.py` | OpenClaw → FoundUpJob → Hermes builder seam | **OBSERVED** |
| AgentDB autonomous tasks | `agent_db.py` | `create_autonomous_task` / `get_autonomous_tasks`; supervisor consumes | **OBSERVED** |
| Extension continuation | #899 `extension.js` | In-tab WSP_97-safe memory; **not** worker intake | **OBSERVED** |

**Stale claim corrected:** RedDog extension `SPECIFIED_NOT_IMPLEMENTED` for governed spine is **obsolete** — spine modules #889–#898 are **LANDED** in `moltbot_bridge`. Extension still does not invoke them at runtime.

---

## Ownership ruling

| Actor | Role | This contract |
|-------|------|---------------|
| **RedDog (extension)** | Advisory; emits governed work orders; **never launches workers** | Source envelope only |
| **OpenClaw Supervisor** | Canonical worker loop scheduler | **Owns intake** after gates |
| **OpenClaw FoundUp orchestrator** | Genesis validation + FoundUpJob creation | Target factory (guarded) |
| **Hermes / WRE** | Execution under OpenClaw job contract | Downstream of FoundUpJob |
| **AssignmentDispatcher** | **NOT canonical** | Simulated scaffold / DTO candidate / deprecation candidate |
| **012 / operator** | Sovereign valve on execution + merge | Separate from adapter |

### AssignmentDispatcher disposition

**Ruling:** `AssignmentDispatcher` is **not** the canonical worker launcher.

| Disposition | Detail |
|-------------|--------|
| Status | **SIMULATED_SCAFFOLD** — `AssignmentDispatchStatus.SIMULATED_DISPATCH` only |
| Allowed use | Typed DTO / protocol reference / future deprecation source |
| Forbidden | RedDog spine termination target; real worker launch; bypass of OpenClaw Supervisor |
| Future | Demote to contract-only module or archive after OpenClaw intake adapter lands |

**Do not wire** RedDog governed work orders → `AssignmentDispatcher.dispatch_assignment()`.

---

## HoloIndex Phase 0 — Baseline (before edits)

| # | Query | Top hits | Expected | Class |
|---|-------|----------|----------|-------|
| 1 | RedDog work order OpenClaw FoundUpJob | `foundup_job_contract.py`; OpenClaw routing tests | Partial — job contract **yes**; adapter doc **no** | **INDEX_GAP** |
| 2 | AssignmentDispatcher simulated dispatch | `worker_assignment_protocol.py`; REAL_WORKER_ASSIGNMENT_PROTOCOL.md | Partial — scaffold **yes**; RedDog binding **no** | **MEDIUM** |
| 3 | OpenClaw Supervisor autonomous tasks | `openclaw_supervisor.py`; skill evolution tests | Partial — supervisor **yes**; RedDog adapter **no** | **MEDIUM** |
| 4 | Hermes WRE FoundUpJob receipt | `hermes_job_executor.py`; proof_of_compute patterns | Partial — executor **yes**; receipt chain **no** | **MEDIUM** |

**Follow-up if post-edit probe fails:** `HOLOINDEX_REDDOG_OPENCLAW_ADAPTER_CONTRACT_INDEX_GAP_PHASE1` — no ranking code changes in this slice.

---

## 1. Source objects (RedDog spine)

Adapter intake MUST require all prior spine artifacts:

| Object | Module | Required fields (digest/ref only in receipts) |
|--------|--------|-----------------------------------------------|
| `RedDogGovernedWorkOrder` | #889 contract / #890 dry-run | `work_order_id`, `requested_operation`, `allowed_paths`, `denied_paths`, `branch_name`, `repo_full_name`, `nonce`, `expiry` |
| `PolicyGateReceipt` | #893 | `decision`, `receipt_digest`, `permission_truth_label`, `no_execution_performed: true` |
| `RedDogWorkOrderReceipt` | #894 | `receipt_id`, `receipt_digest`, `policy_gate_receipt_digest` |
| `WorkOrderDryRunInvocationResult` | #896 | `decision=INVOCATION_ACCEPT`, `receipt_digest`, `no_execution_performed: true` |
| `WREExecutorPlan` | #898 dry-run | `plan_id`, `lock_key`, `proposed_branch_name`, `proposed_worktree_path`, `no_mutation_performed: true` |

Future valve receipt (**SPECIFIED_NOT_IMPLEMENTED** until `REDDOG_WRE_EXECUTION_VALVE_PHASE1`).

---

## 2. Target object options (OpenClaw-owned)

| Target | Owner | When to use | Status |
|--------|-------|-------------|--------|
| **`FoundUpJob`** | OpenClaw → Hermes | Repo-scoped governed work with `requested_action`, `policy_flags`, `evidence_refs` | **CANONICAL** for FoundUp/build/extract/validate ops |
| **AgentDB `autonomous_task`** | OpenClaw Supervisor | Supervisor-scheduled background tasks (`execute_autonomous_task` plan action) | **CANONICAL** for supervisor loop items |
| **OpenClaw queue item (future)** | OpenClaw | Typed intake record linking digests + job_id | **SPECIFIED_NOT_IMPLEMENTED** |
| **`AssignmentDispatcher` assignment** | Simulator | Never for RedDog governed path | **FORBIDDEN** |

---

## 3. Field mapping — RedDog → FoundUpJob (primary)

| RedDog / spine field | FoundUpJob field | Notes |
|----------------------|------------------|-------|
| `work_order_id` | `intent_id` + `payload.reddog_work_order_id` | Correlation; intent_id links OpenClaw session |
| `requested_operation` | `requested_action` | Map via adapter action table (below) |
| `repo_full_name` | `payload.repo_full_name` | Read-only scope declaration |
| `allowed_paths` / `denied_paths` | `payload.path_scope` | Intersection enforced at execution |
| `required_tests` | `payload.required_tests` | Propagate to WRE verification phase |
| `repo_permission_snapshot.digest` | `payload.permission_snapshot_digest` | Must be fresh at intake |
| `holoindex_evidence` digest | `evidence_refs[]` | Append digest refs only |
| `PolicyGateReceipt.receipt_digest` | `evidence_refs[]` | `policy_gate:` prefix |
| `RedDogWorkOrderReceipt.receipt_digest` | `evidence_refs[]` | `reddog_receipt:` prefix |
| `WREExecutorPlan.plan_id` | `payload.executor_plan_id` | Required after #898 |
| `PolicyGateReceipt.permission_truth_label` | `policy_flags.permission_gate_checked` | Server-authored at intake; never from untrusted deserialize |
| Valve state (future) | `policy_flags.*` + capability token flags | **SPECIFIED_NOT_IMPLEMENTED** |
| — | `dry_run_mode` | `True` until valve OPEN + sovereign token |

### Action mapping (initial)

| RedDog `requested_operation` | FoundUpJob `requested_action` | Notes |
|------------------------------|--------------------------------|-------|
| `audit_only`, `docs_audit` | `validate_foundup` | Read-only / advisory translation |
| `feature_slice`, `docs_patch`, `test_fix` | `build_foundup` | Write-sensitive; requires valve + fresh permission |
| `repo`, `write`, `pr`, `merge_request` | **REJECT** at adapter | Use dedicated slices; no merge at adapter |

AgentDB `autonomous_task` mapping (supervisor path):

| Spine field | autonomous_task field |
|-------------|----------------------|
| `work_order_id` | `task_id` prefix `reddog-wo-` + id |
| `task_summary` | `description` (sanitized, max length) |
| `wsp_applicability` | `required_skills[]` |
| WSP_15 tier | `priority_score` / `estimated_complexity` |
| Receipt digests | `context.reddog_receipt_digests[]` |

---

## 4. Gate ordering (mandatory sequence)

```text
1. RedDog advisory (extension) — no execution
2. #890 dry-run validation
3. #892 permission snapshot (read-only probe)
4. #893 OpenClaw policy gate
5. #894 Hermes-compatible receipt
6. #896 runtime invocation dry-run
7. #898 executor plan dry-run
8. REDDOG_WRE_EXECUTION_VALVE_PHASE1 (future — default CLOSED)
9. THIS ADAPTER (future implementation) — translate to FoundUpJob / autonomous_task
10. OpenClaw Supervisor / FoundUp orchestrator intake
11. Hermes / WRE execution (guarded)
```

**No step skipping.** Adapter step 9 MUST NOT run before steps 2–7 pass and step 8 is OPEN for write-sensitive ops.

---

## 5. Rejection rules (fail closed)

| Code | Condition |
|------|-----------|
| R1 | Missing `PolicyGateReceipt` or non-accept decision |
| R2 | Missing `RedDogWorkOrderReceipt` for policy digest |
| R3 | `no_execution_performed != true` on any spine artifact |
| R4 | Stale permission snapshot (TTL exceeded) |
| R5 | `permission_truth_label == NEEDS_VERIFICATION` for write-sensitive ops |
| R6 | `POLICY_ACCEPT_WITH_RETRIEVAL_GAP` + write-sensitive operation |
| R7 | Missing `WREExecutorPlan` for repo-mutation operations |
| R8 | Execution valve CLOSED (future) |
| R9 | Target is `AssignmentDispatcher` or simulated dispatch |
| R10 | Direct worker launch request from RedDog extension |
| R11 | Missing execution valve receipt (future) |
| R12 | `INDEX_GAP` on write-sensitive HoloIndex evidence without sovereign override |

---

## 6. Receipt reconciliation model

Cross-system audit chain (digests/refs only):

```yaml
RedDogAdapterIntakeReceipt:          # future slice
  adapter_intake_id: string
  work_order_id: string
  source_receipts:
    policy_gate_receipt_digest: sha256:...
    reddog_work_order_receipt_digest: sha256:...
    invocation_receipt_digest: sha256:...
    executor_plan_id: sha256:...
  target:
    kind: foundup_job | autonomous_task | openclaw_queue_item
    target_id: string                 # job_id | task_id | queue_item_id
  openclaw_action_ledger_ref: string | null    # from report_daemon_action / central adapter
  hermes_delegation_result_id: string | null   # HermesJobExecutor result
  wre_proof_of_compute_receipt_id: string | null
  no_execution_performed: true               # invariant until valve + downstream execution slices
  adapter_receipt_digest: sha256:...
```

| Receipt layer | Module / store | Role |
|---------------|----------------|------|
| RedDog work order | #894 SQLite store | Pre-execution audit |
| Executor plan | #898 result | Plan-only, no mutation |
| OpenClaw action | `openclaw_action_ledger.py` / DAEmon | Runtime action telemetry |
| FoundUpJob lifecycle | `foundup_job_contract.py` | Job state + `evidence_refs` |
| Hermes delegation | `hermes_job_executor.py` | Delegation adapter result |
| WRE proof-of-compute | `proof_of_compute_receipt` patterns | Post-execution audit (future) |

Reconciliation rule: every downstream id MUST link back to `work_order_id` + `policy_gate_receipt_digest`.

---

## 7. Explicit non-goals

| Non-goal | Status |
|----------|--------|
| Runtime adapter implementation | **SPECIFIED_NOT_IMPLEMENTED** |
| Extension runtime wiring | **SPECIFIED_NOT_IMPLEMENTED** |
| AssignmentDispatcher activation | **FORBIDDEN** |
| Branch/worktree/PR/merge | **FORBIDDEN** in this slice |
| Worker launch from RedDog | **FORBIDDEN** |
| Model/router changes | **OUT OF SCOPE** |
| Live Hermes queue auto-dispatch | **SPECIFIED_NOT_IMPLEMENTED** |
| F0 autonomous merge | **BLOCKED** |

---

## WSP_97 truth table

| # | Claim | Label |
|---|-------|-------|
| 1 | RedDog spine #889–#898 LANDED with `no_execution_performed` | **OBSERVED** |
| 2 | OpenClaw Supervisor is canonical worker loop owner | **OBSERVED** |
| 3 | AssignmentDispatcher is simulated scaffold only | **OBSERVED** |
| 4 | This doc defines adapter contract only; no runtime code | **OBSERVED** |
| 5 | FoundUpJob is primary intake target for repo-scoped work | **INFERRED** |
| 6 | AgentDB autonomous_task is supervisor intake path | **OBSERVED** |
| 7 | Adapter implementation is future slice after valve | **SPECIFIED_NOT_IMPLEMENTED** |
| 8 | Extension #899 continuation memory is UX-only, not worker intake | **OBSERVED** |

---

## WSP_15 — Next implementation slices (ordered)

| Order | Slice | Type | Depends on |
|-------|-------|------|------------|
| 1 | `REDDOG_WRE_EXECUTION_VALVE_PHASE1` | Module | #898 executor plan dry-run |
| 2 | `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1` | Module | This contract + valve |
| 3 | `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_POC_PHASE1` | Module | Dry-run adapter |
| 4 | `REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1` | Module | Valve OPEN |
| 5 | `ASSIGNMENTDISPATCHER_DEPRECATION_AUDIT_PHASE1` | Audit | Adapter PoC |
| 6 | `REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1` | Policy | All above (**BLOCKED** F0) |

**Do not skip:** valve before adapter PoC; adapter dry-run before live intake; never bind to AssignmentDispatcher.

---

## Cross-reference modules

| Module | Adapter relationship |
|--------|---------------------|
| `reddog_governed_work_order_dryrun.py` | Source envelope validation |
| `reddog_openclaw_work_order_policy_gate.py` | Policy gate receipt |
| `reddog_work_order_receipt.py` | Hermes-compatible audit receipt |
| `reddog_work_order_runtime_invocation.py` | Invocation dry-run |
| `reddog_wre_executor_dryrun.py` | Executor plan dry-run |
| `foundup_job_contract.py` | Target FoundUpJob schema |
| `openclaw_foundup_orchestrator.py` | Job creation gate |
| `openclaw_supervisor.py` | autonomous_task loop |
| `hermes_foundup_job_executor.py` | Hermes execution seam |
| `worker_assignment_protocol.py` | **Non-target** simulated scaffold |

---

## ModLog pointer

See `extensions/foundups_advisory_workers/ModLog.md` and `modules/communication/moltbot_bridge/ModLog.md`.

**Slice author:** 0102 worker lane  
**No runtime mutation performed in authoring this document.**
