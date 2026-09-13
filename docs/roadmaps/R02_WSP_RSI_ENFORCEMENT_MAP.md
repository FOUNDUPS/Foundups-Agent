# R02 — WSP requirements and RSI enforcement map

Source baseline: `35ed430c61e4e35c1b779f03c13e40368c82b65f` (main after PRs #1656 and #1702), reviewed 2026-09-13.

This is a derived evidence map for the [system roadmap](../../ROADMAP.md), covering its **26 existing packets**, not every clause of every WSP. WSPs remain normative; current source, tests and authenticated operational receipts establish implementation. This map cannot authorize a worker, change a budget, authenticate its own evaluation or certify production RSI.

**Verdict:** R01's local integrity repair is present. R02's requirement map and selected documentation contradictions are reconciled in this revision. The complete generic evaluator → promoter → activation/rollback → measured retained improvement chain remains unproved. R02 stays partial until historical ledger dispositions and independent review of the required path are complete.

## Evidence levels and use

- `HISTORICAL_OPERATION`: a real observation exists only for its recorded source/generation.
- `LOCAL_CONTRACT_VALIDATED`: named local tests establish a bounded behavior, not production deployment.
- `CONTRACT_AND_GAP`: source and test surfaces exist; the stated composition or operational receipt is still needed.
- `GENERIC_OWNER_MISSING` / `END_TO_END_PROOF_MISSING`: the current generic contract blocks the action, or the required composed proof has not been established. These labels do not claim that no useful specialized component exists elsewhere.
- `DOCUMENTED_PARTIAL` / `SPECIFICATION_AND_COMPONENTS`: planning or lower-level components are present; integrated behavior is not demonstrated.

The **test references below are inventory**, not assertions that every referenced test ran this session. The fresh selection is exactly 18 tests described in Validation. Reused September 9 audit findings are source-compared in the [evidence inventory](R02_WSP_RSI_ENFORCEMENT_EVIDENCE.json); changed documents retain explicit later evidence. No new live worker, evaluator, activation or settlement receipt was produced.

Normative source key: [WSP catalog](../../WSP_framework/src/WSP_MASTER_INDEX.md), [WSP 46](../../WSP_framework/src/WSP_46_Windsurf_Recursive_Engine_Protocol.md), [WSP 48](../../WSP_framework/src/WSP_48_Recursive_Self_Improvement_Protocol.md), [WSP 95](../../WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md), [WSP 97](../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md). Other numbered references resolve through the catalog. Draft WSP 96 is a design reference; its draft status does not confer enforceable authority. WSP 95 §3.1 supplies the seven production-promotion requirements: exact digests, independent held-out outcome evidence, regression/security evidence, runtime binding, authorized receipt, rollback, and immutable independent lineage. They map to R01/R04/R09–R14/R19 below.

## Gate coverage

| Gate | Requirement owners | Current missing proof |
|---|---|---|
| G0: reproducible baseline and ownership | R00–R05, R19 | General current-source Holo entry/closure, full R02 dispositions and required retrieval quality. |
| G1: one admitted real worker | R06–R08 | Exact current authority/runtime, one native leaf lifecycle and independently reproducible artifact. |
| G2: independent verification and evaluation | R09–R11, R14 | Authenticated producer/oracle invocation and retained evidence composed through the selected path. |
| G3: promotion, activation and rollback | R12–R13 | Concrete independent promoter and operational activation/rollback owner. |
| G4: measured retained improvement | R10–R15 | A better subsequent invocation under fixed correctness/regression criteria. |
| G5: sustained bounded operation | R16–R23 | Durable/concurrent/resource-bounded work with longitudinal operational evidence. |
| Rewarded teams and feedback | R24–R25 plus applicable gates | Independent audit, settled reward and active-participant V1 delivery; neither bypasses G0–G5. |

## Packet-by-packet map

### R00 — Holo owner

**Normative references:** WSP 50 / 87 / 97. **Evidence level:** `HISTORICAL_OPERATION`.

**Existing owner surfaces:** [reddog_holoindex_owner_query_once.py](../../scripts/reddog_holoindex_owner_query_once.py).

**Test references:** [test_reddog_holoindex_owner_query_root_binding.py](../../modules/communication/moltbot_bridge/tests/test_reddog_holoindex_owner_query_root_binding.py).

**Observed boundary:** Owner query separates committed semantic authority from workspace overlay. Historical maintenance completed at the audit source; a reference query passed again at published 78b79c36.

**Required next evidence:** New main/feature sources still need their own valid authority/generation. Do not reuse an old success as current-main closure.

### R01 — WRE Skillz admission

**Normative references:** WSP 71 / 95 / 97. **Evidence level:** `LOCAL_CONTRACT_VALIDATED`.

**Existing owner surfaces:** [skill_manifest_guard.py](../../modules/infrastructure/wre_core/src/skill_manifest_guard.py), [skill_runtime_admission.py](../../modules/infrastructure/wre_core/src/skill_runtime_admission.py), [wre_skills_loader.py](../../modules/infrastructure/wre_core/skillz/wre_skills_loader.py).

**Test references:** [test_skill_manifest_guard.py](../../modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py), [test_wre_skills_loader_hygiene.py](../../modules/infrastructure/wre_core/tests/test_wre_skills_loader_hygiene.py), [test_wre_runtime_admission_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_runtime_admission_truth.py).

**Observed boundary:** Registry/frontmatter, raw manifest hashes, paths and scanner policy are checked. PR #1702 repairs both inventories without changing Skillz instructions. Local tier: 235 passed, four platform skips.

**Required next evidence:** Unsigned digest inventories do not authenticate a signer or admit an installed production runtime. Recheck the deployed bytes, scanner and authority separately.

### R02 — WSP documentation owner

**Normative references:** WSP 22 / 46 / 50 / 70 / 81 / 95 / 97. **Evidence level:** `DOCUMENTED_PARTIAL`.

**Existing owner surfaces:** [WSP_46_Windsurf_Recursive_Engine_Protocol.md](../../WSP_framework/src/WSP_46_Windsurf_Recursive_Engine_Protocol.md), [WSP_CORE.md](../../WSP_framework/src/WSP_CORE.md), [ACTIVE_SLICE_LEDGER.md](../../docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md).

**Test references:** [test_wre_execution_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_execution_truth.py), [test_wre_telemetry_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_telemetry_truth.py).

**Observed boundary:** This map covers every R00–R25 requirement, with runtime gaps explicit. Current contract wording and historical entry points are reconciled; 18 existing boundary tests pass.

**Required next evidence:** April ledger entries still require individual owner dispositions; WSP 00 state semantics remains separately owned. This is not a complete audit of every clause in all 110 numbered protocol slots.

### R03 — Holo query/authority owner

**Normative references:** WSP 50 / 60 / 87 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [authority_worktree.py](../../holo_index/authority_worktree.py), [reddog_holoindex_owner_query_once.py](../../scripts/reddog_holoindex_owner_query_once.py).

**Test references:** [test_reddog_holoindex_owner_query_root_binding.py](../../modules/communication/moltbot_bridge/tests/test_reddog_holoindex_owner_query_root_binding.py).

**Observed boundary:** Canonical shared-checkout query rejects HEAD mismatch and labels its bundle as workspace_overlay. A matching clean reference returns CURRENT/no-gap; source and overlay are different evidence scopes.

**Required next evidence:** Qualify clean main, divergent feature, dirty overlay, stale authority, concurrent main advance and no-MCP entry paths. Reconcile old WSP 00 raw-query/reindex examples with the governed maintenance boundary.

Later R03 checkpoint (2026-09-13, source `773a29e70`): the [existing entry procedure](../../holo_index/CLI_REFERENCE.md#source-bound-owner-queries) reconciles bootstrap commands and documents the six-case matrix. All 81 existing entry/root tests pass and local bundle retrieval succeeds. The matched reference now fails owner startup; no new current-main semantic acceptance is claimed. These later observations do not change the pinned R02 source inventory or close R03.

### R04 — Holo runtime builder and independent producer

**Normative references:** WSP 12 / 71 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_holoindex_query_runtime_builder_runtime_composition.py](../../modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_runtime_composition.py).

**Test references:** [test_reddog_holoindex_query_runtime_builder_runtime_composition.py](../../modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_query_runtime_builder_runtime_composition.py).

**Observed boundary:** Runtime composition/binding contracts exist. The earlier audit records runtime_environment_exact_closure_verified=false; presence of these files is not a current positive receipt.

**Required next evidence:** Produce the selected exact-source positive closure and tamper/replaced-source negatives against real declared dependency/runtime bytes.

### R05 — Retrieval benchmark and independent corpus owner

**Normative references:** WSP 50 / 60 / 87 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [m2m_holo_retrieval_benchmark.py](../../modules/ai_intelligence/ai_overseer/src/m2m_holo_retrieval_benchmark.py).

**Test references:** [test_m2m_holo_retrieval_benchmark.py](../../modules/ai_intelligence/ai_overseer/tests/test_m2m_holo_retrieval_benchmark.py).

**Observed boundary:** Public retrieval benchmark implementation and tests are reuse surfaces. The session query is a discovery observation, not a benchmark or independently sealed evaluation.

**Required next evidence:** Bind independent corpus ownership, thresholds, collection coverage and real caller wiring. Evaluate historical noise and missing module artifacts before promoting retrieval quality.

### R06 — Signed work-order owner / WRE / AgentDB

**Normative references:** WSP 11 / 15 / 71 / 77 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [improvement_job_contract.py](../../modules/infrastructure/wre_core/src/improvement_job_contract.py), [reddog_work_order_signature_verifier.py](../../modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py).

**Test references:** [test_improvement_job_contract.py](../../modules/infrastructure/wre_core/tests/test_improvement_job_contract.py), [test_reddog_signed_worker_agentdb_admission.py](../../modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_admission.py).

**Observed boundary:** ImprovementJob has bounded scope and dry-run defaults; the signed-work verifier owns authentication. A roadmap JSON packet grants neither.

**Required next evidence:** Compile one selected packet with exact source, owner, tools, numeric limits, expiry and required receipts. Prove scope changes, stale source, replay and self-granted flags reject before dispatch.

### R07 — OpenClaw supervisor / native Hermes adapter

**Normative references:** WSP 71 / 73 / 77 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_hermes_api_confinement.py](../../modules/communication/moltbot_bridge/src/reddog_hermes_api_confinement.py), [reddog_hermes_api_run_lifecycle.py](../../modules/communication/moltbot_bridge/src/reddog_hermes_api_run_lifecycle.py).

**Test references:** [test_reddog_hermes_api_artifact_provider.py](../../modules/communication/moltbot_bridge/tests/test_reddog_hermes_api_artifact_provider.py).

**Observed boundary:** Native API confinement and child-lifecycle components are identified. Legacy HermesJobExecutor status is a separate surface and must not be used as an operational shortcut.

**Required next evidence:** Prove one real admitted leaf, provider/model agreement, allowed effects, cancellation/timeout and returned artifact bytes. No real leaf is dispatched by this governance slice.

### R08 — Confined artifact writer / verifier

**Normative references:** WSP 34 / 50 / 71 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_bounded_artifact_generation_runtime.py](../../modules/communication/moltbot_bridge/src/reddog_bounded_artifact_generation_runtime.py).

**Test references:** [test_reddog_bounded_artifact_generation_runtime.py](../../modules/communication/moltbot_bridge/tests/test_reddog_bounded_artifact_generation_runtime.py), [test_reddog_bounded_artifact_generation_authority.py](../../modules/communication/moltbot_bridge/tests/test_reddog_bounded_artifact_generation_authority.py).

**Observed boundary:** Bounded artifact-generation and authority tests provide reuse points. Their presence does not prove a complete worker-to-worktree write transaction.

**Required next evidence:** Exercise one disposable workspace and one allowed artifact; bind exact bytes and effect receipts; prove confinement, replay/idempotency and fresh independent reproduction.

### R09 — Independent verification owner

**Normative references:** WSP 5 / 6 / 71 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [wre_autonomous_slice_verifier_runtime.py](../../modules/infrastructure/wre_core/src/wre_autonomous_slice_verifier_runtime.py), [wre_independent_evidence_producer_runtime.py](../../modules/infrastructure/wre_core/src/wre_independent_evidence_producer_runtime.py).

**Test references:** [test_wre_autonomous_slice_verifier_runtime.py](../../modules/infrastructure/wre_core/tests/test_wre_autonomous_slice_verifier_runtime.py), [test_wre_independent_evidence_producer_runtime.py](../../modules/infrastructure/wre_core/tests/test_wre_independent_evidence_producer_runtime.py).

**Observed boundary:** The verifier consumes evidence and checks self-verification, source, scope, signatures and receipt lineage. Its return value does not itself run tests, publish, merge or settle rewards.

**Required next evidence:** Authenticate the independent producer invocation, required test selection and exact runtime. Rejection of author-forged or changed-source evidence must be shown in the selected real work path.

### R10 — Independent outcome evaluator

**Normative references:** WSP 48 / 91 / 95 / 97. **Evidence level:** `GENERIC_OWNER_MISSING`.

**Existing owner surfaces:** [wre_master_orchestrator.py](../../modules/infrastructure/wre_core/wre_master_orchestrator/src/wre_master_orchestrator.py), [local_skill_inference.py](../../modules/infrastructure/wre_core/src/local_skill_inference.py).

**Test references:** [test_wre_execution_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_execution_truth.py).

**Observed boundary:** Generic execution keeps outcome quality unknown; local model text has no effect authority. test_successful_effect_keeps_outcome_quality_unknown is a negative boundary, not a positive evaluator.

**Required next evidence:** Implement and independently invoke a task-specific oracle with held-out cases, baseline, actual cost/latency and false-success rejection. No generic positive evaluation receipt is established here.

### R11 — Verified outcome ratchet / scoped memory owner

**Normative references:** WSP 48 / 60 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_verified_outcome_ratchet.py](../../modules/infrastructure/wre_core/src/reddog_verified_outcome_ratchet.py), [reddog_held_out_recursive_improvement_regression_gate.py](../../modules/infrastructure/wre_core/src/reddog_held_out_recursive_improvement_regression_gate.py), [pattern_memory.py](../../modules/infrastructure/wre_core/src/pattern_memory.py).

**Test references:** [test_reddog_verified_outcome_ratchet.py](../../modules/infrastructure/wre_core/tests/test_reddog_verified_outcome_ratchet.py), [test_reddog_held_out_recursive_improvement_regression_gate.py](../../modules/infrastructure/wre_core/tests/test_reddog_held_out_recursive_improvement_regression_gate.py).

**Observed boundary:** The ratchet can forward independently accepted records to an injected sink; PatternMemory stores outcomes/candidates. These are separate trust boundaries.

**Required next evidence:** Compose authenticated scope, atomic/idempotent retention and failure recovery, then demonstrate the next invocation reads the accepted version. Storage alone is not verified learning.

### R12 — Independent production promoter

**Normative references:** WSP 48 / 71 / 95 / 97. **Evidence level:** `GENERIC_OWNER_MISSING`.

**Existing owner surfaces:** [pattern_ab_evidence.py](../../modules/infrastructure/wre_core/src/pattern_ab_evidence.py).

**Test references:** [test_pattern_memory.py](../../modules/infrastructure/wre_core/tests/test_pattern_memory.py).

**Observed boundary:** promote_variation() raises PermissionError for the unimplemented independent signed promoter. Candidate nomination cannot set production authority.

**Required next evidence:** Compose proposer/verifier/promoter separation, one-time signed decision, expiry/revocation and source/runtime/replay rejection. Do not substitute a database Boolean.

### R13 — Activation and rollback owner

**Normative references:** WSP 48 / 89 / 95 / 97. **Evidence level:** `GENERIC_OWNER_MISSING`.

**Existing owner surfaces:** [learning.py](../../modules/infrastructure/wre_core/recursive_improvement/src/learning.py).

**Test references:** [test_wre_telemetry_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_telemetry_truth.py).

**Observed boundary:** Generic apply_improvement() remains blocked_unimplemented and cannot prove activation or rollback. Existing proposal records are not deployment receipts.

**Required next evidence:** Bind exact-byte activation, known-good previous version, canary, forced regression rollback and interrupted activation recovery under delegated authority.

### R14 — Experiment owner / independent evaluator

**Normative references:** WSP 48 / 91 / 95. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [pattern_ab_evidence.py](../../modules/infrastructure/wre_core/src/pattern_ab_evidence.py).

**Test references:** [test_pattern_memory.py](../../modules/infrastructure/wre_core/tests/test_pattern_memory.py), [test_wre_runtime_admission_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_runtime_admission_truth.py).

**Observed boundary:** A/B sample storage and winner labels exist; active runtime selection is blocked without authenticated candidate/runtime binding. A winner is candidate evidence only.

**Required next evidence:** Bind immutable arms, predeclared outcomes, minimum samples, uncertainty, cost and regression criteria. Under-sampled or mixed-version evidence must stay inconclusive.

### R15 — Internal RSI canary owner

**Normative references:** WSP 48 / 91 / 95 / 97. **Evidence level:** `END_TO_END_PROOF_MISSING`.

**Existing owner surfaces:** [SKILLz.md](../../modules/infrastructure/wre_core/skillz/auto_test_registry_audit/SKILLz.md), [INTERFACE.md](../../modules/infrastructure/wre_core/INTERFACE.md).

**Test references:** [test_wre_test_registry.py](../../modules/infrastructure/wre_core/tests/test_wre_test_registry.py).

**Observed boundary:** The registry-audit skill is an integrity-repaired candidate workflow. Registry contract tests establish inventory behavior, not autonomous improvement of the workflow.

**Required next evidence:** Complete observation, retrieval, bounded execution, independent evaluation, promotion, activation, rollback and a measurably better subsequent invocation without modifying the judge.

### R16 — AgentDB claims and FoundUp queue owner

**Normative references:** WSP 77 / 78 / 91 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [agent_db.py](../../modules/infrastructure/database/src/agent_db.py), [openclaw_foundup_orchestrator.py](../../modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py), [foundup_job_consumer.py](../../modules/infrastructure/wre_core/src/foundup_job_consumer.py).

**Test references:** [test_foundup_job_consumer.py](../../modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py), [test_reddog_signed_worker_agentdb_history.py](../../modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_history.py).

**Observed boundary:** Persistent claims/history and FoundUp consumer contracts exist. A terminal ConsumerResult preserves explicit verification/CABR/payout non-readiness.

**Required next evidence:** Converge the chosen job lifecycle on durable claims with restart, lease expiry, duplicate submission and crash recovery. Avoid a second scheduler or competing owner record.

### R17 — Per-work-item memory/cache owner

**Normative references:** WSP 60 / 78 / 95 / 104. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [pattern_memory.py](../../modules/infrastructure/wre_core/src/pattern_memory.py), [skill_runtime_admission.py](../../modules/infrastructure/wre_core/src/skill_runtime_admission.py).

**Test references:** [test_pattern_memory.py](../../modules/infrastructure/wre_core/tests/test_pattern_memory.py), [test_wre_runtime_admission_truth.py](../../modules/infrastructure/wre_core/tests/test_wre_runtime_admission_truth.py).

**Observed boundary:** Storage and admission-cache code exist, with current byte-binding tests. Those tests are not a proof of concurrent multi-FoundUp ownership.

**Required next evidence:** Specify transaction/cache synchronization, isolation and bounded eviction, then test simultaneous work and cancellation. check_same_thread=False is insufficient.

### R18 — Capacity and assurance-reservation owner

**Normative references:** WSP 15 / 77 / 80 / 91 / 104. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [agent_db.py](../../modules/infrastructure/database/src/agent_db.py).

**Test references:** [test_signed_worker_assurance_reservation.py](../../modules/infrastructure/database/tests/test_signed_worker_assurance_reservation.py), [test_signed_worker_assurance_recovery.py](../../modules/infrastructure/database/tests/test_signed_worker_assurance_recovery.py).

**Observed boundary:** Worker assurance reservation/recovery tests are lower-level reuse evidence. They do not qualify arbitrary team fanout or aggregate provider/token limits.

**Required next evidence:** Bind parent/child limits, aggregate spend/time, fairness/backpressure and reserved verifier capacity before admitting a larger worker/team profile.

### R19 — CI / test-evidence owner

**Normative references:** WSP 5 / 6 / 34 / 95 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [generate_test_registry.py](../../modules/infrastructure/wre_core/scripts/generate_test_registry.py), [WSP_Test_Registry.json](../../WSP_knowledge/WSP_Test_Registry.json), [ci.yml](../../.github/workflows/ci.yml).

**Test references:** [test_wre_test_registry.py](../../modules/infrastructure/wre_core/tests/test_wre_test_registry.py).

**Observed boundary:** Main has 1,650 registered test files and 269 quarantined after PR #1656. Both preceding PRs passed their CI selections. Inventory count is not a passing-test count.

**Required next evidence:** Bind required test, quarantine and independent evidence identities to candidate promotion. Keep skipped, unavailable and unrelated failures visible; source changes invalidate old acceptance.

### R20 — FoundUp lifecycle owner

**Normative references:** WSP 27 / 73 / 95 / 104. **Evidence level:** `END_TO_END_PROOF_MISSING`.

**Existing owner surfaces:** [README.md](../../modules/foundups/agent/README.md), [README.md](../../modules/foundups/agent_market/README.md), [foundup_job_router.py](../../modules/infrastructure/wre_core/src/foundup_job_router.py).

**Test references:** [test_foundup_job_consumer.py](../../modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py).

**Observed boundary:** Agent/FAM lifecycle surfaces and job routing are identified. A bounded internal consumer proof does not establish a complete FoundUp lifecycle through RSI.

**Required next evidence:** Choose one FoundUp and demonstrate its scoped intake-to-delivery/evaluation path with a real participant gateway. A new whole-lifecycle acceptance test/receipt is still needed.

### R21 — pAVS/CABR backend and canonical query owner

**Normative references:** WSP 26 / 29 / 96 draft / 103 / 104. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [server.py](../../modules/infrastructure/pavs_mcp/src/server.py), [INTERFACE.md](../../modules/infrastructure/foundups_mcp_bridge/INTERFACE.md), [cabr_hooks.py](../../modules/foundups/agent_market/src/cabr_hooks.py).

**Test references:** [test_cabr_hooks.py](../../modules/foundups/agent_market/tests/test_cabr_hooks.py).

**Observed boundary:** pAVS query and CABR metric surfaces exist; draft governance and review-only projections do not create production consensus, valuation or payout readiness.

**Required next evidence:** Reconcile canonical authenticated backend/query ownership and typed evidence. Prove supported valuation and confirmed settlement separately from a convenient displayed status.

### R22 — Active RedDog/product lane

**Normative references:** WSP 73 / 91 / 97 / 104. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_authoritative_work_state_query.py](../../modules/communication/moltbot_bridge/src/reddog_authoritative_work_state_query.py), [INTERFACE.md](../../extensions/reddog/INTERFACE.md).

**Test references:** [test_reddog_authoritative_work_state_query.py](../../modules/communication/moltbot_bridge/tests/test_reddog_authoritative_work_state_query.py).

**Observed boundary:** Authoritative work-state query contracts are available for consumer integration. The existing product lane owns delivery and must be reconciled before edits.

**Required next evidence:** Show principal-scoped queued/running/blocked/verified/activated outcomes from authenticated owners in the selected live product. No concurrent YUMORI or RedDog product change is made here.

### R23 — Production RSI operations owner

**Normative references:** WSP 48 / 77 / 91 / 95 / 97. **Evidence level:** `END_TO_END_PROOF_MISSING`.

**Existing owner surfaces:** [ROADMAP.md](../../modules/infrastructure/wre_core/ROADMAP.md), [INTERFACE.md](../../modules/infrastructure/wre_core/INTERFACE.md).

**Test references:** No complete sustained-loop acceptance suite established in this review.

**Observed boundary:** No sustained multi-generation operational proof is established by this audit. Individual successful checks and locally stored variations cannot fill this row.

**Required next evidence:** Predeclare duration/workload, correctness, cost, rollback and intervention limits, then demonstrate retained benefit across repeated governed generations. Independent longitudinal acceptance is still to be supplied.

### R24 — FAM / qualification / ticket / audit / settlement owners

**Normative references:** WSP 15 / 26 / 29 / 77 / 95 / 104. **Evidence level:** `SPECIFICATION_AND_COMPONENTS`.

**Existing owner surfaces:** [task_pipeline.py](../../modules/foundups/agent_market/src/task_pipeline.py), [R24_AGENT_PRODUCTION_LINE_PACKET.md](../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md).

**Test references:** [test_persistent_compute_wiring.py](../../modules/foundups/agent_market/tests/test_persistent_compute_wiring.py).

**Observed boundary:** Existing FAM trigger_payout() sets task PAID while creating an INITIATED payout with paid_at=None. Qualification/team/reward composition remains the R24 plan.

**Required next evidence:** Prove qualification, one ticket, independent audit, acceptance, reward eligibility and confirmed settlement. Optional teams need R07/R18 qualification; majority agreement is not acceptance authority.

### R25 — Conversation / activity-consent / FoundUp validation owners

**Normative references:** WSP 26 / 29 / 48 section 8 / 60 / 73 / 104. **Evidence level:** `SPECIFICATION_AND_COMPONENTS`.

**Existing owner surfaces:** [R25_REDDOG_FEEDBACK_LOOP_PACKET.md](../../docs/roadmaps/R25_REDDOG_FEEDBACK_LOOP_PACKET.md), [cabr_hooks.py](../../modules/foundups/agent_market/src/cabr_hooks.py).

**Test references:** [test_cabr_hooks.py](../../modules/foundups/agent_market/tests/test_cabr_hooks.py).

**Observed boundary:** R25 specifies same-FoundUp active engagement, selection/delivery recheck, consent, attribution and attention limits. CABR hook tests are lower-level task-metric tests, not live feedback delivery.

**Required next evidence:** Implement the scoped V1 feedback adapter with inactive/expired/paused/wrong-FoundUp rejection and deduplication. Feedback cannot self-certify V2, V3, promotion or payout. No participant solicitation is performed here.

## Documentation contradictions and dispositions

| Finding | Disposition in this revision | Remaining limit |
|---|---|---|
| WSP 46 §2.1 offers deterministic execution when Skillz assets are missing. | Align with WSP 95: fail closed; no synthetic success. Keep legacy filename compatibility distinct from fallback execution. | Scanner/signature/runtime readiness is still checked per actual invocation. |
| WSP 46 implies measured 97% token reduction and presents old orchestration achievements as current completion. | Label the token figures as historical targets and the achievement block as historical. Add a current-runtime boundary. | Measured cost/latency and retained improvement are R10/R15/R23 evidence. |
| WRE requirements comment promises mock execution when local inference is unavailable. | Correct the comment to the implemented fail-closed proposal behavior. No dependency requirement is changed. | The local model may be unavailable; no Qwen call is claimed. |
| WSP_CORE describes prose workflows as executable logic and retains old achievement language. | Add a current implementation boundary and require named enforcement/evidence for operational claims. Preserve research material and governing protocol requirements. | WSP 00's separately owned state semantics and old retrieval examples remain outside this edit; R03 owns retrieval-entry reconciliation. |
| Briefing README describes the April ledger as live. | Identify it as a historical snapshot; add a dated RSI handoff and link to current source/PR evidence. | Legacy entries require individual dispositions, not blanket closure or deletion. |
| Catalog points only to an older system-status report. | Add the root roadmap and this derived map as current RSI navigation, retaining the report as a dated source. | An index status is not an enforcement measurement. |
| The knowledge catalog missed the WSP 73 identity correction already merged in `95f28fff4` (#1631). | Copy the canonical framework row to its exact knowledge mirror; WSP 73 itself already states the corrected boundary. | No new RedDog identity decision or product behavior is introduced. |

## R02 remaining work and archival procedure

1. Reconcile each relevant historical ledger row against its exact commits, current owner and interface. Record `still_open`, `superseded`, `merged_bounded_scope`, or `unresolved` with evidence and a replacement pointer. A commit being an ancestor proves inclusion only, not the completeness of its feature.
2. Preserve the April snapshot and raw audit evidence. Move or supersede a historical document only after its replacement link and disposition are recorded; do not rewrite other lanes' history or reset their worktrees.
3. Have a separately bound reviewer challenge the selected R06–R15 chain and requirement/test omissions. This architect-authored map is not its own independent verifier receipt.
4. R03 is the next runtime-facing preparation: qualify a source-selection contract for main, feature and overlay retrieval. Keep query failure separate from owner-controlled maintenance; do not reindex inside a query.

## Retrieval and model-role assessment

The canonical-main helper was invoked first under bytecode suppression. It returned `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`; its module bundle was explicitly a dirty shared-workspace overlay at `0c81418f`. That bundle was not treated as current semantic evidence. A clean matched reference at `78b79c36c2d776e030cd0ee8aa23359a67f952ec` then returned `ok=true`, CURRENT/no-gap and a successful bundle. It does not certify the newer `35ed430c6` source.

Retrieval evaluation: WSP 46/48/95 provided relevant protocol context; older anticipation/completion material added noise. Exact current runtime boundaries, the April ledger disclaimer, checkout-byte fixes and requirements comment needed direct reads. Current WRE README/INTERFACE, roadmap, ModLogs, tests README/TestModLog and requirements were retrieved; optional memory/README is absent. Deduplicated historical claims against current contracts and pinned source evidence. No stub or new memory store was needed.

The Qwen WSP enhancement skill supplied the evidence → recommendation → architectural review → mirror/validation workflow. Its conflict-resolution and cross-WSP review steps call for architect judgment. This slice therefore uses deterministic source comparison and existing tests; it does not claim Qwen/Gemma execution, model-measured savings or automatic production PatternMemory admission. The reusable lesson is recorded here and in the ModLogs: normative text must name its enforcement and evidence scope before it can count toward completion.

Reasoning-effort recommendation for this audit: High for cross-system architecture and evidence reconciliation; evaluate Max on a bounded final challenge only if it improves accepted findings enough to justify cost. Routine mechanical checks should use deterministic tools or qualified economical workers. Ultra is not a requirement for this slice, and no setting or provider route is changed by this recommendation. Measure cost per correctly accepted ticket; a larger reasoning budget is not an independent review or stronger execution authority. This is a task-specific recommendation, not a benchmark result; [OpenAI reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning#reasoning-effort), consulted 2026-09-13, likewise recommends evaluating whether higher effort justifies its cost.

## Validation

- Existing focused boundary selection: **18 passed, 96 deselected in 3.61s**, with importlib mode and explicit async plugin. Five files: execution truth, runtime admission truth, telemetry truth, Skillz loader hygiene and PatternMemory. Selection expression: `skill_load_failure or missing_registered_location or local_inference or outcome_quality or legacy_promote_variation or token or application_is_proposal_only or prototype or manifest_failure`.
- TMP/TEMP, AgentDB, PatternMemory, lyrics database, pytest cache and basetemp were isolated outside the checkout. The selection used injected/test model behavior and did not call a provider, dispatch a worker or change a production database.
- Structural acceptance for this documentation slice: every packet is mapped once; source/test paths exist at the pinned baseline; source inventory hashes reproduce; new local links resolve; framework/knowledge mirrors agree; 26 packets remain non-executable; frozen audit/archives and unrelated product/source paths are unchanged. Final results belong in the slice's ModLog/PR, not a synthetic WRE receipt.
- Prior R01 tier and prior PR CI retain their original scopes. A new documentation check does not upgrade them into a complete production RSI claim.

Recovery: revert the focused documentation commits or restore exact prior documents through Git review. No runtime activation or database rollback is needed. Governance classification: WSP 81 clarification/cross-reference additions under the existing 012 direction to rectify roadmap/WSP drift; no protocol status, priority, budget or fundamental sovereignty rule is changed.
