# Agent Module TestModLog

## 2026-06-09 - FoundUp Manifest Validator Module Path Exact-Match Hardening Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_foundup_manifest_validator.py -q
```

**Result**: PASS

**Summary**: 88 passed in 0.28s.

**Slice**: FOUNDUP_MANIFEST_VALIDATOR_MODULE_PATH_EXACT_MATCH_HARDENING_PHASE1

**Added**:
- `TestExactMatchHelperDirect`: 8 direct unit tests on the
  `_expected_module_path_matches` helper and the two new canonicalize
  helpers. Pin the trust boundary mechanically -- not only through the
  full validator surface.
- `TestSuffixCollisionRejected`: 6 explicit suffix-collision cases that
  must fail under exact-only matching, including the shadow-prefix
  collision and the cross-domain `whack_a_magat` example from the W6
  dispatch.
- `TestCanonicalPathNormalization`: 16 parametrized variants split into
  accept (harmless: `./`, `//`, `.` segment, backslashes, trailing `/`)
  and reject (absolute drive, leading `/`, UNC, `..` traversal anywhere
  in the path, shadow directory, extra suffix segment).
- `TestOldSuffixBehaviorRegression`: 3 tests that compute the OLD
  suffix-fallback locally inside the test, assert it would have accepted
  the input, and assert the NEW exact-only helper rejects it. Pins the
  regression mechanically so any future loosening fails.

**Boundary preserved**:
- `test_validator_imports_no_runtime_executors` still passes (no
  hermes / openclaw / ai_overseer / job_consumer / wre_core imports).
- `test_validator_no_exec_process_network_or_write` still passes
  (no subprocess / socket / urllib / open / Popen / write / etc.).
- Negative controls (shell strings, shell metacharacters, gate-bypass
  flag, missing required gates, external_agent_allowed=true,
  build_ready=true, autonomous_execution_ready=true, manifest_ready=true
  without promotion) all still trigger rejection.

**No skip / xfail on any security assertion.**

---

## 2026-06-08 - FoundUp Manifest Validator Tests (FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_foundup_manifest_validator.py -q
```

**Result**: PASS

**Summary**: 51 passed in 0.28s.

**Coverage**:
1. All 6 updated manifests validate (positive, parametrized).
2. foundup_id matches build_contract.foundup_id (real manifests + mismatch negative).
3. forbidden_paths cover .env / main.py / *_dae.py / vendor (all 6).
4. Negative: reject unknown executor.
5. Negative: reject privileged + self-authorizing executor config.
6. Negative: reject missing required gate (genesis_gate).
7. Negative: reject dry_run.default=false.
8. Negative: reject external_agent_allowed=true.
9. Negative: reject build_ready=true.
10. Negative: reject autonomous_execution_ready=true.
11. Negative: reject manifest_ready=true without promotion.
12. Negative: reject shell-string command for build/test/dry_run.
13. Negative: reject shell metacharacters in argv (4 injection shapes).
14. Negative: reject truthy gate-bypass flag.
15. execution_routing declarative-only (all 6).
16. voteballots/trade flagged NEEDS_LABEL_RECONCILIATION (and not build-trusted).
17. Validator source imports no Hermes/OpenClaw/WRE consumer/AI Overseer runtime (AST).
18. Validator source makes no exec/process/network/file-write calls (AST).
19. Validation is pure (does not mutate input; repeatable).

**Cross-checked existing tests (still pass after manifest edits)**:

```bash
python -m pytest modules/foundups/gotjunk/tests/test_manifest.py -q              # 12 passed
python -m pytest modules/foundups/kosei/tests/test_manifest_contract.py -q       # 7 passed
python -m pytest modules/foundups/trade/tests/test_manifest_contract.py -q       # 15 passed
python -m pytest modules/foundups/voteballots/tests/test_shell_integration.py -q # 62 passed
python -m pytest modules/foundups/agent/tests/ -q                                # 330 passed
```

Note: cross-module collection of two same-named `tests` packages in ONE pytest
invocation collides (pre-existing layout); run per-file as above.

## 2026-05-01 - Worker Queue Observability Tests (OC20)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_queue_observability.py -q
```

**Result**: PASS

**Summary**: 28 passed in 1.04s.

**Coverage**:
1. emit_event stores append-only event
2. emit_heartbeat creates heartbeat event with consecutive tracking
3. emit_lease_expired creates lease expiry signal
4. worker availability/unavailability events are recorded
5. snapshot_queue_health reports queued/processing/completed/expired counts
6. get_events filters by worker_id
7. event fields preserve evidence_refs
8. all observability is in-memory only
9. no real worker/process fields imply execution
10. no CABR/reward/payout/token fields exist

**Notes**:
- Implements WSP 91 (DAEMON Observability Protocol) Pillar 1 (Logs) and partial Pillar 3 (Metrics)
- All 32 agent queue tests still passing (no regressions)
- All 33 VoteBallot PoC tests still passing (no regressions)

**WSP References**: WSP 11, WSP 50, WSP 91, WSP 97.

---

## 2026-04-30 - Full VoteBallot Dispatch PoC Integration (OC19)

**Command**:

```bash
python -m pytest modules/communication/moltbot_bridge/tests/test_internal_voteballot_build_poc.py -q
```

**Result**: PASS

**Summary**: 33 passed in 0.98s.

**Coverage** (TestVoteBallotFullDispatchPoC - 5 new tests):
1. test_full_voteballot_dispatch_pipeline_single_worker - proves Job->BuildPlan->Swarm->Queue->Dispatcher->Coordinator flow
2. test_full_voteballot_dispatch_pipeline_multiple_workers - proves multi-worker capability routing
3. test_full_dispatch_summary_preserves_wsp97_boundaries - proves all_simulated=True, no CABR/payout fields
4. test_full_dispatch_pipeline_preserves_job_plan_receipt_correlation - proves identity chain preserved
5. test_full_dispatch_pipeline_blocks_mismatched_worker - proves capability mismatch blocking

**Notes**:
- Integrates SwarmDispatchCoordinator with VoteBallot PoC
- Full simulated path: FoundUpJob -> BuildPlan -> SwarmCoordinator -> SwarmWorkerQueue -> AssignmentDispatcher -> SwarmDispatchCoordinator -> Evidence
- All 33 VoteBallot PoC tests passing (28 prior + 5 new)
- 57 agent module tests also passing (no regressions)

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Swarm Dispatch Integration Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_swarm_dispatch_integration.py -q
```

**Result**: PASS

**Summary**: 12 passed in 0.89s.

**Coverage**:
1. dispatch_next dequeues matching queue entry and dispatches simulated assignment
2. dispatch_next returns blocked/no-match for wrong capability
3. complete_dispatched_assignment records evidence in queue and dispatcher
4. run_simulated_cycle performs dequeue -> dispatch -> complete
5. multiple workers can process different assignments without file conflicts
6. summary reports all_simulated=True and real_execution_performed=False
7. VoteBallot swarm queue can run one simulated dispatch cycle

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC18)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_swarm_dispatch_integration.py modules/foundups/agent/tests/test_worker_assignment_protocol.py modules/foundups/agent/tests/test_build_plan_swarm_queue.py -q
```

**Result**: PASS

**Summary**: 57 passed.

**Notes**:
- All dispatch integration tests (12) passing
- All worker assignment protocol tests (25) still passing
- All queue tests (20) still passing
- No regressions

---

## 2026-04-30 - Worker Assignment Protocol Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_assignment_protocol.py -q
```

**Result**: PASS

**Summary**: 25 passed in 0.26s.

**Coverage**:
1. register_worker creates tracked worker process
2. register_worker records runtime type and capabilities
3. dispatch_assignment returns simulated/not-implemented status
4. dispatch_assignment does not start process
5. heartbeat updates worker last_seen
6. completion event records evidence_refs
7. deregistration changes status
8. no CABR/reward/payout/token fields exist
9. all WSP_97 truth fields remain false/simulated

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC17)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_assignment_protocol.py modules/foundups/agent/tests/test_build_plan_swarm_queue.py -q
```

**Result**: PASS

**Summary**: 45 passed.

**Notes**:
- All worker assignment protocol tests (25) passing
- All queue tests (20) still passing
- No regressions

---

## 2026-04-30 - BuildPlan Swarm WRE Queue Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm_queue.py -v
```

**Result**: PASS

**Summary**: 20 passed in 2.42s.

**Coverage**:
1. Create queue entry from StepAssignment
2. Dequeue matching worker capability succeeds
3. Dequeue mismatched worker capability is blocked
4. Heartbeat renews lease
5. Completion report marks entry complete with evidence
6. Expired entry can be requeued
7. Simulated completion cannot set real_execution_performed=True
8. Queue entry has no CABR/reward/payout/token fields
9. VoteBallot swarm assignment can be enqueued and dequeued by simulated worker

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC15)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm_queue.py modules/foundups/agent/tests/test_build_plan_swarm.py -q
```

**Result**: PASS

**Summary**: 54 passed.

**Notes**:
- All queue tests (20) passing
- All swarm coordination tests (34) still passing
- No regressions

---

## 2026-04-30 - BuildPlan Swarm Coordination Scaffold Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm.py -q
```

**Result**: PASS

**Summary**: 34 passed in 0.67s.

**Coverage**:
1. Register multiple workers
2. Assign different steps to different workers
3. Block duplicate file claims
4. Allow release then re-claim
5. Expire lease releases claim
6. Reject out-of-scope file claim
7. Aggregate evidence from multiple assignments
8. Summary reports simulated-only execution
9. No real_execution_performed can become true
10. VoteBallot BuildPlan can be split into multiple simulated assignments

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC13)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm.py modules/foundups/agent/tests/test_build_plan_executor.py modules/foundups/agent/tests/test_build_plan_generator.py -q
```

**Result**: PASS

**Summary**: 119 passed.

**Notes**:
- All swarm coordination tests (34) passing
- All executor tests (39 - from OC12) still passing  
- All generator tests (20 - from OC9) still passing
- No regressions

---

## 2026-04-29 - BuildPlanExecutor Interface Stub Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_executor.py -v
```

**Result**: PASS

**Summary**: 39 passed in 0.71s.

**Coverage**:
1. Executor instantiation with dry_run=True
2. validate_plan rejects mode=REAL without approval
3. simulate_step returns StepExecutionResult with SIMULATED
4. execute_step dry_run delegates to simulation
5. execute_step real returns BLOCKED
6. Mutating actions identified correctly
7. ExecutionReceipt WSP 97 truth fields all False
8. No CABR/reward/payout/token fields exist
9. VoteBallot generated BuildPlan validates and simulates

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-29 - Full Agent Module Test Suite

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/ -v
```

**Result**: PASS

**Summary**: 160 passed in 7.67s.

**Notes**:
- All BuildPlan pipeline tests (OC8/OC9/OC12) passing
- Hermes tests passing
- No regressions

---

## 2026-04-25 - Hermes Deploy Surface Detector Alignment

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_builder.py -q
```

**Result**: PASS

**Summary**: 18 passed in 7.29s.

**Notes**:
- Verified Hermes FoundUp Builder recognizes deploy evidence from direct deploy configs, `app/index.html`, `frontend/index.html`, and manifest `entry_url` with `launch_readiness=ready`.
- The first run failed 3 tests on deploy-surface recognition; `HermesFoundUpBuilder._detect_deploy_surface()` was added and the focused suite passed.

**WSP References**: WSP 34, WSP 50, WSP 60, WSP 83, WSP 97.
