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


if __name__ == "__main__":
    unittest.main()
