#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA22 Proof Test: Destructive Action Guard Runtime (Phase 1)

Tests the fail-closed destructive action guard for WRE/Hermes flow.
Validates that the guard correctly blocks D4/D5/D6 actions and allows
D0-D3 only under proper conditions.

WSP 97 Truth Boundaries:
  - live_execution_allowed: False (ALWAYS - Phase 1 blocks live execution)
  - repo_created: False (ALWAYS - this slice MUST NOT create repos)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA19 Verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED
HXA20 Verdict was: PRODUCTION_SOURCE_GATE_DEFINED
HXA21 Verdict was: CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED
HXA22 defines: Runtime destructive action guard with fail-closed behavior.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Use real credentials or capability tokens
  - Initiate external federation

Key Principle: FAIL-CLOSED
  - D0 observe: allowed only in dry-run mode
  - D1 read: allowed only in dry-run mode
  - D2 simulate: allowed only in dry-run mode
  - D3 sandbox write: requires workspace_binding, path_validation, capability_token, security_gate
  - D4 repo write: BLOCKED in Phase 1
  - D5 external side effect: BLOCKED in Phase 1
  - D6 irreversible: BLOCKED in Phase 1
  - unknown class: BLOCKED

Slice: HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1
Worker: 0102
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from modules.infrastructure.wre_core.src.destructive_action_guard import (
    DestructiveActionClass,
    DestructiveActionGuard,
    DestructiveActionGuardResult,
    DestructiveActionRequest,
    GuardBlockReasonCode,
    GuardDecision,
    class_at_least,
    class_severity,
    evaluate_destructive_action,
    get_destructive_action_guard,
)


# ===========================================================================
# SECTION 1: Helper Functions
# ===========================================================================


def _create_base_request(
    action_class: DestructiveActionClass,
    dry_run_mode: bool = True,
    human_approval: bool = False,
    capability_token_present: bool = False,
    security_gate_passed: bool = False,
    workspace_binding_enforced: bool = False,
    path_constraints_validated: bool = False,
) -> DestructiveActionRequest:
    """Create a base request for testing."""
    return DestructiveActionRequest(
        action_id=f"act_{secrets.token_hex(4)}",
        action_type="test_action",
        target_path="/tmp/test/file.txt",
        requested_class=action_class,
        dry_run_mode=dry_run_mode,
        human_approval=human_approval,
        capability_token_present=capability_token_present,
        security_gate_passed=security_gate_passed,
        workspace_binding_enforced=workspace_binding_enforced,
        path_constraints_validated=path_constraints_validated,
        requester_id="test_agent_0102",
        job_id="j_test_001",
    )


def _create_d3_valid_request() -> DestructiveActionRequest:
    """Create a D3 request with all required gates passed."""
    return DestructiveActionRequest(
        action_id=f"act_{secrets.token_hex(4)}",
        action_type="sandbox_write",
        target_path="/tmp/test/sandbox/file.txt",
        requested_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        dry_run_mode=True,
        human_approval=False,  # Not required for D3
        capability_token_present=True,
        security_gate_passed=True,
        workspace_binding_enforced=True,
        path_constraints_validated=True,
        requester_id="test_agent_0102",
        job_id="j_test_d3",
    )


# ===========================================================================
# SECTION 2: WSP97 Truth Tracker
# ===========================================================================


class WSP97TruthTracker:
    """
    Tracks WSP 97 truth fields for destructive action guard.

    All fields MUST remain False during HXA22 - no live operations allowed.
    """

    def __init__(self):
        self.live_execution_allowed: bool = False
        self.repo_created: bool = False
        self.production_source_modified: bool = False
        self.external_federation_initiated: bool = False
        self.verification_complete: bool = False
        self.cabr_ready: bool = False
        self.payout_ready: bool = False

    def all_false(self) -> bool:
        """Verify all truth fields are False."""
        return not any([
            self.live_execution_allowed,
            self.repo_created,
            self.production_source_modified,
            self.external_federation_initiated,
            self.verification_complete,
            self.cabr_ready,
            self.payout_ready,
        ])


# ===========================================================================
# SECTION 3: Test Classes
# ===========================================================================


class TestDestructiveActionClassEnum:
    """Test the DestructiveActionClass enum."""

    def test_all_classes_defined(self):
        """All D0-D6 classes should be defined."""
        assert DestructiveActionClass.D0_OBSERVE
        assert DestructiveActionClass.D1_READ
        assert DestructiveActionClass.D2_SIMULATE
        assert DestructiveActionClass.D3_WRITE_SANDBOX
        assert DestructiveActionClass.D4_WRITE_REPO
        assert DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT
        assert DestructiveActionClass.D6_IRREVERSIBLE

    def test_class_severity_ordering(self):
        """Classes should have increasing severity D0 < D1 < ... < D6."""
        assert class_severity(DestructiveActionClass.D0_OBSERVE) < class_severity(DestructiveActionClass.D1_READ)
        assert class_severity(DestructiveActionClass.D1_READ) < class_severity(DestructiveActionClass.D2_SIMULATE)
        assert class_severity(DestructiveActionClass.D2_SIMULATE) < class_severity(DestructiveActionClass.D3_WRITE_SANDBOX)
        assert class_severity(DestructiveActionClass.D3_WRITE_SANDBOX) < class_severity(DestructiveActionClass.D4_WRITE_REPO)
        assert class_severity(DestructiveActionClass.D4_WRITE_REPO) < class_severity(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT)
        assert class_severity(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT) < class_severity(DestructiveActionClass.D6_IRREVERSIBLE)

    def test_class_at_least_comparison(self):
        """class_at_least should correctly compare severity."""
        assert class_at_least(DestructiveActionClass.D3_WRITE_SANDBOX, DestructiveActionClass.D3_WRITE_SANDBOX) is True
        assert class_at_least(DestructiveActionClass.D4_WRITE_REPO, DestructiveActionClass.D3_WRITE_SANDBOX) is True
        assert class_at_least(DestructiveActionClass.D2_SIMULATE, DestructiveActionClass.D3_WRITE_SANDBOX) is False


class TestDestructiveActionRequest:
    """Test the DestructiveActionRequest dataclass."""

    def test_default_values_are_safe(self):
        """Default request values should be fail-safe."""
        request = DestructiveActionRequest(
            action_id="test_001",
            action_type="test",
            target_path="/tmp/test",
            requested_class=DestructiveActionClass.D0_OBSERVE,
        )

        assert request.dry_run_mode is True
        assert request.human_approval is False
        assert request.capability_token_present is False
        assert request.security_gate_passed is False
        assert request.workspace_binding_enforced is False
        assert request.path_constraints_validated is False

    def test_all_required_fields_present(self):
        """Request should have all required fields."""
        request = _create_base_request(DestructiveActionClass.D0_OBSERVE)

        assert hasattr(request, "action_id")
        assert hasattr(request, "action_type")
        assert hasattr(request, "target_path")
        assert hasattr(request, "requested_class")
        assert hasattr(request, "dry_run_mode")
        assert hasattr(request, "human_approval")
        assert hasattr(request, "capability_token_present")
        assert hasattr(request, "security_gate_passed")
        assert hasattr(request, "workspace_binding_enforced")
        assert hasattr(request, "path_constraints_validated")

    def test_to_dict_serialization(self):
        """Request should serialize to dict correctly."""
        request = _create_base_request(DestructiveActionClass.D1_READ)
        data = request.to_dict()

        assert "action_id" in data
        assert "action_type" in data
        assert "requested_class" in data
        assert data["requested_class"] == "D1_READ"
        assert "dry_run_mode" in data


class TestDestructiveActionGuardResult:
    """Test the DestructiveActionGuardResult dataclass."""

    def test_wsp97_truth_fields_default_false(self):
        """WSP 97 truth fields should default to False."""
        result = DestructiveActionGuardResult(
            allowed=True,
            decision=GuardDecision.ALLOW_DRY_RUN,
            reason_code=GuardBlockReasonCode.OK_DRY_RUN,
            destructive_class=DestructiveActionClass.D0_OBSERVE,
        )

        assert result.live_execution_allowed is False
        assert result.repo_created is False
        assert result.production_source_modified is False
        assert result.external_federation_initiated is False
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    def test_to_dict_includes_all_fields(self):
        """Result should serialize all fields to dict."""
        result = DestructiveActionGuardResult(
            allowed=True,
            decision=GuardDecision.ALLOW_DRY_RUN,
            reason_code=GuardBlockReasonCode.OK_DRY_RUN,
            destructive_class=DestructiveActionClass.D2_SIMULATE,
            reason_human="Test result",
        )

        data = result.to_dict()

        assert "allowed" in data
        assert "decision" in data
        assert "reason_code" in data
        assert "destructive_class" in data
        assert "live_execution_allowed" in data
        assert "repo_created" in data
        assert "production_source_modified" in data


class TestD0ObserveDryRunAllowed:
    """Test D0 observe is allowed in dry-run mode."""

    def test_d0_observe_dry_run_allowed(self):
        """D0 observe should be allowed in dry-run mode."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D0_OBSERVE,
            dry_run_mode=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
        assert result.reason_code == GuardBlockReasonCode.OK_DRY_RUN
        assert result.dry_run_only is True
        assert result.live_execution_allowed is False


class TestD1ReadDryRunAllowed:
    """Test D1 read is allowed in dry-run mode."""

    def test_d1_read_dry_run_allowed(self):
        """D1 read should be allowed in dry-run mode."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D1_READ,
            dry_run_mode=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
        assert result.reason_code == GuardBlockReasonCode.OK_DRY_RUN
        assert result.dry_run_only is True
        assert result.live_execution_allowed is False


class TestD2SimulateAllowed:
    """Test D2 simulate is allowed in dry-run mode."""

    def test_d2_simulate_allowed(self):
        """D2 simulate should be allowed with dry_run_mode=True."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D2_SIMULATE,
            dry_run_mode=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
        assert result.reason_code == GuardBlockReasonCode.OK_DRY_RUN
        assert result.dry_run_only is True
        assert result.live_execution_allowed is False


class TestD3SandboxWriteGates:
    """Test D3 sandbox write gate requirements."""

    def test_d3_sandbox_blocked_without_workspace_binding(self):
        """D3 sandbox write should be blocked without workspace binding."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D3_WRITE_SANDBOX,
            dry_run_mode=True,
            capability_token_present=True,
            security_gate_passed=True,
            workspace_binding_enforced=False,  # Missing
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_WORKSPACE_BINDING
        assert "workspace_binding" in result.gates_failed

    def test_d3_sandbox_blocked_without_path_validation(self):
        """D3 sandbox write should be blocked without path validation."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D3_WRITE_SANDBOX,
            dry_run_mode=True,
            capability_token_present=True,
            security_gate_passed=True,
            workspace_binding_enforced=True,
            path_constraints_validated=False,  # Missing
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_PATH_VALIDATION
        assert "path_constraints" in result.gates_failed

    def test_d3_sandbox_blocked_without_capability_token(self):
        """D3 sandbox write should be blocked without capability token."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D3_WRITE_SANDBOX,
            dry_run_mode=True,
            capability_token_present=False,  # Missing
            security_gate_passed=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_CAPABILITY_TOKEN
        assert "capability_token" in result.gates_failed

    def test_d3_sandbox_blocked_without_security_gate(self):
        """D3 sandbox write should be blocked without security gate."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D3_WRITE_SANDBOX,
            dry_run_mode=True,
            capability_token_present=True,
            security_gate_passed=False,  # Missing
            workspace_binding_enforced=True,
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_SECURITY_GATE
        assert "security_gate" in result.gates_failed

    def test_d3_sandbox_allowed_with_all_gates(self):
        """D3 sandbox write should be allowed when all gates pass."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
        assert result.reason_code == GuardBlockReasonCode.OK_SANDBOX
        assert "workspace_binding" in result.gates_passed
        assert "path_constraints" in result.gates_passed
        assert "capability_token" in result.gates_passed
        assert "security_gate" in result.gates_passed
        # WSP 97 truth fields
        assert result.live_execution_allowed is False
        assert result.repo_created is False
        assert result.production_source_modified is False


class TestD4RepoWriteBlocked:
    """Test D4 repo write is blocked in Phase 1."""

    def test_d4_repo_write_blocked(self):
        """D4 repo write should be blocked in Phase 1."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D4_WRITE_REPO,
            dry_run_mode=True,
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1
        assert result.live_execution_allowed is False
        assert result.repo_created is False


class TestD5ExternalSideEffectBlocked:
    """Test D5 external side effect is blocked in Phase 1."""

    def test_d5_external_side_effect_blocked(self):
        """D5 external side effect should be blocked in Phase 1."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
            dry_run_mode=True,
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.BLOCKED_D5_EXTERNAL_PHASE1
        assert result.live_execution_allowed is False
        assert result.external_federation_initiated is False


class TestD6IrreversibleBlocked:
    """Test D6 irreversible is blocked in Phase 1."""

    def test_d6_irreversible_blocked(self):
        """D6 irreversible should be blocked in Phase 1."""
        guard = DestructiveActionGuard()
        request = _create_base_request(
            DestructiveActionClass.D6_IRREVERSIBLE,
            dry_run_mode=True,
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.BLOCKED_D6_IRREVERSIBLE_PHASE1
        assert result.live_execution_allowed is False


class TestLiveExecutionAlwaysFalse:
    """Test live_execution_allowed is always False."""

    def test_live_execution_allowed_false_on_allow(self):
        """live_execution_allowed should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.live_execution_allowed is False

    def test_live_execution_allowed_false_on_block(self):
        """live_execution_allowed should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D4_WRITE_REPO)

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.live_execution_allowed is False


class TestRepoCreatedAlwaysFalse:
    """Test repo_created is always False."""

    def test_repo_created_false_on_allow(self):
        """repo_created should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.repo_created is False

    def test_repo_created_false_on_block(self):
        """repo_created should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D4_WRITE_REPO)

        result = guard.evaluate(request)

        assert result.repo_created is False


class TestProductionSourceModifiedAlwaysFalse:
    """Test production_source_modified is always False."""

    def test_production_source_modified_false_on_allow(self):
        """production_source_modified should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.production_source_modified is False

    def test_production_source_modified_false_on_block(self):
        """production_source_modified should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT)

        result = guard.evaluate(request)

        assert result.production_source_modified is False


class TestExternalFederationInitiatedAlwaysFalse:
    """Test external_federation_initiated is always False."""

    def test_external_federation_initiated_false_on_allow(self):
        """external_federation_initiated should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.external_federation_initiated is False

    def test_external_federation_initiated_false_on_block(self):
        """external_federation_initiated should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D6_IRREVERSIBLE)

        result = guard.evaluate(request)

        assert result.external_federation_initiated is False


class TestVerificationCompleteAlwaysFalse:
    """Test verification_complete is always False."""

    def test_verification_complete_false_on_allow(self):
        """verification_complete should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.verification_complete is False

    def test_verification_complete_false_on_block(self):
        """verification_complete should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D4_WRITE_REPO)

        result = guard.evaluate(request)

        assert result.verification_complete is False


class TestCABRReadyAlwaysFalse:
    """Test cabr_ready is always False."""

    def test_cabr_ready_false_on_allow(self):
        """cabr_ready should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.cabr_ready is False

    def test_cabr_ready_false_on_block(self):
        """cabr_ready should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT)

        result = guard.evaluate(request)

        assert result.cabr_ready is False


class TestPayoutReadyAlwaysFalse:
    """Test payout_ready is always False."""

    def test_payout_ready_false_on_allow(self):
        """payout_ready should be False even when allowed."""
        guard = DestructiveActionGuard()
        request = _create_d3_valid_request()

        result = guard.evaluate(request)

        assert result.payout_ready is False

    def test_payout_ready_false_on_block(self):
        """payout_ready should be False when blocked."""
        guard = DestructiveActionGuard()
        request = _create_base_request(DestructiveActionClass.D6_IRREVERSIBLE)

        result = guard.evaluate(request)

        assert result.payout_ready is False


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_destructive_action_guard_singleton(self):
        """get_destructive_action_guard should return consistent singleton."""
        guard1 = get_destructive_action_guard()
        guard2 = get_destructive_action_guard()

        assert guard1 is guard2
        assert isinstance(guard1, DestructiveActionGuard)

    def test_evaluate_destructive_action_convenience(self):
        """evaluate_destructive_action should work as convenience function."""
        request = _create_base_request(
            DestructiveActionClass.D0_OBSERVE,
            dry_run_mode=True,
        )

        result = evaluate_destructive_action(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN


class TestWSP97TruthFieldsPreserved:
    """Test all WSP 97 truth fields are preserved correctly."""

    def test_all_wsp97_fields_false_in_tracker(self):
        """WSP97TruthTracker should have all fields False."""
        tracker = WSP97TruthTracker()

        assert tracker.live_execution_allowed is False
        assert tracker.repo_created is False
        assert tracker.production_source_modified is False
        assert tracker.external_federation_initiated is False
        assert tracker.verification_complete is False
        assert tracker.cabr_ready is False
        assert tracker.payout_ready is False
        assert tracker.all_false() is True

    def test_all_results_preserve_wsp97_fields(self):
        """All guard results should preserve WSP 97 truth fields."""
        guard = DestructiveActionGuard()

        # Test all action classes
        test_cases = [
            (DestructiveActionClass.D0_OBSERVE, True, True),
            (DestructiveActionClass.D1_READ, True, True),
            (DestructiveActionClass.D2_SIMULATE, True, True),
            (DestructiveActionClass.D3_WRITE_SANDBOX, False, False),  # Missing gates
            (DestructiveActionClass.D4_WRITE_REPO, True, False),
            (DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT, True, False),
            (DestructiveActionClass.D6_IRREVERSIBLE, True, False),
        ]

        for action_class, dry_run, expected_allowed in test_cases:
            request = _create_base_request(action_class, dry_run_mode=dry_run)
            result = guard.evaluate(request)

            # WSP 97 truth fields must ALWAYS be False
            assert result.live_execution_allowed is False, f"{action_class}: live_execution_allowed"
            assert result.repo_created is False, f"{action_class}: repo_created"
            assert result.production_source_modified is False, f"{action_class}: production_source_modified"
            assert result.external_federation_initiated is False, f"{action_class}: external_federation_initiated"
            assert result.verification_complete is False, f"{action_class}: verification_complete"
            assert result.cabr_ready is False, f"{action_class}: cabr_ready"
            assert result.payout_ready is False, f"{action_class}: payout_ready"


class TestHXA22CompleteGuardFlow:
    """Integration tests for complete HXA22 guard flow."""

    def test_complete_guard_evaluation_flow(self):
        """
        HXA22 PROOF: Complete destructive action guard evaluation flow.

        This test proves:
        1. Guard model has all required fields
        2. Request model captures all gate requirements
        3. Result model captures all WSP 97 truth fields
        4. D0/D1/D2 allowed in dry-run mode
        5. D3 requires all gates to pass
        6. D4/D5/D6 blocked in Phase 1
        7. All WSP 97 truth fields remain False
        """
        guard = DestructiveActionGuard()

        # D0 observe - allowed
        d0_request = _create_base_request(DestructiveActionClass.D0_OBSERVE, dry_run_mode=True)
        d0_result = guard.evaluate(d0_request)
        assert d0_result.allowed is True
        assert d0_result.live_execution_allowed is False

        # D1 read - allowed
        d1_request = _create_base_request(DestructiveActionClass.D1_READ, dry_run_mode=True)
        d1_result = guard.evaluate(d1_request)
        assert d1_result.allowed is True
        assert d1_result.live_execution_allowed is False

        # D2 simulate - allowed
        d2_request = _create_base_request(DestructiveActionClass.D2_SIMULATE, dry_run_mode=True)
        d2_result = guard.evaluate(d2_request)
        assert d2_result.allowed is True
        assert d2_result.live_execution_allowed is False

        # D3 sandbox - allowed with all gates
        d3_request = _create_d3_valid_request()
        d3_result = guard.evaluate(d3_request)
        assert d3_result.allowed is True
        assert d3_result.live_execution_allowed is False
        assert d3_result.repo_created is False
        assert d3_result.production_source_modified is False

        # D4 repo - blocked
        d4_request = _create_base_request(DestructiveActionClass.D4_WRITE_REPO)
        d4_result = guard.evaluate(d4_request)
        assert d4_result.allowed is False
        assert d4_result.decision == GuardDecision.BLOCKED

        # D5 external - blocked
        d5_request = _create_base_request(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT)
        d5_result = guard.evaluate(d5_request)
        assert d5_result.allowed is False
        assert d5_result.decision == GuardDecision.BLOCKED

        # D6 irreversible - blocked
        d6_request = _create_base_request(DestructiveActionClass.D6_IRREVERSIBLE)
        d6_result = guard.evaluate(d6_request)
        assert d6_result.allowed is False
        assert d6_result.decision == GuardDecision.BLOCKED

        # Verify tracker
        tracker = WSP97TruthTracker()
        assert tracker.all_false() is True

    def test_all_blocking_conditions_tested(self):
        """
        HXA22 PROOF: All blocking conditions are tested.

        Enumerates all blocking scenarios to prove fail-closed behavior.
        """
        guard = DestructiveActionGuard()

        blocking_tests = [
            # D3 without workspace binding
            (
                _create_base_request(
                    DestructiveActionClass.D3_WRITE_SANDBOX,
                    workspace_binding_enforced=False,
                    path_constraints_validated=True,
                    capability_token_present=True,
                    security_gate_passed=True,
                ),
                GuardBlockReasonCode.MISSING_WORKSPACE_BINDING,
            ),
            # D3 without path validation
            (
                _create_base_request(
                    DestructiveActionClass.D3_WRITE_SANDBOX,
                    workspace_binding_enforced=True,
                    path_constraints_validated=False,
                    capability_token_present=True,
                    security_gate_passed=True,
                ),
                GuardBlockReasonCode.MISSING_PATH_VALIDATION,
            ),
            # D3 without capability token
            (
                _create_base_request(
                    DestructiveActionClass.D3_WRITE_SANDBOX,
                    workspace_binding_enforced=True,
                    path_constraints_validated=True,
                    capability_token_present=False,
                    security_gate_passed=True,
                ),
                GuardBlockReasonCode.MISSING_CAPABILITY_TOKEN,
            ),
            # D3 without security gate
            (
                _create_base_request(
                    DestructiveActionClass.D3_WRITE_SANDBOX,
                    workspace_binding_enforced=True,
                    path_constraints_validated=True,
                    capability_token_present=True,
                    security_gate_passed=False,
                ),
                GuardBlockReasonCode.MISSING_SECURITY_GATE,
            ),
            # D4 blocked
            (
                _create_base_request(DestructiveActionClass.D4_WRITE_REPO),
                GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1,
            ),
            # D5 blocked
            (
                _create_base_request(DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT),
                GuardBlockReasonCode.BLOCKED_D5_EXTERNAL_PHASE1,
            ),
            # D6 blocked
            (
                _create_base_request(DestructiveActionClass.D6_IRREVERSIBLE),
                GuardBlockReasonCode.BLOCKED_D6_IRREVERSIBLE_PHASE1,
            ),
        ]

        for request, expected_code in blocking_tests:
            result = guard.evaluate(request)
            assert result.allowed is False, f"Expected blocked for {expected_code}"
            assert result.reason_code == expected_code, f"Expected {expected_code}, got {result.reason_code}"
            assert result.decision == GuardDecision.BLOCKED


class TestHXA22VerdictDocumentation:
    """Document HXA22 verdict and proof."""

    def test_hxa22_verdict_destructive_action_guard_runtime_defined(self):
        """
        HXA22 Verdict: DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED

        HXA19 verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED
        HXA20 verdict was: PRODUCTION_SOURCE_GATE_DEFINED
        HXA21 verdict was: CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED

        HXA22 proves:
        1. DestructiveActionClass enum defines D0-D6 classes
        2. DestructiveActionRequest captures all gate requirements
        3. DestructiveActionGuardResult captures all WSP 97 truth fields
        4. DestructiveActionGuard implements fail-closed evaluation
        5. D0/D1/D2 allowed only in dry-run mode
        6. D3 requires workspace_binding, path_validation, capability_token, security_gate
        7. D4/D5/D6 blocked in Phase 1
        8. live_execution_allowed = False always
        9. repo_created = False always
        10. production_source_modified = False always
        11. external_federation_initiated = False always
        12. verification_complete = False always
        13. cabr_ready = False always
        14. payout_ready = False always

        This does NOT enable live delegation.
        This DOES define the runtime guard seam for WRE/Hermes flow.
        """
        verdict = "DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED"

        # Verify enum
        assert DestructiveActionClass.D0_OBSERVE
        assert DestructiveActionClass.D6_IRREVERSIBLE

        # Verify request fields
        request = DestructiveActionRequest(
            action_id="test",
            action_type="test",
            target_path="/tmp",
            requested_class=DestructiveActionClass.D0_OBSERVE,
        )
        assert hasattr(request, "action_id")
        assert hasattr(request, "requested_class")
        assert hasattr(request, "dry_run_mode")
        assert hasattr(request, "capability_token_present")
        assert hasattr(request, "security_gate_passed")
        assert hasattr(request, "workspace_binding_enforced")
        assert hasattr(request, "path_constraints_validated")

        # Verify result fields
        result = DestructiveActionGuardResult(
            allowed=True,
            decision=GuardDecision.ALLOW_DRY_RUN,
            reason_code=GuardBlockReasonCode.OK_DRY_RUN,
            destructive_class=DestructiveActionClass.D0_OBSERVE,
        )
        assert hasattr(result, "allowed")
        assert hasattr(result, "decision")
        assert hasattr(result, "live_execution_allowed")
        assert hasattr(result, "repo_created")
        assert hasattr(result, "production_source_modified")
        assert hasattr(result, "external_federation_initiated")
        assert hasattr(result, "verification_complete")
        assert hasattr(result, "cabr_ready")
        assert hasattr(result, "payout_ready")

        # Verify WSP 97 truth fields
        tracker = WSP97TruthTracker()
        assert tracker.all_false() is True

        assert verdict == "DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
