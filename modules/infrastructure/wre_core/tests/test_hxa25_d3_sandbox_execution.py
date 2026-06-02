#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA25 Proof Test: D3 Sandbox Execution (Phase 1)

Tests enabling D3 sandbox dry-run execution with evidence when all gates pass.

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA24 Verdict was: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED
HXA25 defines: D3 sandbox dry-run execution with evidence when all gates pass.

This slice MUST NOT:
  - Enable production source modification
  - Create repos
  - Call live external delegate
  - Make network calls
  - Use real credentials
  - Initiate external federation
  - Enable D4/D5/D6 actions

Key Behaviors Tested:
  1. D3 sandbox blocked by default (no capability token flags)
  2. D3 sandbox blocked without capability token flags
  3. D3 sandbox blocked if token checked/present but not validated
  4. D3 sandbox blocked if token scope not authorized
  5. D3 sandbox blocked without workspace binding
  6. D3 sandbox blocked without path constraints
  7. D3 sandbox allowed as dry-run when all gates true
  8. Allowed D3 writes evidence/checkpoint only
  9. Allowed D3 does not call live external delegate
  10. Allowed D3 does not create repo
  11. Allowed D3 does not modify production source
  12. Allowed D3 does not set real_execution_performed True
  13. D4/D5/D6 blocked even with all gates true
  14. Blocked result keeps truth fields false

Slice: HXA25_D3_SANDBOX_EXECUTION_PHASE1
Worker: 0102
"""

from __future__ import annotations

import os
import sys
import tempfile
import shutil
from typing import Any, Dict
from unittest.mock import patch

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

# HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746):
# Import the token issuer via the FULL package path so the issued
# CapabilityToken's class identity matches the executor's internal import.
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from modules.infrastructure.wre_core.src.capability_token_validator import (
    LocalCapabilityTokenIssuer,
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


def _create_d3_job_with_all_gates(
    foundup_id: str = "test_foundup",
    requested_action: str = "build_foundup",
) -> FoundUpJob:
    """Create a job with all gates True for D3 sandbox execution.

    HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746): capability_token_*
    flags are now server-authored by the executor's runtime write-back. So we
    supply a REAL valid token in the payload (broad scopes/actions so it
    validates against whatever action class the test patches in) instead of
    forging the capability flags. security_gate_* is still set directly
    (server-authored; this executor has no security-gate evaluator). For
    D4/D5/D6 tests the token validates but the GUARD blocks by class.
    """
    job = create_job(
        tenant_id="tenant_test",
        requested_action=requested_action,
        foundup_id=foundup_id,
        payload={
            "capability_token": LocalCapabilityTokenIssuer().issue_token(
                subject="agent_hxa25",
                audience="wre-local",
                # Broad scopes so the token authorizes whichever class the test
                # patches (D3 passes guard; D4/D5/D6 are blocked by the guard).
                scopes=[
                    "d3:sandbox",
                    "d4:repo",
                    "d5:external",
                    "d6:delete",
                ],
                allowed_actions=[
                    "build_foundup",
                    "extract_foundup",
                    "create_repo",
                    "send_email",
                    "delete_permanently",
                ],
                allowed_paths=["modules/foundups"],
                # Validates whether executor runs dry_run True or False; the
                # guard still bounds execution (D3 dry-run only; D4/D5/D6 blocked).
                dry_run_only=False,
            ),
        },
    )
    # Security gate set by direct (server-authored) assignment.
    job.policy_flags.security_gate_checked = True
    job.policy_flags.security_gate_passed = True
    # Operator-authored dry run mode.
    job.policy_flags.dry_run_mode = True
    return job


# ===========================================================================
# SECTION 2: D3 Sandbox Blocked by Default Tests
# ===========================================================================


class TestD3SandboxBlockedByDefault:
    """Test D3 sandbox write blocked by default (no capability token flags)."""

    def test_d3_blocked_by_default_no_policy_flags(self, temp_workspace):
        """D3 sandbox write should be blocked with default policy flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Default policy_flags: all capability token flags are False

        # Force D3 classification to test guard blocking
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # D3 requires capability_token_present=True
                # Default is False, so guard should block
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] in [
                    "MISSING_CAPABILITY_TOKEN",
                    "MISSING_WORKSPACE_BINDING",
                ]


# ===========================================================================
# SECTION 3: D3 Sandbox Blocked Without Capability Token Flags Tests
# ===========================================================================


class TestD3SandboxBlockedWithoutCapabilityTokenFlags:
    """Test D3 sandbox blocked without capability token flags."""

    def test_d3_blocked_without_capability_token_flags(self, temp_workspace):
        """D3 blocked when capability token flags are all False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Ensure all capability token flags are False (default)
        assert job.policy_flags.capability_token_checked is False
        assert job.policy_flags.capability_token_present is False

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                # Missing capability token should be the reason
                assert result.guard_result["allowed"] is False


# ===========================================================================
# SECTION 4: D3 Sandbox Blocked if Token Checked/Present but Not Validated
# ===========================================================================


class TestD3SandboxBlockedIfNotValidated:
    """Test D3 blocked if token checked/present but not validated."""

    def test_d3_blocked_token_not_validated(self, temp_workspace):
        """D3 blocked when checked+present=True but validated=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = False  # Not validated
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"


# ===========================================================================
# SECTION 5: D3 Sandbox Blocked if Token Scope Not Authorized
# ===========================================================================


class TestD3SandboxBlockedIfScopeNotAuthorized:
    """Test D3 blocked if token scope not authorized."""

    def test_d3_blocked_scope_not_authorized(self, temp_workspace):
        """D3 blocked when checked+present+validated=True but scope_authorized=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = False  # Not authorized
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"


# ===========================================================================
# SECTION 6: D3 Sandbox Blocked Without Workspace Binding
# ===========================================================================


class TestD3SandboxBlockedWithoutWorkspaceBinding:
    """Test D3 blocked without workspace binding."""

    def test_d3_blocked_without_workspace_binding(self, temp_workspace):
        """D3 should be blocked without workspace binding."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

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


# ===========================================================================
# SECTION 7: D3 Sandbox Blocked Without Path Constraints
# ===========================================================================


class TestD3SandboxBlockedWithoutPathConstraints:
    """Test D3 blocked without path constraints."""

    def test_d3_blocked_without_path_constraints(self, temp_workspace):
        """D3 should be blocked without path constraint validation."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        # Mock to return D3 class with path_constraints_validated=False
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
                path_constraints_validated=False,  # Missing
                capability_token_present=True,
                security_gate_passed=True,
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_PATH_VALIDATION"


# ===========================================================================
# SECTION 8: D3 Sandbox Allowed as Dry-Run When All Gates True
# ===========================================================================


class TestD3SandboxAllowedAsDryRunWhenAllGatesTrue:
    """Test D3 sandbox allowed as dry-run when all gates true."""

    def test_d3_allowed_when_all_gates_pass(self, temp_workspace):
        """D3 sandbox allowed when all four token flags True AND security gate passed."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        # Force D3 classification
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # With all gates passing, D3 should be allowed as dry-run
                assert result.guard_evaluated is True
                assert result.guard_result["allowed"] is True
                assert result.guard_result["decision"] == "ALLOW_DRY_RUN"
                # Overall status is SIMULATED (dry_run=True)
                assert result.status == HermesExecutionStatus.SIMULATED

    def test_d3_allowed_guard_result_shows_ok_sandbox(self, temp_workspace):
        """D3 allowed should have OK_SANDBOX reason code."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.guard_result["reason_code"] == "OK_SANDBOX"


# ===========================================================================
# SECTION 9: Allowed D3 Writes Evidence/Checkpoint Only
# ===========================================================================


class TestAllowedD3WritesEvidenceOnly:
    """Test that allowed D3 writes evidence/checkpoint only."""

    def test_d3_allowed_writes_evidence(self, temp_workspace):
        """Allowed D3 should write evidence files to .hermes_evidence."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Evidence path should be set
                assert result.evidence_path is not None
                assert ".hermes_evidence" in result.evidence_path
                assert job.job_id in result.evidence_path

    def test_d3_allowed_evidence_files_exist(self, temp_workspace):
        """Allowed D3 should create evidence files in evidence directory."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Evidence directory should exist
                assert result.evidence_path is not None
                assert os.path.isdir(result.evidence_path)

                # Evidence files should exist
                metadata_path = os.path.join(result.evidence_path, "metadata.json")
                checkpoint_path = os.path.join(result.evidence_path, "checkpoint.json")
                assert os.path.isfile(metadata_path)
                assert os.path.isfile(checkpoint_path)


# ===========================================================================
# SECTION 10: Allowed D3 Does Not Call Live External Delegate
# ===========================================================================


class TestAllowedD3DoesNotCallLiveDelegate:
    """Test that allowed D3 does not call live external delegate."""

    def test_d3_allowed_no_live_delegate_called(self, temp_workspace):
        """Allowed D3 should not call live external delegate."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.live_external_delegate_called is False

    def test_d3_allowed_controlled_delegate_not_invoked(self, temp_workspace):
        """Allowed D3 without controlled_harness should not invoke controlled delegate."""
        executor = HermesJobExecutor(
            workspace_root=temp_workspace,
            dry_run=True,
            controlled_harness=False,
        )
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.controlled_delegate_invoked is False


# ===========================================================================
# SECTION 11: Allowed D3 Does Not Create Repo
# ===========================================================================


class TestAllowedD3DoesNotCreateRepo:
    """Test that allowed D3 does not create repo."""

    def test_d3_allowed_no_repo_created(self, temp_workspace):
        """Allowed D3 should not create repository."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.repo_created is False


# ===========================================================================
# SECTION 12: Allowed D3 Does Not Modify Production Source
# ===========================================================================


class TestAllowedD3DoesNotModifyProductionSource:
    """Test that allowed D3 does not modify production source."""

    def test_d3_allowed_no_production_source_modified(self, temp_workspace):
        """Allowed D3 should not modify production source."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.production_source_modified is False


# ===========================================================================
# SECTION 13: Allowed D3 Does Not Set Real Execution Performed True
# ===========================================================================


class TestAllowedD3DoesNotSetRealExecutionPerformed:
    """Test that allowed D3 does not set real_execution_performed True."""

    def test_d3_allowed_real_execution_performed_false(self, temp_workspace):
        """Allowed D3 should have real_execution_performed=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.real_execution_performed is False


# ===========================================================================
# SECTION 14: D4/D5/D6 Blocked Even With All Gates True
# ===========================================================================


class TestD4D5D6BlockedEvenWithAllGatesTrue:
    """Test D4/D5/D6 blocked even with all gates true."""

    def test_d4_blocked_with_all_gates(self, temp_workspace):
        """D4 repo write blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="create_repo")

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d5_blocked_with_all_gates(self, temp_workspace):
        """D5 external side effect blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="send_email")

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d6_blocked_with_all_gates(self, temp_workspace):
        """D6 irreversible blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="delete_permanently")

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D6_IRREVERSIBLE,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 15: Blocked Result Keeps Truth Fields False
# ===========================================================================


class TestBlockedResultKeepsTruthFieldsFalse:
    """Test that blocked result keeps all truth fields False."""

    def test_blocked_d3_truth_fields_false(self, temp_workspace):
        """Blocked D3 should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Don't set capability token flags - should block

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.real_execution_performed is False
                assert result.repo_created is False
                assert result.production_source_modified is False
                assert result.live_external_delegate_called is False
                assert result.external_federation_initiated is False
                assert result.verification_complete is False
                assert result.cabr_ready is False
                assert result.payout_ready is False

    def test_blocked_d4_truth_fields_false(self, temp_workspace):
        """Blocked D4 should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="create_repo")

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.real_execution_performed is False
                assert result.repo_created is False
                assert result.production_source_modified is False


# ===========================================================================
# SECTION 16: Guard Result Contains Correct Fields
# ===========================================================================


class TestGuardResultContainsCorrectFields:
    """Test guard result contains correct fields for D3."""

    def test_allowed_d3_guard_result_structure(self, temp_workspace):
        """Allowed D3 guard result should have complete structure."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                guard_result = result.guard_result
                assert guard_result["allowed"] is True
                assert guard_result["decision"] == "ALLOW_DRY_RUN"
                assert guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
                assert guard_result["dry_run_only"] is True
                assert guard_result["live_execution_allowed"] is False


# ===========================================================================
# SECTION 17: D3 Classification with Capability Tokens
# ===========================================================================


class TestD3ClassificationWithCapabilityTokens:
    """Test that build_* actions can be classified as D3 when tokens present."""

    def test_build_foundup_allowed_as_d3_with_all_gates(self, temp_workspace):
        """build_foundup should be allowed as D3 dry-run with all gates."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="build_foundup")

        # Force D3 classification (HXA25 enables this naturally)
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.guard_result["allowed"] is True
                assert result.guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
                assert result.status == HermesExecutionStatus.SIMULATED

    def test_extract_foundup_allowed_as_d3_with_all_gates(self, temp_workspace):
        """extract_foundup should be allowed as D3 dry-run with all gates."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates(requested_action="extract_foundup")

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.guard_result["allowed"] is True
                assert result.guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
                assert result.status == HermesExecutionStatus.SIMULATED


# ===========================================================================
# SECTION 18: HXA25 Verdict Documentation Test
# ===========================================================================


class TestHXA25VerdictDocumentation:
    """Document HXA25 verdict and proof."""

    def test_hxa25_verdict_d3_sandbox_execution_defined(self, temp_workspace):
        """
        HXA25 Verdict: D3_SANDBOX_EXECUTION_DEFINED

        HXA24 verdict was: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED

        HXA25 proves:
        1. D3 sandbox blocked by default (no capability token flags)
        2. D3 sandbox blocked without capability token flags
        3. D3 sandbox blocked if token checked/present but not validated
        4. D3 sandbox blocked if token scope not authorized
        5. D3 sandbox blocked without workspace binding
        6. D3 sandbox blocked without path constraints
        7. D3 sandbox allowed as dry-run when all gates true
        8. Allowed D3 writes evidence/checkpoint only
        9. Allowed D3 does not call live external delegate
        10. Allowed D3 does not create repo
        11. Allowed D3 does not modify production source
        12. Allowed D3 does not set real_execution_performed True
        13. D4/D5/D6 blocked even with all gates true
        14. Blocked result keeps truth fields false
        15. All WSP 97 truth fields remain False:
            - live_execution_allowed = False
            - live_external_delegate_called = False
            - repo_created = False
            - production_source_modified = False
            - external_federation_initiated = False
            - real_execution_performed = False
            - verification_complete = False
            - cabr_ready = False
            - payout_ready = False

        This does NOT enable production source modification.
        This does NOT create repos.
        This does NOT call live external delegate.
        This does NOT enable D4/D5/D6 actions.
        This DOES enable D3 sandbox dry-run with evidence.
        """
        verdict = "D3_SANDBOX_EXECUTION_DEFINED"

        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_d3_job_with_all_gates()

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Verify D3 allowed
                assert result.guard_evaluated is True
                assert result.guard_result["allowed"] is True
                assert result.guard_result["decision"] == "ALLOW_DRY_RUN"

                # Verify evidence written
                assert result.evidence_path is not None
                assert os.path.isdir(result.evidence_path)

                # Verify WSP 97 truth fields
                assert result.live_external_delegate_called is False
                assert result.repo_created is False
                assert result.production_source_modified is False
                assert result.external_federation_initiated is False
                assert result.real_execution_performed is False
                assert result.verification_complete is False
                assert result.cabr_ready is False
                assert result.payout_ready is False

                assert verdict == "D3_SANDBOX_EXECUTION_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
