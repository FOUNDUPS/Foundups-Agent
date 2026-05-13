#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA30 Proof Test: Scope-to-Action-Class Hermes Integration (Phase 1)

Tests that HermesJobExecutor integrates scope-to-action-class validation
into the token validation request flow.

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA29 Verdict was: TOKEN_SCOPE_VALIDATION_DEFINED
HXA30 integrates: Scope-to-action-class validation into HermesJobExecutor.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Weaken guard logic
  - Allow D3 scopes to authorize D4/D5/D6 actions

Integration Behaviors Tested:
  1. D3 token + D3 classified action -> token validation passes, guard may allow
  2. D3 token + D4 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
  3. D3 token + D5 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
  4. D3 token + D6 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
  5. repo/source/external scope + D4/D5/D6 action -> token validates but guard blocks
  6. invalid token still blocks before guard
  7. no token follows existing guard behavior
  8. valid token does not enable live delegate call
  9. no repo creation
  10. no production source modification
  11. real_execution_performed=False
  12. verification_complete=False
  13. cabr_ready=False
  14. payout_ready=False

Slice: HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_PHASE1
Worker: W1
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
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.infrastructure.wre_core.src.capability_token_validator import (
    CapabilityToken,
    LocalCapabilityTokenValidator,
    LocalCapabilityTokenIssuer,
    TokenValidationResult,
    TokenValidationReasonCode,
    get_default_validator,
    reset_default_validator,
    ACTION_CLASS_SCOPES,
    SCOPE_TO_ACTION_CLASS,
    validate_scope_for_action_class,
)
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    HermesDelegationResult,
    HermesExecutionStatus,
    HermesJobExecutor,
)
from modules.infrastructure.wre_core.src.destructive_action_guard import (
    DestructiveActionClass,
    DestructiveActionRequest,
    GuardDecision,
    GuardBlockReasonCode,
)


# ===========================================================================
# SECTION 1: Test Fixtures
# ===========================================================================


@dataclass
class MockPolicyFlags:
    """Mock PolicyFlags for testing."""
    security_gate_passed: bool = True
    capability_token_checked: bool = True
    capability_token_present: bool = True
    capability_token_validated: bool = True
    capability_token_scope_authorized: bool = True
    security_gate_checked: bool = True
    dry_run_mode: bool = True

    def to_dict(self):
        return vars(self)


@dataclass
class MockFoundUpJob:
    """Mock FoundUpJob for testing."""
    job_id: str = "job_hxa30_001"
    tenant_id: str = "tenant_hxa30"
    foundup_id: str = "test_foundup"
    requested_action: str = "build_foundup"
    intent_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    policy_flags: Optional[MockPolicyFlags] = None


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def token_issuer() -> LocalCapabilityTokenIssuer:
    """Create a fresh token issuer for testing."""
    return LocalCapabilityTokenIssuer()


@pytest.fixture
def token_validator() -> LocalCapabilityTokenValidator:
    """Create a fresh token validator for testing."""
    return LocalCapabilityTokenValidator()


@pytest.fixture
def executor(temp_workspace, token_validator) -> HermesJobExecutor:
    """Create executor with injected token validator."""
    return HermesJobExecutor(
        dry_run=True,
        workspace_root=temp_workspace,
        token_validator=token_validator,
    )


# ===========================================================================
# SECTION 2: D3 Token + D3 Action Tests (Token Passes, Guard May Allow)
# ===========================================================================


class TestD3TokenD3ActionPasses:
    """Test D3 scoped token with D3 classified action passes token validation."""

    def test_d3_token_d3_action_passes_token_validation(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with D3 action should pass token validation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        # Create D3 scoped token for D3 action (build_foundup)
        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope
            allowed_actions=["build_foundup"],  # D3 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="build_foundup",  # D3 action
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should pass
            assert result.token_validation_performed is True
            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            # Guard should be evaluated
            assert result.guard_evaluated is True
            # D3 with all gates should be allowed
            assert result.guard_result["destructive_class"] == "D3_WRITE_SANDBOX"
            assert result.guard_result["allowed"] is True
            # Final status should be SIMULATED (dry-run)
            assert result.status == HermesExecutionStatus.SIMULATED

    def test_d3_evidence_scope_d3_action_passes(self, temp_workspace, token_issuer):
        """D3 evidence scope with D3 action should pass token validation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:evidence"],  # D3 evidence scope
            allowed_actions=["write_evidence"],  # D3 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="write_evidence",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.guard_evaluated is True


# ===========================================================================
# SECTION 3: D3 Token + D4 Action Tests (Token BLOCKED Before Guard)
# ===========================================================================


class TestD3TokenD4ActionBlocked:
    """Test D3 scoped token with D4 classified action blocked by token validation."""

    def test_d3_token_d4_action_blocked_before_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with D4 action should be blocked by token validation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        # Create D3 scoped token but request D4 action
        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope - does NOT authorize D4
            allowed_actions=["create_repo"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",  # D4 action
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should BLOCK
            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.token_validation_performed is True
            assert result.token_validation_result is not None
            assert (
                result.token_validation_result["reason_code"]
                == "SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS"
            )
            assert result.token_validation_result["scope_action_class_mismatch"] is True
            assert result.token_validation_result["requested_action_class"] == "D4_WRITE_REPO"
            # Guard should NOT be evaluated (blocked before guard)
            assert result.guard_evaluated is False
            assert result.guard_result is None

    def test_d3_token_git_push_blocked_before_guard(self, temp_workspace, token_issuer):
        """D3 scoped token with git_push (D4) blocked before guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox", "d3:evidence"],  # D3 scopes only
            allowed_actions=["git_push"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="git_push",  # D4 action
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.guard_evaluated is False


# ===========================================================================
# SECTION 4: D3 Token + D5 Action Tests (Token BLOCKED Before Guard)
# ===========================================================================


class TestD3TokenD5ActionBlocked:
    """Test D3 scoped token with D5 classified action blocked by token validation."""

    def test_d3_token_d5_action_blocked_before_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with D5 action should be blocked by token validation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope - does NOT authorize D5
            allowed_actions=["send_email"],  # D5 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="send_email",  # D5 action
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should BLOCK
            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.token_validation_result["reason_code"] == "SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS"
            assert result.token_validation_result["requested_action_class"] == "D5_EXTERNAL_SIDE_EFFECT"
            assert result.guard_evaluated is False

    def test_d3_token_deploy_service_blocked_before_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with deploy_service (D5) blocked before guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:dry-run"],  # D3 scope
            allowed_actions=["deploy_service"],  # D5 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="deploy_service",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.guard_evaluated is False


# ===========================================================================
# SECTION 5: D3 Token + D6 Action Tests (Token BLOCKED Before Guard)
# ===========================================================================


class TestD3TokenD6ActionBlocked:
    """Test D3 scoped token with D6 classified action blocked by token validation."""

    def test_d3_token_d6_action_blocked_before_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with D6 action should be blocked by token validation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope - does NOT authorize D6
            allowed_actions=["delete_foundup"],  # D6 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="delete_foundup",  # D6 action
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should BLOCK
            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.token_validation_result["reason_code"] == "SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS"
            assert result.token_validation_result["requested_action_class"] == "D6_IRREVERSIBLE"
            assert result.guard_evaluated is False

    def test_d3_token_payout_trigger_blocked_before_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scoped token with payout_trigger (D6) blocked before guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox", "d3:evidence", "d3:dry-run"],  # All D3 scopes
            allowed_actions=["payout_trigger"],  # D6 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="payout_trigger",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.guard_evaluated is False


# ===========================================================================
# SECTION 6: D4/D5/D6 Scope Token Validates But Guard Blocks
# ===========================================================================


class TestHigherScopeTokenValidatesButGuardBlocks:
    """Test D4/D5/D6 scoped tokens validate but guard still blocks in Phase 1."""

    def test_d4_scope_token_validates_but_guard_blocks(
        self, temp_workspace, token_issuer
    ):
        """D4 scoped token should validate but guard blocks D4 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope - authorizes D4 class
            allowed_actions=["create_repo"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation should PASS (D4 scope authorizes D4 action)
            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            # Guard should be evaluated
            assert result.guard_evaluated is True
            # But guard blocks D4 in Phase 1
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d5_scope_token_validates_but_guard_blocks(
        self, temp_workspace, token_issuer
    ):
        """D5 scoped token should validate but guard blocks D5 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d5:external"],  # D5 scope
            allowed_actions=["send_email"],  # D5 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="send_email",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation passes
            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            # Guard blocks D5
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d6_scope_token_validates_but_guard_blocks(
        self, temp_workspace, token_issuer
    ):
        """D6 scoped token should validate but guard blocks D6 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d6:delete"],  # D6 scope
            allowed_actions=["delete_foundup"],  # D6 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="delete_foundup",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation passes
            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            # Guard blocks D6
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 7: Invalid Token Still Blocks Before Guard
# ===========================================================================


class TestInvalidTokenStillBlocksBeforeGuard:
    """Test that invalid tokens still block before guard evaluation."""

    def test_expired_token_blocks_before_guard(self, temp_workspace, token_issuer):
        """Expired token should block before guard evaluation."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        # Create an expired token
        expired_token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
            validity_duration=timedelta(seconds=-1),  # Expired
        )

        job = MockFoundUpJob(
            requested_action="build_foundup",
            payload={"capability_token": expired_token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.token_validation_result["reason_code"] == "TOKEN_EXPIRED"
            assert result.guard_evaluated is False

    def test_wrong_audience_blocks_before_guard(self, temp_workspace, token_issuer):
        """Token with wrong audience should block before guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        bad_token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wrong-audience",  # Wrong audience
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
        )

        job = MockFoundUpJob(
            requested_action="build_foundup",
            payload={"capability_token": bad_token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.guard_evaluated is False


# ===========================================================================
# SECTION 8: No Token Follows Existing Guard Behavior
# ===========================================================================


class TestNoTokenFollowsExistingGuardBehavior:
    """Test that no token follows existing guard behavior."""

    def test_no_token_d0_action_allowed(self, temp_workspace):
        """No token with D0 action should be allowed by guard."""
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
        )

        job = MockFoundUpJob(
            requested_action="validate_foundup",  # D0 action
            payload={},  # No token
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # No token validation performed
            assert result.token_validation_performed is False
            # Guard evaluated
            assert result.guard_evaluated is True
            # D0 allowed
            assert result.guard_result["allowed"] is True
            assert result.status == HermesExecutionStatus.SIMULATED

    def test_no_token_d4_action_blocked_by_guard(self, temp_workspace):
        """No token with D4 action should be blocked by guard (not token)."""
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
        )

        job = MockFoundUpJob(
            requested_action="create_repo",  # D4 action
            payload={},  # No token
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # No token validation performed
            assert result.token_validation_performed is False
            # Guard evaluated
            assert result.guard_evaluated is True
            # D4 blocked by guard
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD


# ===========================================================================
# SECTION 9: WSP 97 Truth Fields Tests
# ===========================================================================


class TestWSP97TruthFieldsAlwaysFalse:
    """Test all WSP 97 truth fields remain False."""

    def test_token_blocked_truth_fields_false(self, temp_workspace, token_issuer):
        """Token blocked result should have all truth fields False."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope
            allowed_actions=["create_repo"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",  # D4 - will fail scope validation
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False
            assert result.repo_created is False
            assert result.production_source_modified is False
            assert result.live_external_delegate_called is False

    def test_guard_blocked_truth_fields_false(self, temp_workspace, token_issuer):
        """Guard blocked result should have all truth fields False."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        # D4 scope token for D4 action (token passes, guard blocks)
        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False

    def test_simulated_truth_fields_false(self, temp_workspace, token_issuer):
        """Simulated result should have all truth fields False."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="build_foundup",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.status == HermesExecutionStatus.SIMULATED
            assert result.real_execution_performed is False
            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False


# ===========================================================================
# SECTION 10: No Live Delegate / Repo / Source Modification
# ===========================================================================


class TestNoLiveDelegateOrRepoOrSourceModification:
    """Test no live delegate, repo creation, or source modification."""

    def test_valid_token_no_live_delegate(self, temp_workspace, token_issuer):
        """Valid token should NOT enable live delegate call."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="build_foundup",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.live_external_delegate_called is False
            assert result.controlled_delegate_invoked is False

    def test_no_repo_created(self, temp_workspace, token_issuer):
        """No repo should be created even with D4 scope token."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.repo_created is False

    def test_no_production_source_modified(self, temp_workspace, token_issuer):
        """No production source should be modified."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d4:source"],  # D4 source scope
            allowed_actions=["modify_source"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="modify_source",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.production_source_modified is False


# ===========================================================================
# SECTION 11: Token-vs-Guard Decision Ordering
# ===========================================================================


class TestTokenVsGuardDecisionOrdering:
    """Test token validation happens before guard evaluation."""

    def test_d3_scope_d4_action_blocked_by_token_not_guard(
        self, temp_workspace, token_issuer
    ):
        """D3 scope with D4 action should be blocked by TOKEN, not guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope
            allowed_actions=["create_repo"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Key assertion: Blocked by TOKEN, not by GUARD
            assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert result.status != HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            # Guard was NOT evaluated
            assert result.guard_evaluated is False

    def test_d4_scope_d4_action_blocked_by_guard_not_token(
        self, temp_workspace, token_issuer
    ):
        """D4 scope with D4 action should be blocked by GUARD, not token."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope - matches D4 action
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )

        job = MockFoundUpJob(
            requested_action="create_repo",
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Key assertion: Blocked by GUARD, not by TOKEN
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.status != HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            # Guard WAS evaluated
            assert result.guard_evaluated is True


# ===========================================================================
# SECTION 12: HXA30 Verdict Documentation Test
# ===========================================================================


class TestHXA30VerdictDocumentation:
    """Document HXA30 verdict and proof."""

    def test_hxa30_verdict_scope_to_action_class_integration_defined(
        self, temp_workspace, token_issuer
    ):
        """
        HXA30 Verdict: SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED

        HXA29 verdict was: TOKEN_SCOPE_VALIDATION_DEFINED

        HXA30 proves:
        1. D3 token + D3 classified action -> token validation passes
        2. D3 token + D4 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
        3. D3 token + D5 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
        4. D3 token + D6 classified action -> BLOCKED_BY_TOKEN_VALIDATION before guard
        5. repo/source/external scope + D4/D5/D6 action -> token validates but guard blocks
        6. invalid token still blocks before guard
        7. no token follows existing guard behavior
        8. valid token does not enable live delegate call
        9. no repo creation
        10. no production source modification
        11. real_execution_performed=False
        12. verification_complete=False
        13. cabr_ready=False
        14. payout_ready=False

        This does NOT enable live delegation.
        This does NOT create repos.
        This does NOT modify production source.
        This does NOT weaken guard logic.
        This DOES add scope-to-action-class validation before guard evaluation.
        """
        verdict = "SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED"

        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        # Test 1: D3 token + D3 action -> passes
        d3_token = token_issuer.issue_token(
            subject="agent_hxa30",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        d3_job = MockFoundUpJob(
            requested_action="build_foundup",
            payload={"capability_token": d3_token},
            policy_flags=MockPolicyFlags(),
        )
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d3_result = executor.execute(d3_job)
            assert d3_result.status == HermesExecutionStatus.SIMULATED

        # Test 2: D3 token + D4 action -> blocked by token
        d4_token = token_issuer.issue_token(
            subject="agent_hxa30_2",
            audience="wre-local",
            scopes=["d3:sandbox"],  # D3 scope, D4 action
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )
        d4_job = MockFoundUpJob(
            job_id="job_hxa30_002",
            requested_action="create_repo",
            payload={"capability_token": d4_token},
            policy_flags=MockPolicyFlags(),
        )
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d4_result = executor.execute(d4_job)
            assert d4_result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
            assert d4_result.guard_evaluated is False

        # Test 3: D4 scope + D4 action -> guard blocks (not token)
        d4_scope_token = token_issuer.issue_token(
            subject="agent_hxa30_3",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )
        d4_scope_job = MockFoundUpJob(
            job_id="job_hxa30_003",
            requested_action="create_repo",
            payload={"capability_token": d4_scope_token},
            policy_flags=MockPolicyFlags(),
        )
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            d4_scope_result = executor.execute(d4_scope_job)
            assert d4_scope_result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert d4_scope_result.guard_evaluated is True

        assert verdict == "SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
