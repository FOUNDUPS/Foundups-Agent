#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA28 Proof Test: D3 Native Classification (Phase 1)

Tests deterministic and explicit destructive action classification in
HermesJobExecutor._classify_destructive_action().

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA27 Verdict was: HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED
HXA28 defines: Native destructive action classification for D0-D6.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Weaken guard logic
  - Downgrade D4/D5/D6 based on token

Classification Rules Tested:
  1. D0/D1 dry-run allowed for observe/read/status actions
  2. D2 allowed for simulate/plan/dry_run actions
  3. D3 for sandbox-local evidence/checkpoint writes
  4. D4 for repo creation, git operations, production source
  5. D5 for external API mutations
  6. D6 for delete, credential mutation, payout, irreversible
  7. Unknown/ambiguous -> D6 (fail-closed)
  8. Valid token does NOT downgrade D4/D5/D6

Slice: HXA28_D3_NATIVE_CLASSIFICATION_PHASE1
Worker: 0102
"""

from __future__ import annotations

import os
import sys
import tempfile
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
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


def _create_job_with_action(action: str) -> FoundUpJob:
    """Create a job with the specified requested_action."""
    return create_job(
        tenant_id="tenant_hxa28",
        requested_action=action,
        foundup_id="test_foundup",
    )


def _create_job_with_all_gates(
    action: str,
    foundup_id: str = "test_foundup",
) -> FoundUpJob:
    """Create a job with all capability token gates True."""
    job = create_job(
        tenant_id="tenant_hxa28",
        requested_action=action,
        foundup_id=foundup_id,
    )
    job.policy_flags.capability_token_checked = True
    job.policy_flags.capability_token_present = True
    job.policy_flags.capability_token_validated = True
    job.policy_flags.capability_token_scope_authorized = True
    job.policy_flags.security_gate_checked = True
    job.policy_flags.security_gate_passed = True
    job.policy_flags.dry_run_mode = True
    return job


# ===========================================================================
# SECTION 2: D0/D1 Observe/Read Classification Tests
# ===========================================================================


class TestD0D1ObserveReadClassification:
    """Test D0/D1 classification for observe/read/status actions."""

    @pytest.mark.parametrize("action", [
        "validate_foundup",
        "validate_manifest",
        "queue_foundup_job",
        "queue_task",
        "check_status",
        "check_health",
        "status_foundup",
        "observe_metrics",
        "read_config",
        "get_foundup",
        "get_status",
        "list_foundups",
        "list_jobs",
        "inspect_manifest",
        "describe_foundup",
        "info_job",
    ])
    def test_d0_observe_actions_classified_correctly(self, executor, action):
        """D0 observe actions should be classified as D0_OBSERVE."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D0_OBSERVE

    @pytest.mark.parametrize("action", [
        "fetch_data",
        "fetch_config",
        "load_manifest",
        "load_settings",
        "retrieve_evidence",
        "lookup_foundup",
        "search_jobs",
    ])
    def test_d1_read_actions_classified_correctly(self, executor, action):
        """D1 read actions should be classified as D1_READ."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D1_READ

    def test_d0_action_allowed_in_dryrun(self, temp_workspace):
        """D0 actions should be allowed in dry-run mode."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("validate_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.guard_result["allowed"] is True
            assert result.guard_result["destructive_class"] == "D0_OBSERVE"
            assert result.status == HermesExecutionStatus.SIMULATED


# ===========================================================================
# SECTION 3: D2 Simulate/Plan Classification Tests
# ===========================================================================


class TestD2SimulatePlanClassification:
    """Test D2 classification for simulate/plan/dry_run actions."""

    @pytest.mark.parametrize("action", [
        "simulate_build",
        "simulate_deploy",
        "plan_foundup",
        "plan_migration",
        "dry_run_build",
        "dry_run_deploy",
        "preview_changes",
        "preview_manifest",
        "analyze_foundup",
        "analyze_dependencies",
        "estimate_cost",
        "calculate_budget",
        "compare_versions",
        "diff_manifests",
    ])
    def test_d2_simulate_actions_classified_correctly(self, executor, action):
        """D2 simulate actions should be classified as D2_SIMULATE."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D2_SIMULATE

    def test_d2_action_allowed_in_dryrun(self, temp_workspace):
        """D2 actions should be allowed in dry-run mode."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("simulate_build")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.guard_result["allowed"] is True
            assert result.guard_result["destructive_class"] == "D2_SIMULATE"


# ===========================================================================
# SECTION 4: D3 Sandbox Write Classification Tests
# ===========================================================================


class TestD3SandboxWriteClassification:
    """Test D3 classification for sandbox-local evidence/checkpoint writes."""

    @pytest.mark.parametrize("action", [
        "build_foundup",
        "extract_foundup",
        "write_evidence",
        "write_checkpoint",
        "save_evidence",
        "evidence_save",
        "checkpoint_create",
        "sandbox_write_test",
    ])
    def test_d3_sandbox_actions_classified_correctly(self, executor, action):
        """D3 sandbox actions should be classified as D3_WRITE_SANDBOX."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D3_WRITE_SANDBOX

    def test_d3_hermes_evidence_scoped_writes(self, temp_workspace):
        """D3 evidence-scoped writes should classify as D3."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("build_foundup")
        request = executor.build_delegation_request(job)

        # Verify workspace binding includes .hermes_evidence/ path
        assert request.workspace_binding is not None
        evidence_path = request.workspace_binding.evidence_output_path
        assert ".hermes_evidence" in evidence_path

        result = executor._classify_destructive_action(job, request)
        assert result == DestructiveActionClass.D3_WRITE_SANDBOX

    def test_d3_allowed_with_all_gates_true(self, temp_workspace):
        """D3 actions allowed when all capability token gates True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("build_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.guard_result["allowed"] is True
            assert result.guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
            assert result.guard_result["reason_code"] == "OK_SANDBOX"


# ===========================================================================
# SECTION 5: D4 Repo/Git Operations Blocked Tests
# ===========================================================================


class TestD4RepoGitOperationsBlocked:
    """Test D4 classification for repo creation/git operations (BLOCKED)."""

    @pytest.mark.parametrize("action", [
        "create_repo",
        "create_repository",
        "init_repo",
        "fork_repo",
        "git_push",
        "git_commit",
        "git_tag",
        "git_release",
        "git_merge",
        "branch_create",
        "branch_delete",
        "pr_create",
        "pr_merge",
        "modify_source",
        "edit_source",
        "write_source",
        "patch_source",
        "git_reset",
        "repo_delete",
        "branch_rename",
        "production_deploy",
        "source_edit_main",
        "source_modify_config",
        "source_write_file",
    ])
    def test_d4_repo_actions_classified_correctly(self, executor, action):
        """D4 repo/git actions should be classified as D4_WRITE_REPO."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D4_WRITE_REPO

    def test_d4_blocked_in_phase1(self, temp_workspace):
        """D4 actions should be blocked in Phase 1."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("create_repo")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["allowed"] is False
            assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d4_blocked_even_with_valid_token(self, temp_workspace):
        """D4 actions blocked even with valid capability token."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("git_push")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"


# ===========================================================================
# SECTION 6: D5 External API Mutations Blocked Tests
# ===========================================================================


class TestD5ExternalAPIMutationsBlocked:
    """Test D5 classification for external API mutations (BLOCKED)."""

    @pytest.mark.parametrize("action", [
        "send_email",
        "send_notification",
        "email_user",
        "notify_team",
        "broadcast_message",
        "publish_event",
        "post_update",
        "webhook_trigger",
        "api_call_external",
        "invoke_service",
        "trigger_external_api",
        "deploy_service",
        "release_version",
        "promote_build",
        "rollout_feature",
    ])
    def test_d5_external_actions_classified_correctly(self, executor, action):
        """D5 external API actions should be classified as D5_EXTERNAL_SIDE_EFFECT."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT

    def test_d5_blocked_in_phase1(self, temp_workspace):
        """D5 actions should be blocked in Phase 1."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("send_email")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["allowed"] is False
            assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d5_blocked_even_with_valid_token(self, temp_workspace):
        """D5 actions blocked even with valid capability token."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("publish_event")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"


# ===========================================================================
# SECTION 7: D6 Irreversible/Delete Actions Blocked Tests
# ===========================================================================


class TestD6IrreversibleDeleteBlocked:
    """Test D6 classification for delete/credential/payout actions (BLOCKED)."""

    @pytest.mark.parametrize("action", [
        "delete_foundup",
        "delete_repo",
        "remove_user",
        "purge_data",
        "wipe_evidence",
        "destroy_workspace",
        "revoke_token",
        "credential_rotate",
        "credential_delete",
        "token_revoke",
        "key_delete",
        "secret_purge",
        "payout_trigger",
        "transfer_funds",
        "finalize_payment",
        "irreversible_action",
    ])
    def test_d6_irreversible_actions_classified_correctly(self, executor, action):
        """D6 irreversible actions should be classified as D6_IRREVERSIBLE."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D6_IRREVERSIBLE

    def test_d6_blocked_in_phase1(self, temp_workspace):
        """D6 actions should be blocked in Phase 1."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("delete_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["allowed"] is False
            assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"

    def test_d6_blocked_even_with_valid_token(self, temp_workspace):
        """D6 actions blocked even with valid capability token."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("payout_trigger")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 8: Ambiguous/Unknown Actions Fail-Closed Tests
# ===========================================================================


class TestAmbiguousActionsFailClosed:
    """Test unknown/ambiguous actions fail-closed to D6."""

    @pytest.mark.parametrize("action", [
        "unknown_action",
        "custom_operation",
        "do_something",
        "execute_task",
        "process_item",
        "run_job",
        "perform_work",
        "",  # Empty action
    ])
    def test_unknown_actions_classified_as_d6(self, executor, action):
        """Unknown/ambiguous actions should be classified as D6_IRREVERSIBLE."""
        job = _create_job_with_action(action)
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D6_IRREVERSIBLE

    def test_ambiguous_action_blocked(self, temp_workspace):
        """Ambiguous actions should be blocked by guard."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("unknown_operation")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["allowed"] is False
            assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"

    def test_empty_action_blocked(self, temp_workspace):
        """Empty action should be blocked (fail-closed via job validation)."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Empty action is caught by job validation before classification
            # This is correct fail-closed behavior
            assert result.status == HermesExecutionStatus.BLOCKED_INVALID_JOB


# ===========================================================================
# SECTION 9: Token Does Not Downgrade Classification Tests
# ===========================================================================


class TestTokenDoesNotDowngradeClassification:
    """Test that valid tokens do NOT downgrade D4/D5/D6 classification."""

    def test_d4_not_downgraded_with_token(self, temp_workspace):
        """D4 classification not downgraded even with valid token flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("create_repo")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Should still be blocked as D4, not downgraded to D3
            assert result.guard_result["destructive_class"] == "D4_WRITE_REPO"
            assert result.guard_result["allowed"] is False

    def test_d5_not_downgraded_with_token(self, temp_workspace):
        """D5 classification not downgraded even with valid token flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("deploy_service")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_result["destructive_class"] == "D5_EXTERNAL_SIDE_EFFECT"
            assert result.guard_result["allowed"] is False

    def test_d6_not_downgraded_with_token(self, temp_workspace):
        """D6 classification not downgraded even with valid token flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("delete_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_result["destructive_class"] == "D6_IRREVERSIBLE"
            assert result.guard_result["allowed"] is False


# ===========================================================================
# SECTION 10: Invalid Token Still Blocks Tests
# ===========================================================================


class TestInvalidTokenStillBlocks:
    """Test that invalid token blocks before classification/guard."""

    def test_invalid_token_blocks_before_guard(self, temp_workspace):
        """Invalid token in payload should block before guard evaluation."""
        from datetime import timedelta

        # Import token components
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(PROJECT_ROOT))
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            LocalCapabilityTokenIssuer,
            LocalCapabilityTokenValidator,
        )

        issuer = LocalCapabilityTokenIssuer()
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            workspace_root=temp_workspace,
            dry_run=True,
            token_validator=validator,
        )

        # Create an expired token
        expired_token = issuer.issue_token(
            subject="test_agent",
            audience="wre-local",
            validity_duration=timedelta(seconds=-1),  # Expired
        )

        job = _create_job_with_action("build_foundup")
        job.payload = {"capability_token": expired_token}

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should block BEFORE guard
            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.token_validation_performed is True
            assert result.guard_evaluated is False  # Guard NOT evaluated


# ===========================================================================
# SECTION 11: WSP 97 Truth Fields Tests
# ===========================================================================


class TestWSP97TruthFieldsRemainFalse:
    """Test all WSP 97 truth fields remain False."""

    def test_d0_simulated_truth_fields_false(self, temp_workspace):
        """D0 SIMULATED result should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("validate_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False

    def test_d3_simulated_truth_fields_false(self, temp_workspace):
        """D3 SIMULATED result should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_all_gates("build_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False

    def test_d4_blocked_truth_fields_false(self, temp_workspace):
        """D4 BLOCKED result should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("create_repo")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.real_execution_performed is False
            assert result.repo_created is False
            assert result.production_source_modified is False
            assert result.live_external_delegate_called is False

    def test_d6_blocked_truth_fields_false(self, temp_workspace):
        """D6 BLOCKED result should have all truth fields False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = _create_job_with_action("delete_foundup")

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False


# ===========================================================================
# SECTION 12: Classification Determinism Tests
# ===========================================================================


class TestClassificationDeterminism:
    """Test classification is deterministic and case-insensitive."""

    def test_classification_case_insensitive(self, executor):
        """Classification should be case-insensitive."""
        actions = ["VALIDATE_FOUNDUP", "Validate_Foundup", "validate_foundup"]
        for action in actions:
            job = _create_job_with_action(action)
            request = executor.build_delegation_request(job)
            result = executor._classify_destructive_action(job, request)
            assert result == DestructiveActionClass.D0_OBSERVE

    def test_classification_deterministic(self, executor):
        """Classification should be deterministic (same input -> same output)."""
        job = _create_job_with_action("build_foundup")
        request = executor.build_delegation_request(job)

        results = [
            executor._classify_destructive_action(job, request)
            for _ in range(10)
        ]
        assert all(r == DestructiveActionClass.D3_WRITE_SANDBOX for r in results)

    def test_classification_handles_whitespace(self, executor):
        """Classification should handle leading/trailing whitespace."""
        job = _create_job_with_action("  validate_foundup  ")
        request = executor.build_delegation_request(job)
        result = executor._classify_destructive_action(job, request)

        assert result == DestructiveActionClass.D0_OBSERVE


# ===========================================================================
# SECTION 13: HXA28 Verdict Documentation Test
# ===========================================================================


class TestHXA28VerdictDocumentation:
    """Document HXA28 verdict and proof."""

    def test_hxa28_verdict_d3_native_classification_defined(self, temp_workspace):
        """
        HXA28 Verdict: D3_NATIVE_CLASSIFICATION_DEFINED

        HXA27 verdict was: HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED

        HXA28 proves:
        1. D0/D1 observe/read actions -> dry-run allowed
        2. D2 simulate/plan/dry_run actions -> dry-run allowed
        3. D3 sandbox evidence/checkpoint writes -> allowed with all gates
        4. D4 repo creation/git operations -> BLOCKED Phase 1
        5. D5 external API mutations -> BLOCKED Phase 1
        6. D6 delete/credential/payout/irreversible -> BLOCKED Phase 1
        7. Unknown/ambiguous actions -> D6 fail-closed -> BLOCKED
        8. Valid token does NOT downgrade D4/D5/D6 classification
        9. Invalid token still blocks before classification/guard
        10. Classification is deterministic and case-insensitive
        11. All WSP 97 truth fields remain False:
            - real_execution_performed = False
            - verification_complete = False
            - cabr_ready = False
            - payout_ready = False
            - repo_created = False
            - production_source_modified = False
            - live_external_delegate_called = False
            - external_federation_initiated = False

        This does NOT enable live delegation.
        This does NOT create repos.
        This does NOT modify production source.
        This does NOT weaken guard logic.
        This DOES harden classification to be explicit and deterministic.
        """
        verdict = "D3_NATIVE_CLASSIFICATION_DEFINED"

        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)

        # Test D0 allowed
        d0_job = _create_job_with_action("validate_foundup")
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d0_result = executor.execute(d0_job)
            assert d0_result.guard_result["destructive_class"] == "D0_OBSERVE"
            assert d0_result.guard_result["allowed"] is True

        # Test D3 allowed with all gates
        d3_job = _create_job_with_all_gates("build_foundup")
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d3_result = executor.execute(d3_job)
            assert d3_result.guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
            assert d3_result.guard_result["allowed"] is True

        # Test D4 blocked
        d4_job = _create_job_with_action("create_repo")
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d4_result = executor.execute(d4_job)
            assert d4_result.guard_result["destructive_class"] == "D4_WRITE_REPO"
            assert d4_result.guard_result["allowed"] is False

        # Test D6 blocked (unknown action)
        d6_job = _create_job_with_action("unknown_operation")
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d6_result = executor.execute(d6_job)
            assert d6_result.guard_result["destructive_class"] == "D6_IRREVERSIBLE"
            assert d6_result.guard_result["allowed"] is False

        # Verify WSP 97 truth fields
        assert d0_result.real_execution_performed is False
        assert d3_result.real_execution_performed is False
        assert d4_result.repo_created is False
        assert d6_result.real_execution_performed is False

        assert verdict == "D3_NATIVE_CLASSIFICATION_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
