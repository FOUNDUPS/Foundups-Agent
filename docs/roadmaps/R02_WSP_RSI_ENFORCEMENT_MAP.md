# R02 — WSP requirements and RSI enforcement map

Source baseline: `35ed430c61e4e35c1b779f03c13e40368c82b65f` (main after PRs #1656 and #1702), reviewed 2026-09-13.

This is a derived evidence map for the [system roadmap](../../ROADMAP.md), covering its **26 existing packets**, not every clause of every WSP. WSPs remain normative; current source, tests and authenticated operational receipts establish implementation. This map cannot authorize a worker, change a budget, authenticate its own evaluation or certify production RSI.

**Verdict:** R01's local integrity repair is present. R02's requirement map, selected documentation contradictions and pending-ledger dispositions are reconciled in this revision. The complete generic evaluator → promoter → activation/rollback → measured retained improvement chain remains unproved. R02 stays partial until remaining owner/archival decisions and independent review of the required path are complete.

Current planning constraint (012 clarification, 2026-09-13): the [system roadmap's validation scope](../../ROADMAP.md#rsi-validation-scope-internal-workflows-and-dedicated-fixtures) starts with system RSI and permits selected early-stage FoundUps/other repositories as test workloads. YUMORI/eSingularity and reserved lanes remain protected. The [expanded component map](../operations/RSI_SWARM_DISPATCH.md#existing-component-coverage-and-rsi-insertion-points) explicitly includes WRE Auto Researcher, model AutoResearch, PQN research and external Science Swarm Hub. These later source observations do not rewrite the original pinned inventory or prove complete integration.

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

**Required next evidence:** The September ledger reconciliation below covers all pending April rows, with unresolved owner receipts and SoftProto per-contract replacement decisions retained; WSP 00 state semantics remains separately owned. This is not a complete audit of every clause in all 110 numbered protocol slots.

### R03 — Holo query/authority owner

**Normative references:** WSP 50 / 60 / 87 / 97. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [authority_worktree.py](../../holo_index/authority_worktree.py), [reddog_holoindex_owner_query_once.py](../../scripts/reddog_holoindex_owner_query_once.py).

**Test references:** [test_reddog_holoindex_owner_query_root_binding.py](../../modules/communication/moltbot_bridge/tests/test_reddog_holoindex_owner_query_root_binding.py).

**Observed boundary:** Canonical shared-checkout query rejects HEAD mismatch and labels its bundle as workspace_overlay. A matching clean reference returns CURRENT/no-gap; source and overlay are different evidence scopes.

**Required next evidence:** Qualify clean main, divergent feature, dirty overlay, stale authority, concurrent main advance and no-MCP entry paths. Reconcile old WSP 00 raw-query/reindex examples with the governed maintenance boundary.

Later R03 checkpoint (2026-09-13, source `773a29e70`): the [existing entry procedure](../../holo_index/CLI_REFERENCE.md#source-bound-owner-queries) reconciles bootstrap commands and documents the six-case matrix. All 81 existing entry/root tests pass and local bundle retrieval succeeds. The matched reference now fails owner startup; no new current-main semantic acceptance is claimed. These later observations do not change the pinned R02 source inventory or close R03.

Later runtime-selection checkpoint (2026-09-13, documentation source `89bdd7a5`): a bounded child diagnostic identified missing NumPy under the ambient interpreter. Using the existing vetted venv and default query budget restored uninstrumented CURRENT/no-gap retrieval with one attempt at the matched `78b79c36` reference. Current-main `89bdd7a5` still rejects the older authority before owner startup. See the [recorded correction](../../holo_index/CLI_REFERENCE.md#interpreter-correction-checkpoint--2026-09-13); R03 remains partial. No runtime source or index change was needed.

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

**2026-09-14 local checkpoint:** The existing recorder, retention gate and final
memory-admission adapter now enforce matching work/verifier evidence, valid
measurements, explicit retention eligibility and nonempty write acknowledgments.
The composed synthetic fixture reaches the injected sink only for its accepted
case; 315 selected core, dependency and disposable sink/canary tests pass. These are structural contract
checks on supplied receipts, not proof of their independent authenticity. See
[outcome retention evidence](../operations/RSI_SWARM_DISPATCH.md#outcome-retention-checkpoint--2026-09-14).

**Existing retention implementation to reuse:**
[reddog_verified_pattern_memory_sink.py](../../modules/communication/moltbot_bridge/src/reddog_verified_pattern_memory_sink.py)
already provides idempotent staging outside normal recall. Its current
`activation_ready` remains false; direct activation rejects without an
independent durable authority source. Existing sink tests cover same-record
staging, conflicting records and recall isolation. Preserve this boundary and
compose the existing authority/activation path instead of creating another
memory store. The full authenticated cycle still needs the evidence below.

**Staging replay follow-up:** Four local counterexamples now pass after the
existing sink snapshots input and reconciles competing insertions through the
same SQLite record key. The 51-case sink/admission selection includes preserved
winner bytes and before/after-commit retry. See the
[staging checkpoint](../operations/RSI_SWARM_DISPATCH.md#staging-replay-checkpoint--2026-09-14).
This is preparatory R11/R17 evidence; activation/revocation atomicity and real
crash/sustained-concurrency proof remain open.

**Active-record identity follow-up:** The existing sink's active-row retry now
uses canonical JSON equality, preserving boolean/numeric/signed-zero identity.
Three previously acknowledged mismatches now reject; valid fixture-seeded
active retries retain their IDs. The 55-case sink/admission selection passes.
See the [identity checkpoint](../operations/RSI_SWARM_DISPATCH.md#active-record-identity-checkpoint--2026-09-14).
This is local R11 evidence; fixture insertion is not authenticated activation.

**Required next evidence:** Compose authenticated scope, atomic/idempotent retention and failure recovery, then demonstrate the next invocation reads the accepted version. Storage alone is not verified learning.

**2026-09-14 composition audit:** The queue-to-publisher and authority-to-Memex
connections already exist. The queue constructs a staging-only PatternMemory
sink; the independent activation dependency/method and whole-workflow acceptance
remain absent. Static caller search also leaves the existing protected-use loader
and WSP 71 ephemeral factory without production callers. A disposable real-adapter
probe with signer/verifier doubles shows ACTIVE evidence after failed memory
activation and a conflicting publication on a one-second-later retry. The real
sink remains closed. Existing selected suites: **46 passed / one Linux ownership
skip**. See the [connection map and R11-A–F sequence](../operations/RSI_SWARM_DISPATCH.md#authority-to-memory-connection-checkpoint--2026-09-14).
R11-A (immutable publication/retry) is the next local implementation target;
production composition still requires authentic independent authority inputs.

**Publication retry follow-up:** The existing publisher/store now acknowledge
the original signed envelope without re-signing or renewing it. Three reproduced
failures pass; the connected selection passes 91 tests, including two real local
child-process retries with unchanged durable bytes and fresh expiry/revocation
rejection. See the [publication checkpoint](../operations/RSI_SWARM_DISPATCH.md#publication-retry-checkpoint--2026-09-14).
At the publication-only checkpoint, queue reconstruction still changed
`verified_at`; the event-time follow-up below addresses that gap. Publication
acknowledgment alone establishes neither activation nor retained benefit.

**Event timestamp follow-up:** The existing chain receipt records the accepted
stage time once; canonical admission derivation reuses the unique matching
held-out receipt's timestamp. Later snapshot time does not change metadata.
Missing/invalid/ambiguous/foreign event evidence rejects, including historical
receipts without a timestamp. The connected selection passes 214 tests with
four platform skips; see the [event checkpoint](../operations/RSI_SWARM_DISPATCH.md#event-timestamp-checkpoint--2026-09-14).
The next follow-up addresses recoverable publication conflicts; owner-controlled
legacy event recovery and production acceptance remain open.

**Publication commit follow-up:** The existing store retries revision conflicts
with the same signed bytes, bounded to three attempts. The publisher validates a
durable winner after a lost acknowledgment or competing write; unrelated state,
original signature/issuance and staging visibility are preserved. The connected
selection passes 118 tests; see the [commit checkpoint](../operations/RSI_SWARM_DISPATCH.md#publication-commit-checkpoint--2026-09-14).
R11-A still needs a durable response handoff for process death before publication
and owner recovery after exhaustion. Existing outcome-root and conversation
replay contracts are the next retrieval targets; their authorities are distinct.

**Root-commit acknowledgment follow-up:** The existing service acknowledges the
exact committed marker after fresh authority validation. Its client retries the
same encoded COMMIT once only after ConnectionError/TimeoutError; burned grants
never reopen. The connected selection passes 115 tests with one Linux-root skip;
see the [root checkpoint](../operations/RSI_SWARM_DISPATCH.md#root-commit-acknowledgment-checkpoint--2026-09-14).
This recovers an in-process lost acknowledgment. Full outcome-response durability,
authenticated restart readback and the process-local reservation seal remain the
next R11-A boundary. Conversation replay has distinct authority and is not a grant.

**Signer-response handoff follow-up:** The publisher now uses response validation
from the existing outcome-signing owner; malformed boolean claims, contradictory
rejection and non-boolean cryptographic verifier results reject. The connected
selection passes 207 tests with one Linux-root skip. Root-backed interruption and
clock tests preserve consumed grants. The [handoff contract](../operations/RSI_SWARM_DISPATCH.md#signer-response-handoff-checkpoint--2026-09-14)
orders immutable response records, pending durability, terminal commitment,
separately authorized readback and publisher recovery. The next local layer is
the bounded record/binding contract; persistence and readback remain unimplemented.
Object reconstruction is not production process-death recovery or retained RSI.

**Immutable-record follow-up:** the [record checkpoint](../operations/RSI_SWARM_DISPATCH.md#immutable-response-record-checkpoint--2026-09-14)
implements exact bounded response bytes in the existing outcome-signing owner,
reusing the root codec, co-signed descriptor and shared signature validation.
The connected selection passes 294 tests with one Linux-root skip. This closes
the local schema prerequisite only. Pending durability, full-response commitment,
authenticated readback and retained improvement remain open; no runtime caller
or activation is added. WSP 15's historical 16/P1 label is corrected to 16/P0
with an additive baseline erratum.

**Pending-storage follow-up:** the [checkpoint](../operations/RSI_SWARM_DISPATCH.md#pending-response-storage-checkpoint--2026-09-14)
adds a local primitive to the existing root state owner: exact current reservation,
mirrored record-digest selection, bounded atomic pending bytes and exact retry.
The outcome grant stays reserved. This is single-copy payload storage with tested
local failures, not root RPC admission, terminal commitment or authorized readback.
Those integrations, process recovery and R11-B–F remain open.

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

### R22 — RedDog interface / isolated test consumer

**Normative references:** WSP 73 / 91 / 97 / 104. **Evidence level:** `CONTRACT_AND_GAP`.

**Existing owner surfaces:** [reddog_authoritative_work_state_query.py](../../modules/communication/moltbot_bridge/src/reddog_authoritative_work_state_query.py), [INTERFACE.md](../../extensions/reddog/INTERFACE.md).

**Test references:** [test_reddog_authoritative_work_state_query.py](../../modules/communication/moltbot_bridge/tests/test_reddog_authoritative_work_state_query.py).

**Observed boundary:** Authoritative work-state query contracts are available for consumer integration. The existing product lane owns delivery and must be reconciled before edits.

**Required next evidence:** Show principal-scoped queued/running/blocked/verified/activated outcomes from authenticated owners in a dedicated synthetic test consumer. Protected active FoundUps and unscoped live product state are excluded; selected early-stage test consumers may be qualified under the current scope.

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

## Historical ledger dispositions — 2026-09-13

Source: main `cc9c79361ef8e9075d0b09759027ad88a2adfd90`. This is a documentation reconciliation under R02 (existing WSP 15 score 15/P1), not a worker dispatch or runtime experiment. WSP 00 bootstrap/strict gate passed; WSP 97 source, adjacent-owner and alternative checks precede the dispositions. WRE execution is not applicable to this local documentation slice.

Coverage: all **nine Open Slices**, the **one Deferred Slice**, and the **one Archive / Reconcile-Needed track** in the preserved April ledger, plus four closed groundwork rows directly relevant to RSI. The empty Blocked table has no work row. Other closed product/history rows are preserved without a new audit or completion claim. Original April prose and row statuses remain byte-for-byte unchanged after newline normalization.

Disposition vocabulary: `merged_bounded_scope` means the named deliverable is included with the limits below; `still_open` means an identified acceptance requirement remains missing; `unresolved` means evidence is insufficient for closure; `superseded` requires an explicit replacement. No row is superseded merely because a newer file or similarly named function exists. Owner labels below name code/contract responsibilities, not current personnel, lane leases or authorization.

| Historical row | Disposition | Existing owner / replacement packet | Current evidence and precise remaining work |
|---|---|---|---|
| `bh1_branch_hygiene_forensics` | `unresolved` | Git/PR provenance owner; existing PR scope guard; R02 | The commit-to-PR API now associates fde9d64a4 with merged PR #384. That PR has a rolodex title; association and ancestry do not settle the original mixed-scope/provenance question. Preserve forensic follow-up; do not repeat the obsolete no-associated-PR claim. Evidence: [pr_scope_guard.py](../../tools/pr_scope_guard/pr_scope_guard.py). |
| `dj2_b_ironclaw_skip_intentionality_assertion` | `still_open` | main.py preflight / AI Overseer owner; R02 | run_ironclaw_runtime_preflight skips every non-ironclaw backend when ALWAYS is false. The requested unknown-backend classification is absent from that branch. Reuse the existing dispatcher and known-backend test; qualify the unknown case without probing a live runtime. Evidence: [main.py](../../main.py), [test_main_ironclaw_preflight.py](../../tests/test_main_ironclaw_preflight.py). |
| `dj2_d_brain_artifact_missing_dir_event` | `still_open` | main.py preflight / AI Overseer owner; R02 | The missing-directory branch returns True after PASS (missing), so the later false-return startup-blocker diagnostic cannot cover it. Preserve return behavior; specify the low-severity non-automation event before any owner implementation. Evidence: [main.py](../../main.py), [preflight_resolution.py](../../modules/ai_intelligence/ai_overseer/src/preflight_resolution.py). |
| `dj2_e_git_merge_sentinel_import_failure_event` | `still_open` | main.py / WRE sentinel owner; R02 | The ImportError branch logs WARN and returns True. It does not invoke the existing failure dispatcher or the later startup-blocker diagnostic. Scope any follow-up to that branch and a synthetic import-failure test. Evidence: [main.py](../../main.py), [preflight_resolution.py](../../modules/ai_intelligence/ai_overseer/src/preflight_resolution.py). |
| `dj2_f_openclaw_security_fail_dispatch` | `still_open` | main.py security / RedDog diagnostic owner; R02 | Commit f450b5bbcd (#1247) adds startup-blocker diagnostics for false preflight returns. However passed=False with enforcement disabled still returns True, and the original severity/payload contract is not proved by that diagnostic. Narrow the old ticket to the uncovered failure branch and payload; reuse the landed owner. Evidence: [main.py](../../main.py), [test_main_runtime_bootstrap.py](../../tests/test_main_runtime_bootstrap.py), [test_preflight_resolution.py](../../modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py). |
| `yt_cleanup2_stream_resolver_api_contract_rebase` | `unresolved` | stream_resolver test owner; R19 | The April count of 12 failures is not current test evidence. Current test documentation and history exist, but no exact failing selection was reproduced in this documentation slice. Preserve the owner handoff; require an isolated selection before closing or re-implementing it. Evidence: [README.md](../../modules/platform_integration/stream_resolver/tests/README.md), [ModLog.md](../../modules/platform_integration/stream_resolver/ModLog.md). |
| `legal_ii1_bonding_curve_review_packet` | `unresolved` | Financial/legal review owner, assignment unverified; R21 | The April planning row is not a completed review or current owner assignment. Retain a separate review handoff; no legal conclusion, financial execution or RSI test is authorized by this disposition. Evidence: [ACTIVE_SLICE_LEDGER.md](../../docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md). |
| `fam_ideation2_envelope_schema_validator` | `still_open` | AI Overseer foundup_genesis owner; R20 | Schema and structured acceptance validation landed in 864e89b28 (#428), with later input-hardening commits. The existing envelope has truth_state_map, not the original task_graph/backpropagation DAG. WSP 27 section 8.1.10 still requires cycle, missing-precondition and orphan-postcondition validation. Extend/reconcile the existing contract; do not create another envelope. Evidence: [WSP_27_pArtifact_DAE_Architecture.md](../../WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md), [envelope.py](../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py), [validator.py](../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py), [test_foundup_genesis_validator.py](../../modules/ai_intelligence/ai_overseer/tests/test_foundup_genesis_validator.py). |
| `fam_ideation3_ai_overseer_truth_sentinel` | `still_open` | AI Overseer / existing OpenClaw intake gate owner; R20 | The intake validator rejects implementation markers without evidence; this is not a repository-bound field-status drift check. No occurrence of the original sentinel field/event names was found in tracked modules Python source. FAM LaunchOrchestrator exposes launch_foundup, not accept_envelope. Preserve IDEATION3-before-IDEATION4 and reconcile the existing WSP 109 gate before implementation. Evidence: [WSP_27_pArtifact_DAE_Architecture.md](../../WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md), [validator.py](../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py), [openclaw_foundup_orchestrator.py](../../modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py), [orchestrator.py](../../modules/foundups/agent_market/src/orchestrator.py). |
| `de4_hermes_extraction_next_sandbox` | `unresolved` | Existing DE/Hermes extraction owner; R20 | DI1 deferred externalization; the separate DE4 entry-URL briefing records a later URL activation. URL activation does not prove repository publication or a fresh extraction gate. This product-specific track is outside the internal RSI experiment scope; preserve both records and obtain owner evidence separately. Evidence: [DI1_DECISION_GATE.md](../../docs/0102_session_briefings/DI1_DECISION_GATE.md), [DE4_GOTJUNK_ENTRY_URL_ACTIVATION.md](../../docs/0102_session_briefings/DE4_GOTJUNK_ENTRY_URL_ACTIVATION.md). |
| `softproto` | `unresolved` | Existing UI/PMCTRL/WRE contract owners; R02 | The rollout document still proposes a UI architecture branch while the April ledger requests reconciliation. Overlap alone is insufficient to archive each contract. Preserve the five prompts and eight contracts/plans; require a per-contract replacement and owner disposition. Do not revive this as an RSI implementation wave. Evidence: [SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md](../../modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md), [SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md](../../modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md). |
| `skill_evolution_loop_phase1_report_surface` | `merged_bounded_scope` | OpenClaw skill-evolution report owner; R10-R15 | 3ae311767 is included. The report surface exists; reporting and supervisor integration do not prove an independent evaluator, production activation or retained benefit. Evidence: [openclaw_skill_evolution.py](../../modules/communication/moltbot_bridge/src/openclaw_skill_evolution.py), [test_openclaw_skill_evolution.py](../../modules/communication/moltbot_bridge/tests/test_openclaw_skill_evolution.py). |
| `skill_evolution_loop_phase2_mutation_surface` | `merged_bounded_scope` | OpenClaw report / WRE promotion owners; R12-R15 | 448424358 is included. A/B status and readiness queries exist, but the current legacy promote_variation method raises PermissionError pending an independent signed promoter. Nomination/readiness is not promotion. Reuse these surfaces in R12-R15. Evidence: [openclaw_skill_evolution.py](../../modules/communication/moltbot_bridge/src/openclaw_skill_evolution.py), [pattern_ab_evidence.py](../../modules/infrastructure/wre_core/src/pattern_ab_evidence.py). |
| `fam_ideation1_foundup_outcome_backpropagation_contract_phase1` | `merged_bounded_scope` | WSP 27 / FAM lifecycle contract owner; R20 | dcc9ddfdd is included and WSP 27 retains the outcome/backpropagation contract and ordered future slices. This closes the documented specification only; the IDEATION2/3 rows above retain their implementation gaps. Evidence: [WSP_27_pArtifact_DAE_Architecture.md](../../WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md). |
| `fx1_holoindex_truth_restoration` | `merged_bounded_scope` | Holo query / authority owner; R03-R05 | 9a89fedeb is included. The current source-bound entry supports local bundle fallback with explicit UNKNOWN freshness. Historical truth-restoration work is not a current semantic-generation or runtime-closure receipt; continue through the existing R03-R05 owners. Evidence: [CLI_REFERENCE.md](../../holo_index/CLI_REFERENCE.md), [reddog_holoindex_owner_query_once.py](../../scripts/reddog_holoindex_owner_query_once.py). |

### Reconciliation decisions and next tickets

1. **Reuse before implementation:** do not issue another schema, skill-evolution report, A/B engine, diagnostic owner, or Holo query bridge. The code above already supplies those bounded surfaces. The missing acceptance conditions are the ticket scope.
2. **Avoid accidental dependency growth:** the old main.py warning hooks, financial review and UI/extraction tracks are owner handoffs, not new prerequisites for the first internal registry-audit RSI canary. Under 012's later scope clarification, R20 may use a dedicated synthetic fixture or a selected early-stage repository; YUMORI/eSingularity and reserved lanes remain protected.
3. **Preserve archive evidence:** the April ledger and SoftProto documents remain in place. Per-contract SoftProto replacement review and unresolved owner receipts remain open. No old retention instruction is executed, no project is activated and no lane is reassigned.
4. **Separate review remains required:** the 15 dispositions are architect-authored source analysis, not independent verification. A separately bound reviewer must challenge the R06–R15 chain and the coverage omissions. Keep R02 partial and every backlog packet non-executable.
5. **Next runtime-facing preparation:** continue the existing R03 exact-current-main authority qualification (the matched-reference interpreter correction is recorded above), then R06–R08 admission and one bounded artifact. Do not bypass failed runtime binding or launch a parallel orchestrator to accelerate dispatch.

Evidence inventory: the existing [R02 source inventory](R02_WSP_RSI_ENFORCEMENT_EVIDENCE.json) retains its original 70-source baseline and adds a separate `ledger_reconciliation` block with this source, exact Git-blob hashes, commit ancestry and all 15 dispositions. Commit ancestry proves inclusion, not feature completeness. The GitHub commit-to-PR lookup for `fde9d64a4` returned #384, merged at `59b2ed3df115e4ae2194f80149eb9ac3e6f3716e`; its title is `docs(rolodex): regenerate artifacts after CF4 file-specific binding`. This records the mismatch for BH1 rather than silently closing provenance.

Retrieval evaluation: the existing helper returned `source=holoindex_bundle`, `ok=true`, `bundle_ok=true`, `freshness=UNKNOWN`, `index_gap_detected=true`, `owner_attempts=0`, `no_reindex=true`. Local WRE context was usable, but dated completion prose and incomplete module mapping required direct tracked-file/contract reads. Deduplicated repeated history and distinguished the current startup-blocker path from successful warning returns. No semantic CURRENT claim, model-worker execution, provider cost measurement or learning admission is made. Deterministic source/commit checks are sufficient for this reconciliation; no additional agent runtime was started.

Validation for this slice is structural and read-only: preserve the original inventory and April body; reproduce added source hashes and commit ancestry; cover every pending ledger row exactly once; resolve new local links; retain packet IDs, dependencies, priorities, scope exclusions and `dispatchable=false`; refresh only changed document-index entries. Referenced module tests are inventory, not fresh execution results. The validation result and exact changed-file count are recorded in ModLog/PR after checking.

## R02 remaining work and archival procedure

1. Resolve the remaining owner evidence and per-contract archival decisions identified in the historical-ledger dispositions above. Revalidate source and ownership before acting; a recorded disposition or ancestor commit does not prove feature completion.
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
