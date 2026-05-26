# TestModLog - wre_core/tests

## 2026-05-27: REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1 Validator tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_validate_session_closeout.py -v`
- Status: PASS
- Result: `21 passed`
- Notes:
  - NEW file: `test_validate_session_closeout.py` (180 lines)
  - Tests session closeout validator for schema and secret safety:
    - `TestRequiredFields` (4 tests) - Required field validation
    - `TestSourceValidation` (3 tests) - Source enum validation
    - `TestWorkSummaryLength` (3 tests) - Max 2000 char limit
    - `TestSecretDetection` (5 tests) - API key/token rejection
    - `TestRawTranscriptDetection` (4 tests) - Transcript marker rejection
    - `TestFullFileValidation` (6 tests) - End-to-end file validation
  - Key patterns tested:
    - OpenAI keys (`sk-*`)
    - Google API keys (`AIza*`)
    - GitHub PATs (`github_pat_*`)
    - Env secret patterns (`*_SECRET=*`)
    - Role-based transcript markers (`"role": "assistant"`)
  - No network calls, no .env reads, synthetic data only
  - Verdict: `SESSION_CLOSEOUT_VALIDATOR_TESTS_DEFINED`
- Slice: REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1

---

## 2026-05-15: HXA31 Destructive Action Guard Edge Case tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_destructive_action_guard_edge_cases.py -v`
- Status: PASS (with expected xfails)
- Result: `26 passed, 2 skipped, 5 xfailed`
- Notes:
  - NEW file: `test_destructive_action_guard_edge_cases.py` (626 lines)
  - Tests edge cases from PR #613 audit (DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_EXPANSION_AUDIT_PHASE1):
    - `TestDirectoryTraversalBlocked` (3 tests) - `../` traversal normalized and blocked
    - `TestMixedSeparatorHandling` (2 tests) - `/` and `\` normalized correctly
    - `TestSymlinkTraversal` (2 tests) - Symlink detection (xfail - P0 gap)
    - `TestWindowsUNCPaths` (4 tests) - UNC paths, device paths blocked
    - `TestControlCharactersInPaths` (4 tests) - Null/newline/CR/tab (xfail - P1 gap)
    - `TestWindowsDriveCaseNormalization` (2 tests) - Drive case sensitivity (1 xfail)
    - `TestD3SandboxBoundary` (4 tests) - Gate validation for D3 sandbox writes
    - `TestWSP97TruthBoundaries` (4 tests) - Truth field invariants preserved
    - `TestBlockedPathOverride` (3 tests) - Blocked paths override allowed paths
    - `TestEmptyAndNullInputs` (3 tests) - Edge case input handling
    - `TestGuardIntegrationWithPathValidation` (2 tests) - Guard + path validation flow
  - Key test patterns:
    - `pytest.mark.xfail` for documenting known gaps with fix slices
    - Parametrized tests for systematic coverage
    - Helper functions for consistent request creation
  - Gaps documented (xfail):
    - P0: Symlink traversal (os.path.normpath does not resolve symlinks)
    - P1: Control characters (no explicit blocking for \x00, \n, \r)
    - P1: Windows drive case (c:\ vs C:\ may bypass checks)
  - Skipped tests: Symlink tests on Windows require admin privileges
  - Verdict: `DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TESTS_DEFINED`
- Regression: test_hxa22 (40 passed), test_hxa23 (36 passed), test_hxa30 (24 passed)
- Slice: DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TEST_IMPL_PHASE1

---

## 2026-05-13: HXA30 Scope-to-Action-Class Hermes Integration tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa30_scope_to_action_class_integration.py -v`
- Status: PASS
- Result: `24 passed`
- Notes:
  - NEW file: `test_hxa30_scope_to_action_class_integration.py` (400+ lines)
  - Tests scope-to-action-class integration in HermesJobExecutor:
    - `TestActionClassPassedToTokenValidation` - Action class flows to validator
    - `TestD3TokenD3Action` - D3 token + D3 action passes, reaches SIMULATED
    - `TestD3TokenD4Action` - D3 token + D4 action blocked at token validation
    - `TestD3TokenD5Action` - D3 token + D5 action blocked at token validation
    - `TestD3TokenD6Action` - D3 token + D6 action blocked at token validation
    - `TestD4ScopeTokenD4Action` - D4 scope passes validation, guard still blocks
    - `TestD5ScopeTokenD5Action` - D5 scope passes validation, guard still blocks
    - `TestD6ScopeTokenD6Action` - D6 scope passes validation, guard still blocks
    - `TestInvalidTokenStillBlocks` - Token validation before scope check
    - `TestNoTokenFollowsExistingBehavior` - No token = PolicyFlags control
    - `TestValidTokenDoesNotEnableLiveDelegate` - Live delegation remains disabled
    - `TestWSP97TruthFields` - All truth fields remain False
  - Key integration: Action classified at Step 2.2, passed to Step 2.3
  - Verdict: `SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED`
- Updated files:
  - `test_hxa27_hermes_token_validation_integration.py`: Added proper scopes to fixtures
  - `test_hxa29_token_scope_validation.py`: Updated expectations for HXA30 behavior
- Regression: 335 tests passing (HXA27-30 + executor)
- Slice: HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_PHASE1

---

## 2026-05-12: HXA29 Token Scope Validation tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa29_token_scope_validation.py -v`
- Status: PASS
- Result: `54 passed`
- Notes:
  - NEW file: `test_hxa29_token_scope_validation.py` (700+ lines)
  - Tests token scope validation against action classes:
    - `TestScopeConstantsExist` (6 tests) - Constants defined correctly
    - `TestD3SandboxScopeAuthorizesD3Only` (3 tests) - D3 scope authorization
    - `TestD3ScopeDoesNotAuthorizeD4` (4 tests) - D3 blocked for D4
    - `TestD3ScopeDoesNotAuthorizeD5` (4 tests) - D3 blocked for D5
    - `TestD3ScopeDoesNotAuthorizeD6` (4 tests) - D3 blocked for D6
    - `TestD4D5D6ScopesDefinedButBlocked` (3 tests) - Scopes validate, guard blocks
    - `TestMissingScopeFailsClosed` (2 tests) - Missing scope blocked
    - `TestUnknownScopeFailsClosed` (2 tests) - Unknown scope blocked
    - `TestMixedScopesObeyActionClass` (2 tests) - Multiple scopes respect class
    - `TestBlockedPathOverridesAllowedScope` (1 test) - Path blocks override scope
    - `TestPathTraversalBlocked` (2 tests) - Traversal attempts blocked
    - `TestDryRunOnlyBlocksLiveExecution` (2 tests) - dry_run_only enforced
    - `TestWSP97TruthFieldsAlwaysFalse` (4 tests) - Truth field invariants
    - `TestValidateScopeForActionClass` (14 tests) - Parametrized validation
    - `TestHXA29VerdictDocumentation` (1 test) - Verdict constant
  - Key test: `test_hxa29_verdict_token_scope_validation_defined`
  - Verdict: `TOKEN_SCOPE_VALIDATION_DEFINED`
- Scope validation behaviors tested:
  - D3 scopes (d3:sandbox, d3:evidence, d3:dry-run) authorize D3_WRITE_SANDBOX only
  - D3 scopes do NOT authorize D4_WRITE_REPO
  - D3 scopes do NOT authorize D5_EXTERNAL_SIDE_EFFECT
  - D3 scopes do NOT authorize D6_IRREVERSIBLE
  - D4/D5/D6 scopes defined but guard still blocks in Phase 1
  - Unknown scopes fail closed (return False)
  - Missing scopes fail closed (validation fails)
- WSP 97 Coverage (HXA29):
  - live_external_delegate_called=False (all scenarios)
  - verification_complete=False (all scenarios)
  - cabr_ready=False (all scenarios)
  - payout_ready=False (all scenarios)
- Slice: HXA29_TOKEN_SCOPE_VALIDATION_PHASE1

---

## 2026-05-12: HXA28 D3 Native Classification tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa28_d3_native_classification.py -v`
- Status: PASS
- Result: `132 passed`
- Notes:
  - NEW file: `test_hxa28_d3_native_classification.py` (600+ lines)
  - Tests deterministic, explicit D0-D6 classification:
    - `TestD0ObserveValidateClassification` (16 tests) - D0 prefix matching
    - `TestD1ReadFetchClassification` (12 tests) - D1 prefix matching
    - `TestD2SimulatePlanClassification` (10 tests) - D2 prefix matching
    - `TestD3SandboxWriteClassification` (10 tests) - D3 exact match + token gates
    - `TestD4RepoGitOperationsBlocked` (24 tests) - D4 blocking + no downgrade
    - `TestD5ExternalAPIMutationsBlocked` (18 tests) - D5 blocking + no downgrade
    - `TestD6IrreversibleDeleteBlocked` (20 tests) - D6 blocking + no downgrade
    - `TestAmbiguousActionsFailClosed` (10 tests) - Unknown action handling
    - `TestTokenDoesNotDowngradeClassification` (3 tests) - Token immutability
    - `TestInvalidTokenStillBlocks` (1 test) - Invalid token rejection
    - `TestWSP97TruthFieldsRemainFalse` (4 tests) - Truth field invariants
    - `TestClassificationDeterminism` (3 tests) - Case/whitespace handling
    - `TestHXA28VerdictDocumentation` (1 test) - Verdict constant
  - Key test: `test_hxa28_verdict_d3_native_classification_defined`
  - Verdict: `D3_NATIVE_CLASSIFICATION_DEFINED`
- Classification behaviors tested:
  - D0 (observe_*, validate_*, check_*, read_*, get_*, list_*) - always allowed
  - D1 (fetch_*, load_*, retrieve_*, search_*) - always allowed
  - D2 (simulate_*, plan_*, preview_*, analyze_*) - allowed in dry_run
  - D3 (build_foundup, extract_foundup, write_evidence) - requires capability tokens
  - D4 (create_repo, git_push, git_commit, modify_source) - BLOCKED Phase 1
  - D5 (send_*, email_*, webhook_*, deploy_*) - BLOCKED Phase 1
  - D6 (delete_*, purge_*, credential_*, payout_*) - BLOCKED always
- Fail-closed behavior tested:
  - Unknown actions return D6_IRREVERSIBLE
  - Empty action blocked as BLOCKED_INVALID_JOB
  - Ambiguous patterns fail to D6
- Token immutability tested:
  - Valid token does NOT downgrade D4 to D3
  - Valid token does NOT downgrade D5 to D3
  - Valid token does NOT downgrade D6 to D3
- WSP 97 Coverage (HXA28):
  - real_execution_performed=False (all classes)
  - verification_complete=False (all classes)
  - cabr_ready=False (all classes)
  - payout_ready=False (all classes)
- Slice: HXA28_D3_NATIVE_CLASSIFICATION_PHASE1

---

## 2026-05-12: test_hxa23_hermes_guard_integration.py updates

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa23_hermes_guard_integration.py -v`
- Status: PASS
- Result: `34 passed`
- Notes:
  - Updated expectations for build_foundup (now D3, was D2)
  - Changed test_extract_action_classified_as_d2 to use simulate_build
  - Changed test_build_action_classified_as_d2 to test_build_action_classified_as_d3

---

## 2026-05-12: test_hermes_job_executor.py updates

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v`
- Status: PASS
- Result: `94 passed`
- Notes:
  - Changed build_foundup to validate_foundup in TestEvidenceCollection
  - Changed build_foundup to validate_foundup in TestNoQueueConsumption
  - Changed build_foundup to validate_foundup in TestCheckpointStateSimulated
  - Reason: build_foundup is now D3 (requires tokens), validate_foundup is D0 (no tokens)

---

## 2026-05-12: HXA27 Hermes token validation integration tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa27_hermes_token_validation_integration.py -v`
- Status: PASS
- Result: `30 passed`
- Notes:
  - NEW file: `test_hxa27_hermes_token_validation_integration.py` (500+ lines)
  - Tests token validation integration into HermesJobExecutor:
    - `TestTokenValidatorInjection` (3 tests) - Validator injection
    - `TestTokenExtraction` (6 tests) - Token extraction from payload
    - `TestTokenValidationIntegration` (5 tests) - Validation in execute flow
    - `TestGuardAfterTokenValidation` (2 tests) - Guard eval after token
    - `TestWSP97TruthFields` (3 tests) - Truth field enforcement
    - `TestResultSerialization` (2 tests) - Result serialization
    - `TestNonceReplayProtection` (1 test) - Replay prevention
    - `TestD3D4D6Behavior` (2 tests) - D4-D6 still blocked
    - `TestHXA27VerdictDocumentation` (3 tests) - Verdict documentation
    - `TestModuleImports` (3 tests) - Import verification
  - Key test: `test_hxa27_verdict_hermes_token_validation_integration_defined`
  - Verdict: `HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED`
- Integration behaviors tested:
  - Token validator injectable into executor
  - Token extraction from dict and instance
  - Invalid token blocks execution (guard NOT evaluated)
  - Valid token allows proceeding (guard evaluated)
  - No token = no validation (PolicyFlags control guard)
  - Nonce replay blocked on second use
- Token failure behaviors tested:
  - TOKEN_EXPIRED
  - WRONG_AUDIENCE
  - ACTION_NOT_ALLOWED
  - REPLAY_DETECTED
- WSP 97 Coverage (HXA27):
  - token_validation_performed field added
  - token_validation_result field added
  - real_execution_performed=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Slice: HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION_PHASE1

---

## 2026-05-12: HXA26 Token validation service tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa26_token_validation_service.py -v`
- Status: PASS
- Result: `52 passed`
- Notes:
  - NEW file: `test_hxa26_token_validation_service.py` (500+ lines)
  - Tests production-ready capability token validation service:
    - `TestCapabilityTokenModel` (11 tests) - Token model fields
    - `TestTokenRedaction` (2 tests) - Security logging
    - `TestTokenValidationResult` (3 tests) - Result model
    - `TestLocalCapabilityTokenValidator` (15 tests) - All 12 validation gates
    - `TestValidatorNonceRegistry` (3 tests) - Replay prevention
    - `TestLocalCapabilityTokenIssuer` (3 tests) - Test token issuance
    - `TestDefaultValidator` (3 tests) - Singleton accessor
    - `TestWSP97TruthBoundaries` (4 tests) - Truth field enforcement
    - `TestValidatorIntegration` (2 tests) - End-to-end flows
    - `TestHXA26Verdict` (1 test) - Verdict documentation
    - `TestModuleImports` (5 tests) - Import verification
  - Key test: `test_hxa26_verdict_documented`
  - Verdict: `TOKEN_VALIDATION_SERVICE_DEFINED`
- Validation gates tested (12 total):
  - Missing token
  - Missing signature
  - Unverified signature
  - Token expired
  - Token not yet valid
  - Wrong audience
  - Wrong issuer
  - Nonce missing/replayed
  - Action not allowed
  - Scope not allowed
  - Path blocked/outside roots
  - Dry-run blocks live
- WSP 97 Coverage (HXA26):
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Slice: HXA26_TOKEN_VALIDATION_SERVICE_PHASE1

---

## 2026-05-12: HXA25 D3 sandbox execution tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa25_d3_sandbox_execution.py -v`
- Status: PASS
- Result: `24 passed`
- Notes:
  - NEW file: `test_hxa25_d3_sandbox_execution.py` (600+ lines)
  - Tests D3 sandbox dry-run execution with evidence when all gates pass:
    - `TestD3SandboxBlockedByDefault` (1 test)
    - `TestD3SandboxBlockedWithoutCapabilityTokenFlags` (1 test)
    - `TestD3SandboxBlockedIfNotValidated` (1 test)
    - `TestD3SandboxBlockedIfScopeNotAuthorized` (1 test)
    - `TestD3SandboxBlockedWithoutWorkspaceBinding` (1 test)
    - `TestD3SandboxBlockedWithoutPathConstraints` (1 test)
    - `TestD3SandboxAllowedAsDryRunWhenAllGatesTrue` (2 tests)
    - `TestAllowedD3WritesEvidenceOnly` (2 tests)
    - `TestAllowedD3DoesNotCallLiveDelegate` (2 tests)
    - `TestAllowedD3DoesNotCreateRepo` (1 test)
    - `TestAllowedD3DoesNotModifyProductionSource` (1 test)
    - `TestAllowedD3DoesNotSetRealExecutionPerformed` (1 test)
    - `TestD4D5D6BlockedEvenWithAllGatesTrue` (3 tests)
    - `TestBlockedResultKeepsTruthFieldsFalse` (2 tests)
    - `TestGuardResultContainsCorrectFields` (1 test)
    - `TestD3ClassificationWithCapabilityTokens` (2 tests)
    - `TestHXA25VerdictDocumentation` (1 test)
  - Key test: `test_hxa25_verdict_d3_sandbox_execution_defined`
  - Verdict: `D3_SANDBOX_EXECUTION_DEFINED`
- D3 allow conditions tested:
  - All four capability token flags True
  - security_gate_passed True
  - workspace_binding_enforced True
  - path_constraints_validated True
  - dry_run_mode True
- When allowed:
  - Evidence written to `.hermes_evidence/`
  - No live delegate called
  - No repo created
  - No production source modified
  - Status: SIMULATED
- WSP 97 Coverage (HXA25):
  - live_execution_allowed=False
  - live_external_delegate_called=False
  - repo_created=False
  - production_source_modified=False
  - external_federation_initiated=False
  - real_execution_performed=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Slice: HXA25_D3_SANDBOX_EXECUTION_PHASE1

---

## 2026-05-12: HXA24 Capability token policyflags tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa24_capability_token_policyflags.py -v`
- Status: PASS
- Result: `31 passed`
- Notes:
  - NEW file: `test_hxa24_capability_token_policyflags.py` (500+ lines)
  - Tests capability token policy flags in PolicyFlags and guard integration:
    - `TestPolicyFlagsCapabilityTokenFields` (5 tests)
    - `TestPolicyFlagsSerialization` (4 tests)
    - `TestJobSerializationWithCapabilityToken` (2 tests)
    - `TestDefaultPolicyFlagsBlockD3` (1 test)
    - `TestPartialCapabilityTokenFlagsBlockD3` (3 tests)
    - `TestAllFourTrueAllowsD3SandboxDryRun` (2 tests)
    - `TestD4D5D6StillBlockedEvenWithToken` (3 tests)
    - `TestWSP97TruthFieldsPreserved` (7 tests)
    - `TestGuardRequestConstruction` (3 tests)
    - `TestHXA24VerdictDocumentation` (1 test)
  - Key test: `test_all_four_true_with_security_gate_allows_d3`
  - Verdict: `CAPABILITY_TOKEN_POLICYFLAGS_DEFINED`
- Capability token logic tested:
  - Default flags (all False) block D3
  - Partial flags (some False) block D3
  - All four True + security gate allows D3 dry-run
  - D4/D5/D6 blocked regardless of token flags
- WSP 97 Coverage (HXA24):
  - live_execution_allowed=False
  - repo_created=False
  - production_source_modified=False
  - real_execution_performed=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Slice: HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1

---

## 2026-05-12: HXA23 Hermes guard integration tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa23_hermes_guard_integration.py -v`
- Status: PASS
- Result: `34 passed`
- Notes:
  - NEW file: `test_hxa23_hermes_guard_integration.py` (800+ lines)
  - Integration tests for HXA22 guard into HermesJobExecutor:
    - `TestHermesCallsDestructiveGuard` (4 tests)
    - `TestD0D1D2D3AllowedAsDryRunOnly` (5 tests)
    - `TestD4RepoWriteBlocked` (2 tests)
    - `TestD5ExternalSideEffectBlocked` (2 tests)
    - `TestD6IrreversibleBlocked` (1 test)
    - `TestBlockedGuardDoesNotWriteFiles` (3 tests)
    - `TestWSP97TruthFieldsPreserved` (8 tests)
    - `TestEvidenceCheckpointFieldsPreserved` (2 tests)
    - `TestD3MissingGatesBlocked` (2 tests)
    - `TestGuardIntegrationFlow` (2 tests)
    - `TestExistingDryRunBehaviorPreserved` (2 tests)
    - `TestHXA23VerdictDocumentation` (1 test)
  - Key test: `test_complete_guard_integration_flow`
  - Verdict: `HERMES_GUARD_INTEGRATION_DEFINED`
- WSP 97 Coverage (HXA23):
  - live_external_delegate_called=False
  - repo_created=False
  - production_source_modified=False
  - external_federation_initiated=False
  - real_execution_performed=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Integration behaviors tested:
  - Guard evaluated before delegation paths
  - D0/D1/D2 allowed as dry-run
  - D4/D5/D6 blocked by guard
  - Blocked guard does not call delegate adapter
  - Existing dry-run behavior preserved
- Slice: HXA23_HERMES_GUARD_INTEGRATION_PHASE1

---

## 2026-05-12: HXA22 Destructive action guard runtime tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa22_destructive_action_guard_runtime.py -v`
- Status: PASS
- Result: `40 passed`
- Notes:
  - NEW file: `test_hxa22_destructive_action_guard_runtime.py` (700+ lines)
  - NEW file: `src/destructive_action_guard.py` (450+ lines) - production code
  - Fail-closed destructive action guard with D0-D6 classification:
    - `DestructiveActionClass`: D0_OBSERVE through D6_IRREVERSIBLE
    - `DestructiveActionRequest`: Request model with all gate requirements
    - `DestructiveActionGuardResult`: Result with WSP 97 truth fields
    - `DestructiveActionGuard`: Fail-closed evaluator
  - Test classes:
    - `TestDestructiveActionClassEnum` (3 tests)
    - `TestDestructiveActionRequest` (3 tests)
    - `TestDestructiveActionGuardResult` (2 tests)
    - `TestD0ObserveDryRunAllowed` (1 test)
    - `TestD1ReadDryRunAllowed` (1 test)
    - `TestD2SimulateAllowed` (1 test)
    - `TestD3SandboxWriteGates` (5 tests)
    - `TestD4RepoWriteBlocked` (1 test)
    - `TestD5ExternalSideEffectBlocked` (1 test)
    - `TestD6IrreversibleBlocked` (1 test)
    - `TestLiveExecutionAlwaysFalse` (2 tests)
    - `TestRepoCreatedAlwaysFalse` (2 tests)
    - `TestProductionSourceModifiedAlwaysFalse` (2 tests)
    - `TestExternalFederationInitiatedAlwaysFalse` (2 tests)
    - `TestVerificationCompleteAlwaysFalse` (2 tests)
    - `TestCABRReadyAlwaysFalse` (2 tests)
    - `TestPayoutReadyAlwaysFalse` (2 tests)
    - `TestConvenienceFunctions` (2 tests)
    - `TestWSP97TruthFieldsPreserved` (2 tests)
    - `TestHXA22CompleteGuardFlow` (2 tests)
    - `TestHXA22VerdictDocumentation` (1 test)
  - Key test: `test_complete_guard_evaluation_flow`
  - Verdict: `DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED`
- WSP 97 Coverage (HXA22):
  - live_execution_allowed=False (Phase 1 blocks live execution)
  - repo_created=False (no GitHub operations)
  - production_source_modified=False (no source modifications)
  - external_federation_initiated=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Fail-closed rules tested (7 blocking scenarios):
  - D3 without workspace_binding -> MISSING_WORKSPACE_BINDING
  - D3 without path_validation -> MISSING_PATH_VALIDATION
  - D3 without capability_token -> MISSING_CAPABILITY_TOKEN
  - D3 without security_gate -> MISSING_SECURITY_GATE
  - D4 repo write -> BLOCKED_D4_REPO_WRITE_PHASE1
  - D5 external side effect -> BLOCKED_D5_EXTERNAL_PHASE1
  - D6 irreversible -> BLOCKED_D6_IRREVERSIBLE_PHASE1
- Slice: HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1

---

## 2026-05-12: HXA21 Capability token infrastructure tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa21_capability_token_infrastructure.py -v`
- Status: PASS
- Result: `42 passed`
- Notes:
  - NEW file: `test_hxa21_capability_token_infrastructure.py` (800+ lines)
  - Test-only capability token infrastructure (no production code modified):
    - `CapabilityToken`: Token model with all required fields
    - `TokenValidationReasonCode`: Enum of validation failure reasons (15 codes)
    - `TokenValidationResult`: Validation result with all failure details
    - `FakeTokenIssuer`: Test fixture that issues fake tokens (no real secrets)
    - `FakeTokenValidator`: Test fixture with in-memory nonce registry
    - `WSP97TruthTracker`: Truth field tracker for validation
  - Test classes:
    - `TestCapabilityTokenModel` (11 tests)
    - `TestTokenValidationResult` (2 tests)
    - `TestFakeTokenIssuer` (2 tests)
    - `TestFakeTokenValidator` (15 tests)
    - `TestTokenRedaction` (2 tests)
    - `TestWSP97TruthFieldsPreserved` (10 tests)
    - `TestHXA21CompleteCapabilityToken` (2 tests)
    - `TestHXA21VerdictDocumentation` (1 test)
  - Key test: `test_complete_token_validation_flow`
  - Verdict: `CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED`
- WSP 97 Coverage (HXA21):
  - repo_created=False (no GitHub operations)
  - production_source_modified=False (no source modifications)
  - network_called=False (no network calls)
  - live_external_delegate_called=False
  - external_federation_initiated=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Validation failure modes tested (12 total):
  - MISSING_TOKEN
  - MISSING_SIGNATURE
  - SIGNATURE_NOT_VERIFIED
  - TOKEN_EXPIRED
  - WRONG_AUDIENCE
  - REPLAY_DETECTED
  - ACTION_NOT_ALLOWED
  - SCOPE_NOT_ALLOWED
  - PATH_OUTSIDE_ALLOWED_ROOTS
  - PATH_IN_BLOCKED_LIST
  - DRY_RUN_ONLY_BLOCKS_LIVE
  - VALID_DRY_RUN_ONLY (success case)
- Slice: HXA21_CAPABILITY_TOKEN_INFRASTRUCTURE_PHASE1

---

## 2026-05-12: HXA20 Production source modification gate tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa20_production_source_gate.py -v`
- Status: PASS
- Result: `32 passed`
- Notes:
  - NEW file: `test_hxa20_production_source_gate.py` (650+ lines)
  - Test-only approval gate contract (no production code modified):
    - `ProductionSourceGate`: Gate model with all required fields
    - `ProductionSourceBlockReason`: Enum of blocking reasons (10 conditions)
    - `ProductionSourceGateResult`: Enum of gate results (BLOCKED, SIMULATED_ONLY)
    - `DestructiveClass`: D0-D6 destructive action classification
    - `FakePatchAdapter`: Test fixture that never modifies production source
    - `FakePatchAdapterResult`: Result type with WSP 97 fields
  - Test classes:
    - `TestProductionSourceGateModel` (3 tests)
    - `TestProductionSourceGateBlocking` (9 tests)
    - `TestProductionSourceDryRunSimulation` (2 tests)
    - `TestFakePatchAdapter` (6 tests)
    - `TestNoWritesOutsideTmpDir` (1 test)
    - `TestWSP97TruthFieldsPreserved` (5 tests)
    - `TestLiveExternalDelegateCalledFalse` (1 test)
    - `TestVerificationCompleteCABRPayoutFalse` (1 test)
    - `TestExternalFederationInitiatedFalse` (1 test)
    - `TestHXA20CompleteSourceGate` (2 tests)
    - `TestHXA20VerdictDocumentation` (1 test)
  - Key test: `test_complete_source_gate_contract`
  - Verdict: `PRODUCTION_SOURCE_GATE_DEFINED`
- WSP 97 Coverage (HXA20):
  - production_source_modified=False (no file modifications)
  - file_written=False (no file writes)
  - network_called=False (no network calls)
  - repo_created=False (no GitHub operations)
  - live_external_delegate_called=False
  - external_federation_initiated=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Block conditions tested (10 total):
  - MISSING_HUMAN_APPROVAL
  - MISSING_CAPABILITY_TOKEN
  - SECURITY_GATE_NOT_PASSED
  - TARGET_PATH_OUTSIDE_ALLOWED_ROOTS
  - TARGET_PATH_IN_BLOCKED_PATHS
  - WORKSPACE_BINDING_NOT_ENFORCED
  - PATH_CONSTRAINTS_NOT_VALIDATED
  - UNSUPPORTED_OPERATION
  - DESTRUCTIVE_CLASS_ABOVE_THRESHOLD
  - DRY_RUN_MODE_ACTIVE (returns SIMULATED_ONLY)
- Slice: HXA20_PRODUCTION_SOURCE_GATE_PHASE1

---

## 2026-05-12: HXA19 Repo creation approval gate tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa19_repo_creation_approval_gate.py -v`
- Status: PASS
- Result: `35 passed`
- Notes:
  - NEW file: `test_hxa19_repo_creation_approval_gate.py` (580 lines)
  - Test-only approval gate contract (no production code modified):
    - `RepoCreationApproval`: Approval model with all required fields
    - `RepoCreationBlockReason`: Enum of blocking reasons
    - `RepoCreationGateResult`: Enum of gate results (BLOCKED, APPROVED_DRY_RUN_ONLY)
    - `FakeRepoAdapter`: Test fixture that never creates repos
    - `FakeRepoAdapterResult`: Result type with WSP 97 fields
  - Test classes:
    - `TestRepoCreationApprovalModel` (11 tests)
    - `TestRepoCreationGateBlocking` (6 tests)
    - `TestRepoCreationDryRunApproval` (2 tests)
    - `TestFakeRepoAdapter` (6 tests)
    - `TestWSP97TruthFieldsPreserved` (4 tests)
    - `TestLiveExternalDelegateCalledFalse` (1 test)
    - `TestExternalFederationInitiatedFalse` (1 test)
    - `TestVerificationCompleteCABRPayoutFalse` (1 test)
    - `TestHXA19CompleteApprovalGate` (2 tests)
    - `TestHXA19VerdictDocumentation` (1 test)
  - Key test: `test_complete_approval_gate_contract`
  - Verdict: `REPO_CREATION_APPROVAL_GATE_DEFINED`
- WSP 97 Coverage (HXA19):
  - repo_created=False (no GitHub operations)
  - network_called=False (no network calls)
  - production_source_modified=False
  - live_external_delegate_called=False
  - external_federation_initiated=False
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Block conditions tested:
  - MISSING_HUMAN_APPROVAL
  - MISSING_CAPABILITY_TOKEN
  - SECURITY_GATE_NOT_PASSED
  - APPROVAL_EXPIRED
  - TARGET_ORG_NOT_ALLOWLISTED
  - REPO_NAME_INVALID
  - DRY_RUN_MODE_ACTIVE (returns APPROVED_DRY_RUN_ONLY)
- Slice: HXA19_REPO_CREATION_APPROVAL_GATE_PHASE1

---

## 2026-05-12: HXA18 Hermes runtime fixture safe harness tests

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_hxa18_hermes_runtime_fixture_safe_harness.py -v`
- Status: PASS
- Result: `35 passed`
- Notes:
  - NEW file: `test_hxa18_hermes_runtime_fixture_safe_harness.py` (620 lines)
  - Test-only fixture objects (no production code modified):
    - `FakeHermesParentAgent`: Satisfies parent_agent interface
    - `FakeToolsetRegistry`: Satisfies toolsets interface (read-only)
    - `RedactedCredentials`: Satisfies credentials interface (redacted)
    - `InMemoryTerminalSessions`: Satisfies terminal_sessions interface
    - `FakeDelegateAdapter`: Records calls without real delegation
    - `HermesRuntimeFixture`: Bundles all fixtures
  - Test classes:
    - `TestRuntimeFixtureSuppliesParentAgent` (5 tests)
    - `TestRuntimeFixtureSuppliesToolsets` (4 tests)
    - `TestRuntimeFixtureUsesRedactedCredentialsOnly` (6 tests)
    - `TestRuntimeFixtureUsesInMemoryTerminalSessions` (4 tests)
    - `TestSafeDelegateAdapterInvoked` (3 tests)
    - `TestLiveExternalDelegateCalledFalse` (2 tests)
    - `TestRepoCreatedFalse` (2 tests)
    - `TestProductionSourceModifiedFalse` (2 tests)
    - `TestNoNetworkOrRealCredentials` (2 tests)
    - `TestEvidenceOrCheckpointTruthFieldsPreserved` (2 tests)
    - `TestHXA18CompleteFixtureHarness` (2 tests)
    - `TestHXA18VerdictDocumentation` (1 test)
  - Key test: `test_complete_fixture_harness_satisfies_runtime_surface`
  - Verdict: `RUNTIME_FIXTURE_HARNESS_SATISFIES_MISSING_SURFACE`
- WSP 97 Coverage (HXA18):
  - real_delegate_adapter_invoked=True (for local fake adapter only)
  - live_external_delegate_called=False (no real external delegation)
  - repo_created=False (no GitHub)
  - production_source_modified=False
  - external_federation_initiated=False
  - production_readiness_claimed=False
  - real_execution_performed=False (test fixtures only)
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
- Slice: HXA18_HERMES_RUNTIME_FIXTURE_SAFE_HARNESS_PHASE1

---

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
