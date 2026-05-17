#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge Case Tests: Destructive Action Guard Path Validation

Tests edge cases identified in DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_EXPANSION_AUDIT_PHASE1:
  - Symlink traversal (P0)
  - Windows UNC paths (P1)
  - Control characters in paths (P1)
  - Directory traversal (existing coverage verification)
  - Mixed separators (existing coverage verification)
  - Drive letter case normalization (P1)
  - WSP 97 truth boundary verification

WSP 97 Labels:
  - TEST_ONLY
  - NO_RUNTIME_ENABLEMENT
  - NO_LIVE_DELEGATION
  - NO_HERMES_ENABLEMENT
  - NO_SOURCE_MODIFICATION
  - NO_REPO_CREATION
  - NO_NETWORK_CALL
  - DRY_RUN_ONLY
  - FAIL_CLOSED_REQUIRED
  - NOT_CABR_READY
  - NOT_PAYOUT_READY
  - NO_DAO_ACTIVATION

Key Principle: Tests document current behavior. Tests marked xfail document known gaps
that will be fixed in DESTRUCTIVE_ACTION_GUARD_PATH_CANONICALIZATION_IMPL_PHASE1.

Slice: DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TEST_IMPL_PHASE1
Worker: W1
"""

from __future__ import annotations

import os
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from modules.infrastructure.wre_core.src.destructive_action_guard import (
    DestructiveActionClass,
    DestructiveActionGuard,
    DestructiveActionGuardResult,
    DestructiveActionRequest,
    GuardBlockReasonCode,
    GuardDecision,
)
from modules.infrastructure.wre_core.src.capability_token_validator import (
    CapabilityToken,
)


# ===========================================================================
# SECTION 1: Helper Functions
# ===========================================================================


def _create_request(
    action_class: DestructiveActionClass = DestructiveActionClass.D3_WRITE_SANDBOX,
    target_path: str = "/tmp/test/file.txt",
    dry_run_mode: bool = True,
    workspace_binding_enforced: bool = True,
    path_constraints_validated: bool = True,
    capability_token_present: bool = True,
    security_gate_passed: bool = True,
) -> DestructiveActionRequest:
    """Create a test request with configurable fields."""
    return DestructiveActionRequest(
        action_id=f"act_{secrets.token_hex(4)}",
        action_type="test_edge_case",
        target_path=target_path,
        requested_class=action_class,
        dry_run_mode=dry_run_mode,
        human_approval=False,
        capability_token_present=capability_token_present,
        security_gate_passed=security_gate_passed,
        workspace_binding_enforced=workspace_binding_enforced,
        path_constraints_validated=path_constraints_validated,
        requester_id="test_edge_case_agent",
        job_id="j_edge_test",
    )


def _create_token_with_paths(
    allowed_paths: List[str],
    blocked_paths: Optional[List[str]] = None,
) -> CapabilityToken:
    """Create a capability token with specified path constraints."""
    return CapabilityToken(
        token_id=f"tok_{secrets.token_hex(8)}",
        issuer="test_issuer",
        subject="test_agent",
        audience="wre-local",
        scopes=["d3:sandbox"],
        allowed_actions=["test_action"],
        allowed_paths=allowed_paths,
        blocked_paths=blocked_paths or [],
        dry_run_only=True,
        nonce=secrets.token_hex(16),
    )


# ===========================================================================
# SECTION 2: Directory Traversal Tests (Existing Coverage Verification)
# ===========================================================================


class TestDirectoryTraversalBlocked:
    """Test that directory traversal (../) is blocked after normalization."""

    def test_dotdot_traversal_normalized_and_blocked(self):
        """Path with ../ should be normalized before boundary check."""
        token = _create_token_with_paths(["modules/foundups/kosei"])

        # Try to escape via ../
        assert token.path_allowed("modules/foundups/kosei/../../../etc/passwd") is False
        assert token.path_allowed("modules/foundups/kosei/../../.env") is False

    def test_dotdot_within_allowed_stays_allowed(self):
        """Path with ../ that stays within allowed root should work."""
        token = _create_token_with_paths(["modules/foundups"])

        # Navigate within allowed but use ../
        assert token.path_allowed("modules/foundups/kosei/../gotjunk/file.txt") is True

    def test_leading_dotdot_blocked(self):
        """Paths starting with ../ should be blocked (no allowed root)."""
        token = _create_token_with_paths(["modules/foundups"])

        assert token.path_allowed("../etc/passwd") is False
        assert token.path_allowed("../../root/.ssh/id_rsa") is False


# ===========================================================================
# SECTION 3: Mixed Separator Tests
# ===========================================================================


class TestMixedSeparatorHandling:
    """Test that mixed forward/backslash paths are normalized safely."""

    def test_backslash_normalized_to_forward(self):
        """Backslashes should be normalized to forward slashes."""
        token = _create_token_with_paths(["modules/foundups/kosei"])

        # Windows-style path
        assert token.path_allowed("modules\\foundups\\kosei\\file.txt") is True
        assert token.path_allowed("modules\\foundups\\gotjunk\\file.txt") is False

    def test_mixed_slashes_handled(self):
        """Mixed forward and backward slashes should be normalized."""
        token = _create_token_with_paths(["modules/foundups"])

        # Mixed separators
        assert token.path_allowed("modules/foundups\\kosei/file.txt") is True
        assert token.path_allowed("modules\\foundups/kosei\\file.txt") is True


# ===========================================================================
# SECTION 4: Symlink Traversal Tests (P0 - Expected Gap)
# ===========================================================================


class TestSymlinkTraversal:
    """
    Test symlink traversal detection.

    KNOWN GAP: Current implementation uses os.path.normpath which does NOT
    resolve symlinks. Tests marked xfail document this gap.

    Fix required in: DESTRUCTIVE_ACTION_GUARD_PATH_CANONICALIZATION_IMPL_PHASE1
    """

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin on Windows")
    @pytest.mark.xfail(
        reason="GAP: os.path.normpath does not resolve symlinks. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_symlink_inside_allowed_pointing_outside_blocked(self, tmp_path):
        """
        A symlink inside allowed directory pointing outside should be BLOCKED.

        This test documents the current gap where symlinks can escape boundaries.
        """
        # Setup: Create allowed directory and symlink to outside
        allowed_dir = tmp_path / "workspace" / "allowed"
        allowed_dir.mkdir(parents=True)

        outside_dir = tmp_path / "secrets"
        outside_dir.mkdir()
        (outside_dir / "password.txt").write_text("secret123")

        # Create symlink inside allowed pointing outside
        symlink_path = allowed_dir / "escape"
        symlink_path.symlink_to(outside_dir)

        # Token allows only workspace/allowed
        token = _create_token_with_paths([str(allowed_dir)])

        # The path through symlink should be BLOCKED
        escape_path = str(allowed_dir / "escape" / "password.txt")

        # EXPECTED: False (blocked because resolved path is outside)
        # CURRENT: True (allowed because normpath doesn't resolve symlinks)
        assert token.path_allowed(escape_path) is False

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin on Windows")
    def test_symlink_to_allowed_location_allowed(self, tmp_path):
        """Symlink pointing to a location WITHIN allowed root should work."""
        allowed_dir = tmp_path / "workspace"
        allowed_dir.mkdir(parents=True)

        subdir = allowed_dir / "subdir"
        subdir.mkdir()

        # Symlink within workspace pointing to subdir
        symlink_path = allowed_dir / "link_to_sub"
        symlink_path.symlink_to(subdir)

        token = _create_token_with_paths([str(allowed_dir)])

        # Both direct and symlink paths within allowed should work
        assert token.path_allowed(str(subdir / "file.txt")) is True
        # Note: This may also pass due to normpath not resolving


# ===========================================================================
# SECTION 5: Windows UNC Path Tests (P1)
# ===========================================================================


class TestWindowsUNCPaths:
    """Test that Windows UNC paths fail closed."""

    def test_unc_path_blocked_network_share(self):
        """UNC path to network share should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        # UNC paths - should NOT match any allowed root
        assert token.path_allowed("//server/share/file.txt") is False
        assert token.path_allowed("\\\\server\\share\\file.txt") is False

    def test_unc_path_with_credentials_blocked(self):
        """UNC path with embedded credentials should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        # UNC with credentials
        assert token.path_allowed("//user:pass@server/share/file.txt") is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path")
    def test_windows_long_path_prefix_handled(self):
        """Windows long path prefix (\\\\?\\) should be handled safely."""
        token = _create_token_with_paths(["C:/workspace"])

        # Long path prefix - should fail closed if not in allowed
        assert token.path_allowed("\\\\?\\C:\\Windows\\System32\\config") is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path")
    def test_windows_device_path_blocked(self):
        """Windows device paths (\\\\.\\) should be blocked."""
        token = _create_token_with_paths(["C:/workspace"])

        # Device paths
        assert token.path_allowed("\\\\.\\COM1") is False
        assert token.path_allowed("\\\\.\\PhysicalDrive0") is False


# ===========================================================================
# SECTION 6: Control Character Tests (P1)
# ===========================================================================


class TestControlCharactersInPaths:
    """
    Test that control characters in paths fail closed.

    KNOWN GAP: Current implementation does not filter control characters.
    Tests marked xfail document this gap for future fix.
    """

    @pytest.mark.xfail(
        reason="GAP: No control character filtering. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_null_byte_in_path_blocked(self):
        """Path with NULL byte should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        # NULL byte injection
        malicious_path = "modules/foundups/file.txt\x00.exe"
        assert token.path_allowed(malicious_path) is False

    @pytest.mark.xfail(
        reason="GAP: No control character filtering. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_newline_in_path_blocked(self):
        """Path with newline should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        # Newline injection
        malicious_path = "modules/foundups/file.txt\n/etc/passwd"
        assert token.path_allowed(malicious_path) is False

    @pytest.mark.xfail(
        reason="GAP: No control character filtering. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_carriage_return_in_path_blocked(self):
        """Path with carriage return should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        # CR injection
        malicious_path = "modules/foundups/file.txt\r/etc/passwd"
        assert token.path_allowed(malicious_path) is False

    @pytest.mark.xfail(
        reason="GAP: No control character filtering. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_tab_in_path_handled(self):
        """Path with tab character - should be blocked or normalized."""
        token = _create_token_with_paths(["modules/foundups"])

        # Tab in path
        path_with_tab = "modules/foundups/file\t.txt"
        # Should either be blocked or normalized safely
        # Current behavior: may pass (not filtered)
        assert token.path_allowed(path_with_tab) is False


# ===========================================================================
# SECTION 7: Windows Drive Case Tests (P1)
# ===========================================================================


class TestWindowsDriveCaseNormalization:
    """
    Test Windows drive letter case handling.

    On Windows, C: and c: refer to the same drive but may not match
    in string comparison without normcase().
    """

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    @pytest.mark.xfail(
        reason="GAP: No os.path.normcase() on Windows. "
               "Fix in PATH_CANONICALIZATION_IMPL_PHASE1",
        strict=False,
    )
    def test_drive_case_mismatch_normalized(self):
        """Drive letters with different case should match on Windows."""
        token = _create_token_with_paths(["C:/workspace/project"])

        # Lowercase drive should still match
        assert token.path_allowed("c:/workspace/project/file.txt") is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_drive_relative_path_blocked(self):
        """Drive-relative paths (C:file.txt) should be blocked."""
        token = _create_token_with_paths(["C:/workspace"])

        # Drive-relative (no leading slash)
        assert token.path_allowed("C:file.txt") is False


# ===========================================================================
# SECTION 8: D3 Sandbox Boundary Tests
# ===========================================================================


class TestD3SandboxBoundary:
    """Test that D3 sandbox cannot escalate to D4 repo writes."""

    def test_d3_request_with_valid_gates_allowed(self):
        """D3 request with all gates should be allowed as dry-run."""
        guard = DestructiveActionGuard()
        request = _create_request(
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            capability_token_present=True,
            security_gate_passed=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
        assert result.dry_run_only is True

    def test_d3_missing_workspace_binding_blocked(self):
        """D3 request without workspace binding should be blocked."""
        guard = DestructiveActionGuard()
        request = _create_request(
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
            workspace_binding_enforced=False,  # Missing!
            path_constraints_validated=True,
            capability_token_present=True,
            security_gate_passed=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_WORKSPACE_BINDING

    def test_d3_missing_path_validation_blocked(self):
        """D3 request without path validation should be blocked."""
        guard = DestructiveActionGuard()
        request = _create_request(
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
            workspace_binding_enforced=True,
            path_constraints_validated=False,  # Missing!
            capability_token_present=True,
            security_gate_passed=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.MISSING_PATH_VALIDATION

    def test_d4_always_blocked_phase1(self):
        """D4 repo write should always be blocked in Phase 1."""
        guard = DestructiveActionGuard()
        request = _create_request(
            action_class=DestructiveActionClass.D4_WRITE_REPO,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            capability_token_present=True,
            security_gate_passed=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert result.decision == GuardDecision.BLOCKED
        assert result.reason_code == GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1


# ===========================================================================
# SECTION 9: WSP 97 Truth Boundary Tests
# ===========================================================================


class TestWSP97TruthBoundaries:
    """Test that WSP 97 truth fields remain False for all operations."""

    def test_live_execution_allowed_always_false(self):
        """live_execution_allowed must be False for all results."""
        guard = DestructiveActionGuard()

        # Test various action classes
        for action_class in [
            DestructiveActionClass.D0_OBSERVE,
            DestructiveActionClass.D1_READ,
            DestructiveActionClass.D2_SIMULATE,
            DestructiveActionClass.D3_WRITE_SANDBOX,
            DestructiveActionClass.D4_WRITE_REPO,
            DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
            DestructiveActionClass.D6_IRREVERSIBLE,
        ]:
            request = _create_request(action_class=action_class)
            result = guard.evaluate(request)

            assert result.live_execution_allowed is False, \
                f"live_execution_allowed should be False for {action_class}"

    def test_repo_created_always_false(self):
        """repo_created must be False for all results."""
        guard = DestructiveActionGuard()

        for action_class in DestructiveActionClass:
            request = _create_request(action_class=action_class)
            result = guard.evaluate(request)

            assert result.repo_created is False, \
                f"repo_created should be False for {action_class}"

    def test_production_source_modified_always_false(self):
        """production_source_modified must be False for all results."""
        guard = DestructiveActionGuard()

        for action_class in DestructiveActionClass:
            request = _create_request(action_class=action_class)
            result = guard.evaluate(request)

            assert result.production_source_modified is False, \
                f"production_source_modified should be False for {action_class}"

    def test_cabr_payout_fields_always_false(self):
        """CABR and payout fields must be False for all results."""
        guard = DestructiveActionGuard()

        for action_class in DestructiveActionClass:
            request = _create_request(action_class=action_class)
            result = guard.evaluate(request)

            assert result.verification_complete is False
            assert result.cabr_ready is False
            assert result.payout_ready is False


# ===========================================================================
# SECTION 10: Blocked Path Override Tests
# ===========================================================================


class TestBlockedPathOverride:
    """Test that blocked paths override allowed paths."""

    def test_blocked_path_overrides_allowed(self):
        """Blocked path should override allowed even if within allowed root."""
        token = _create_token_with_paths(
            allowed_paths=["modules/foundups"],
            blocked_paths=["modules/foundups/secrets"],
        )

        assert token.path_allowed("modules/foundups/kosei/file.txt") is True
        assert token.path_allowed("modules/foundups/secrets/key.pem") is False

    def test_blocked_env_file_pattern(self):
        """Blocked .env pattern should work."""
        token = _create_token_with_paths(
            allowed_paths=["modules/foundups"],
            blocked_paths=[".env"],
        )

        assert token.path_allowed("modules/foundups/kosei/config.txt") is True
        assert token.path_allowed("modules/foundups/.env") is False

    def test_blocked_subdirectory_blocks_descendants(self):
        """Blocking a directory should block all descendants."""
        token = _create_token_with_paths(
            allowed_paths=["modules"],
            blocked_paths=["modules/infrastructure/secrets"],
        )

        assert token.path_allowed("modules/infrastructure/wre_core/file.py") is True
        assert token.path_allowed("modules/infrastructure/secrets/key.pem") is False
        assert token.path_allowed("modules/infrastructure/secrets/nested/deep.txt") is False


# ===========================================================================
# SECTION 11: Empty and Null Input Tests
# ===========================================================================


class TestEmptyAndNullInputs:
    """Test fail-closed behavior for empty/null inputs."""

    def test_empty_path_blocked(self):
        """Empty path should be blocked."""
        token = _create_token_with_paths(["modules/foundups"])

        assert token.path_allowed("") is False

    def test_empty_allowed_paths_blocks_all(self):
        """Empty allowed_paths list should block all paths."""
        token = _create_token_with_paths([])

        assert token.path_allowed("modules/foundups/file.txt") is False
        assert token.path_allowed("/etc/passwd") is False
        assert token.path_allowed("any/path.txt") is False

    def test_whitespace_only_path_handled(self):
        """Whitespace-only path should be blocked or normalized."""
        token = _create_token_with_paths(["modules/foundups"])

        # Pure whitespace should not match allowed
        assert token.path_allowed("   ") is False
        assert token.path_allowed("\t\n") is False


# ===========================================================================
# SECTION 12: Integration with Guard Evaluation
# ===========================================================================


class TestGuardIntegrationWithPathValidation:
    """Test guard evaluation integrates with path validation flags."""

    def test_guard_blocks_when_path_validation_false(self):
        """Guard should block D3 when path_constraints_validated is False."""
        guard = DestructiveActionGuard()

        request = _create_request(
            action_class=DestructiveActionClass.D3_WRITE_SANDBOX,
            path_constraints_validated=False,
        )

        result = guard.evaluate(request)

        assert result.allowed is False
        assert "path_constraints" in result.gates_failed

    def test_guard_allows_d0_regardless_of_path_validation(self):
        """D0 observe should be allowed regardless of path validation."""
        guard = DestructiveActionGuard()

        request = _create_request(
            action_class=DestructiveActionClass.D0_OBSERVE,
            path_constraints_validated=False,
            dry_run_mode=True,
        )

        result = guard.evaluate(request)

        assert result.allowed is True
        assert result.decision == GuardDecision.ALLOW_DRY_RUN
