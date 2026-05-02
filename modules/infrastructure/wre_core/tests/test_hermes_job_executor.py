#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for HermesJobExecutor adapter seam.

Verifies:
  - FoundUpJob maps to HermesDelegationRequest
  - dry_run defaults True
  - delegate_task is NOT called when HERMES_DELEGATE_ENABLED unset
  - Result preserves WSP 97 false fields
  - Import failure returns BLOCKED_IMPORT_UNAVAILABLE
  - No CABR/reward/payout/token fields exist
  - No queue consumption occurs in this adapter

Run with:
    python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v

Slice: HERMES_JOB_EXECUTOR_ADAPTER_PHASE1
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "modules", "communication", "moltbot_bridge", "src"))

from hermes_job_executor import (
    HermesDelegationRequest,
    HermesDelegationResult,
    HermesExecutionStatus,
    HermesJobExecutor,
    WorkspaceBinding,
    BLOCKED_PATHS,
    ACTION_ALLOWED_PATHS,
    build_allowed_paths,
    get_evidence_output_path,
    is_hermes_delegation_enabled,
    get_executor,
    execute_foundup_job,
)
from foundup_job_contract import (
    FoundUpJob,
    PolicyFlags,
    JobStatus,
    create_job,
)


class TestFeatureFlag(unittest.TestCase):
    """Test HERMES_DELEGATE_ENABLED feature flag."""

    def test_default_disabled(self):
        """Feature flag defaults to disabled."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key entirely
            os.environ.pop("HERMES_DELEGATE_ENABLED", None)
            self.assertFalse(is_hermes_delegation_enabled())

    def test_explicit_zero_disabled(self):
        """HERMES_DELEGATE_ENABLED=0 is disabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            self.assertFalse(is_hermes_delegation_enabled())

    def test_explicit_one_enabled(self):
        """HERMES_DELEGATE_ENABLED=1 is enabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            self.assertTrue(is_hermes_delegation_enabled())

    def test_explicit_true_enabled(self):
        """HERMES_DELEGATE_ENABLED=true is enabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "true"}):
            self.assertTrue(is_hermes_delegation_enabled())

    def test_explicit_yes_enabled(self):
        """HERMES_DELEGATE_ENABLED=yes is enabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "yes"}):
            self.assertTrue(is_hermes_delegation_enabled())


class TestHermesDelegationRequest(unittest.TestCase):
    """Test HermesDelegationRequest dataclass."""

    def test_default_dry_run_true(self):
        """Request defaults to dry_run=True."""
        request = HermesDelegationRequest(goal="test", context="ctx")
        self.assertTrue(request.dry_run)

    def test_default_toolsets_empty(self):
        """Request defaults to empty toolsets."""
        request = HermesDelegationRequest(goal="test", context="ctx")
        self.assertEqual(request.toolsets, [])

    def test_to_dict_serializes_all_fields(self):
        """to_dict includes all fields."""
        request = HermesDelegationRequest(
            goal="Build foundup",
            context="Context here",
            toolsets=["terminal"],
            max_iterations=25,
            job_id="j_build_123",
            foundup_id="gotjunk",
            tenant_id="tenant_a",
            requested_action="build_foundup",
            policy_snapshot={"security_gate_passed": True},
            dry_run=False,
        )
        d = request.to_dict()

        self.assertEqual(d["goal"], "Build foundup")
        self.assertEqual(d["context"], "Context here")
        self.assertEqual(d["toolsets"], ["terminal"])
        self.assertEqual(d["max_iterations"], 25)
        self.assertEqual(d["job_id"], "j_build_123")
        self.assertEqual(d["foundup_id"], "gotjunk")
        self.assertEqual(d["tenant_id"], "tenant_a")
        self.assertEqual(d["requested_action"], "build_foundup")
        self.assertEqual(d["policy_snapshot"], {"security_gate_passed": True})
        self.assertFalse(d["dry_run"])
        self.assertIn("created_at", d)


class TestHermesDelegationResult(unittest.TestCase):
    """Test HermesDelegationResult dataclass."""

    def test_wsp97_truth_fields_default_false(self):
        """WSP 97 truth fields default to False."""
        result = HermesDelegationResult(
            status=HermesExecutionStatus.SIMULATED,
            status_reason="Test",
        )
        self.assertFalse(result.real_execution_performed)
        self.assertFalse(result.verification_complete)
        self.assertFalse(result.cabr_ready)
        self.assertFalse(result.payout_ready)

    def test_no_cabr_token_payout_reward_fields(self):
        """Result has NO CABR/token/payout/reward fields."""
        result = HermesDelegationResult(
            status=HermesExecutionStatus.SIMULATED,
            status_reason="Test",
        )

        # These fields MUST NOT exist
        self.assertFalse(hasattr(result, "token_balance"))
        self.assertFalse(hasattr(result, "reward_amount"))
        self.assertFalse(hasattr(result, "cabr_score"))
        self.assertFalse(hasattr(result, "payout_amount"))
        self.assertFalse(hasattr(result, "fi_tokens"))

    def test_to_dict_serializes_all_fields(self):
        """to_dict includes all fields."""
        request = HermesDelegationRequest(goal="test", context="ctx")
        result = HermesDelegationResult(
            status=HermesExecutionStatus.SIMULATED,
            status_reason="Simulated run",
            request=request,
            duration_seconds=1.5,
            api_calls=0,
        )
        d = result.to_dict()

        self.assertEqual(d["status"], "SIMULATED")
        self.assertEqual(d["status_reason"], "Simulated run")
        self.assertIsNotNone(d["request"])
        self.assertEqual(d["duration_seconds"], 1.5)
        self.assertEqual(d["api_calls"], 0)
        self.assertFalse(d["real_execution_performed"])
        self.assertFalse(d["verification_complete"])
        self.assertFalse(d["cabr_ready"])
        self.assertFalse(d["payout_ready"])


class TestFoundUpJobMapping(unittest.TestCase):
    """Test FoundUpJob -> HermesDelegationRequest mapping."""

    def test_maps_core_identity_fields(self):
        """Request includes job_id, foundup_id, tenant_id."""
        job = create_job(
            tenant_id="tenant_123",
            requested_action="build_foundup",
            foundup_id="social_twin",
            intent_id="intent_abc",
        )

        executor = HermesJobExecutor()
        request = executor.build_delegation_request(job)

        self.assertEqual(request.job_id, job.job_id)
        self.assertEqual(request.foundup_id, "social_twin")
        self.assertEqual(request.tenant_id, "tenant_123")

    def test_maps_requested_action(self):
        """Request includes requested_action."""
        job = create_job(
            tenant_id="t1",
            requested_action="extract_foundup",
        )

        executor = HermesJobExecutor()
        request = executor.build_delegation_request(job)

        self.assertEqual(request.requested_action, "extract_foundup")

    def test_builds_goal_from_action(self):
        """Goal string derived from requested_action."""
        test_cases = [
            ("build_foundup", "Build FoundUp"),
            ("extract_foundup", "Extract FoundUp"),
            ("validate_foundup", "Validate FoundUp"),
            ("queue_foundup_job", "Queue job"),
        ]

        for action, expected_substring in test_cases:
            job = create_job(
                tenant_id="t1",
                requested_action=action,
                foundup_id="test_foundup",
            )
            executor = HermesJobExecutor()
            request = executor.build_delegation_request(job)
            self.assertIn(expected_substring, request.goal, f"Action {action} should produce goal with '{expected_substring}'")

    def test_context_includes_payload(self):
        """Context includes serialized payload."""
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            payload={"key": "value", "nested": {"a": 1}},
        )

        executor = HermesJobExecutor()
        request = executor.build_delegation_request(job)

        self.assertIn("key", request.context)
        self.assertIn("value", request.context)

    def test_policy_snapshot_copied(self):
        """Policy flags snapshot included in request."""
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
        )
        job.policy_flags.security_gate_passed = True
        job.policy_flags.permission_gate_checked = True

        executor = HermesJobExecutor()
        request = executor.build_delegation_request(job)

        self.assertTrue(request.policy_snapshot["security_gate_passed"])
        self.assertTrue(request.policy_snapshot["permission_gate_checked"])


class TestExecutorDryRunDefault(unittest.TestCase):
    """Test executor dry_run defaults."""

    def test_executor_defaults_dry_run_true(self):
        """Executor defaults to dry_run=True."""
        executor = HermesJobExecutor()
        self.assertTrue(executor.dry_run)

    def test_request_inherits_dry_run(self):
        """Request inherits dry_run from executor."""
        executor = HermesJobExecutor(dry_run=True)
        job = create_job(tenant_id="t1", requested_action="build_foundup")
        request = executor.build_delegation_request(job)
        self.assertTrue(request.dry_run)

        executor_live = HermesJobExecutor(dry_run=False)
        request_live = executor_live.build_delegation_request(job)
        self.assertFalse(request_live.dry_run)


class TestExecutorFeatureFlagDisabled(unittest.TestCase):
    """Test executor behavior when feature flag disabled."""

    def test_returns_simulated_when_disabled(self):
        """Execute returns SIMULATED when HERMES_DELEGATE_ENABLED=0."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")
            executor = HermesJobExecutor()
            result = executor.execute(job)

            self.assertEqual(result.status, HermesExecutionStatus.SIMULATED)
            self.assertFalse(result.real_execution_performed)

    def test_delegate_task_not_called_when_disabled(self):
        """delegate_task is NOT imported/called when disabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            executor = HermesJobExecutor()

            # Verify import was not attempted
            self.assertFalse(executor._import_attempted)

            job = create_job(tenant_id="t1", requested_action="build_foundup")
            result = executor.execute(job)

            # Import should still not be attempted (fast path)
            self.assertFalse(executor._import_attempted)
            self.assertEqual(result.status, HermesExecutionStatus.SIMULATED)

    def test_wsp97_fields_false_when_disabled(self):
        """WSP 97 truth fields remain False when disabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")
            executor = HermesJobExecutor()
            result = executor.execute(job)

            self.assertFalse(result.real_execution_performed)
            self.assertFalse(result.verification_complete)
            self.assertFalse(result.cabr_ready)
            self.assertFalse(result.payout_ready)


class TestExecutorDryRunMode(unittest.TestCase):
    """Test executor behavior with dry_run=True (even if flag enabled)."""

    def test_returns_simulated_when_dry_run(self):
        """Execute returns SIMULATED when dry_run=True even if flag enabled."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")
            executor = HermesJobExecutor(dry_run=True)  # Explicit dry_run
            result = executor.execute(job)

            self.assertEqual(result.status, HermesExecutionStatus.SIMULATED)
            self.assertIn("dry_run=True", result.status_reason)


class TestExecutorImportFailure(unittest.TestCase):
    """Test executor behavior when Hermes import fails."""

    def test_returns_blocked_on_import_failure(self):
        """Execute returns BLOCKED_IMPORT_UNAVAILABLE on import error."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            executor = HermesJobExecutor(dry_run=False)

            # Simulate import failure
            with patch.object(
                executor,
                "_lazy_import_delegate_task",
                return_value=False,
            ):
                executor._import_error = "No module named 'vendor.hermes_agent'"

                job = create_job(tenant_id="t1", requested_action="build_foundup")
                result = executor.execute(job)

                self.assertEqual(result.status, HermesExecutionStatus.BLOCKED_IMPORT_UNAVAILABLE)
                self.assertIn("Cannot import", result.status_reason)
                self.assertFalse(result.real_execution_performed)


class TestExecutorRealDelegationBlocked(unittest.TestCase):
    """Test executor blocks real delegation in Phase 1."""

    def test_returns_blocked_when_enabled_not_dry_run(self):
        """Execute returns BLOCKED when enabled and dry_run=False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            executor = HermesJobExecutor(dry_run=False)

            # Simulate successful import
            executor._import_attempted = True
            executor._delegate_task_fn = MagicMock()

            job = create_job(tenant_id="t1", requested_action="build_foundup")
            result = executor.execute(job)

            self.assertEqual(
                result.status,
                HermesExecutionStatus.BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED,
            )
            self.assertIn("not implemented", result.status_reason.lower())
            self.assertFalse(result.real_execution_performed)

    def test_delegate_task_not_actually_called(self):
        """delegate_task function is NOT called even when import succeeds."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            executor = HermesJobExecutor(dry_run=False)

            mock_delegate = MagicMock()
            executor._import_attempted = True
            executor._delegate_task_fn = mock_delegate

            job = create_job(tenant_id="t1", requested_action="build_foundup")
            result = executor.execute(job)

            # Verify delegate_task was NOT called
            mock_delegate.assert_not_called()
            self.assertEqual(
                result.status,
                HermesExecutionStatus.BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED,
            )


class TestExecutorJobValidation(unittest.TestCase):
    """Test executor job validation."""

    def test_rejects_none_job(self):
        """Execute returns error for None job."""
        executor = HermesJobExecutor()
        result = executor.execute(None)

        self.assertEqual(result.status, HermesExecutionStatus.BLOCKED_INVALID_JOB)
        self.assertIn("None", result.status_reason)

    def test_rejects_missing_job_id(self):
        """Execute returns error for job without job_id."""
        executor = HermesJobExecutor()

        # Create job then clear job_id
        job = create_job(tenant_id="t1", requested_action="build_foundup")
        job.job_id = ""

        result = executor.execute(job)

        self.assertEqual(result.status, HermesExecutionStatus.BLOCKED_INVALID_JOB)
        self.assertIn("job_id", result.status_reason)

    def test_rejects_missing_tenant_id(self):
        """Execute returns error for job without tenant_id."""
        executor = HermesJobExecutor()

        job = create_job(tenant_id="t1", requested_action="build_foundup")
        job.tenant_id = ""

        result = executor.execute(job)

        self.assertEqual(result.status, HermesExecutionStatus.BLOCKED_INVALID_JOB)
        self.assertIn("tenant_id", result.status_reason)

    def test_rejects_missing_requested_action(self):
        """Execute returns error for job without requested_action."""
        executor = HermesJobExecutor()

        job = create_job(tenant_id="t1", requested_action="build_foundup")
        job.requested_action = ""

        result = executor.execute(job)

        self.assertEqual(result.status, HermesExecutionStatus.BLOCKED_INVALID_JOB)
        self.assertIn("requested_action", result.status_reason)


class TestNoQueueConsumption(unittest.TestCase):
    """Test that executor does NOT consume from any queue."""

    def test_execute_does_not_modify_job_status(self):
        """Execute does NOT transition job status."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")
            original_status = job.status

            executor = HermesJobExecutor()
            result = executor.execute(job)

            # Job status unchanged
            self.assertEqual(job.status, original_status)
            self.assertEqual(job.status, JobStatus.QUEUED)

    def test_execute_does_not_call_job_start(self):
        """Execute does NOT call job.start()."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")

            with patch.object(job, "start") as mock_start:
                executor = HermesJobExecutor()
                executor.execute(job)

                mock_start.assert_not_called()


class TestSingletonExecutor(unittest.TestCase):
    """Test singleton executor functions."""

    def test_get_executor_returns_singleton(self):
        """get_executor returns same instance."""
        # Reset singleton
        import hermes_job_executor
        hermes_job_executor._executor_singleton = None

        exec1 = get_executor()
        exec2 = get_executor()

        self.assertIs(exec1, exec2)

    def test_execute_foundup_job_convenience(self):
        """execute_foundup_job uses default executor."""
        # Reset singleton
        import hermes_job_executor
        hermes_job_executor._executor_singleton = None

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            job = create_job(tenant_id="t1", requested_action="build_foundup")
            result = execute_foundup_job(job)

            self.assertEqual(result.status, HermesExecutionStatus.SIMULATED)


# ---------------------------------------------------------------------------
# Workspace Binding Tests (HERMES_WORKSPACE_BINDING_CONTRACT_PHASE1)
# ---------------------------------------------------------------------------


class TestWorkspaceBindingDataclass(unittest.TestCase):
    """Test WorkspaceBinding dataclass."""

    def test_to_dict_serializes_all_fields(self):
        """WorkspaceBinding.to_dict includes all fields."""
        binding = WorkspaceBinding(
            workspace_root="/path/to/repo",
            workspace_hint="modules/foundups/gotjunk",
            allowed_paths=["modules/foundups/gotjunk/", ".hermes_evidence/j_123/"],
            blocked_paths=[".env", "*.pem"],
            evidence_output_path="/path/to/repo/.hermes_evidence/j_123",
            retention_on_failure="preserve",
        )
        d = binding.to_dict()

        self.assertEqual(d["workspace_root"], "/path/to/repo")
        self.assertEqual(d["workspace_hint"], "modules/foundups/gotjunk")
        self.assertEqual(d["allowed_paths"], ["modules/foundups/gotjunk/", ".hermes_evidence/j_123/"])
        self.assertIn(".env", d["blocked_paths"])
        self.assertEqual(d["evidence_output_path"], "/path/to/repo/.hermes_evidence/j_123")
        self.assertEqual(d["retention_on_failure"], "preserve")


class TestWorkspaceBindingPathValidation(unittest.TestCase):
    """Test WorkspaceBinding.is_path_allowed method."""

    def test_allowed_path_within_scope(self):
        """Path within allowed_paths is allowed."""
        binding = WorkspaceBinding(
            workspace_root="/repo",
            allowed_paths=["modules/foundups/gotjunk/"],
            blocked_paths=list(BLOCKED_PATHS),
        )

        self.assertTrue(binding.is_path_allowed("modules/foundups/gotjunk/src/main.py"))
        self.assertTrue(binding.is_path_allowed("modules/foundups/gotjunk/README.md"))

    def test_path_outside_allowed_rejected(self):
        """Path outside allowed_paths is rejected."""
        binding = WorkspaceBinding(
            workspace_root="/repo",
            allowed_paths=["modules/foundups/gotjunk/"],
            blocked_paths=list(BLOCKED_PATHS),
        )

        self.assertFalse(binding.is_path_allowed("modules/foundups/social_twin/src/main.py"))
        self.assertFalse(binding.is_path_allowed("holo_index/core/indexing.py"))

    def test_blocked_path_rejected(self):
        """Path matching blocked_paths is rejected even if in allowed_paths."""
        binding = WorkspaceBinding(
            workspace_root="/repo",
            allowed_paths=["modules/foundups/gotjunk/"],
            blocked_paths=[".env", "*.pem", "**/secrets/"],
        )

        # These should be rejected due to blocked patterns
        self.assertFalse(binding.is_path_allowed(".env"))
        self.assertFalse(binding.is_path_allowed("cert.pem"))
        self.assertFalse(binding.is_path_allowed("modules/foundups/gotjunk/secrets/api.json"))

    def test_env_patterns_blocked(self):
        """All .env patterns are blocked."""
        binding = WorkspaceBinding(
            workspace_root="/repo",
            allowed_paths=["./"],  # Allow everything...
            blocked_paths=list(BLOCKED_PATHS),  # ...except blocked
        )

        self.assertFalse(binding.is_path_allowed(".env"))
        self.assertFalse(binding.is_path_allowed(".env.local"))
        self.assertFalse(binding.is_path_allowed(".env.production"))

    def test_vendor_path_blocked(self):
        """vendor/ is always blocked (Hermes cannot modify itself)."""
        binding = WorkspaceBinding(
            workspace_root="/repo",
            allowed_paths=["./"],
            blocked_paths=list(BLOCKED_PATHS),
        )

        self.assertFalse(binding.is_path_allowed("vendor/hermes-agent/tools/delegate.py"))


class TestBlockedPathsConstant(unittest.TestCase):
    """Test BLOCKED_PATHS security constant."""

    def test_blocked_paths_includes_env(self):
        """.env patterns in BLOCKED_PATHS."""
        self.assertIn(".env", BLOCKED_PATHS)
        self.assertIn(".env.*", BLOCKED_PATHS)

    def test_blocked_paths_includes_secrets(self):
        """secrets/ and credentials/ in BLOCKED_PATHS."""
        self.assertIn("**/secrets/", BLOCKED_PATHS)
        self.assertIn("**/credentials/", BLOCKED_PATHS)

    def test_blocked_paths_includes_vendor(self):
        """vendor/ in BLOCKED_PATHS."""
        self.assertIn("vendor/", BLOCKED_PATHS)

    def test_blocked_paths_includes_keys(self):
        """Key file patterns in BLOCKED_PATHS."""
        self.assertIn("*.pem", BLOCKED_PATHS)
        self.assertIn("*.key", BLOCKED_PATHS)

    def test_blocked_paths_is_frozenset(self):
        """BLOCKED_PATHS is immutable."""
        self.assertIsInstance(BLOCKED_PATHS, frozenset)


class TestBuildAllowedPaths(unittest.TestCase):
    """Test build_allowed_paths function."""

    def test_build_foundup_includes_foundup_path(self):
        """build_foundup action includes modules/foundups/{foundup_id}/."""
        paths = build_allowed_paths(
            action="build_foundup",
            foundup_id="gotjunk",
            job_id="j_123",
        )

        self.assertIn("modules/foundups/gotjunk/", paths)
        self.assertIn(".hermes_evidence/j_123/", paths)

    def test_validate_foundup_includes_foundup_path(self):
        """validate_foundup action includes foundup path."""
        paths = build_allowed_paths(
            action="validate_foundup",
            foundup_id="social_twin",
            job_id="j_456",
        )

        self.assertIn("modules/foundups/social_twin/", paths)

    def test_queue_job_only_evidence_path(self):
        """queue_foundup_job action only includes evidence path."""
        paths = build_allowed_paths(
            action="queue_foundup_job",
            foundup_id="any",
            job_id="j_789",
        )

        self.assertEqual(paths, [".hermes_evidence/j_789/"])

    def test_no_foundup_id_uses_default(self):
        """No foundup_id falls back to evidence-only paths."""
        paths = build_allowed_paths(
            action="build_foundup",
            foundup_id=None,
            job_id="j_abc",
        )

        self.assertEqual(paths, [".hermes_evidence/j_abc/"])

    def test_unknown_action_uses_default(self):
        """Unknown action uses default paths."""
        paths = build_allowed_paths(
            action="unknown_action",
            foundup_id="test",
            job_id="j_def",
        )

        self.assertEqual(paths, [".hermes_evidence/j_def/"])


class TestGetEvidenceOutputPath(unittest.TestCase):
    """Test get_evidence_output_path function."""

    def test_includes_job_id(self):
        """Evidence path includes job_id."""
        path = get_evidence_output_path(
            workspace_root="/path/to/repo",
            job_id="j_build_123",
        )

        self.assertIn("j_build_123", path)
        self.assertIn(".hermes_evidence", path)

    def test_absolute_path(self):
        """Evidence path is absolute (starts with workspace_root)."""
        path = get_evidence_output_path(
            workspace_root="/path/to/repo",
            job_id="j_test",
        )

        self.assertTrue(path.startswith("/path/to/repo"))


class TestWorkspaceHintInRequest(unittest.TestCase):
    """Test workspace_hint is included in HermesDelegationRequest."""

    def test_workspace_binding_field_exists(self):
        """HermesDelegationRequest has workspace_binding field."""
        request = HermesDelegationRequest(goal="test", context="ctx")
        self.assertTrue(hasattr(request, "workspace_binding"))

    def test_request_includes_workspace_binding(self):
        """build_delegation_request includes workspace_binding."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)

        self.assertIsNotNone(request.workspace_binding)
        self.assertEqual(request.workspace_binding.workspace_root, "/test/repo")

    def test_workspace_hint_derived_from_foundup_id(self):
        """workspace_hint is derived from foundup_id."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="social_twin",
        )

        request = executor.build_delegation_request(job)

        self.assertEqual(
            request.workspace_binding.workspace_hint,
            "modules/foundups/social_twin",
        )

    def test_workspace_hint_none_when_no_foundup_id(self):
        """workspace_hint is None when foundup_id is None."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="queue_foundup_job",
        )

        request = executor.build_delegation_request(job)

        self.assertIsNone(request.workspace_binding.workspace_hint)


class TestAllowedPathsInRequest(unittest.TestCase):
    """Test allowed_paths are constrained in request."""

    def test_allowed_paths_includes_foundup_path(self):
        """Request allowed_paths includes foundup module path."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)

        self.assertIn("modules/foundups/gotjunk/", request.workspace_binding.allowed_paths)

    def test_allowed_paths_includes_evidence_path(self):
        """Request allowed_paths includes evidence output path."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)

        # Evidence path includes job_id
        evidence_paths = [p for p in request.workspace_binding.allowed_paths if ".hermes_evidence" in p]
        self.assertEqual(len(evidence_paths), 1)
        self.assertIn(job.job_id, evidence_paths[0])


class TestBlockedPathsInRequest(unittest.TestCase):
    """Test blocked_paths are honored in request."""

    def test_blocked_paths_populated(self):
        """Request blocked_paths includes security patterns."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)

        self.assertIn(".env", request.workspace_binding.blocked_paths)
        self.assertIn("vendor/", request.workspace_binding.blocked_paths)

    def test_blocked_paths_is_list(self):
        """blocked_paths is a list (not frozenset) for JSON serialization."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)

        self.assertIsInstance(request.workspace_binding.blocked_paths, list)


class TestWorkspaceRootDetection(unittest.TestCase):
    """Test workspace_root auto-detection."""

    def test_uses_env_var_if_set(self):
        """Executor uses FOUNDUPS_WORKSPACE_ROOT env var."""
        # Use os.path.abspath to get expected path (handles Windows drive letter)
        expected = os.path.abspath("/custom/path")
        with patch.dict(os.environ, {"FOUNDUPS_WORKSPACE_ROOT": "/custom/path"}):
            executor = HermesJobExecutor()
            self.assertEqual(executor.workspace_root, expected)

    def test_falls_back_to_cwd(self):
        """Executor falls back to cwd if env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FOUNDUPS_WORKSPACE_ROOT", None)
            with patch("os.getcwd", return_value="/fallback/cwd"):
                executor = HermesJobExecutor()
                self.assertEqual(executor.workspace_root, "/fallback/cwd")

    def test_explicit_workspace_root_overrides(self):
        """Explicit workspace_root parameter overrides detection."""
        with patch.dict(os.environ, {"FOUNDUPS_WORKSPACE_ROOT": "/env/path"}):
            executor = HermesJobExecutor(workspace_root="/explicit/path")
            self.assertEqual(executor.workspace_root, "/explicit/path")


class TestNoRealExecutionWithWorkspaceBinding(unittest.TestCase):
    """Test no real execution occurs with workspace binding."""

    def test_wsp97_fields_false_with_workspace_binding(self):
        """WSP 97 fields remain False even with workspace binding."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            executor = HermesJobExecutor(workspace_root="/test/repo")
            job = create_job(
                tenant_id="t1",
                requested_action="build_foundup",
                foundup_id="gotjunk",
            )

            result = executor.execute(job)

            # Workspace binding should be present in request
            self.assertIsNotNone(result.request.workspace_binding)

            # But no real execution
            self.assertFalse(result.real_execution_performed)
            self.assertFalse(result.verification_complete)
            self.assertFalse(result.cabr_ready)
            self.assertFalse(result.payout_ready)

    def test_request_to_dict_includes_workspace_binding(self):
        """Request.to_dict serializes workspace_binding."""
        executor = HermesJobExecutor(workspace_root="/test/repo")
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        request = executor.build_delegation_request(job)
        d = request.to_dict()

        self.assertIn("workspace_binding", d)
        self.assertIsNotNone(d["workspace_binding"])
        self.assertEqual(d["workspace_binding"]["workspace_root"], "/test/repo")


if __name__ == "__main__":
    unittest.main()
