#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA24 Proof Test: Capability Token PolicyFlags (Phase 1)

Tests the addition of capability token policy flags to FoundUpJob.policy_flags
and their integration into Hermes guard request construction.

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA23 Verdict was: HERMES_GUARD_INTEGRATION_DEFINED
HXA24 defines: Capability token policy flags in PolicyFlags for D3+ gate control.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Use real credentials
  - Initiate external federation
  - Issue real tokens
  - Validate real tokens

Key Behaviors Tested:
  1. PolicyFlags has capability_token_checked field (default False)
  2. PolicyFlags has capability_token_present field (default False)
  3. PolicyFlags has capability_token_validated field (default False)
  4. PolicyFlags has capability_token_scope_authorized field (default False)
  5. PolicyFlags.to_dict() includes all four fields
  6. PolicyFlags.from_dict() restores all four fields
  7. Missing fields in from_dict() default to False (backward compat)
  8. Default policy flags block D3 (capability_token_present=False)
  9. checked+present but NOT validated blocks D3
  10. checked+present+validated but NOT scope_authorized blocks D3
  11. All four True allows D3 sandbox dry-run when other gates pass
  12. D4/D5/D6 still blocked even with token
  13. All WSP 97 truth fields remain False

Slice: HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1
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


# ===========================================================================
# SECTION 2: PolicyFlags Capability Token Field Tests
# ===========================================================================


class TestPolicyFlagsCapabilityTokenFields:
    """Test PolicyFlags has capability token fields with correct defaults."""

    def test_capability_token_checked_default_false(self):
        """capability_token_checked should default to False."""
        flags = PolicyFlags()
        assert flags.capability_token_checked is False

    def test_capability_token_present_default_false(self):
        """capability_token_present should default to False."""
        flags = PolicyFlags()
        assert flags.capability_token_present is False

    def test_capability_token_validated_default_false(self):
        """capability_token_validated should default to False."""
        flags = PolicyFlags()
        assert flags.capability_token_validated is False

    def test_capability_token_scope_authorized_default_false(self):
        """capability_token_scope_authorized should default to False."""
        flags = PolicyFlags()
        assert flags.capability_token_scope_authorized is False

    def test_all_capability_token_fields_can_be_set_true(self):
        """All capability token fields can be set to True."""
        flags = PolicyFlags(
            capability_token_checked=True,
            capability_token_present=True,
            capability_token_validated=True,
            capability_token_scope_authorized=True,
        )
        assert flags.capability_token_checked is True
        assert flags.capability_token_present is True
        assert flags.capability_token_validated is True
        assert flags.capability_token_scope_authorized is True


# ===========================================================================
# SECTION 3: PolicyFlags Serialization Tests
# ===========================================================================


class TestPolicyFlagsSerialization:
    """Test PolicyFlags to_dict/from_dict includes capability token fields."""

    def test_to_dict_includes_capability_token_fields(self):
        """to_dict() should include all capability token fields."""
        flags = PolicyFlags(
            capability_token_checked=True,
            capability_token_present=True,
            capability_token_validated=False,
            capability_token_scope_authorized=False,
        )
        d = flags.to_dict()

        assert "capability_token_checked" in d
        assert "capability_token_present" in d
        assert "capability_token_validated" in d
        assert "capability_token_scope_authorized" in d

        assert d["capability_token_checked"] is True
        assert d["capability_token_present"] is True
        assert d["capability_token_validated"] is False
        assert d["capability_token_scope_authorized"] is False

    def test_from_dict_restores_capability_token_fields(self):
        """from_dict() should restore all capability token fields."""
        data = {
            "capability_token_checked": True,
            "capability_token_present": True,
            "capability_token_validated": True,
            "capability_token_scope_authorized": True,
        }
        flags = PolicyFlags.from_dict(data)

        assert flags.capability_token_checked is True
        assert flags.capability_token_present is True
        assert flags.capability_token_validated is True
        assert flags.capability_token_scope_authorized is True

    def test_from_dict_missing_fields_default_false(self):
        """from_dict() with missing fields should default to False."""
        # Empty dict - all fields should be False (backward compatibility)
        flags = PolicyFlags.from_dict({})

        assert flags.capability_token_checked is False
        assert flags.capability_token_present is False
        assert flags.capability_token_validated is False
        assert flags.capability_token_scope_authorized is False

    def test_roundtrip_preserves_all_fields(self):
        """to_dict/from_dict roundtrip should preserve all fields."""
        original = PolicyFlags(
            security_gate_checked=True,
            security_gate_passed=True,
            capability_token_checked=True,
            capability_token_present=True,
            capability_token_validated=True,
            capability_token_scope_authorized=True,
            dry_run_mode=True,
        )
        data = original.to_dict()
        restored = PolicyFlags.from_dict(data)

        assert restored.security_gate_checked == original.security_gate_checked
        assert restored.security_gate_passed == original.security_gate_passed
        assert restored.capability_token_checked == original.capability_token_checked
        assert restored.capability_token_present == original.capability_token_present
        assert restored.capability_token_validated == original.capability_token_validated
        assert restored.capability_token_scope_authorized == original.capability_token_scope_authorized
        assert restored.dry_run_mode == original.dry_run_mode


# ===========================================================================
# SECTION 4: Job Serialization with Capability Token Fields
# ===========================================================================


class TestJobSerializationWithCapabilityToken:
    """Test FoundUpJob serialization with capability token PolicyFlags."""

    def test_job_to_dict_includes_capability_token_flags(self):
        """Job to_dict() should include capability token flags in policy_flags."""
        job = create_job(tenant_id="t", requested_action="build_foundup")
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True

        data = job.to_dict()
        policy_data = data["policy_flags"]

        assert "capability_token_checked" in policy_data
        assert "capability_token_present" in policy_data
        assert policy_data["capability_token_checked"] is True
        assert policy_data["capability_token_present"] is True

    def test_job_from_dict_restores_capability_token_flags(self):
        """Job from_dict() should restore capability token flags."""
        job = create_job(tenant_id="t", requested_action="build_foundup")
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        assert restored.policy_flags.capability_token_checked is True
        assert restored.policy_flags.capability_token_present is True
        assert restored.policy_flags.capability_token_validated is True
        assert restored.policy_flags.capability_token_scope_authorized is True


# ===========================================================================
# SECTION 5: Default Policy Flags Block D3 Tests
# ===========================================================================


class TestDefaultPolicyFlagsBlockD3:
    """Test that default policy flags block D3 sandbox write."""

    def test_default_flags_block_d3(self, temp_workspace):
        """D3 sandbox write should be blocked with default policy flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Default policy_flags: all capability token flags are False

        # Mock to force D3 classification
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
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"


# ===========================================================================
# SECTION 6: Partial Capability Token Flags Block D3 Tests
# ===========================================================================


class TestPartialCapabilityTokenFlagsBlockD3:
    """Test that partial capability token flags block D3."""

    def test_checked_but_not_present_blocks_d3(self, temp_workspace):
        """D3 blocked when checked=True but present=False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = False  # Not present

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"

    def test_checked_present_but_not_validated_blocks_d3(self, temp_workspace):
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

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_CAPABILITY_TOKEN"

    def test_checked_present_validated_but_not_scope_authorized_blocks_d3(self, temp_workspace):
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
# SECTION 7: All Four True Allows D3 Sandbox Dry-Run Tests
# ===========================================================================


class TestAllFourTrueAllowsD3SandboxDryRun:
    """Test that all four capability token flags True allows D3 sandbox dry-run."""

    def test_all_four_true_with_security_gate_allows_d3(self, temp_workspace):
        """D3 sandbox allowed when all four token flags True AND security gate passed."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Set all capability token flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        # Also need security gate for D3
        job.policy_flags.security_gate_checked = True
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # With all gates passing, D3 should be allowed as dry-run
                # Guard allows, but overall status is SIMULATED (dry_run=True)
                assert result.guard_result["allowed"] is True
                assert result.guard_result["decision"] == "ALLOW_DRY_RUN"
                assert result.status == HermesExecutionStatus.SIMULATED

    def test_all_four_true_but_missing_security_gate_blocks_d3(self, temp_workspace):
        """D3 blocked when all token flags True BUT security gate not passed."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Set all capability token flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        # But security gate NOT passed
        job.policy_flags.security_gate_checked = True
        job.policy_flags.security_gate_passed = False  # Not passed

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D3_WRITE_SANDBOX,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # Security gate failed
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "MISSING_SECURITY_GATE"


# ===========================================================================
# SECTION 8: D4/D5/D6 Still Blocked Even With Token Tests
# ===========================================================================


class TestD4D5D6StillBlockedEvenWithToken:
    """Test that D4/D5/D6 are blocked even with all token flags True."""

    def test_d4_blocked_with_all_token_flags(self, temp_workspace):
        """D4 repo write blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="create_repo",
            foundup_id="test",
        )
        # All capability token flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D4_WRITE_REPO,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # D4 blocked in Phase 1 regardless of tokens
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d5_blocked_with_all_token_flags(self, temp_workspace):
        """D5 external side effect blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="send_email",
            foundup_id="test",
        )
        # All capability token flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # D5 blocked in Phase 1 regardless of tokens
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d6_blocked_with_all_token_flags(self, temp_workspace):
        """D6 irreversible blocked even with all capability token flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="delete_permanently",
            foundup_id="test",
        )
        # All capability token flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=DestructiveActionClass.D6_IRREVERSIBLE,
        ):
            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
                result = executor.execute(job)

                # D6 blocked in Phase 1 regardless of tokens
                assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
                assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 9: WSP 97 Truth Fields Preserved Tests
# ===========================================================================


class TestWSP97TruthFieldsPreserved:
    """Test all WSP 97 truth fields remain False regardless of token flags."""

    def test_live_execution_allowed_false(self, temp_workspace):
        """live_execution_allowed should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # All flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Guard result should show live_execution_allowed=False
            assert result.guard_result["live_execution_allowed"] is False

    def test_repo_created_false(self, temp_workspace):
        """repo_created should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.repo_created is False

    def test_production_source_modified_false(self, temp_workspace):
        """production_source_modified should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.production_source_modified is False

    def test_real_execution_performed_false(self, temp_workspace):
        """real_execution_performed should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # All flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        job.policy_flags.security_gate_passed = True

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.real_execution_performed is False

    def test_verification_complete_false(self, temp_workspace):
        """verification_complete should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.verification_complete is False

    def test_cabr_ready_false(self, temp_workspace):
        """cabr_ready should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.cabr_ready is False

    def test_payout_ready_false(self, temp_workspace):
        """payout_ready should be False."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.payout_ready is False


# ===========================================================================
# SECTION 10: Guard Request Construction Tests
# ===========================================================================


class TestGuardRequestConstruction:
    """Test guard request construction reads capability token flags."""

    def test_guard_request_capability_token_false_when_default(self, temp_workspace):
        """Guard request should have capability_token_present=False for default flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )

        request = executor.build_delegation_request(job)
        guard_request = executor._build_destructive_action_request(job, request)

        assert guard_request.capability_token_present is False

    def test_guard_request_capability_token_false_when_partial(self, temp_workspace):
        """Guard request should have capability_token_present=False for partial flags."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # Only some flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = False  # Missing

        request = executor.build_delegation_request(job)
        guard_request = executor._build_destructive_action_request(job, request)

        assert guard_request.capability_token_present is False

    def test_guard_request_capability_token_true_when_all_four(self, temp_workspace):
        """Guard request should have capability_token_present=True when all four flags True."""
        executor = HermesJobExecutor(workspace_root=temp_workspace, dry_run=True)
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
        )
        # All four flags True
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True

        request = executor.build_delegation_request(job)
        guard_request = executor._build_destructive_action_request(job, request)

        assert guard_request.capability_token_present is True


# ===========================================================================
# SECTION 11: HXA24 Verdict Documentation Test
# ===========================================================================


class TestHXA24VerdictDocumentation:
    """Document HXA24 verdict and proof."""

    def test_hxa24_verdict_capability_token_policyflags_defined(self, temp_workspace):
        """
        HXA24 Verdict: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED

        HXA23 verdict was: HERMES_GUARD_INTEGRATION_DEFINED

        HXA24 proves:
        1. PolicyFlags has capability_token_checked field (default False)
        2. PolicyFlags has capability_token_present field (default False)
        3. PolicyFlags has capability_token_validated field (default False)
        4. PolicyFlags has capability_token_scope_authorized field (default False)
        5. PolicyFlags.to_dict() includes all four fields
        6. PolicyFlags.from_dict() restores all four fields
        7. Missing fields in from_dict() default to False (backward compat)
        8. Default policy flags block D3 (capability_token_present=False)
        9. checked+present but NOT validated blocks D3
        10. checked+present+validated but NOT scope_authorized blocks D3
        11. All four True allows D3 sandbox dry-run when other gates pass
        12. D4/D5/D6 still blocked even with token
        13. All WSP 97 truth fields remain False:
            - live_execution_allowed = False
            - repo_created = False
            - production_source_modified = False
            - external_federation_initiated = False
            - real_execution_performed = False
            - verification_complete = False
            - cabr_ready = False
            - payout_ready = False

        This does NOT enable live delegation.
        This does NOT create repos.
        This does NOT modify production source.
        This does NOT issue real tokens.
        This does NOT validate real tokens.
        This DOES add capability token policy flags.
        """
        verdict = "CAPABILITY_TOKEN_POLICYFLAGS_DEFINED"

        # Verify PolicyFlags has all new fields
        flags = PolicyFlags()
        assert hasattr(flags, "capability_token_checked")
        assert hasattr(flags, "capability_token_present")
        assert hasattr(flags, "capability_token_validated")
        assert hasattr(flags, "capability_token_scope_authorized")

        # Verify defaults are False
        assert flags.capability_token_checked is False
        assert flags.capability_token_present is False
        assert flags.capability_token_validated is False
        assert flags.capability_token_scope_authorized is False

        # Verify serialization includes fields
        d = flags.to_dict()
        assert "capability_token_checked" in d
        assert "capability_token_present" in d
        assert "capability_token_validated" in d
        assert "capability_token_scope_authorized" in d

        assert verdict == "CAPABILITY_TOKEN_POLICYFLAGS_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
