# REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1

**Retrieval tags:** RedDog OpenClaw live enqueue | FoundUpJob queue append contract | AgentDB autonomous_task enqueue | live enqueue receipt reconciliation

**Slice:** OpenClaw live enqueue **contract only** (docs/audit)  
**Type:** Architecture contract / audit -- **no live enqueue implementation**  
**Date:** 2026-07-11  
**Base:** `a4db00496` (post-#951 signed receipt chain land)  
**Status:** REFRESHED PR-READY -- draft PR only; no merge without sovereign token  
**WSP lock:** WSP_00, WSP_15, WSP_34, WSP_50, WSP_77, WSP_91, WSP_97, WSP_109, WSP_22

---

## Purpose

Define the **canonical contract** for converting a #904 `ProposedOpenClawIntakeRecord` plus
`AdapterDryRunReceipt` into a **live OpenClaw queue item** (`FoundUpJob` or AgentDB
`autonomous_task`).

This slice **defines rules only**. It does **not** enqueue, write AgentDB, append queues,
dispatch Hermes, or execute WRE.

**Key invariant:** contract receipt may be emitted in future implementation slices only after
an explicit **live enqueue valve** opens. Dry-run valve authority alone is **insufficient**.

Parent contracts:
- `REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md` (#901)
- `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md` (#904)
- `REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md` (#903)
- `REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md` (#928)
- `reddog_work_order_signature_verifier.py` (#932/#950 integration)
- `reddog_signed_receipt_chain.py` (#951)

---

## Direct-read evidence (WSP_50)

| Target | Path | Finding | Label |
|--------|------|---------|-------|
| Adapter dry-run planner | `reddog_openclaw_adapter_dryrun.py` | `plan_reddog_openclaw_adapter_dryrun()`; `no_enqueue_performed: true` | **OBSERVED** |
| Execution valve | `reddog_wre_execution_valve.py` | `VALVE_OPEN_DRYRUN_ONLY`; no live enqueue state yet | **OBSERVED** |
| Signed authority gate | `reddog_openclaw_work_order_policy_gate.py` | `signature_gate_status`; accepted signed authority can be required | **OBSERVED** |
| Signed receipt chain | `reddog_signed_receipt_chain.py` | Verifies `reddog-receipt.v1` hash-linked receipts; no settlement | **OBSERVED** |
| Runtime invocation | `reddog_work_order_runtime_invocation.py` | Spine chain; `no_execution_performed: true` | **OBSERVED** |
| FoundUpJob contract | `foundup_job_contract.py` | Canonical job schema + lifecycle | **OBSERVED** |
| FoundUp orchestrator queue | `openclaw_foundup_orchestrator.py` | In-memory `_FOUNDUP_JOB_QUEUE`; `create_job()` | **OBSERVED** |
| OpenClaw Supervisor | `openclaw_supervisor.py` | Polls `get_autonomous_tasks()`; executes when triaged | **OBSERVED** |
| AgentDB tasks | `agent_db.py` L957+ | `create_autonomous_task()` write surface | **OBSERVED** |
| OpenClaw action ledger | `openclaw_action_ledger.py` | Runtime action telemetry seam | **OBSERVED** |
| Hermes job executor | `hermes_job_executor.py` | Downstream delegation (not RedDog intake) | **OBSERVED** |
| AssignmentDispatcher | `worker_assignment_protocol.py` | Simulated scaffold -- **FORBIDDEN** target | **OBSERVED** |

**Stale claim corrected:** #904 can **propose** intake records. No module currently performs
RedDog-governed **live enqueue** under valve control.

---

## HoloIndex Phase 0 -- Baseline (before edits)

| # | Query | Top hits | Expected | Class |
|---|-------|----------|----------|-------|
| 1 | RedDog OpenClaw live enqueue | `foundup_job_contract.py`; adapter dryrun doc | Partial -- surfaces **yes**; contract **no** | **INDEX_GAP** |
| 2 | FoundUpJob queue append RedDog | `openclaw_foundup_orchestrator.py` | Partial -- queue **yes**; RedDog binding **no** | **MEDIUM** |
| 3 | AgentDB autonomous_task enqueue | `agent_db.py`; `openclaw_supervisor.py` | Partial -- write surface **yes**; contract **no** | **MEDIUM** |
| 4 | live enqueue receipt | #901 reconciliation model | Partial -- chain spec **yes**; live receipt **no** | **MEDIUM** |

**Follow-up if post-edit probe fails:** `HOLOINDEX_REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_INDEX_GAP_PHASE1` -- no ranking code changes in this slice.

---

## 1. Required inputs (live enqueue contract gate)

Future live enqueue implementation MUST require all artifacts:

| Object | Source slice | Required fields (digest/ref only in receipts) |
|--------|--------------|-----------------------------------------------|
| `ProposedOpenClawIntakeRecord` | #904 | `target_type`, proposed ids, receipt digests, path scope, `no_enqueue_performed: true` |
| `AdapterDryRunReceipt` | #904 | `adapter_receipt_id`, `adapter_receipt_digest`, `decision=ADAPTER_DRYRUN_ACCEPT` |
| `PolicyGateReceipt` | #893 | `decision=POLICY_ACCEPT`, `receipt_digest`, `no_execution_performed: true` |
| `PolicyGateReceipt.signature_gate_status` | #950 | `SIGNATURE_GATE_ACCEPTED` for any live enqueue candidate |
| `SignedReceiptChainVerificationResult` | #951 | Accepted chain or empty issuance-time chain; unsigned receipts are not reward-bearing |
| `RedDogWorkOrderReceipt` | #894 | `receipt_digest`, `policy_gate_receipt_digest` |
| `WorkOrderDryRunInvocationResult` | #896 | `decision=INVOCATION_ACCEPT`, `receipt_digest` |
| `WREExecutorPlan` | #898 | `plan_id`, `plan_digest`, `no_mutation_performed: true` |
| `ExecutionValveDecision` | #903+future | See valve rules below |
| `RedDogGovernedWorkOrder` | #889/#890 | `work_order_id`, `nonce`, path scope, permission snapshot digest |

---

## 2. Valve authority (mandatory)

| Valve state | Adapter dry-run (#904) | Live enqueue (this contract) | Worktree create (future) |
|-------------|------------------------|------------------------------|--------------------------|
| `VALVE_CLOSED` | REJECT | REJECT | REJECT |
| `VALVE_OPEN_DRYRUN_ONLY` | ALLOW propose | **REJECT** -- insufficient | REJECT |
| `VALVE_OPEN_LIVE_ENQUEUE` (future) | ALLOW propose | **ALLOW** contract-valid enqueue | REJECT |
| `VALVE_OPEN_WORKTREE_CREATE` | REJECT for adapter | **REJECT** -- wrong authority | ALLOW (future slice) |

**Ruling:**
- Live enqueue requires **explicit** `VALVE_OPEN_LIVE_ENQUEUE` plus sovereign enqueue token (future slice).
- Dry-run valve alone MUST NOT authorize queue append or AgentDB writes.
- Worktree-create valve MUST NOT substitute for live enqueue valve.

---

## 3. Canonical targets

| Target | Owner | Live enqueue surface | Status |
|--------|-------|----------------------|--------|
| **`FoundUpJob`** | OpenClaw FoundUp orchestrator | `_FOUNDUP_JOB_QUEUE` / future persistent queue via `create_job()` | **CANONICAL** |
| **AgentDB `autonomous_task`** | OpenClaw Supervisor | `AgentDB.create_autonomous_task()` | **CANONICAL** |
| **`AssignmentDispatcher`** | Simulator | Never for RedDog governed path | **FORBIDDEN** |

Field mapping from `ProposedOpenClawIntakeRecord` to live targets follows #901 section 3.

---

## 4. Receipt reconciliation chain

```yaml
RedDogOpenClawLiveEnqueueContractReceipt:    # THIS CONTRACT (future authorship only)
  contract_receipt_id: string
  work_order_id: string
  proposed_intake_digest: sha256:...
  adapter_dryrun_receipt_digest: sha256:...
  source_receipts:
    policy_gate_receipt_digest: sha256:...
    signature_gate_status: SIGNATURE_GATE_ACCEPTED
    signed_receipt_chain_terminal_hash: sha256:... | null
    reddog_work_order_receipt_digest: sha256:...
    invocation_receipt_digest: sha256:...
    executor_plan_id: sha256:...
    valve_decision_digest: sha256:...
  target:
    kind: foundup_job | autonomous_task
    proposed_target_id: string
  live_enqueue_performed: false              # contract slice invariant
  no_enqueue_performed: true                 # until implementation slice + valve OPEN
  no_execution_performed: true
  contract_receipt_digest: sha256:...

RedDogOpenClawLiveEnqueueReceipt:            # future IMPLEMENTATION slice only
  live_enqueue_id: string
  contract_receipt_digest: sha256:...
  openclaw_queue_item_id: string | null
  agentdb_task_id: string | null
  openclaw_action_ledger_ref: string | null
  no_execution_performed: true               # until Hermes/WRE downstream
  live_enqueue_receipt_digest: sha256:...
```

Downstream (future, not this contract):
- OpenClaw action ledger entry
- Hermes delegation receipt
- WRE proof-of-compute receipt

Reconciliation rule: every live enqueue id MUST link back to `adapter_dryrun_receipt_digest` +
`work_order_id` + `policy_gate_receipt_digest`.

---

## 5. Fail-closed rejection rules

| Code | Condition |
|------|-----------|
| E1 | Valve not `VALVE_OPEN_LIVE_ENQUEUE` (includes dry-run-only or closed) |
| E2 | Missing or rejected `AdapterDryRunReceipt` |
| E3 | `ProposedOpenClawIntakeRecord.no_enqueue_performed != true` on input |
| E4 | Missing / mismatched receipt digest in chain |
| E5 | Stale permission snapshot (TTL exceeded at enqueue time) |
| E6 | Path-scope mismatch between proposed intake and work order / executor plan |
| E7 | Target is `AssignmentDispatcher` or non-canonical |
| E8 | Replay: `work_order_id` + `nonce` already live-enqueued (idempotency violation) |
| E9 | `INDEX_GAP` on write-sensitive operation without sovereign override |
| E10 | `permission_truth_label == NEEDS_VERIFICATION` for write-sensitive enqueue |
| E11 | Worktree-create valve presented as enqueue authority |
| E12 | Missing sovereign live-enqueue token (future implementation) |
| E13 | `signature_gate_status != SIGNATURE_GATE_ACCEPTED` |
| E14 | Signed receipt chain rejected, malformed, unsigned, or reward-account mismatched |

---

## 6. Output contract (this slice)

This slice defines the **contract receipt shape only**:

### `RedDogOpenClawLiveEnqueueContractReceipt`

| Field | Value in contract slice |
|-------|-------------------------|
| `contract_receipt_id` | Deterministic id (future implementation) |
| `contract_receipt_digest` | sha256 canonical body |
| `decision` | `LIVE_ENQUEUE_CONTRACT_SPECIFIED` |
| `live_enqueue_performed` | **false** |
| `no_enqueue_performed` | **true** |
| `no_execution_performed` | **true** |
| `implementation_status` | **SPECIFIED_NOT_IMPLEMENTED** |

No runtime module emits this receipt in **this** slice.

---

## 7. Gate ordering (updated spine)

```text
1. RedDog advisory (extension) -- no execution
2. #890 dry-run validation
3. #892 permission snapshot
4. #893 policy gate
5. #950 signed work-authority binding -- SIGNATURE_GATE_ACCEPTED required for live enqueue
6. #894 receipt
7. #951 signed receipt-chain verification -- unsigned receipts are not reward-bearing
8. #896 invocation dry-run
9. #898 executor plan dry-run
10. #903 execution valve -- VALVE_OPEN_DRYRUN_ONLY for adapter dry-run
11. #904 adapter dry-run -- propose intake + AdapterDryRunReceipt
12. THIS CONTRACT -- live enqueue rules (no runtime)
13. Future: VALVE_OPEN_LIVE_ENQUEUE + REDDOG_OPENCLAW_LIVE_ENQUEUE_PHASE1 implementation
14. Future: Hermes / WRE execution (separate valves)
15. Future: worktree create -- VALVE_OPEN_WORKTREE_CREATE only
```

**No step skipping.** Step 13 MUST NOT run before step 11 accept + explicit live enqueue valve.

---

## WSP_97 truth table

| # | Claim | Label |
|---|-------|-------|
| 1 | This doc is contract-only; no runtime enqueue module | **OBSERVED** |
| 2 | Dry-run valve alone is insufficient for live enqueue | **OBSERVED** |
| 3 | Worktree-create valve is not enqueue authority | **OBSERVED** |
| 4 | FoundUpJob / autonomous_task are canonical live targets | **OBSERVED** |
| 5 | AssignmentDispatcher is forbidden | **OBSERVED** |
| 6 | Live enqueue implementation is future slice | **SPECIFIED_NOT_IMPLEMENTED** |
| 7 | `RedDogOpenClawLiveEnqueueContractReceipt` runtime emission is future | **SPECIFIED_NOT_IMPLEMENTED** |
| 8 | #904 propose-only boundary preserved | **OBSERVED** |

---

## WSP_15 -- Next implementation slices (ordered)

| Order | Slice | Type | Depends on |
|-------|-------|------|------------|
| 1 | `REDDOG_OPENCLAW_LIVE_ENQUEUE_VALVE_PHASE1` | Module | This contract + #903 valve |
| 2 | `REDDOG_OPENCLAW_LIVE_ENQUEUE_PHASE1` | Module | Live enqueue valve OPEN + #904 accept |
| 3 | `REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1` | Module | Worktree valve OPEN (separate) |
| 4 | `REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_POC_PHASE1` | Module | Live enqueue receipt chain |

**Do not skip:** live enqueue valve before first queue append; never bind to AssignmentDispatcher.

---

## Explicit non-goals

| Non-goal | Status |
|----------|--------|
| Live OpenClaw Supervisor enqueue | **FORBIDDEN** in this slice |
| AgentDB writes | **FORBIDDEN** in this slice |
| FoundUpJob queue append | **FORBIDDEN** in this slice |
| Hermes / WRE execute | **FORBIDDEN** in this slice |
| Branch/worktree/PR/merge | **FORBIDDEN** |
| Extension runtime wiring | **SPECIFIED_NOT_IMPLEMENTED** |
| Runtime contract receipt module | **SPECIFIED_NOT_IMPLEMENTED** |

---

## ModLog pointer

See `extensions/foundups_advisory_workers/ModLog.md` and `modules/communication/moltbot_bridge/ModLog.md`.

**Slice author:** 0102 worker lane  
**No runtime mutation performed in authoring this document.**
