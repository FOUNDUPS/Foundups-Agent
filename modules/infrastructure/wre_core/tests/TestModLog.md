# TestModLog - wre_core/tests

## 2026-05-10: HXA16 Real Hermes delegate adapter safe harness tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa16_real_hermes_delegate_adapter_safe_harness.py -v`
- Status: PASS
- Result: `14 passed`
- Notes:
  - NEW file: `test_hxa16_real_hermes_delegate_adapter_safe_harness.py` (340 lines)
  - Test classes:
    - `TestHermesRealDelegateInterfaceExists` (4 tests) - delegate_tool.py exists
    - `TestHermesDelegateInterfaceRequirements` (2 tests) - interface requirements documented
    - `TestHXA16AdapterBoundaryProof` (3 tests) - adapter boundary proven
    - `TestRealDelegateAdapterDisabledByDefault` (2 tests) - explicit opt-in required
    - `TestHXA16VerdictDocumentation` (1 test) - verdict documented
    - `TestHXA16EvidenceGeneration` (2 tests) - evidence files generated
  - Key test: `test_adapter_boundary_proven_via_controlled_harness`
  - Verdict: `DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED`
- WSP 97 Coverage (HXA16):
  - real_delegate_adapter_invoked=True (boundary proven)
  - live_external_delegate_called=False (not enabled - requires full Hermes runtime)
  - controlled_delegate_invoked=True (controlled harness path)
  - repo_created=False
  - production_source_modified=False
  - external_federation_initiated=False
  - production_readiness_claimed=False
- Evidence Files:
  - adapter_boundary_proof.json: verdict, rationale, interface documentation
  - delegate_interface_requirements.json: parent_agent, toolsets, etc.
- Slice: HXA16_REAL_HERMES_DELEGATE_ADAPTER_SAFE_HARNESS_PHASE1

---

## 2026-05-12: HXA14 Controlled live Hermes delegation harness tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa14_controlled_live_hermes_harness.py -v`
- Status: PASS
- Result: `22 passed`
- Notes:
  - NEW file: `test_hxa14_controlled_live_hermes_harness.py` (520 lines)
  - Test classes:
    - `TestHarnessDisabledByDefault` (3 tests) - harness off by default
    - `TestHarnessRequiresExplicitOptIn` (3 tests) - explicit controlled_harness=True required
    - `TestHarnessSafetyBoundaries` (6 tests) - all safety gates enforced
    - `TestControlledDelegateBehavior` (3 tests) - controlled delegate semantics
    - `TestVoteBallotsThroughHarness` (1 test) - VoteBallots safe execution
    - `TestGotJunkThroughHarness` (1 test) - GotJunk safe execution
    - `TestNoGitHubAPICalls` (1 test) - no GitHub API calls
    - `TestNoProductionSourceModification` (2 tests) - no production source writes
    - `TestWSP97TruthTableEnforcement` (2 tests) - complete truth table
- New HXA14 Truth Fields:
  - controlled_delegate_invoked=True (harness invoked)
  - live_external_delegate_called=False (no real external delegate)
  - repo_created=False (no GitHub)
  - production_source_modified=False
  - external_federation_ready=False
  - production_ready=False
- Slice: HXA14_CONTROLLED_LIVE_HERMES_DELEGATION_HARNESS_PHASE1

---

## 2026-05-10: HXA12 GotJunk second proof safe dry-run tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa12_gotjunk_second_proof_dryrun.py -v`
- Status: PASS
- Result: `9 passed`
- Notes:
  - NEW file: `test_hxa12_gotjunk_second_proof_dryrun.py` (390 lines)
  - Test classes:
    - `TestGotJunkBuildIntentDetection` (3 tests) - intent parsing for gotjunk_001
    - `TestGotJunkDryRunJobCreation` (1 test) - job creation via OpenClaw
    - `TestHXA12GotJunkSecondProofSafeDryRun` (3 tests) - main HXA12 proof
    - `TestGotJunkVoteBallotsParity` (2 tests) - verifies same treatment as VoteBallots
  - Key test: `test_gotjunk_second_proof_safe_dryrun_reaches_hermes_and_generates_preview`
  - Proves factory generalizes beyond VoteBallots to second FoundUp
- WSP 97 Coverage (HXA12):
  - GotJunk target: foundup_id=gotjunk_001
  - dry_run=True enforced
  - real_execution_performed=False
  - repo_created=False
  - live_delegate_called=False
  - production_source_modified=False
  - Same evidence artifacts as VoteBallots (parity verified)
- Slice: HXA12_GOTJUNK_SECOND_PROOF_SAFE_DRYRUN_PHASE1

---

## 2026-05-10: HXA10 Controlled scaffold generation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa4_real_hermes_object_dryrun.py -v`
- Status: PASS
- Result: `17 passed`
- Notes:
  - Added `TestHXA10ControlledScaffoldGeneration` class (3 tests):
    - `test_voteballots_controlled_scaffold_generation_safe_dryrun_writes_temp_artifacts` - HXA10 proof
    - `test_scaffold_files_contain_generation_metadata` - metadata verification
    - `test_validate_foundup_does_not_create_scaffold` - validate does NOT create scaffold
  - HXA10 proves VoteBallots build_foundup generates actual scaffold files in temp workspace
  - Generated files: README.md, manifest.preview.json, interface.preview.md, implementation_plan.md
  - All files marked as DRY-RUN PREVIEW / NOT PRODUCTION CODE
- WSP 97 Coverage (HXA10):
  - controlled_scaffold_generated=True (files written to temp)
  - real_execution_performed=False (not production)
  - repo_created=False (no GitHub operations)
  - live_delegate_called=False (no delegate_task invocation)
  - production_source_modified=False (temp only)
- Slice: HXA10_VOTEBALLOTS_CONTROLLED_SCAFFOLD_GENERATION_PHASE1

---

## 2026-05-10: HXA9 PoC artifact bundle generation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa4_real_hermes_object_dryrun.py -v`
- Status: PASS
- Result: `14 passed`
- Notes:
  - Added `TestHXA9PocArtifactBundleGeneration` class (3 tests):
    - `test_voteballots_poc_generation_safe_dryrun_creates_artifact_bundle` - HXA9 proof
    - `test_extract_foundup_creates_artifact_bundle` - extract action creates bundle
    - `test_validate_foundup_does_not_create_artifact_bundle` - validate does NOT create bundle
  - HXA9 proves VoteBallots build_foundup generates `poc_artifact_bundle.json`
  - Bundle contains deterministic artifact plan (NOT actual files)
- WSP 97 Coverage (HXA9):
  - poc_generation=True (plan generated)
  - real_execution_performed=False (no actual file creation)
  - repo_created=False (no GitHub operations)
  - live_delegate_called=False (no delegate_task invocation)
  - artifacts_written_to_source=False (plan only, not execution)
- Slice: HXA9_VOTEBALLOTS_POC_GENERATION_SAFE_DRYRUN_PHASE1

---

## 2026-05-03: WRE Hermes executor consumer binding tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v`
- Status: PASS
- Result: `31 passed`
- Notes:
  - Refactored `TestHermesDispatch` (3 tests) - mocks WRE executor path
  - Renamed `TestConsumerResultReceiptBinding` -> `TestConsumerResultCheckpointBinding`
  - Added checkpoint/evidence field assertions to dispatch tests
  - Added `test_wre_dry_run_job_retained_with_evidence` - retention semantics
  - Updated `test_closed_loop_dry_run_proof_single_result` for checkpoint evidence
  - Updated `test_blocked_wre_result_has_checkpoint_evidence` for blocked checkpoint
  - Added `test_dry_run_simulated_retention_reason` - WSP 97 truthful retention
- WSP 97 Coverage (Phase 1C):
  - ConsumerResult.checkpoint_state from WRE executor
  - ConsumerResult.evidence_path from WRE executor
  - ConsumerResult.real_execution_performed=False always
  - No receipt emission for dry-run (evidence in checkpoint files)
  - to_dict() always includes WSP 97 truth fields
  - retention_reason="dry_run_evidence_only" for SIMULATED (not "receipt_emission_failed")

---

## 2026-05-03: Hermes checkpoint protocol tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v`
- Status: PASS
- Result: `84 passed`
- Notes:
  - Added `TestCheckpointProtocolFields` (6 tests) - checkpoint field defaults
  - Added `TestCheckpointInResult` (6 tests) - to_dict checkpoint serialization
  - Added `TestCheckpointStateSimulated` (4 tests) - dry_run checkpoint behavior
  - Added `TestCheckpointWSP97` (4 tests) - truth field isolation with checkpoint
- WSP 97 Coverage:
  - checkpoint_state="SIMULATED" when dry_run or flag disabled
  - checkpoint fields do NOT imply real_execution_performed
  - checkpoint fields do NOT imply verification_complete
  - Checkpoint protocol is structural, not proof of execution

---

## 2026-05-02: Hermes workspace binding contract tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v`
- Status: PASS
- Result: `64 passed`
- Notes:
  - Added `TestWorkspaceBindingDataclass` (1 test) - WorkspaceBinding.to_dict() serialization
  - Added `TestWorkspaceBindingPathValidation` (5 tests) - is_path_allowed() logic
  - Added `TestBlockedPathsConstant` (5 tests) - BLOCKED_PATHS frozenset contents
  - Added `TestBuildAllowedPaths` (5 tests) - action-to-path template mapping
  - Added `TestGetEvidenceOutputPath` (2 tests) - evidence path derivation
  - Added `TestWorkspaceHintInRequest` (4 tests) - workspace_hint in HermesDelegationRequest
  - Added `TestAllowedPathsInRequest` (2 tests) - allowed_paths population
  - Added `TestBlockedPathsInRequest` (2 tests) - blocked_paths population
  - Added `TestWorkspaceRootDetection` (3 tests) - workspace_root auto-detection
  - Added `TestNoRealExecutionWithWorkspaceBinding` (2 tests) - WSP 97 truth with binding
- WSP 97 Coverage (extended):
  - workspace_binding field exists in request
  - Path constraints defined but NOT enforced (Phase 1)
  - Evidence output path derived from job_id
  - No real execution even with workspace binding
- Test Fixes:
  - Fixed glob `**` pattern matching using PurePath.match()
  - Fixed Windows path compatibility for env var detection

---

## 2026-05-02: Hermes job executor adapter tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v`
- Status: PASS
- Result: `33 passed`
- Notes:
  - Added `TestFeatureFlag` (5 tests) - HERMES_DELEGATE_ENABLED env var behavior
  - Added `TestHermesDelegationRequest` (3 tests) - request dataclass serialization
  - Added `TestHermesDelegationResult` (3 tests) - result dataclass with WSP 97 fields
  - Added `TestFoundUpJobMapping` (5 tests) - FoundUpJob -> HermesDelegationRequest mapping
  - Added `TestExecutorDryRunDefault` (2 tests) - dry_run=True default behavior
  - Added `TestExecutorFeatureFlagDisabled` (3 tests) - SIMULATED when flag=0
  - Added `TestExecutorDryRunMode` (1 test) - SIMULATED when dry_run=True
  - Added `TestExecutorImportFailure` (1 test) - BLOCKED_IMPORT_UNAVAILABLE on error
  - Added `TestExecutorRealDelegationBlocked` (2 tests) - BLOCKED in Phase 1
  - Added `TestExecutorJobValidation` (4 tests) - job validation errors
  - Added `TestNoQueueConsumption` (2 tests) - no job state mutation
  - Added `TestSingletonExecutor` (2 tests) - singleton and convenience function
- WSP 97 Coverage:
  - real_execution_performed=False verified
  - verification_complete=False verified
  - cabr_ready=False verified
  - payout_ready=False verified
  - No CABR/token/payout/reward fields exist

---

## 2026-05-02: Model routing policy validation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q`
- Status: PASS
- Result: `111 passed`
- Notes:
  - Added `TestFreemiumTierModelRouting` (4 tests) - freemium allows auto/free only
  - Added `TestBasicTierModelRouting` (4 tests) - basic allows auto/free/standard
  - Added `TestEnterpriseTierModelRouting` (4 tests) - enterprise allows all
  - Added `TestAutoPreferenceAllTiers` (3 tests) - auto valid for all tiers
  - Added `TestModelRoutingPolicyWSP97Truth` (2 tests) - policy validation is structural
  - Added `TestGenericDAERoutingPolicyIgnored` (1 test) - generic DAE skips routing
  - Updated 2 existing model preference tests to include compatible tiers
  - Added EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER
  - Added TIER_ALLOWED_PREFERENCES map in foundup_job_router.py
  - Added model_routing_policy_validated/model_routing_policy_reason fields
  - Full suite: 517 passed (excluding production_gates)

---

## 2026-05-02: Compute budget validation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q`
- Status: PASS
- Result: `93 passed`
- Notes:
  - Added `TestComputeBudgetTypeValidation` (5 tests) - int/None valid, float/str/bool fail
  - Added `TestComputeBudgetNegativeValidation` (3 tests) - 0 and positive pass, negative fails
  - Added `TestComputeUsedTypeValidation` (4 tests) - int valid, float/str/bool fail
  - Added `TestComputeUsedNegativeValidation` (3 tests) - 0 and positive pass, negative fails
  - Added `TestComputeUsedExceedsBudget` (4 tests) - used <= budget or None budget
  - Added `TestLiveModeRequiresComputeBudget` (3 tests) - live mode needs explicit budget
  - Added `TestComputeTierValidation` (4 tests) - freemium/basic/enterprise only
  - Added `TestModelPreferenceValidation` (5 tests) - auto/free/standard/premium only
  - Added `TestComputeBudgetWSP97Truth` (2 tests) - no metering accuracy claims
  - Added `TestGenericDAEComputeIgnored` (1 test) - generic DAE skips compute validation
  - Updated 7 existing live mode tests to include compute_budget
  - Full suite: 499 passed (excluding production_gates)

---

## 2026-05-02: Live mode policy gate tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q`
- Status: PASS
- Result: `59 passed`
- Notes:
  - Added `TestDryRunWithPendingEvidenceStillPasses` (2 tests) - dry-run behavior unchanged
  - Added `TestLiveModeWithoutApprovalFails` (2 tests) - human_approval required
  - Added `TestLiveModeWithoutEvidenceFails` (2 tests) - evidence required in live mode
  - Added `TestLiveModeWithMalformedEvidenceFails` (2 tests) - evidence must be valid
  - Added `TestLiveModeWithApprovalAndEvidenceNoVerification` (3 tests) - WSP 97 truth
  - Added `TestLiveModeSecurityGate` (2 tests) - security gate validation
  - Added `TestLiveModeValidationErrorDetails` (4 tests) - error details include missing gates
  - Updated 2 existing tests to include live mode approval
  - Full suite: 465 passed (excluding production_gates)

---

## 2026-05-02: Evidence refs validation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q`
- Status: PASS
- Result: `42 passed`
- Notes:
  - Added `TestEvidenceRefsListOfStrings` (2 tests) - list of strings passes
  - Added `TestEvidenceRefsEmptyWithDryRun` (3 tests) - empty evidence in dry-run pending
  - Added `TestEvidenceRefsWrongType` (3 tests) - wrong type fails
  - Added `TestEvidenceRefsEmptyString` (2 tests) - empty string fails
  - Added `TestEvidenceRefsMalformedDict` (6 tests) - dict validation
  - Added `TestEvidenceRefsWSP97TruthFields` (4 tests) - verification/cabr/payout always False
  - Added `TestGenericDAEEvidenceBehavior` (2 tests) - generic DAE ignores evidence
  - Updated existing tests for evidence_pending validation code
  - Full suite: 448 passed (excluding production_gates)

---

## 2026-05-02: FoundUpJob envelope validation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -v`
- Status: PASS
- Result: `20 passed`
- Notes:
  - Added `TestGenericDAEEnvelope` (3 tests) - generic envelope permissive validation
  - Added `TestFoundUpJobMissingJobId` (2 tests) - job_id required validation
  - Added `TestFoundUpJobMissingFoundupId` (2 tests) - foundup_id required validation
  - Added `TestFoundUpJobDryRunDefault` (3 tests) - dry_run defaulting to True
  - Added `TestValidDryRunFoundUpJob` (2 tests) - valid envelope passes
  - Added `TestFailureMessagesIdentifyFields` (4 tests) - explicit failure messages
  - Added `TestEnvelopeTypeDetection` (4 tests) - envelope classification
  - Full suite: 426 passed (excluding production_gates)

---

## 2026-05-02: Success clearing proof for retention semantics

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -q`
- Status: PASS
- Result: `30 passed`
- Notes:
  - Added `test_successful_terminal_job_cleared` to TestRetentionSemantics
  - Proves terminal + receipt success -> job cleared from queue
  - Asserts job_id in cleared_job_ids, not in retained_job_ids
  - Confirms WSP 97 truth fields remain false

---

## 2026-05-02: Queue retention semantics + retention-aware drain

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v`
- Status: PASS
- Result: `29 passed`
- Notes:
  - Added `TestRetentionSemantics` class with 4 tests
  - Tests routing_failure, routing_blocked, empty queue, should_clear properties
  - Updated TestDrainOpenClawQueue for retention-aware behavior
  - Updated TestDrainOpenClawQueueDryRun for retention metadata output

---

## 2026-05-02: drain_openclaw_queue_dry_run convenience function + CLI command

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v`
- Status: PASS
- Result: `20 passed`
- Notes:
  - Added `TestDrainOpenClawQueueDryRun` class with 4 tests
  - Tests structured evidence dict, WSP 97 truth fields, empty queue, --no-clear flag
  - CLI: `python run_wre.py drain [--no-clear]`

---

## 2026-03-08: Brain artifact extractor incremental refresh + training signal validation

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_extract_brain_artifacts.py`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Notes:
  - Validates DPO/SFT extraction from implementation-plan revision chains and walkthroughs.
  - Validates incremental refresh state so unchanged brain directories skip full re-scan.

---

## 2026-03-05: Self-audit escalation lane validation (phase 2)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py`
- Status: PASS
- Result: `6 passed, 2 warnings`
- Notes:
  - Validates adaptive remediation + repeated-signature escalation behavior.
  - Includes escalation command dispatch and escalation state persistence checks.

---

## 2026-03-05: Targeted WSP 15/WSP 48 security regression sweep (post-escalation)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `16 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms no regression after self-audit escalation phase.

---

## 2026-03-05: Full wre_core suite sweep (bounded)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests -k "not production_gates"`
- Status: PASS
- Result: `73 passed, 1 skipped, 4 deselected, 3 warnings`
- Notes:
  - Excludes long-running `test_production_gates` lane for bounded local verification.
  - One async test was skipped under plugin-autoload-disabled mode (`PytestUnhandledCoroutineWarning`).

---

## 2026-03-05: WSP 15 security + preflight + self-audit verification sweep

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `20 passed, 30 deselected, 2 warnings`
- Notes:
  - Covers self-audit adaptive remediation tests, CodeAct hardening, dependency preflight, manifest verification, shared DAE preflight behavior, and WRE orchestrator supply-chain gating.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-03-06: Dependency preflight multi-lockfile regression test

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py`
- Status: PASS
- Result: `6 passed, 2 warnings`
- Notes:
  - Validates new Node lockfile scope behavior (`OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE=all`).
  - Confirms aggregate high-vulnerability counting across multiple `package-lock.json` targets.
  - Confirms hidden nested worktree lockfiles are excluded from Node dependency audit.
  - Confirms pip-audit dict payload parsing and unknown-severity threshold enforcement (`OPENCLAW_DEP_SECURITY_MAX_UNKNOWN`).
  - Warnings are unchanged repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---
