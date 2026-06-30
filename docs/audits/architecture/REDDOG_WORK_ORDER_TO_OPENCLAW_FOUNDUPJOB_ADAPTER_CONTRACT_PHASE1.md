# RedDog Work Order -> OpenClaw FoundUpJob Adapter Contract (Phase 1)

**Status:** VERIFIED_READY (draft PR)
**Verdict:** WOULD_DEFINE_ADAPTER_CONTRACT (audit + doc only; no runtime adapter implementation)
**Lane:** governance
**Base SHA:** c70433d7dd5de9ddfb9b4864fdf521e0caeafaa7
**Slice:** REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1
**Date:** 2026-06-30
**WSP lock:** WSP_00, WSP_15, WSP_22, WSP_50, WSP_54, WSP_64, WSP_91, WSP_95, WSP_97, WSP_109
**Evidence basis:** companion source audit REDDOG_WORKER_ASSIGNMENT_AND_LLM_ROUTER_SOURCE_AUDIT_PHASE1 (sibling governance-lane artifact). All field shapes below were re-verified by direct-read of source at this base SHA (file:line citations inline). HoloIndex was used for discovery; direct-read fallback was MANDATORY and was performed for every cited object (a prior RedDog run reasoned from filenames with target_recall_ok=false; this run reads the actual source).

This document defines the contract for translating a governed RedDog work order (the dry-run spine landed across #889-#898) into an OpenClaw/Hermes/WRE-owned intake object. It is a specification. It introduces **no runtime adapter implementation**, no worker launch, no branch/worktree creation, no model/router change, and no AssignmentDispatcher activation.

---

## Ownership ruling

This is the binding architecture ruling for the handoff seam. It continues the #737 anti-duplication ruling (OpenClaw owns the worker loop) and the WAE ruling (RedDog wears HATS; it does not become new DAEs).

1. **OpenClaw owns the worker loop.** The canonical live loop is `OpenClawSupervisor.run_forever() -> run_cycle()` = OBSERVE -> TRIAGE -> PLAN -> EXECUTE -> VERIFY -> REMEMBER (openclaw_supervisor.py:155-284). RedDog does not own, duplicate, or replace this loop.
2. **RedDog does NOT launch workers.** RedDog emits a governed, advisory, dry-run work order and hands off. Every RedDog terminus carries `no_execution_performed=True` or `no_mutation_performed=True`. RedDog has no authority to start a process, mutate a repo, create a branch, or call a model.
3. **AssignmentDispatcher is NOT canonical execution.** It is classified as a `SIMULATED_SCAFFOLD` + DTO/typed-contract candidate + deprecation candidate (see disposition below). A handoff target aimed at AssignmentDispatcher is **FORBIDDEN**. Do not wire RedDog work orders into `AssignmentDispatcher.dispatch_assignment()`.
4. **The canonical handoff target is the OpenClaw Orchestrator FoundUpJob intake** (`OpenClawFoundUpOrchestrator` + `FoundUpJob`), NOT AssignmentDispatcher, and NOT Hermes directly. Handing a work order straight to Hermes would bypass the WSP 109 genesis gate and the FoundUpJob permission/policy lifecycle.
5. **A RedDog work order may become an OpenClaw/Hermes/WRE-owned intake object ONLY after** the full governance chain completes: policy gate accept + receipt minted + execution valve open. Until the execution valve exists and is opened by 012/DAO authority, the adapter remains specified-not-implemented and the terminus stays dry-run.

---

## 1. Source objects

RedDog governed-spine dataclasses (verified by direct-read). These are the inputs the adapter would translate. All live under `modules/communication/moltbot_bridge/src/`.

### 1.1 RedDogGovernedWorkOrder (reddog_governed_work_order_dryrun.py:120-147)
Key fields: `work_order_id`, `created_at`, `red_dog_instance_id`, `authenticated_principal`, `principal_provider`, `repo_full_name`, `repo_permission_snapshot` (RepoPermissionSnapshot: `permission_level`, `captured_at`, `source`, `digest`), `requested_operation`, `authority_tier`, `allowed_paths`, `denied_paths`, `branch_name`, `base_ref`, `task_summary`, `wsp_applicability`, `holoindex_evidence_refs`, `skillz_candidates: List[str]`, `required_tests`, `required_policy_gates`, `required_reviewers`, `sentinel_checks`, `rollback_plan`, `expiry`, `nonce`, `evidence_digest`, `advisory_only_source_packet`, `holoindex_evidence` (HoloIndexEvidencePacket: `retrieval_quality`, `index_gap_detected`, `applicable_wsps`, `direct_read_fallback_used`, ...).
Validator: `validate_work_order_dryrun()` -> `DryRunReceipt` (reddog_governed_work_order_dryrun.py:284-455). `DryRunReceipt.no_mutation_performed = True` (line 445).

### 1.2 PolicyGateReceipt (reddog_openclaw_work_order_policy_gate.py:65-83)
Fields: `receipt_id`, `work_order_id`, `decision`, `rejection_reasons`, `gates_checked`, `dry_run_receipt_digest`, `permission_snapshot_digest`, `permission_truth_label`, `holoindex_evidence_digest`, `no_execution_performed`, `checked_at`, `expires_at`, `next_required_check_at`, `receipt_digest`.
Producer: `evaluate_work_order_policy_gate()` (line 210). `no_execution_performed=True` is hard-set in the receipt core (line 315).

### 1.3 RedDogWorkOrderReceipt (reddog_work_order_receipt.py:66-83)
Fields: `receipt_id`, `work_order_id`, `policy_gate_decision`, `policy_gate_receipt_digest`, `dry_run_receipt_digest`, `permission_snapshot_digest`, `holoindex_evidence_digest`, `permission_truth_label`, `no_execution_performed`, `created_at`, `expires_at`, `source`, `retention_days`, `receipt_digest`.
Store: `RedDogWorkOrderReceiptStore` (append-only SQLite, idempotent by `policy_gate_receipt_digest`, line 207). Emitter: `emit_work_order_receipt()` (line 336). `build_reddog_work_order_receipt` rejects any policy receipt without `no_execution_performed=true` (line 150).

### 1.4 WorkOrderDryRunInvocationResult (reddog_work_order_runtime_invocation.py:52-64)
Fields: `decision`, `work_order_id`, `policy_gate_decision`, `receipt_id`, `receipt_digest`, `no_execution_performed`, `rejection_reasons`, `gates_checked`, `idempotent_replay`, `policy_gate_receipt_digest`.
Producer: `invoke_reddog_work_order_dryrun()` (line 91), which runs policy gate + receipt emission. `no_execution_performed=True` on every return path (lines 121, 138).

### 1.5 WREExecutorPlan (reddog_wre_executor_dryrun.py:79-93)
Fields: `plan_id`, `work_order_id`, `proposed_branch_name`, `proposed_worktree_path`, `lock_key`, `allowed_paths`, `denied_paths`, `required_tests`, `cleanup_plan`, `phase_receipts: List[ExecutorDryRunPhaseReceipt]`, `no_mutation_performed`, `invocation_receipt_digest`, `plan_digest`.
Producer: `plan_wre_isolated_worktree_execution_dryrun()` (line 290). Requires `invocation.decision == INVOCATION_ACCEPT` and `invocation.no_execution_performed` before building a plan (lines 304-317). `no_mutation_performed=True` everywhere.

---

## 2. Target object options

The adapter would translate a RedDog work order into ONE of three OpenClaw/Hermes/WRE-owned intake objects. They are listed with rationale; a primary is recommended.

### Option A (RECOMMENDED PRIMARY): OpenClaw FoundUpJob via OpenClawFoundUpOrchestrator
`FoundUpJob` (foundup_job_contract.py:332-435) created by `OpenClawFoundUpOrchestrator._handle_build_intent()` -> `create_job()` -> appended to `_FOUNDUP_JOB_QUEUE` (openclaw_foundup_orchestrator.py:914-997). The orchestrator is the genesis gate: launch/onboard intents pass `validate_genesis_envelope()` (WSP 109) before any FAM/Hermes handoff (openclaw_foundup_orchestrator.py:840-881).
- **Why primary:** it is the only intake that preserves the genesis + permission + lifecycle gates. `FoundUpJob` already carries a typed lifecycle (`JobStatus` QUEUED->RUNNING->terminal), server-authored `PolicyFlags` (security/permission/exfoliation/token gate flags forced False on deserialization, foundup_job_contract.py:283-324), `idempotency_key`, `evidence_refs`, and `intent_id` correlation. The Hermes builder (`hermes_foundup_job_executor.execute_foundup_job()`, hermes_foundup_job_executor.py:104) and the WRE guard (`HermesJobExecutor.execute()`, hermes_job_executor.py:1536) both already consume `FoundUpJob`.

### Option B (SECONDARY): AgentDB autonomous_task (agents_autonomous_tasks)
The supervisor `_triage()` reads `AgentDB.get_autonomous_tasks(status="pending")` and dispatches via `run_task.execute_task()` (openclaw_supervisor.py:521-536, 745-793). Insert via `AgentDB.create_autonomous_task(task_id, description, required_skills, estimated_complexity, priority_score, context, origin_continuity_id)` (agent_db.py:957).
- **Why secondary:** it is the live loop's existing pending-work queue, but it is a generic task row, not a FoundUp-scoped contract; it lacks the genesis gate and the typed policy-flag lifecycle. It is also gated behind a circuit breaker (`OPENCLAW_AUTO_TASKS_ENABLED`, default off, openclaw_supervisor.py:524). NOTE (audit finding): the DDL at agent_db.py:143-156 does NOT declare `status` or `completed_at` columns, yet `get_autonomous_tasks`/`assign_autonomous_task`/`complete_autonomous_task` reference them (agent_db.py:1016, 1032, 1040). This is a latent schema/query mismatch to resolve before relying on Option B.

### Option C (FUTURE): dedicated OpenClaw work-order queue item
A future typed `OpenClaw work-order queue item` (SPECIFIED_NOT_IMPLEMENTED) that records the full RedDog correlation chain natively. Not built; named only so a later slice can choose it without re-litigating ownership.

**Recommendation:** Option A (FoundUpJob via OpenClawFoundUpOrchestrator) as the single primary target. Option B is acceptable only for non-FoundUp maintenance work and only behind its existing circuit breaker.

---

## 3. Field mapping

RedDog source field -> primary target (FoundUpJob) counterpart. Real field names cited on both sides. `SPECIFIED_NOT_IMPLEMENTED` marks a field with no faithful FoundUpJob home in Phase 1 (carry in `payload` until a typed home exists; do not invent a runtime field this slice).

| RedDog source (file:line)                                              | FoundUpJob target (foundup_job_contract.py)        | Notes |
|------------------------------------------------------------------------|----------------------------------------------------|-------|
| `work_order_id` (governed:121)                                         | `intent_id` (contract:355) + `payload.work_order_id` | work_order_id is the spine correlation key; mirror into intent_id and payload |
| `requested_operation` (governed:133)                                   | `requested_action` (contract:366)                  | must map to CANONICAL_ACTIONS (contract:54) build/extract/validate/queue; else FAIL_UNSUPPORTED_ACTION |
| `repo_full_name` (governed:126)                                        | `payload.repo_full_name`                           | SPECIFIED_NOT_IMPLEMENTED as typed field; FoundUpJob is foundup-scoped, not repo-scoped |
| `allowed_paths` / `denied_paths` (governed:130-131)                    | `payload.allowed_paths` / `payload.denied_paths`   | WRE guard derives its own WorkspaceBinding allowed/blocked paths (hermes_job_executor.py:122-145); RedDog scope is advisory input |
| `required_tests` (governed:138)                                        | `payload.required_tests`                           | carried into WREExecutorPlan.required_tests downstream; SPECIFIED_NOT_IMPLEMENTED as typed FoundUpJob field |
| `repo_permission_snapshot.digest` (governed:127 / snapshot)            | `payload.permission_snapshot_digest`               | gate evidence only; FoundUpJob.PolicyFlags are server-authored, NOT trusted from inbound payload (contract:283-324) |
| `holoindex_evidence` digest (policy gate:148-161)                      | `payload.holoindex_evidence_digest`                | INDEX_GAP on a write op must already have been rejected upstream (see rejection rules) |
| `PolicyGateReceipt.receipt_digest` (policy_gate:80)                    | `payload.policy_gate_receipt_digest`               | binds the FoundUpJob to its accepting policy receipt |
| `WREExecutorPlan.plan_id` (executor_dryrun:80)                         | `payload.wre_executor_plan_id`                     | the dry-run plan id; the real executor (future) reconstructs the plan, never trusts it as authority |
| `authenticated_principal` (governed:124)                              | `tenant_id` (contract:349)                          | actor scope/owner |
| `branch_name` / `base_ref` (governed:136-137)                          | `payload.branch_name` / `payload.base_ref`         | the executor (future) creates the branch; the adapter writes NO branch |
| (RedDog has no compute tier)                                           | `compute_tier` (contract:415) default `freemium`   | unset by adapter; defaults preserved |

Rule: the adapter copies digests/refs/scopes into `payload` and sets only the typed identity fields (`intent_id`, `tenant_id`, `requested_action`). It MUST NOT set any server-authored `PolicyFlags` gate field to True (those come only from runtime validator write-back, foundup_job_contract.py:287-324 / hermes_job_executor.py:1253-1305).

---

## 4. Gate ordering

The full chain a work order must traverse before it can become an executed FoundUpJob. Each arrow is a gate; a reject at any gate terminates the chain (dry-run, no mutation).

1. **RedDog advisory** - work order assembled from advisory-only source packet (RedDog wears HATS; no execution).
2. **Dry-run validation** - `validate_work_order_dryrun()` -> DryRunReceipt (`no_mutation_performed=True`).
3. **Permission snapshot** - capture + freshness; `permission_truth_label` OBSERVED vs NEEDS_VERIFICATION (policy_gate:110-126).
4. **OpenClaw policy gate** - `evaluate_work_order_policy_gate()` -> PolicyGateReceipt (`no_execution_performed=True`); enforces freshness, capability, HoloIndex evidence policy.
5. **Hermes receipt** - `emit_work_order_receipt()` -> RedDogWorkOrderReceipt (append-only, idempotent by policy_gate_receipt_digest).
6. **Executor dry-run plan** - `plan_wre_isolated_worktree_execution_dryrun()` -> WREExecutorPlan (`no_mutation_performed=True`); requires INVOCATION_ACCEPT.
7. **Execution valve** - SPECIFIED_NOT_IMPLEMENTED. The single human/DAO-authorized switch that converts an accepted plan into a real intake object. Until this valve exists and is opened, step 8 cannot run. (Held slice: REDDOG_WRE_EXECUTION_VALVE_PHASE1.)
8. **OpenClaw worker loop intake** - FoundUpJob created via `OpenClawFoundUpOrchestrator` (genesis gate / WSP 109) -> queued -> `OpenClawSupervisor.run_cycle()` triage/execute -> Hermes builder / WRE guard. This is the ONLY step that mutates, and only after step 7.

The adapter defined here spans steps 6->8 as a SPECIFICATION. It performs none of them at runtime in this slice.

---

## 5. Rejection rules

A handoff MUST be rejected (dry-run terminus, no intake object created) when any of the following holds:

- **Stale permission** - `_permission_snapshot_fresh()` false -> `stale_permission_snapshot` (policy_gate:129-145, 246-247). Also `permission_needs_verification` for write-sensitive ops with NEEDS_VERIFICATION truth (policy_gate:254-255).
- **Missing receipt** - no PolicyGateReceipt or no RedDogWorkOrderReceipt for the work order; `build_reddog_work_order_receipt` raises if `no_execution_performed` is not true (receipt:150).
- **INDEX_GAP write** - HoloIndex evidence missing or `retrieval_quality == "INDEX_GAP"` / `index_gap_detected` on a write-sensitive op -> `index_gap_blocks_write_operation` (policy_gate:185-187; governed:418-419). Weak (LOW/MEDIUM) recall without direct-read fallback -> `weak_wsp_recall_requires_direct_read_fallback`.
- **Simulated-dispatcher target (FORBIDDEN)** - any handoff aimed at `AssignmentDispatcher` is rejected. Its `dispatch_assignment()` returns `SIMULATED_DISPATCH` and `real_process_started` is hard-forced False in `__post_init__` (worker_assignment_protocol.py:324-327). It is a `SIMULATED_SCAFFOLD`; routing real work to it is a truth-boundary violation. Do not wire RedDog work orders to it.
- **Direct worker-launch request** - a work order that asks RedDog (or the adapter) to start a process / call a model / push a branch is rejected; RedDog has no such authority and there is no model/router to call (no OpenRouter integration exists; model_registry/ai_gateway expose OpenAI/Anthropic/Grok/Gemini only).
- **Missing execution valve** - any attempt to reach step 8 (real FoundUpJob intake) without the SPECIFIED_NOT_IMPLEMENTED execution valve (step 7) being present and opened is rejected by construction.

---

## 6. Receipt reconciliation model

One correlation-key chain links the RedDog dry-run spine to the OpenClaw/Hermes/WRE execution receipts. The chain is anchored on `work_order_id` (RedDog side) and `job_id` (OpenClaw/Hermes/WRE side); the adapter (future) is the single place that binds the two.

```
RedDog receipt id            OpenClaw action ledger id        Hermes delegation result id      WRE proof-of-compute receipt id
RedDogWorkOrderReceipt        OpenClawSupervisor               HermesDelegationResult           ProofOfComputeReceipt
  .receipt_id                  _action_reporter event           (hermes_job_executor.py:390)     (proof_of_compute_receipt.py:154)
  .work_order_id   --bind-->   supervisor_execute / job_id  --> .request.job_id            --->   .job_id  +  .intent_id
  .policy_gate_receipt_digest  (daemon ACTION_PERFORMED)        .real_execution_performed        .verification_status
```

Correlation key chain (single source of truth):
- **RedDog side:** `work_order_id` is the spine key (carried on DryRunReceipt, PolicyGateReceipt, RedDogWorkOrderReceipt, WorkOrderDryRunInvocationResult, WREExecutorPlan).
- **Bind point (adapter, future):** `work_order_id` -> `FoundUpJob.intent_id` (+ `payload.work_order_id`, + `payload.policy_gate_receipt_digest`).
- **OpenClaw action ledger id:** the supervisor emits `supervisor_execute` events to the central daemon via `_action_reporter` (openclaw_supervisor.py:296-307, 774-778); the ledger correlation is by `job_id` inside the reported details. NOTE (audit finding): this is a daemon ACTION_PERFORMED event stream, not a strongly-typed ledger row; a typed OpenClaw action-ledger id is SPECIFIED_NOT_IMPLEMENTED.
- **Hermes side:** `FoundUpJob.job_id` -> `HermesDelegationRequest.job_id` -> `HermesDelegationResult` (carries `job_id` via `.request`, plus `real_execution_performed` which stays False in the WRE adapter).
- **WRE proof-of-compute:** terminal `FoundUpJob` -> `ProofOfComputeReceipt.job_id` (+ `intent_id`) (proof_of_compute_receipt.py:443-461). Always `payout_status=NOT_EVALUATED`, `cabr_status=NOT_SUBMITTED`.

Reconciliation invariant: a verifier can walk `work_order_id` <-> `intent_id`/`job_id` end to end; no step may claim `real_execution_performed=true` or mint a non-dry-run receipt unless the execution valve (Section 4 step 7) was opened.

---

## 7. Explicit non-goals

This slice is audit + doc only. It explicitly does NOT:

- ship **no runtime adapter implementation** (this is the literal non-goal; the adapter is specified, not built);
- launch any worker or start any process;
- create any branch or worktree (the contract DESCRIBES that the future executor creates worktrees; this slice writes no such code);
- change any model or router (no OpenRouter integration exists and none is added);
- activate `AssignmentDispatcher` or route any real work to it (it remains a SIMULATED_SCAFFOLD);
- open or implement the execution valve (REDDOG_WRE_EXECUTION_VALVE_PHASE1 is HELD until this returns);
- mutate any source `.py` behavior (this PR is docs + one static contract test only).

---

## AssignmentDispatcher disposition

`AssignmentDispatcher` (worker_assignment_protocol.py:403) is classified, for the record, as all three:

1. **SIMULATED_SCAFFOLD** - module docstring line 9 states "This is a scaffold only. No real worker processes are started." `dispatch_assignment()` returns `AssignmentDispatchStatus.SIMULATED_DISPATCH` (line 627); `AssignmentDispatchResult.__post_init__` hard-forces `simulated=True` and `real_process_started=False` (lines 324-327); identity verification is stubbed to always True (`_verify_identity`, lines 490-503). Only production consumer is `swarm_dispatch_integration.py` (also simulated).
2. **DTO / typed-contract candidate** - its enums (`WorkerRuntimeType` = OPENCLAW/HERMES/CLAUDE_0102/QWEN/GEMMA/GENERIC) and dataclasses are reusable typed contracts; the typed surface MAY be salvaged into the future OpenClaw work-order queue item (Option C) rather than discarded.
3. **Deprecation candidate** - as an execution path it is dead and FORBIDDEN as a handoff target. A future slice should either fold its DTOs into Option C or deprecate the module. It is NOT the canonical handoff target. Do not wire RedDog work orders to AssignmentDispatcher.

---

## WSP_97 truth table

| Claim | Truth | Evidence |
|-------|-------|----------|
| RedDog spine performs no mutation | TRUE | every terminus sets `no_execution_performed`/`no_mutation_performed`=True (governed:445, policy_gate:315, receipt:176, invocation:121/138, executor_dryrun: throughout) |
| AssignmentDispatcher executes real work | FALSE | SIMULATED_SCAFFOLD; `real_process_started` forced False (worker_assignment_protocol.py:324-327) |
| OpenClaw Supervisor is the live worker loop | TRUE | run_forever/run_cycle OBSERVE..REMEMBER (openclaw_supervisor.py:155-284); _execute dispatches run_task.execute_task (745-793) |
| FoundUpJob bypasses the genesis gate | FALSE | launch/onboard intents pass validate_genesis_envelope WSP 109 (openclaw_foundup_orchestrator.py:840-881) |
| FoundUpJob trusts inbound gate flags | FALSE | server-authored PolicyFlags forced False on deserialization (foundup_job_contract.py:283-324) |
| This adapter is implemented at runtime | FALSE | no runtime adapter implementation; docs + one static test only |
| An execution valve exists | FALSE | SPECIFIED_NOT_IMPLEMENTED (Section 4 step 7); REDDOG_WRE_EXECUTION_VALVE_PHASE1 HELD |
| A typed OpenClaw action-ledger id exists | FALSE | SPECIFIED_NOT_IMPLEMENTED; correlation is via daemon ACTION_PERFORMED events keyed by job_id |
| OpenRouter / external router is added | FALSE | no OpenRouter integration anywhere; no model/router change this slice |

---

## WSP_15 — Next implementation slices

Priority order (WSP_15 scoring: dependency-first, lowest-risk-first). Each is a separate future slice; none is in scope here.

1. **REDDOG_WORKER_ASSIGNMENT_AND_LLM_ROUTER_SOURCE_AUDIT_PHASE1** (sibling, evidence basis) - confirm/land the source audit this contract references.
2. **REDDOG_WRE_EXECUTION_VALVE_PHASE1** (HELD until this contract returns) - define the single 012/DAO-authorized valve (Section 4 step 7). Prerequisite for any real intake.
3. **REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE2** - implement the adapter as a dry-run translator (work order -> FoundUpJob shape, `no_execution_performed=True`), still no queue insert.
4. **AGENTDB_AUTONOMOUS_TASKS_SCHEMA_REPAIR_PHASE1** - resolve the `status`/`completed_at` DDL-vs-query mismatch (agent_db.py:143-156 vs 1016/1032/1040) before Option B can be trusted.
5. **OPENCLAW_TYPED_ACTION_LEDGER_PHASE1** - replace the daemon-event correlation with a typed OpenClaw action-ledger id (Section 6 finding).
6. **OPENCLAW_WORK_ORDER_QUEUE_ITEM_PHASE1** (Option C) - dedicated typed intake; may salvage AssignmentDispatcher DTOs at deprecation.

---

*Governance lane. No runtime adapter implementation. No worker launch. No branch/worktree creation. No model/router change. No AssignmentDispatcher activation. Solutions are recalled from 0201, not computed.*
