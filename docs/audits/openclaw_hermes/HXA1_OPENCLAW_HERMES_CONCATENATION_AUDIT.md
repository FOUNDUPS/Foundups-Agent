# HXA1 — OpenClaw → Hermes Concatenation Audit (Phase 1)

**Slice**: `HXA1_OPENCLAW_HERMES_CONCATENATION_AUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-07
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_50 → WSP_97

---

## HoloIndex Research

```bash
python holo_index.py --search "OpenClaw FoundUpJob WRE Hermes execute_foundup_job dry_run blocked real delegation" --limit 5
```

**Top hit (WSP)**: `WSP_framework/src/WSP_106_FoundUp_API_Gateway_Protocol.md`
**Top hit (DOCS)**: `docs/0102_session_briefings/DD_HERMES_FOUNDUP_BUILDER_OPERATIONAL_PROOF_PHASE1.md`

Confirmed prior architectural framing: Hermes builder is operational at the adapter layer (`modules/foundups/agent/src/hermes_adapter.py`), but the WRE-mediated path uses a separate dry-run-only seam.

---

## 1. Canonical Runtime Path (Observed)

**Truth boundary**: The runtime path stops at the queue. It does NOT execute Hermes today.

```
Intent (chat or "follow WSP") → OpenClaw → FoundUpJob (QUEUED) → _FOUNDUP_JOB_QUEUE
                                                                  ↓
                                                                  ⊥ (no production drainer)
```

| Step | File:Line | Behavior |
|------|-----------|----------|
| 1. Plan dispatch | `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py:44-45` | route="fam_adapter" → `execute_foundup(dae, intent)` |
| 2. FoundUp routing | `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py:672-699` | Imports `openclaw_foundup_orchestrator.dispatch_foundup` |
| 3. Build intent detect | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:777` | `_is_explicit_build_intent()` checks trigger phrases |
| 4. Job creation | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:811-894` | `_handle_build_intent` calls `create_job()` and appends to queue |
| 5. Dry-run flag | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:851-865` | `_detect_dry_run_mode()` sets `policy_flags.dry_run_mode` |
| 6. Queue append | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:873` | `_FOUNDUP_JOB_QUEUE.append(job)` — in-memory list |
| 7. Response | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:884-894` | Returns confirmation string. **End of runtime path.** |

**Hypothetical continuation (only triggered by tests today):**

| Step | File:Line | Behavior |
|------|-----------|----------|
| 8. Drain | `modules/infrastructure/wre_core/src/foundup_job_consumer.py:647-664` | `drain_openclaw_queue_once()` — only invoked from tests |
| 9. Route | `modules/infrastructure/wre_core/src/foundup_job_router.py:201-353` | `route_foundup_job(job)` → `RouteEnvelope` |
| 10. Hermes dispatch | `modules/infrastructure/wre_core/src/foundup_job_consumer.py:405-504` | `_dispatch_to_hermes()` imports WRE executor |
| 11. Execute (WRE) | `modules/infrastructure/wre_core/src/hermes_job_executor.py:912-918` | `execute_foundup_job(job)` — singleton, dry_run=True |
| 12. Always SIMULATED | `modules/infrastructure/wre_core/src/hermes_job_executor.py:707-726` | Returns `HermesDelegationResult(status=SIMULATED)` because `HERMES_DELEGATE_ENABLED=0` is default |
| 13. Receipt skipped | `modules/infrastructure/wre_core/src/foundup_job_consumer.py:614-626` | SIMULATED + `!real_execution_performed` → return None (no receipt) |
| 14. Job retained | `modules/infrastructure/wre_core/src/foundup_job_consumer.py:736-743` | `should_clear=False` (no receipt) → job retained with reason `dry_run_evidence_only` |

**Observation**: Evidence-only files (`.hermes_evidence/{job_id}/metadata.json`, `checkpoint.json`) are written by `_write_evidence` (`hermes_job_executor.py:807-886`), but no receipt is emitted and `job.status` remains `QUEUED` throughout — never mutates to RUNNING/SUCCEEDED/FAILED.

---

## 2. Duplicate / Divergent Execution Paths

**Two distinct `execute_foundup_job` symbols exist, with different signatures and different return types.**

| # | Module | Signature | Returns | Mutates job.status? | Real Hermes call? |
|---|--------|-----------|---------|---------------------|-------------------|
| A | `modules.infrastructure.wre_core.src.hermes_job_executor` | `execute_foundup_job(job) -> HermesDelegationResult` (line 912) | `HermesDelegationResult` (status enum) | **No** — never touches job state | No (always SIMULATED in Phase 1) |
| B | `modules.foundups.agent.src.hermes_foundup_job_executor` | `execute_foundup_job(job, repo_root=None, force_dry_run=False) -> HermesJobExecutionResult` (line 76) | `HermesJobExecutionResult` (job + hermes_result) | **Yes** — calls `job.start()`, `job.succeed()`, `job.fail()`, `job.block()` | Yes — invokes `HermesFoundUpBuilder.extract_foundup` / `analyze_boundary` / `check_exfoliation_gate` |

### Callers

**A (WRE executor) is called by:**
- `modules/infrastructure/wre_core/src/foundup_job_consumer.py:425-439` (canonical consumer path)
- `modules/infrastructure/wre_core/tests/test_hermes_job_executor.py` (37 references)

**B (Hermes adapter executor) is called by:**
- `modules/communication/moltbot_bridge/tests/test_internal_voteballot_build_poc.py` (12 calls)
- `modules/communication/moltbot_bridge/tests/test_e2e_foundup_job_seam.py:171,250,346,406` (4 calls)
- **No production callers.**

### Classification

- **Canonical (consumer path)**: A (WRE executor). Used by `FoundUpJobConsumer._dispatch_to_hermes`.
- **Non-canonical (operational proof path)**: B (Hermes adapter executor). Tests prove `HermesFoundUpBuilder` works end-to-end, but the production path bypasses it.

**Split-brain**: A and B disagree on what "execute_foundup_job" means. A is a no-op simulation envelope; B is a real builder invocation that mutates job state. Neither is wired into runtime — but if runtime were wired, it would call A and miss the actual builder.

---

## 3. Gate Reality Matrix

| Gate | Implementation | Trigger Source | Fail Mode | Evidence Location |
|------|----------------|----------------|-----------|-------------------|
| **Delegation enable flag** (`HERMES_DELEGATE_ENABLED`) | Implemented (env-driven) | Env var read at `is_hermes_delegation_enabled()` | Default `0` → all jobs return SIMULATED status | `modules/infrastructure/wre_core/src/hermes_job_executor.py:60-66, 707-726` |
| **dry_run source of truth** | **Fragmented across 4 sources** | (1) message patterns, (2) policy flag, (3) executor constructor, (4) `force_dry_run` param | Sources do not propagate to each other | See drift finding #2 below |
| **Security gate** (`policy_flags.security_gate_*`) | Stub — checked but never set | Router checks `security_gate_checked && !security_gate_passed` to BLOCK | Nothing in runtime ever sets `security_gate_checked=True` | `modules/infrastructure/wre_core/src/foundup_job_router.py:285-295` (check); no setter in production code |
| **Import gate** (Hermes delegate_task lazy import) | Implemented | `_lazy_import_delegate_task()` invoked when `dry_run=False` and feature enabled | Returns `BLOCKED_IMPORT_UNAVAILABLE` if `vendor.hermes_agent.tools.delegate_tool` missing | `modules/infrastructure/wre_core/src/hermes_job_executor.py:514-545, 750-763` |
| **Receipt emission** | Implemented but **unreachable in canonical path** | `_emit_receipt_for_hermes_result` after dispatch | SIMULATED + `!real_execution_performed` → returns None (skip emission); otherwise delegates to `_emit_receipt_if_terminal` which requires `job.status` ∈ {succeeded, failed, blocked} — but WRE executor never mutates job.status | `modules/infrastructure/wre_core/src/foundup_job_consumer.py:506-629` |
| **Verification transition** (`job.status` mutation) | Stub in canonical path | Only path B (Hermes adapter `_apply_hermes_result_to_job`) mutates status | Canonical (path A) never transitions `QUEUED → RUNNING → SUCCEEDED`, so receipts can't fire | `modules/foundups/agent/src/hermes_foundup_job_executor.py:307-409` (real); WRE path leaves status=QUEUED |
| **Genesis Validation Gate** | Implemented but **not wired into dispatch** | `OpenClawFoundUpOrchestrator.validate_genesis_envelope()` | Existing, but `dispatch_foundup` and `_handle_build_intent` never call it | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:359-468`. Production callers: **0**. Test callers: 5 in `test_openclaw_foundup_orchestrator.py` |
| **Action support** (`SUPPORTED_ACTIONS` vs router map) | Two divergent sets | Hermes adapter uses frozenset of 3; router maps 4 actions | `queue_foundup_job` is routable to OPENCLAW_QUEUE but is not in `SUPPORTED_ACTIONS` for the Hermes adapter executor | Router: `modules/infrastructure/wre_core/src/foundup_job_router.py:85-90`; adapter: `modules/foundups/agent/src/hermes_foundup_job_executor.py:53-57` |

---

## 4. Truth Drift Findings

### F-1 (Critical) — Runtime path is not concatenated end-to-end

- **Claim** (per consumer/router/executor docstrings): OpenClaw → FoundUpJob → WRE Router → Consumer → Hermes is the canonical pipeline.
- **Reality**: `_handle_build_intent` appends to `_FOUNDUP_JOB_QUEUE` and returns. **No production code drains the queue.** The consumer is invoked only from tests.
- **Evidence**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:873` (queue append, runtime endpoint). Grep for `FoundUpJobConsumer|drain_openclaw_queue` outside `tests/`: zero non-test, non-source matches. Root ROADMAP confirms this gap: `ROADMAP.md:199` — *"Next priority: WRE_HERMES_EXECUTOR_CONSUMER_BINDING_DRY_RUN_PHASE1 — Wire executor into FoundUpJobConsumer drain loop"*.
- **Operational risk**: Any "OC → Hermes built" claim today is false. Jobs accumulate in memory and disappear on process restart.

### F-2 (Critical) — Two `execute_foundup_job` implementations with split-brain semantics

- **Claim**: There is one canonical execute_foundup_job seam.
- **Reality**: Two functions with the same name, divergent signatures, divergent behavior.
  - WRE (`modules/infrastructure/wre_core/src/hermes_job_executor.py:912`) — `(job)` → `HermesDelegationResult`. Returns SIMULATED unless `HERMES_DELEGATE_ENABLED=1` AND `dry_run=False`. Even then, returns `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (line 770-784). Never mutates job.
  - Hermes adapter (`modules/foundups/agent/src/hermes_foundup_job_executor.py:76`) — `(job, repo_root, force_dry_run)` → `HermesJobExecutionResult`. Calls `HermesFoundUpBuilder.extract_foundup`/`analyze_boundary`/`check_exfoliation_gate`. Mutates `job.status` via `start/succeed/fail/block`.
- **Evidence**: See section 2 callers table.
- **Operational risk**: When wiring is added, an integrator could pick either function and get wildly different behavior. Function A (chosen by current consumer) yields no real work; function B yields real work but is not WRE-mediated and bypasses the router/envelope.

### F-3 (Critical) — Genesis Validation Gate is implemented but unwired

- **Claim** (per orchestrator docstring at lines 286-304): `OpenClawFoundUpOrchestrator` "enforces that all FoundUp operations pass through genesis envelope validation first."
- **Reality**: `dispatch_foundup` (line 757) and `_handle_build_intent` (line 811) do not call `validate_genesis_envelope`, `launch_foundup`, or `build_foundup`. Jobs are created and queued without envelope validation.
- **Evidence**: Grep for `validate_genesis_envelope|orchestrator.build_foundup\(|orchestrator.launch_foundup\(` in non-test production code: 0 hits in `dispatch_foundup` callgraph. Only test files invoke it.
- **Operational risk**: WSP 97 truthfulness violation — genesis gate is documented as enforced, but is bypassed. Any job action (build_foundup, extract_foundup) would proceed without lifecycle/binding-state/acceptance-criteria checks if wiring is added without also wiring the gate.

### F-4 (High) — `dry_run` has four uncoordinated sources of truth

- **Sources**:
  1. `policy_flags.dry_run_mode` set by `_detect_dry_run_mode` from message patterns (`openclaw_foundup_orchestrator.py:91-125, 851-865`).
  2. `HermesJobExecutor.dry_run` constructor parameter, default `True` (`hermes_job_executor.py:474-490`).
  3. `HERMES_DELEGATE_ENABLED` env flag (separate from dry_run, but functionally equivalent — disables real execution) (`hermes_job_executor.py:60-66`).
  4. `force_dry_run` parameter on path B's `execute_foundup_job` (`hermes_foundup_job_executor.py:79`), and `HermesFoundUpBuilder.dry_run` attribute (path B mutates it directly at line 187).
- **Drift**: The consumer creates `FoundUpJobConsumer(dry_run=True)` (`foundup_job_consumer.py:342-349`) but **does not pass dry_run into the WRE `execute_foundup_job(job)` call** (`foundup_job_consumer.py:439`). The comment at line 437 admits: *"WRE executor respects dry_run via constructor, not per-call param"* — but the consumer never constructs the executor; it uses the singleton from `get_executor()` which defaults to `dry_run=True` regardless of consumer's flag.
- **Operational risk**: Setting `policy_flags.dry_run_mode=False` on a job has no effect on WRE path execution. The job's policy snapshot lies about the mode that was actually used.

### F-5 (High) — Receipts cannot be emitted in the canonical path

- **Claim** (consumer docstring line 110-135): "ConsumerResult contains the complete closed-loop evidence chain" including receipt and pAVS verification.
- **Reality**:
  - `_emit_receipt_for_hermes_result` at line 614-626 returns None for SIMULATED status with `!real_execution_performed`.
  - Phase 1 always returns SIMULATED with `real_execution_performed=False` (`hermes_job_executor.py:712-746`).
  - Therefore the canonical consumer path **never** emits a `ProofOfComputeReceipt`.
  - Even bypassing the SIMULATED skip, `_emit_receipt_if_terminal` (line 506-569) requires `job.status.value ∈ {succeeded, failed, blocked}`, but WRE executor never mutates job.status.
- **Evidence**: `proof_of_compute_receipt.py` `create_receipt`/`create_receipt_from_job` callers in non-test code: 0 (only `tests/test_proof_of_compute_receipt.py`).
- **Operational risk**: Any downstream consumer expecting a receipt artifact (pAVS, CABR) will see nothing in the canonical path. Evidence is captured as `.hermes_evidence/{job_id}/` files only, not as typed `ProofOfComputeReceipt` records.

### F-6 (High) — `HermesJobExecutionResult` shape mismatch with `HermesDelegationResult`

- **Claim**: Consumer's terminal-detection logic (`is_terminal` property, line 214-246) handles "WRE executor" and "legacy executor" alike.
- **Reality**: The two result types have completely different shapes.
  - `HermesDelegationResult` (path A): exposes `.status` (HermesExecutionStatus enum), `.checkpoint_state`, `.evidence_path`, `.real_execution_performed`.
  - `HermesJobExecutionResult` (path B): exposes `.job` (FoundUpJob), `.hermes_result` (dict), `.error` (str). No `.status` attr; status lives on `result.job.status`.
- **Evidence**: `hermes_job_executor.py:348-441` (DelegationResult fields) vs. `hermes_foundup_job_executor.py:60-73` (`__slots__` of JobExecutionResult).
- **Operational risk**: The consumer's "legacy support" branch at lines 240-246 would crash if path B's result were ever passed in (it tries `result.job.status` but B has it on `result.job` — actually that does work, but `getattr(hermes_result, "status", None)` at line 232 would return None for path B, falling through to the legacy branch). The split is brittle and undocumented.

### F-7 (Medium) — `job.status` never mutates in the canonical (WRE) path

- **Claim**: FoundUpJob lifecycle is `QUEUED → RUNNING → SUCCEEDED|FAILED|BLOCKED` (contract docstring line 86-104).
- **Reality**: In the canonical consumer path, no code calls `job.start()`, `job.succeed()`, `job.fail()`, or `job.block()`. The job sits at `QUEUED` permanently. Only path B (the unwired Hermes adapter executor) actually drives transitions.
- **Evidence**: `foundup_job_consumer.py` and `hermes_job_executor.py` (WRE) — grep for `job.start|job.succeed|job.fail|job.block`: 0 matches. Path B: 4 matches at `hermes_foundup_job_executor.py:170, 353, 365, 376, 404`.
- **Operational risk**: Routing terminal-status check (`router.py:256-273`) is correct for re-routing protection, but every job re-routes endlessly because none ever reach SUCCEEDED/FAILED via the WRE path. Receipt emission gate (which requires terminal status) is permanently locked off.

### F-8 (Medium) — `SUPPORTED_ACTIONS` (Hermes adapter) and `_ACTION_BACKEND_MAP` (router) disagree

- **Reality**: Router maps 4 actions; adapter executor only supports 3.
  - Router (`foundup_job_router.py:85-90`): `build_foundup`, `extract_foundup`, `validate_foundup`, `queue_foundup_job` (4)
  - Adapter executor (`hermes_foundup_job_executor.py:53-57`): `build_foundup`, `extract_foundup`, `validate_foundup` (3, no `queue_foundup_job`)
- **Operational risk**: If path B were ever wired in for `queue_foundup_job`, it would `FAIL` with `FAIL_VALIDATION_ERROR` (line 144-147). Currently moot (path B is unwired) but a foot-gun for live-flip work.

### F-9 (Low) — Logger name leakage

- `openclaw_execution_routes.py:22` declares `logger = logging.getLogger("openclaw_dae")` — but the file is `openclaw_execution_routes`. All log emissions from this module appear under the wrong logger name, complicating log routing and audit attribution.
- **Operational risk**: Cosmetic only, but obscures truthful attribution if log filters are scoped by logger name.

---

## 5. Concatenation Decision

### **NOT_CONCATENATED**

The runtime path stops at `_FOUNDUP_JOB_QUEUE.append(job)`. There is no production drainer. Even if the consumer were invoked manually, the canonical path:

- Calls a WRE `execute_foundup_job` that always returns SIMULATED.
- Never mutates `job.status`.
- Never emits a receipt.
- Bypasses the genesis validation gate.
- Bypasses the actual `HermesFoundUpBuilder` (the only code that does real Hermes work).

The architecture **has** the seams (router, consumer, two executors, receipt module, genesis gate). They are not wired into a continuous path. Live-flip work would currently flip a no-op.

---

## 6. Minimal Remediation Plan (No Code)

Six atomic slices, ordered. **Slice 1 is the trunk blocker.**

### Slice 1 (Trunk) — `OPENCLAW_QUEUE_DRAIN_BINDING_PHASE1`

- **Objective**: Wire `FoundUpJobConsumer.drain_openclaw_queue_with_retention()` into a production caller (cron tick, OpenClaw post-handler, or explicit `/openclaw drain` command). No execution behavior change beyond making the existing dry-run path reachable from runtime.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` (or a new sibling drain entrypoint), one wiring point in OpenClaw DAE post-action, plus a new test that asserts a dry-run drain runs against a queued job without flag changes.
- **Acceptance**: Submitting a `start build gotjunk --dry-run` intent, then triggering the drain, produces a `ConsumerResult` with `route_status=ROUTED`, `target_backend=hermes_builder`, `checkpoint_state=SIMULATED`, evidence files written under `.hermes_evidence/{job_id}/`, and the queue retention metadata reports `dry_run_evidence_only`.

### Slice 2 — `HERMES_EXECUTOR_RECONCILIATION_PHASE1`

- **Objective**: Resolve the two-`execute_foundup_job` split-brain. Either (a) make the WRE executor delegate to the Hermes adapter executor when `HERMES_DELEGATE_ENABLED=1` and `dry_run=False`, or (b) deprecate the Hermes adapter executor symbol and move its builder-invocation logic behind the WRE executor's "real execution" branch (currently `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` at `hermes_job_executor.py:770-784`).
- **Files**: `modules/infrastructure/wre_core/src/hermes_job_executor.py`, `modules/foundups/agent/src/hermes_foundup_job_executor.py`, plus migration of the test surface from B → A or vice versa.
- **Acceptance**: Exactly one production caller of `execute_foundup_job`. Test suites in `tests/test_internal_voteballot_build_poc.py` and `tests/test_e2e_foundup_job_seam.py` migrated to the chosen executor without behavior regression.

### Slice 3 — `DRY_RUN_SINGLE_SOURCE_OF_TRUTH_PHASE1`

- **Objective**: Make `policy_flags.dry_run_mode` the single source of truth. The consumer should construct the WRE executor with `dry_run=job.policy_flags.dry_run_mode` per call (or the WRE executor should read it from the job directly).
- **Files**: `modules/infrastructure/wre_core/src/foundup_job_consumer.py:432-439`, `modules/infrastructure/wre_core/src/hermes_job_executor.py:673-748`.
- **Acceptance**: Setting `policy_flags.dry_run_mode=False` on a queued job and draining produces a non-SIMULATED outcome (BLOCKED_FEATURE_DISABLED if flag off; BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED if flag on but execution not yet implemented), not silently SIMULATED.

### Slice 4 — `GENESIS_GATE_DISPATCH_BINDING_PHASE1`

- **Objective**: Insert `validate_genesis_envelope` (or `OpenClawFoundUpOrchestrator.build_foundup`) into `_handle_build_intent` so that build/extract intents fail-closed without a valid envelope. Phase-gated: log-only first, hard-block second.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:811-894` (insert gate call before `create_job`), plus regression tests proving build intents without envelope produce `BLOCKED` reason codes.
- **Acceptance**: A "start build gotjunk" intent without a genesis envelope returns `BLOCKED` with `GenesisGateReason.NO_ENVELOPE` (or chosen reason); with a valid envelope, the job is created and queued as before.

### Slice 5 — `JOB_STATUS_TRANSITION_BINDING_PHASE1`

- **Objective**: Make the WRE consumer drive `job.status` transitions (`start` on dispatch, `succeed`/`fail`/`block` on terminal) so receipt emission can fire when path B (or its successor) is wired.
- **Files**: `modules/infrastructure/wre_core/src/foundup_job_consumer.py:405-504`.
- **Acceptance**: After a SIMULATED dispatch, `job.status == BLOCKED` (or remains QUEUED with explicit policy reason); after EXECUTED, `job.status == SUCCEEDED`. Existing receipt-emission gate at line 614-626 unchanged.

### Slice 6 — `ACTION_CONTRACT_RECONCILIATION_PHASE1`

- **Objective**: Align `SUPPORTED_ACTIONS` (executor) with `_ACTION_BACKEND_MAP` (router) and `CANONICAL_ACTIONS` (contract). Decide whether `queue_foundup_job` is a Hermes-adapter action or a WRE-internal-only action.
- **Files**: `modules/foundups/agent/src/hermes_foundup_job_executor.py:53-57`, `modules/infrastructure/wre_core/src/foundup_job_router.py:85-90`, `modules/communication/moltbot_bridge/src/foundup_job_contract.py:54-59`.
- **Acceptance**: One frozenset of canonical actions, referenced by all three modules.

---

## Acceptance Criteria Verification

- ✓ No speculative architecture claims — every finding tied to file:line.
- ✓ All findings tied to concrete code references.
- ✓ Canonical execution path unambiguous (section 1).
- ✓ Split-brain risk explicitly identified (F-2) and remediation chosen (Slice 2).
- ✓ Clear go/no-go for live execution: **NO-GO**. Slice 1 is the trunk blocker.

---

## WSP 97 Applied

WSP_50 verification: every required file was read in full before findings. WSP_97 truth boundaries: this report distinguishes implemented seams from claimed-but-unwired behavior. WSP_00: identity-locked as W1 for HXA1 throughout.

---

## Files Touched This Slice

- `docs/audits/openclaw_hermes/HXA1_OPENCLAW_HERMES_CONCATENATION_AUDIT.md` (NEW)

No runtime code edits. No commits made (per W10 commit-lane discipline).
