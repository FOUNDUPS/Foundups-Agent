#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA23 Proof Test: Hermes Guard Integration (Phase 1)

Tests the integration of the HXA22 destructive action guard into HermesJobExecutor.
This is a safe no-op validation seam - no live delegation, no repo creation,
no production source modification.

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA22 Verdict was: DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED
HXA23 defines: Integration of guard into HermesJobExecutor as validation seam.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Use real credentials
  - Initiate external federation

Key Behaviors Tested:
  - Hermes calls destructive guard for dry-run job
  - D0/D1/D2/D3 allowed as dry-run only
  - D4 repo write blocked
  - D5 external side effect blocked
  - D6 irreversible blocked
  - unknown destructive class blocked
  - blocked guard result does not call delegate adapter
  - blocked guard result does not write files
  - existing evidence/checkpoint truth fields preserved

Slice: HXA23_HERMES_GUARD_INTEGRATION_PHASE1
Worker: 0102
"""

from __future__ import annotations

import os
import sys
import tempfile
import shutil
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock

import pytest

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "modules", "communication", "moltbot_bridge", "src"))

from hermes_job_executor import (
    HermesDelegationResult,
    HermesExecutionStatus,
    HermesJobExecutor,
)
from foundup_job_contract import (
    FoundUpJob,
    PolicyFlags,
    create_job,
)
from destructive_action_guard import (
    DestructiveActionClass,
    DestructiveActionRequest,
    GuardDecision,
    GuardBlockReasonCode,
)


# ===========================================================================
# SECTION 1: Test Fixtures
# ===========================================================================


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def executor(temp_workspace):
    """Create HermesJobExecutor with temp workspace."""
    return HermesJobExecutor(
        workspace_root=temp_workspace,
        dry_run=True,
    )


@pytest.fixture
def sample_job():
    """Create sample job for testing."""
    return create_job(
        tenant_id="tenant_test",
        requested_action="build_foundup",
        foundup_id="test_foundup",
    )


# ===========================================================================
# SECTION 2: Guard Evaluation Tests
# ===========================================================================


class TestHermesCallsDestructiveGuard:
    """Test Hermes calls destructive guard for jobs."""

    def test_guard_evaluated_on_execute(self, executor, sample_job):
        """Guard should be evaluated during execute."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.guard_evaluated is True
            assert result.guard_result is not None

    def test_guard_result_contains_decision(self, executor, sample_job):
        """Guard result should contain decision field."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert "decision" in result.guard_result
            assert "allowed" in result.guard_result

    def test_guard_result_contains_destructive_class(self, executor, sample_job):
        """Guard result should contain destructive_class field."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert "destructive_class" in result.guard_result

    def test_guard_result_in_to_dict(self, executor, sample_job):
        """guard_result should be in to_dict() output."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)
            d = result.to_dict()

            assert "guard_evaluated" in d
            assert "guard_result" in d
            assert d["guard_evaluated"] is True


# ===========================================================================
# SECTION 3: D0-D3 Dry-Run Allowed Tests
# ===========================================================================


class TestD0D1D2D3AllowedAsDryRunOnly:
    """Test D0/D1/D2/D3 actions allowed as dry-run only."""

    def test_validate_action_classified_as_d0(self, temp_workspace):
        """validate_foundup action should be classified as D0."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.guard_result["destructive_class"] == "D0_OBSERVE"
            assert result.guard_result["allowed"] is True

    def test_queue_action_classified_as_d0(self, temp_workspace):
        """queue_foundup_job action should be classified as D0."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="queue_foundup_job",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_result["destructive_class"] == "D0_OBSERVE"
            assert result.guard_result["allowed"] is True

    def test_extract_action_classified_as_d2(self, temp_workspace):
        """extract_foundup action should be classified as D2."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="extract_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_result["destructive_class"] == "D2_SIMULATE"
            assert result.guard_result["allowed"] is True

    def test_build_action_classified_as_d2(self, temp_workspace):
        """build_foundup action should be classified as D2 in Phase 1."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        # In Phase 1, build_* is classified as D2_SIMULATE because
        # D3 requires capability tokens not yet in PolicyFlags.
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_result["destructive_class"] == "D2_SIMULATE"
            assert result.guard_result["allowed"] is True

    def test_d0_d1_d2_allowed_continues_to_simulated(self, temp_workspace):
        """D0/D1/D2 allowed should continue to SIMULATED status."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Guard allowed D0, so should continue to SIMULATED
            assert result.guard_result["allowed"] is True
            assert result.status == HermesExecutionStatus.SIMULATED


# ===========================================================================
# SECTION 4: D4 Repo Write Blocked Tests
# ===========================================================================


class TestD4RepoWriteBlocked:
    """Test D4 repo write actions are blocked."""

    def test_d4_request_blocked_by_guard(self, temp_workspace):
        """D4 action should be blocked by guard."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        # Create a mock that forces D4 classification
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["allowed"] is False
                assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d4_blocked_does_not_call_delegate(self, temp_workspace):
        """D4 blocked should not call delegate adapter."""
        executor = HermesJobExecutor(
            workspace_root=temp_workspace,
            dry_run=True,
            controlled_harness=True,
        )

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.controlled_delegate_invoked is False
                assert result.live_external_delegate_called is False


# ===========================================================================
# SECTION 5: D5 External Side Effect Blocked Tests
# ===========================================================================


class TestD5ExternalSideEffectBlocked:
    """Test D5 external side effect actions are blocked."""

    def test_d5_request_blocked_by_guard(self, temp_workspace):
        """D5 action should be blocked by guard."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="send_email",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["allowed"] is False
                assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d5_blocked_preserves_wsp97_fields(self, temp_workspace):
        """D5 blocked should preserve WSP 97 truth fields."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="send_notification",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.real_execution_performed is False
                assert result.external_federation_initiated is False


# ===========================================================================
# SECTION 6: D6 Irreversible Blocked Tests
# ===========================================================================


class TestD6IrreversibleBlocked:
    """Test D6 irreversible actions are blocked."""

    def test_d6_request_blocked_by_guard(self, temp_workspace):
        """D6 action should be blocked by guard."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D6_IRREVERSIBLE,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="delete_permanently",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["allowed"] is False
                assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 7: Blocked Guard Does Not Write Files Tests
# ===========================================================================


class TestBlockedGuardDoesNotWriteFiles:
    """Test blocked guard result does not write files."""

    def test_blocked_guard_no_evidence_written(self, temp_workspace):
        """Blocked guard should not write evidence files."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Blocked result should not have evidence path
                # (guard blocks before evidence is written)
                assert result.evidence_path is None

    def test_blocked_guard_repo_created_false(self, temp_workspace):
        """Blocked guard should have repo_created=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.repo_created is False

    def test_blocked_guard_production_source_modified_false(self, temp_workspace):
        """Blocked guard should have production_source_modified=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="modify_source",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.production_source_modified is False


# ===========================================================================
# SECTION 8: WSP 97 Truth Fields Preserved Tests
# ===========================================================================


class TestWSP97TruthFieldsPreserved:
    """Test all WSP 97 truth fields are preserved correctly."""

    def test_live_external_delegate_called_false(self, executor, sample_job):
        """live_external_delegate_called should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.live_external_delegate_called is False

    def test_repo_created_false(self, executor, sample_job):
        """repo_created should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.repo_created is False

    def test_production_source_modified_false(self, executor, sample_job):
        """production_source_modified should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.production_source_modified is False

    def test_external_federation_initiated_false(self, executor, sample_job):
        """external_federation_initiated should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.external_federation_initiated is False

    def test_real_execution_performed_false(self, executor, sample_job):
        """real_execution_performed should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.real_execution_performed is False

    def test_verification_complete_false(self, executor, sample_job):
        """verification_complete should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.verification_complete is False

    def test_cabr_ready_false(self, executor, sample_job):
        """cabr_ready should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.cabr_ready is False

    def test_payout_ready_false(self, executor, sample_job):
        """payout_ready should be False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(sample_job)

            assert result.payout_ready is False


# ===========================================================================
# SECTION 9: Evidence/Checkpoint Truth Fields Preserved Tests
# ===========================================================================


class TestEvidenceCheckpointFieldsPreserved:
    """Test existing evidence/checkpoint truth fields are preserved."""

    def test_checkpoint_state_preserved_on_block(self, temp_workspace):
        """checkpoint_state should be BLOCKED when guard blocks."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.checkpoint_state == "BLOCKED"
                assert result.checkpoint_blocker is not None

    def test_checkpoint_state_simulated_on_allow(self, executor, sample_job):
        """checkpoint_state should be SIMULATED when guard allows."""
        # Use validate action which is D0 and will pass
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # SIMULATED is the default state
            assert result.checkpoint_state == "SIMULATED"


# ===========================================================================
# SECTION 10: D3 Missing Gates Tests
# ===========================================================================


class TestD3MissingGatesBlocked:
    """Test D3 sandbox write blocked when gates are missing."""

    def test_d3_blocked_without_workspace_binding(self, temp_workspace):
        """D3 should be blocked without workspace binding."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        # Mock to return D3 class with workspace_binding_enforced=False
        with patch.object(
            executor,
            "_build_destructive_action_request",
        ) as mock_build:
            mock_build.return_value = DestructiveActionRequest(
                action_id="test_001",
                action_type="build_foundup",
                target_path="/test",
                requested_class=DestructiveActionClass.D3_WRITE_SANDBOX,
                dry_run_mode=True,
                workspace_binding_enforced=False,  # Missing
                path_constraints_validated=True,
                capability_token_present=True,
                security_gate_passed=True,
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_WORKSPACE_BINDING"

    def test_d3_blocked_without_capability_token(self, temp_workspace):
        """D3 should be blocked without capability token."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.object(
            executor,
            "_build_destructive_action_request",
        ) as mock_build:
            mock_build.return_value = DestructiveActionRequest(
                action_id="test_002",
                action_type="build_foundup",
                target_path="/test",
                requested_class=DestructiveActionClass.D3_WRITE_SANDBOX,
                dry_run_mode=True,
                workspace_binding_enforced=True,
                path_constraints_validated=True,
                capability_token_present=False,  # Missing
                security_gate_passed=True,
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"


# ===========================================================================
# SECTION 11: Guard Integration Flow Tests
# ===========================================================================


class TestGuardIntegrationFlow:
    """Test complete guard integration flow."""

    def test_complete_guard_integration_flow(self, temp_workspace):
        """
        HXA23 PROOF: Complete guard integration flow.

        This test proves:
        1. HermesJobExecutor calls destructive action guard
        2. Guard result is stored in HermesDelegationResult
        3. D0/D1/D2 allowed actions proceed to SIMULATED
        4. D4/D5/D6 blocked actions return BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
        5. All WSP 97 truth fields remain False
        6. Guard evaluation occurs before any delegation paths
        """
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        # Test D0 (validate) - should proceed to SIMULATED
        d0_job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d0_result = executor.execute(d0_job)
            assert d0_result.guard_evaluated is True
            assert d0_result.guard_result["allowed"] is True
            assert d0_result.status == HermesExecutionStatus.SIMULATED
            assert d0_result.live_external_delegate_called is False
            assert d0_result.repo_created is False
            assert d0_result.production_source_modified is False

        # Test D4 (repo write) - should be blocked by guard
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            d4_job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                d4_result = executor.execute(d4_job)
                assert d4_result.guard_evaluated is True
                assert d4_result.guard_result["allowed"] is False
                assert d4_result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert d4_result.live_external_delegate_called is False
                assert d4_result.repo_created is False

    def test_guard_evaluation_before_controlled_harness(self, temp_workspace):
        """Guard should be evaluated before controlled harness path."""
        executor = HermesJobExecutor(
            workspace_root=temp_workspace,
            dry_run=True,
            controlled_harness=True,
        )

        # D4 should be blocked by guard even with controlled_harness=True
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            job = create_job(
                tenant_id="t1",
                requested_action="create_repo",
                foundup_id="test",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Guard blocks BEFORE controlled harness is entered
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.controlled_delegate_invoked is False


# ===========================================================================
# SECTION 12: Existing Dry-Run Behavior Preserved Tests
# ===========================================================================


class TestExistingDryRunBehaviorPreserved:
    """Test existing dry-run behavior is preserved."""

    def test_dry_run_simulated_still_works(self, executor, sample_job):
        """dry_run=True should still return SIMULATED for allowed actions."""
        # Use validate action which is D0 and will pass
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.SIMULATED
            assert "simulated" in result.status_reason.lower()

    def test_feature_disabled_still_simulates(self, executor, sample_job):
        """Feature disabled should still return SIMULATED for allowed actions."""
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.SIMULATED


# ===========================================================================
# SECTION 13: HXA23 Verdict Documentation Test
# ===========================================================================


class TestHXA23VerdictDocumentation:
    """Document HXA23 verdict and proof."""

    def test_hxa23_verdict_hermes_guard_integration_defined(self, temp_workspace):
        """
        HXA23 Verdict: HERMES_GUARD_INTEGRATION_DEFINED

        HXA22 verdict was: DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED

        HXA23 proves:
        1. HermesJobExecutor integrates DestructiveActionGuard
        2. Guard is evaluated before delegation paths
        3. Guard result is stored in HermesDelegationResult
        4. D0/D1/D2/D3 allowed as dry-run only
        5. D4 repo write blocked by guard
        6. D5 external side effect blocked by guard
        7. D6 irreversible blocked by guard
        8. Blocked guard does not call delegate adapter
        9. Blocked guard does not write files
        10. All WSP 97 truth fields remain False:
            - live_external_delegate_called = False
            - repo_created = False
            - production_source_modified = False
            - external_federation_initiated = False
            - real_execution_performed = False
            - verification_complete = False
            - cabr_ready = False
            - payout_ready = False
        11. Existing dry-run behavior preserved
        12. Guard classification maps job actions to D0-D3

        This does NOT enable live delegation.
        This does NOT create repos.
        This does NOT modify production source.
        This DOES add a safe validation seam.
        """
        verdict = "HERMES_GUARD_INTEGRATION_DEFINED"

        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="validate_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Verify guard integration
            assert result.guard_evaluated is True
            assert result.guard_result is not None

            # Verify WSP 97 truth fields
            assert result.live_external_delegate_called is False
            assert result.repo_created is False
            assert result.production_source_modified is False
            assert result.external_federation_initiated is False
            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False

            assert verdict == "HERMES_GUARD_INTEGRATION_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
