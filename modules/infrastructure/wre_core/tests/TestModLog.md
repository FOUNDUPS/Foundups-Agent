# TestModLog - wre_core/tests

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
