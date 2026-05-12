#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA29 Proof Test: Token Scope Validation (Phase 1)

Tests capability token scope validation against Hermes destructive-action classes.

WSP 97 Truth Boundaries:
  - live_external_delegate_called: False (ALWAYS)
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - real_execution_performed: False (ALWAYS in Phase 1)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA28 Verdict was: D3_NATIVE_CLASSIFICATION_DEFINED
HXA29 defines: Token scope validation against action classes.

This slice MUST NOT:
  - Enable live delegation
  - Create repos
  - Modify production source
  - Weaken guard logic
  - Allow D3 scopes to authorize D4/D5/D6

Scope Validation Rules Tested:
  1. D3 sandbox scopes authorize only D3 dry-run/sandbox evidence actions
  2. D3 scopes must NEVER authorize D4 repo creation
  3. D3 scopes must NEVER authorize D5 external side effects
  4. D3 scopes must NEVER authorize D6 irreversible actions
  5. Separate scopes for repo/source/external defined but blocked
  6. Missing scope fails closed
  7. Unknown scope fails closed
  8. Mixed scopes still obey action class
  9. Blocked path overrides allowed scope
  10. Path traversal blocks
  11. dry_run_only token blocks live execution
  12. Valid token cannot set live_external_delegate_called=True
  13. verification_complete=False (always)
  14. cabr_ready=False (always)
  15. payout_ready=False (always)

Slice: HXA29_TOKEN_SCOPE_VALIDATION_PHASE1
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
# SECTION 2: Scope Constants Validation Tests
# ===========================================================================


class TestScopeConstantsExist:
    """Test that scope constants are properly defined."""

    def test_action_class_scopes_defined(self):
        """ACTION_CLASS_SCOPES should define scopes for each action class."""
        assert ACTION_CLASS_SCOPES is not None
        assert isinstance(ACTION_CLASS_SCOPES, dict)
        # D0 through D6 should have entries
        assert "D0_OBSERVE" in ACTION_CLASS_SCOPES
        assert "D1_READ" in ACTION_CLASS_SCOPES
        assert "D2_SIMULATE" in ACTION_CLASS_SCOPES
        assert "D3_WRITE_SANDBOX" in ACTION_CLASS_SCOPES
        assert "D4_WRITE_REPO" in ACTION_CLASS_SCOPES
        assert "D5_EXTERNAL_SIDE_EFFECT" in ACTION_CLASS_SCOPES
        assert "D6_IRREVERSIBLE" in ACTION_CLASS_SCOPES

    def test_scope_to_action_class_defined(self):
        """SCOPE_TO_ACTION_CLASS should map scopes to action classes."""
        assert SCOPE_TO_ACTION_CLASS is not None
        assert isinstance(SCOPE_TO_ACTION_CLASS, dict)
        # Core scopes should be mapped
        assert "d3:sandbox" in SCOPE_TO_ACTION_CLASS
        assert "d3:evidence" in SCOPE_TO_ACTION_CLASS
        assert "d3:dry-run" in SCOPE_TO_ACTION_CLASS

    def test_d3_scopes_map_to_d3_class(self):
        """D3 scopes should map to D3_WRITE_SANDBOX class."""
        d3_scopes = ["d3:sandbox", "d3:evidence", "d3:dry-run"]
        for scope in d3_scopes:
            assert SCOPE_TO_ACTION_CLASS.get(scope) == "D3_WRITE_SANDBOX"

    def test_d4_scopes_map_to_d4_class(self):
        """D4 scopes should map to D4_WRITE_REPO class."""
        d4_scopes = ["d4:repo", "d4:source", "d4:git"]
        for scope in d4_scopes:
            assert SCOPE_TO_ACTION_CLASS.get(scope) == "D4_WRITE_REPO"

    def test_d5_scopes_map_to_d5_class(self):
        """D5 scopes should map to D5_EXTERNAL_SIDE_EFFECT class."""
        d5_scopes = ["d5:external", "d5:api", "d5:webhook"]
        for scope in d5_scopes:
            assert SCOPE_TO_ACTION_CLASS.get(scope) == "D5_EXTERNAL_SIDE_EFFECT"

    def test_d6_scopes_map_to_d6_class(self):
        """D6 scopes should map to D6_IRREVERSIBLE class."""
        d6_scopes = ["d6:delete", "d6:irreversible", "d6:payout"]
        for scope in d6_scopes:
            assert SCOPE_TO_ACTION_CLASS.get(scope) == "D6_IRREVERSIBLE"


# ===========================================================================
# SECTION 3: D3 Sandbox Scope Tests
# ===========================================================================


class TestD3SandboxScopeAuthorizesD3Only:
    """Test D3 sandbox scopes authorize only D3 dry-run/sandbox actions."""

    def test_d3_sandbox_scope_authorizes_d3_action(self, token_validator, token_issuer):
        """D3 sandbox scope should authorize D3 action class."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        # D3 scope for D3 action = allowed
        result = validate_scope_for_action_class(
            scope="d3:sandbox",
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        )
        assert result is True

    def test_d3_evidence_scope_authorizes_d3_action(self, token_validator, token_issuer):
        """D3 evidence scope should authorize D3 action class."""
        result = validate_scope_for_action_class(
            scope="d3:evidence",
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        )
        assert result is True

    def test_d3_dryrun_scope_authorizes_d3_action(self, token_validator, token_issuer):
        """D3 dry-run scope should authorize D3 action class."""
        result = validate_scope_for_action_class(
            scope="d3:dry-run",
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        )
        assert result is True


class TestD3ScopeDoesNotAuthorizeD4:
    """Test D3 scopes do NOT authorize D4 repo creation."""

    @pytest.mark.parametrize("scope", ["d3:sandbox", "d3:evidence", "d3:dry-run"])
    def test_d3_scope_does_not_authorize_d4(self, scope):
        """D3 scope should NOT authorize D4 action class."""
        result = validate_scope_for_action_class(
            scope=scope,
            action_class=DestructiveActionClass.D4_WRITE_REPO,
        )
        assert result is False

    def test_d3_token_blocked_for_d4_create_repo(self, temp_workspace, token_issuer):
        """Token with D3 scope blocked for D4 create_repo action."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["create_repo"],  # D4 action
            allowed_paths=["modules/foundups"],
        )

        # Create mock job with token
        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d4_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "create_repo"  # D4 action
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # D4 should be blocked by guard regardless of token
            assert result.guard_evaluated is True
            assert result.guard_result["destructive_class"] == "D4_WRITE_REPO"
            assert result.guard_result["allowed"] is False


class TestD3ScopeDoesNotAuthorizeD5:
    """Test D3 scopes do NOT authorize D5 external side effects."""

    @pytest.mark.parametrize("scope", ["d3:sandbox", "d3:evidence", "d3:dry-run"])
    def test_d3_scope_does_not_authorize_d5(self, scope):
        """D3 scope should NOT authorize D5 action class."""
        result = validate_scope_for_action_class(
            scope=scope,
            action_class=DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
        )
        assert result is False

    def test_d3_token_blocked_for_d5_send_email(self, temp_workspace, token_issuer):
        """Token with D3 scope blocked for D5 send_email action."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["send_email"],  # D5 action
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d5_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "send_email"  # D5 action
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # D5 should be blocked by guard regardless of token
            assert result.guard_evaluated is True
            assert result.guard_result["destructive_class"] == "D5_EXTERNAL_SIDE_EFFECT"
            assert result.guard_result["allowed"] is False


class TestD3ScopeDoesNotAuthorizeD6:
    """Test D3 scopes do NOT authorize D6 irreversible actions."""

    @pytest.mark.parametrize("scope", ["d3:sandbox", "d3:evidence", "d3:dry-run"])
    def test_d3_scope_does_not_authorize_d6(self, scope):
        """D3 scope should NOT authorize D6 action class."""
        result = validate_scope_for_action_class(
            scope=scope,
            action_class=DestructiveActionClass.D6_IRREVERSIBLE,
        )
        assert result is False

    def test_d3_token_blocked_for_d6_delete_foundup(self, temp_workspace, token_issuer):
        """Token with D3 scope blocked for D6 delete_foundup action."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["delete_foundup"],  # D6 action
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d6_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "delete_foundup"  # D6 action
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # D6 should be blocked by guard regardless of token
            assert result.guard_evaluated is True
            assert result.guard_result["destructive_class"] == "D6_IRREVERSIBLE"
            assert result.guard_result["allowed"] is False


# ===========================================================================
# SECTION 4: D4/D5/D6 Scopes Defined But Blocked Tests
# ===========================================================================


class TestD4D5D6ScopesDefinedButBlocked:
    """Test D4/D5/D6 scopes are defined but blocked by guard policy."""

    def test_d4_scope_validates_but_guard_blocks(self, temp_workspace, token_issuer):
        """D4 scope token validates but guard still blocks D4 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d4:repo"],  # D4 scope
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d4_scope_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "create_repo"
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # Token validation passes but guard blocks D4
            assert result.guard_evaluated is True
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D4_REPO_WRITE_PHASE1"

    def test_d5_scope_validates_but_guard_blocks(self, temp_workspace, token_issuer):
        """D5 scope token validates but guard still blocks D5 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d5:external"],  # D5 scope
            allowed_actions=["send_email"],
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d5_scope_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "send_email"
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D5_EXTERNAL_PHASE1"

    def test_d6_scope_validates_but_guard_blocks(self, temp_workspace, token_issuer):
        """D6 scope token validates but guard still blocks D6 in Phase 1."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d6:delete"],  # D6 scope
            allowed_actions=["delete_foundup"],
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_d6_scope_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "delete_foundup"
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.guard_evaluated is True
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
            assert result.guard_result["reason_code"] == "BLOCKED_D6_IRREVERSIBLE_PHASE1"


# ===========================================================================
# SECTION 5: Missing/Unknown Scope Tests
# ===========================================================================


class TestMissingScopeFailsClosed:
    """Test missing scope fails closed."""

    def test_missing_scope_fails_validation(self, token_validator, token_issuer):
        """Token with no scopes should fail scope validation."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=[],  # No scopes
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        result = token_validator.validate_token(
            token,
            requested_action="build_foundup",
            requested_scope="d3:sandbox",  # Require scope
        )
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.SCOPE_NOT_ALLOWED

    def test_empty_scopes_list_fails_scope_check(self, token_issuer):
        """Empty scopes list should fail scope_allowed check."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=[],
        )
        assert token.scope_allowed("d3:sandbox") is False
        assert token.scope_allowed("d3:evidence") is False
        assert token.scope_allowed("d4:repo") is False


class TestUnknownScopeFailsClosed:
    """Test unknown scope fails closed."""

    def test_unknown_scope_fails_validation(self, token_validator, token_issuer):
        """Token with unknown scope should fail scope validation."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["unknown:scope"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        # Unknown scope can't authorize any action class
        result = validate_scope_for_action_class(
            scope="unknown:scope",
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        )
        assert result is False

    def test_unknown_scope_not_mapped(self):
        """Unknown scope should not be in SCOPE_TO_ACTION_CLASS."""
        assert "unknown:scope" not in SCOPE_TO_ACTION_CLASS
        assert "admin:all" not in SCOPE_TO_ACTION_CLASS
        assert "superuser" not in SCOPE_TO_ACTION_CLASS


# ===========================================================================
# SECTION 6: Mixed Scopes Tests
# ===========================================================================


class TestMixedScopesObeyActionClass:
    """Test mixed scopes still obey action class restrictions."""

    def test_mixed_d3_d4_scopes_d3_action_allowed(self, token_issuer):
        """Token with D3+D4 scopes should allow D3 action."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox", "d4:repo"],  # Mixed scopes
        )
        # D3 scope for D3 action = allowed
        assert token.scope_allowed("d3:sandbox") is True
        result = validate_scope_for_action_class(
            scope="d3:sandbox",
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
        )
        assert result is True

    def test_mixed_d3_d4_scopes_d4_action_blocked_by_guard(self, temp_workspace, token_issuer):
        """Token with D3+D4 scopes still blocked for D4 by guard."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox", "d4:repo"],
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_mixed_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "create_repo"
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            # D4 blocked by guard, regardless of token scopes
            assert result.guard_evaluated is True
            assert result.status == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD


# ===========================================================================
# SECTION 7: Path Validation Tests
# ===========================================================================


class TestBlockedPathOverridesAllowedScope:
    """Test blocked path overrides allowed scope."""

    def test_blocked_path_overrides_valid_token(self, token_issuer, token_validator):
        """Blocked path should override valid scope and action."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
            blocked_paths=[".env", "secrets"],
        )
        # Path validation fails for blocked path
        result = token_validator.validate_token(
            token,
            requested_action="build_foundup",
            target_path="modules/foundups/.env",
        )
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.PATH_IN_BLOCKED_LIST


class TestPathTraversalBlocked:
    """Test path traversal is blocked."""

    def test_path_traversal_blocked(self, token_issuer):
        """Path traversal attempts should be blocked."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_paths=["modules/foundups"],
        )
        # Traversal attempts
        assert token.path_allowed("modules/foundups/../secrets/key.pem") is False
        assert token.path_allowed("modules/foundups/../../.env") is False

    def test_normalized_path_outside_allowed(self, token_issuer):
        """Normalized path outside allowed roots should be blocked."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_paths=["modules/foundups/kosei"],
        )
        # Even with traversal that normalizes to allowed, should check normalized path
        assert token.path_allowed("/etc/passwd") is False
        assert token.path_allowed("C:\\Windows\\System32\\config") is False


# ===========================================================================
# SECTION 8: Dry Run Only Tests
# ===========================================================================


class TestDryRunOnlyBlocksLiveExecution:
    """Test dry_run_only token blocks live execution."""

    def test_dry_run_only_blocks_live_operation(self, token_validator, token_issuer):
        """dry_run_only=True token should block live operation."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
            dry_run_only=True,
        )
        result = token_validator.validate_token(
            token,
            requested_action="build_foundup",
            target_path="modules/foundups/test.py",
            is_live_operation=True,  # Attempt live operation
        )
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.DRY_RUN_ONLY_BLOCKS_LIVE
        assert result.dry_run_only_blocked_live is True

    def test_dry_run_only_allows_dry_run_operation(self, token_validator, token_issuer):
        """dry_run_only=True token should allow dry-run operation."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
            dry_run_only=True,
        )
        result = token_validator.validate_token(
            token,
            requested_action="build_foundup",
            target_path="modules/foundups/test.py",
            is_live_operation=False,  # Dry-run operation
        )
        assert result.token_valid is True
        assert result.reason_code == TokenValidationReasonCode.VALID_DRY_RUN_ONLY


# ===========================================================================
# SECTION 9: WSP 97 Truth Fields Tests
# ===========================================================================


class TestWSP97TruthFieldsAlwaysFalse:
    """Test WSP 97 truth fields remain False."""

    def test_valid_token_cannot_set_live_external_delegate_called(
        self, temp_workspace, token_issuer
    ):
        """Valid token cannot set live_external_delegate_called=True."""
        validator = LocalCapabilityTokenValidator()
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=temp_workspace,
            token_validator=validator,
        )

        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )

        @dataclass
        class MockPolicyFlags:
            security_gate_passed: bool = True
            capability_token_checked: bool = True
            capability_token_present: bool = True
            capability_token_validated: bool = True
            capability_token_scope_authorized: bool = True

            def to_dict(self):
                return vars(self)

        @dataclass
        class MockFoundUpJob:
            job_id: str = "job_hxa29_wsp97_001"
            tenant_id: str = "tenant_hxa29"
            foundup_id: str = "test_foundup"
            requested_action: str = "build_foundup"
            intent_id: Optional[str] = None
            payload: Optional[Dict[str, Any]] = None
            policy_flags: Optional[MockPolicyFlags] = None

        job = MockFoundUpJob(
            payload={"capability_token": token},
            policy_flags=MockPolicyFlags(),
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            result = executor.execute(job)

            assert result.live_external_delegate_called is False

    def test_verification_complete_always_false(self, token_validator, token_issuer):
        """verification_complete should always be False."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        result = token_validator.validate_token(
            token,
            requested_action="build_foundup",
            target_path="modules/foundups/test.py",
        )
        assert result.verification_complete is False

    def test_cabr_ready_always_false(self, token_validator, token_issuer):
        """cabr_ready should always be False."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
        )
        result = token_validator.validate_token(token)
        assert result.cabr_ready is False

    def test_payout_ready_always_false(self, token_validator, token_issuer):
        """payout_ready should always be False."""
        token = token_issuer.issue_token(
            subject="agent_hxa29",
            audience="wre-local",
            scopes=["d3:sandbox"],
        )
        result = token_validator.validate_token(token)
        assert result.payout_ready is False


# ===========================================================================
# SECTION 10: Scope Validation Function Tests
# ===========================================================================


class TestValidateScopeForActionClass:
    """Test validate_scope_for_action_class function."""

    @pytest.mark.parametrize("scope,action_class,expected", [
        # D3 scopes authorize D3 only
        ("d3:sandbox", DestructiveActionClass.D3_WRITE_SANDBOX, True),
        ("d3:evidence", DestructiveActionClass.D3_WRITE_SANDBOX, True),
        ("d3:dry-run", DestructiveActionClass.D3_WRITE_SANDBOX, True),
        # D3 scopes do NOT authorize D4/D5/D6
        ("d3:sandbox", DestructiveActionClass.D4_WRITE_REPO, False),
        ("d3:sandbox", DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT, False),
        ("d3:sandbox", DestructiveActionClass.D6_IRREVERSIBLE, False),
        # D4 scopes authorize D4
        ("d4:repo", DestructiveActionClass.D4_WRITE_REPO, True),
        ("d4:source", DestructiveActionClass.D4_WRITE_REPO, True),
        # D4 scopes do NOT authorize D5/D6
        ("d4:repo", DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT, False),
        ("d4:repo", DestructiveActionClass.D6_IRREVERSIBLE, False),
        # D5 scopes authorize D5
        ("d5:external", DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT, True),
        # D6 scopes authorize D6
        ("d6:delete", DestructiveActionClass.D6_IRREVERSIBLE, True),
        # Unknown scope fails closed
        ("unknown:scope", DestructiveActionClass.D3_WRITE_SANDBOX, False),
        ("unknown:scope", DestructiveActionClass.D6_IRREVERSIBLE, False),
    ])
    def test_scope_action_class_validation(self, scope, action_class, expected):
        """Test scope validation for various action classes."""
        result = validate_scope_for_action_class(scope, action_class)
        assert result is expected


# ===========================================================================
# SECTION 11: HXA29 Verdict Documentation Test
# ===========================================================================


class TestHXA29VerdictDocumentation:
    """Document HXA29 verdict and proof."""

    def test_hxa29_verdict_token_scope_validation_defined(self):
        """
        HXA29 Verdict: TOKEN_SCOPE_VALIDATION_DEFINED

        HXA28 verdict was: D3_NATIVE_CLASSIFICATION_DEFINED

        HXA29 proves:
        1. D3 sandbox scopes authorize only D3 dry-run/sandbox evidence actions
        2. D3 sandbox scopes do NOT authorize D4 repo creation
        3. D3 sandbox scopes do NOT authorize D5 external side effects
        4. D3 sandbox scopes do NOT authorize D6 irreversible actions
        5. D4/D5/D6 scopes defined but still blocked by guard policy
        6. Missing scope fails closed
        7. Unknown scope fails closed
        8. Mixed scopes still obey action class restrictions
        9. Blocked path overrides allowed scope
        10. Path traversal is blocked
        11. dry_run_only token blocks live execution
        12. Valid token cannot set live_external_delegate_called=True
        13. verification_complete=False (always)
        14. cabr_ready=False (always)
        15. payout_ready=False (always)

        This does NOT enable live delegation.
        This does NOT create repos.
        This does NOT modify production source.
        This does NOT weaken guard logic.
        This DOES harden scope validation to be explicit and deterministic.
        """
        verdict = "TOKEN_SCOPE_VALIDATION_DEFINED"

        # Verify constants exist
        assert ACTION_CLASS_SCOPES is not None
        assert SCOPE_TO_ACTION_CLASS is not None

        # Verify D3 scope authorization
        assert validate_scope_for_action_class(
            "d3:sandbox", DestructiveActionClass.D3_WRITE_SANDBOX
        ) is True
        assert validate_scope_for_action_class(
            "d3:sandbox", DestructiveActionClass.D4_WRITE_REPO
        ) is False
        assert validate_scope_for_action_class(
            "d3:sandbox", DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT
        ) is False
        assert validate_scope_for_action_class(
            "d3:sandbox", DestructiveActionClass.D6_IRREVERSIBLE
        ) is False

        # Verify unknown scope fails closed
        assert validate_scope_for_action_class(
            "unknown:scope", DestructiveActionClass.D3_WRITE_SANDBOX
        ) is False

        assert verdict == "TOKEN_SCOPE_VALIDATION_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
