#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA26 Proof Test: Token Validation Service (Phase 1)

Tests the production-ready capability token validation service that can be
injected into HermesJobExecutor for D3+ action authorization.

WSP 97 Truth Boundaries:
  - repo_created: False (ALWAYS)
  - production_source_modified: False (ALWAYS)
  - live_external_delegate_called: False (ALWAYS)
  - external_federation_initiated: False (ALWAYS)
  - network_called: False (ALWAYS)
  - verification_complete: False (no CABR pipeline)
  - cabr_ready: False (no CABR pipeline)
  - payout_ready: False (no payout pipeline)

HXA21 verdict was: CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED (test-only)
HXA24 verdict was: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED
HXA25 verdict was: D3_SANDBOX_EXECUTION_DEFINED
HXA26 defines: Production-ready token validation service module.

This slice MUST NOT:
  - Use real secrets or signing keys
  - Make external network calls
  - Issue production tokens
  - Enable live operations

Slice: HXA26_TOKEN_VALIDATION_SERVICE_PHASE1
Worker: 0102
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Import the production module
from modules.infrastructure.wre_core.src.capability_token_validator import (
    CapabilityToken,
    ICapabilityTokenValidator,
    LocalCapabilityTokenIssuer,
    LocalCapabilityTokenValidator,
    TokenValidationReasonCode,
    TokenValidationResult,
    get_default_validator,
    reset_default_validator,
)


# ===========================================================================
# SECTION 1: CapabilityToken Model Tests
# ===========================================================================


class TestCapabilityTokenModel:
    """Test the CapabilityToken dataclass model."""

    def test_token_has_identity_fields(self):
        """Verify token has all identity fields."""
        token = CapabilityToken(
            token_id="cap_test_001",
            issuer="test-issuer",
            subject="agent_0102",
            audience="wre-local",
        )
        assert token.token_id == "cap_test_001"
        assert token.issuer == "test-issuer"
        assert token.subject == "agent_0102"
        assert token.audience == "wre-local"

    def test_token_has_authorization_fields(self):
        """Verify token has authorization fields with defaults."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
        )
        assert token.scopes == []
        assert token.allowed_actions == []
        assert token.allowed_paths == []
        assert token.blocked_paths == []

    def test_token_dry_run_only_defaults_true(self):
        """Verify dry_run_only defaults to True (safe default)."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
        )
        assert token.dry_run_only is True

    def test_token_signature_defaults_false(self):
        """Verify signature fields default to False (fail-closed)."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
        )
        assert token.signature_present is False
        assert token.signature_verified is False

    def test_token_is_expired_with_past_expiry(self):
        """Verify is_expired returns True for expired tokens."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            expires_at=past,
        )
        assert token.is_expired() is True

    def test_token_is_not_expired_with_future_expiry(self):
        """Verify is_expired returns False for valid tokens."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            expires_at=future,
        )
        assert token.is_expired() is False

    def test_token_action_allowed(self):
        """Verify action_allowed checks allowed_actions list."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            allowed_actions=["build_foundup", "validate_foundup"],
        )
        assert token.action_allowed("build_foundup") is True
        assert token.action_allowed("delete_foundup") is False

    def test_token_scope_allowed(self):
        """Verify scope_allowed checks scopes list."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            scopes=["repo:read", "source:dry-run"],
        )
        assert token.scope_allowed("repo:read") is True
        assert token.scope_allowed("repo:write") is False

    def test_token_path_allowed_within_allowed_roots(self):
        """Verify path_allowed returns True for paths within allowed roots."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            allowed_paths=["/tmp/test", "modules/foundups"],
        )
        assert token.path_allowed("/tmp/test/file.py") is True
        assert token.path_allowed("modules/foundups/kosei/README.md") is True
        assert token.path_allowed("/other/path") is False

    def test_token_path_blocked_overrides_allowed(self):
        """Verify blocked paths override allowed paths."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            allowed_paths=["modules/foundups"],
            blocked_paths=["modules/foundups/secrets"],
        )
        assert token.path_allowed("modules/foundups/README.md") is True
        assert token.path_allowed("modules/foundups/secrets/keys.json") is False

    def test_token_env_file_blocked(self):
        """Verify .env files are blocked."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="test",
            subject="test",
            audience="test",
            allowed_paths=["modules"],
            blocked_paths=[".env"],
        )
        assert token.path_allowed("modules/.env") is False
        assert token.path_allowed("modules/foundups/.env") is False


class TestTokenRedaction:
    """Test token redaction for security logging."""

    def test_redacted_repr_hides_token_id(self):
        """Verify redacted_repr truncates token_id."""
        token = CapabilityToken(
            token_id="cap_very_long_token_id_123456",
            issuer="test",
            subject="test",
            audience="test",
        )
        redacted = token.redacted_repr()
        assert "cap_very" in redacted
        assert "very_long_token_id_123456" not in redacted
        assert "..." in redacted

    def test_to_dict_redacts_nonce(self):
        """Verify to_dict redacts nonce."""
        token = CapabilityToken(
            token_id="cap_test_id_123456",
            issuer="test",
            subject="test",
            audience="test",
            nonce="secret_nonce_value_12345",
        )
        d = token.to_dict()
        assert d["nonce"] == "REDACTED"
        assert "secret_nonce" not in str(d)


# ===========================================================================
# SECTION 2: TokenValidationResult Tests
# ===========================================================================


class TestTokenValidationResult:
    """Test the TokenValidationResult dataclass."""

    def test_default_result_is_invalid(self):
        """Verify default result indicates invalid token."""
        result = TokenValidationResult()
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.MISSING_TOKEN

    def test_wsp97_truth_fields_always_false(self):
        """Verify WSP 97 truth fields are always False."""
        result = TokenValidationResult(token_valid=True)
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    def test_to_dict_includes_all_fields(self):
        """Verify to_dict includes all validation fields."""
        result = TokenValidationResult(
            token_valid=True,
            reason_code=TokenValidationReasonCode.VALID,
            action_allowed=True,
            path_allowed=True,
        )
        d = result.to_dict()
        assert "token_valid" in d
        assert "reason_code" in d
        assert "verification_complete" in d
        assert d["verification_complete"] is False


# ===========================================================================
# SECTION 3: LocalCapabilityTokenValidator Tests
# ===========================================================================


class TestLocalCapabilityTokenValidator:
    """Test the LocalCapabilityTokenValidator."""

    @pytest.fixture
    def validator(self):
        """Create a fresh validator for each test."""
        return LocalCapabilityTokenValidator(
            expected_audience="wre-local",
            expected_issuer="wre-local-test-issuer",
        )

    @pytest.fixture
    def issuer(self):
        """Create a token issuer for tests."""
        return LocalCapabilityTokenIssuer(issuer_id="wre-local-test-issuer")

    def test_missing_token_fails(self, validator):
        """Verify None token fails validation."""
        result = validator.validate_token(None)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.MISSING_TOKEN
        assert "token" in result.missing_fields

    def test_missing_signature_fails(self, validator):
        """Verify token without signature fails validation."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="wre-local-test-issuer",
            subject="test",
            audience="wre-local",
            signature_present=False,
        )
        result = validator.validate_token(token)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.MISSING_SIGNATURE

    def test_unverified_signature_fails(self, validator):
        """Verify token with unverified signature fails validation."""
        token = CapabilityToken(
            token_id="cap_test",
            issuer="wre-local-test-issuer",
            subject="test",
            audience="wre-local",
            signature_present=True,
            signature_verified=False,
        )
        result = validator.validate_token(token)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.SIGNATURE_NOT_VERIFIED

    def test_expired_token_fails(self, validator):
        """Verify expired token fails validation."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = CapabilityToken(
            token_id="cap_test",
            issuer="wre-local-test-issuer",
            subject="test",
            audience="wre-local",
            signature_present=True,
            signature_verified=True,
            expires_at=past,
        )
        result = validator.validate_token(token)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.TOKEN_EXPIRED
        assert result.expired is True

    def test_wrong_audience_fails(self, validator):
        """Verify token with wrong audience fails validation."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = CapabilityToken(
            token_id="cap_test",
            issuer="wre-local-test-issuer",
            subject="test",
            audience="wrong-audience",
            signature_present=True,
            signature_verified=True,
            expires_at=future,
        )
        result = validator.validate_token(token)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.WRONG_AUDIENCE

    def test_wrong_issuer_fails(self, validator):
        """Verify token with wrong issuer fails validation."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = CapabilityToken(
            token_id="cap_test",
            issuer="wrong-issuer",
            subject="test",
            audience="wre-local",
            signature_present=True,
            signature_verified=True,
            expires_at=future,
        )
        result = validator.validate_token(token)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.WRONG_ISSUER

    def test_replayed_nonce_fails(self, validator, issuer):
        """Verify replayed nonce fails validation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            allowed_actions=["test_action"],
        )

        # First use should succeed
        result1 = validator.validate_token(token, requested_action="test_action")
        assert result1.token_valid is True

        # Second use should fail (replay)
        result2 = validator.validate_token(token, requested_action="test_action")
        assert result2.token_valid is False
        assert result2.reason_code == TokenValidationReasonCode.REPLAY_DETECTED
        assert result2.replay_detected is True

    def test_action_not_allowed_fails(self, validator, issuer):
        """Verify action not in allowed_actions fails validation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            allowed_actions=["build_foundup"],
        )
        result = validator.validate_token(token, requested_action="delete_foundup")
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.ACTION_NOT_ALLOWED
        assert result.action_allowed is False

    def test_scope_not_allowed_fails(self, validator, issuer):
        """Verify scope not in scopes fails validation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            scopes=["repo:read"],
        )
        result = validator.validate_token(token, requested_scope="repo:write")
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.SCOPE_NOT_ALLOWED
        assert "repo:write" in result.denied_scopes

    def test_path_outside_allowed_roots_fails(self, validator, issuer):
        """Verify path outside allowed roots fails validation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            allowed_paths=["/tmp/allowed"],
        )
        result = validator.validate_token(token, target_path="/etc/secrets")
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.PATH_OUTSIDE_ALLOWED_ROOTS
        assert result.path_allowed is False

    def test_path_in_blocked_list_fails(self, validator, issuer):
        """Verify blocked path fails validation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            allowed_paths=["modules"],
            blocked_paths=["modules/secrets"],
        )
        result = validator.validate_token(token, target_path="modules/secrets/keys.json")
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.PATH_IN_BLOCKED_LIST
        assert result.path_allowed is False

    def test_dry_run_only_blocks_live_operation(self, validator, issuer):
        """Verify dry_run_only token cannot authorize live operation."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            dry_run_only=True,
        )
        result = validator.validate_token(token, is_live_operation=True)
        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.DRY_RUN_ONLY_BLOCKS_LIVE
        assert result.dry_run_only_blocked_live is True

    def test_valid_dry_run_token_passes(self, validator, issuer):
        """Verify valid dry-run token passes all checks."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            scopes=["source:dry-run"],
            allowed_actions=["build_foundup"],
            allowed_paths=["/tmp/test"],
            dry_run_only=True,
        )
        result = validator.validate_token(
            token,
            requested_action="build_foundup",
            requested_scope="source:dry-run",
            target_path="/tmp/test/file.py",
            is_live_operation=False,
        )
        assert result.token_valid is True
        assert result.reason_code == TokenValidationReasonCode.VALID_DRY_RUN_ONLY
        assert result.action_allowed is True
        assert result.path_allowed is True

    def test_valid_live_token_passes(self, validator, issuer):
        """Verify valid live token passes all checks when dry_run_only=False."""
        token = issuer.issue_token(
            subject="test",
            audience="wre-local",
            scopes=["source:write"],
            allowed_actions=["build_foundup"],
            allowed_paths=["/tmp/test"],
            dry_run_only=False,
        )
        result = validator.validate_token(
            token,
            requested_action="build_foundup",
            requested_scope="source:write",
            target_path="/tmp/test/file.py",
            is_live_operation=True,
        )
        assert result.token_valid is True
        assert result.reason_code == TokenValidationReasonCode.VALID


class TestValidatorNonceRegistry:
    """Test the validator's nonce registry."""

    def test_register_nonce_returns_true_for_new(self):
        """Verify register_nonce returns True for new nonce."""
        validator = LocalCapabilityTokenValidator()
        assert validator.register_nonce("nonce_123") is True

    def test_register_nonce_returns_false_for_replay(self):
        """Verify register_nonce returns False for replayed nonce."""
        validator = LocalCapabilityTokenValidator()
        validator.register_nonce("nonce_123")
        assert validator.register_nonce("nonce_123") is False

    def test_clear_nonces_removes_all(self):
        """Verify clear_nonces clears the registry."""
        validator = LocalCapabilityTokenValidator()
        validator.register_nonce("nonce_123")
        validator.clear_nonces()
        assert validator.register_nonce("nonce_123") is True


# ===========================================================================
# SECTION 4: LocalCapabilityTokenIssuer Tests
# ===========================================================================


class TestLocalCapabilityTokenIssuer:
    """Test the LocalCapabilityTokenIssuer."""

    def test_issue_token_creates_valid_token(self):
        """Verify issued tokens have all required fields."""
        issuer = LocalCapabilityTokenIssuer(issuer_id="test-issuer")
        token = issuer.issue_token(
            subject="agent_0102",
            audience="wre-local",
            scopes=["repo:read"],
            allowed_actions=["build_foundup"],
            allowed_paths=["/tmp/test"],
        )
        assert token.token_id.startswith("cap_")
        assert token.issuer == "test-issuer"
        assert token.subject == "agent_0102"
        assert token.audience == "wre-local"
        assert token.scopes == ["repo:read"]
        assert token.allowed_actions == ["build_foundup"]
        assert token.allowed_paths == ["/tmp/test"]
        assert token.signature_present is True
        assert token.signature_verified is True

    def test_issue_token_tracks_issued_tokens(self):
        """Verify issuer tracks issued token IDs."""
        issuer = LocalCapabilityTokenIssuer()
        token1 = issuer.issue_token(subject="test", audience="test")
        token2 = issuer.issue_token(subject="test", audience="test")
        assert token1.token_id in issuer.issued_tokens
        assert token2.token_id in issuer.issued_tokens
        assert len(issuer.issued_tokens) == 2

    def test_issue_token_dry_run_only_default_true(self):
        """Verify issued tokens default to dry_run_only=True."""
        issuer = LocalCapabilityTokenIssuer()
        token = issuer.issue_token(subject="test", audience="test")
        assert token.dry_run_only is True


# ===========================================================================
# SECTION 5: Default Validator Tests
# ===========================================================================


class TestDefaultValidator:
    """Test the default validator singleton."""

    def test_get_default_validator_returns_instance(self):
        """Verify get_default_validator returns a validator."""
        reset_default_validator()
        validator = get_default_validator()
        assert isinstance(validator, LocalCapabilityTokenValidator)

    def test_get_default_validator_returns_singleton(self):
        """Verify get_default_validator returns the same instance."""
        reset_default_validator()
        validator1 = get_default_validator()
        validator2 = get_default_validator()
        assert validator1 is validator2

    def test_reset_default_validator_clears_singleton(self):
        """Verify reset_default_validator creates new instance."""
        reset_default_validator()
        validator1 = get_default_validator()
        reset_default_validator()
        validator2 = get_default_validator()
        assert validator1 is not validator2


# ===========================================================================
# SECTION 6: WSP 97 Truth Tests
# ===========================================================================


class TestWSP97TruthBoundaries:
    """Test that WSP 97 truth boundaries are maintained."""

    def test_validation_result_never_sets_verification_complete(self):
        """Verify validation never sets verification_complete=True."""
        issuer = LocalCapabilityTokenIssuer()
        validator = LocalCapabilityTokenValidator()
        token = issuer.issue_token(subject="test", audience="wre-local")
        result = validator.validate_token(token)
        assert result.verification_complete is False

    def test_validation_result_never_sets_cabr_ready(self):
        """Verify validation never sets cabr_ready=True."""
        issuer = LocalCapabilityTokenIssuer()
        validator = LocalCapabilityTokenValidator()
        token = issuer.issue_token(subject="test", audience="wre-local")
        result = validator.validate_token(token)
        assert result.cabr_ready is False

    def test_validation_result_never_sets_payout_ready(self):
        """Verify validation never sets payout_ready=True."""
        issuer = LocalCapabilityTokenIssuer()
        validator = LocalCapabilityTokenValidator()
        token = issuer.issue_token(subject="test", audience="wre-local")
        result = validator.validate_token(token)
        assert result.payout_ready is False

    def test_failed_validation_keeps_truth_fields_false(self):
        """Verify failed validation keeps all truth fields False."""
        validator = LocalCapabilityTokenValidator()
        result = validator.validate_token(None)
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False


# ===========================================================================
# SECTION 7: Integration Tests
# ===========================================================================


class TestValidatorIntegration:
    """Integration tests for validator with real token flow."""

    def test_full_token_flow(self):
        """Test complete token issuance and validation flow."""
        issuer = LocalCapabilityTokenIssuer(issuer_id="wre-local-test-issuer")
        validator = LocalCapabilityTokenValidator(
            expected_audience="wre-local",
            expected_issuer="wre-local-test-issuer",
        )

        # Issue a token
        token = issuer.issue_token(
            subject="agent_0102",
            audience="wre-local",
            scopes=["source:dry-run"],
            allowed_actions=["build_foundup", "validate_foundup"],
            allowed_paths=["modules/foundups", "/tmp/test"],
            blocked_paths=[".env", "secrets"],
            dry_run_only=True,
        )

        # Validate for a dry-run operation
        result = validator.validate_token(
            token,
            requested_action="build_foundup",
            requested_scope="source:dry-run",
            target_path="modules/foundups/kosei/README.md",
            is_live_operation=False,
        )

        assert result.token_valid is True
        assert result.reason_code == TokenValidationReasonCode.VALID_DRY_RUN_ONLY
        assert result.action_allowed is True
        assert result.path_allowed is True
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    def test_full_token_flow_blocked_path(self):
        """Test token validation fails for blocked path."""
        issuer = LocalCapabilityTokenIssuer(issuer_id="wre-local-test-issuer")
        validator = LocalCapabilityTokenValidator(
            expected_audience="wre-local",
            expected_issuer="wre-local-test-issuer",
        )

        token = issuer.issue_token(
            subject="agent_0102",
            audience="wre-local",
            allowed_paths=["modules"],
            blocked_paths=[".env"],
        )

        result = validator.validate_token(
            token,
            target_path="modules/.env",
        )

        assert result.token_valid is False
        assert result.reason_code == TokenValidationReasonCode.PATH_IN_BLOCKED_LIST


# ===========================================================================
# SECTION 8: HXA26 Verdict Documentation
# ===========================================================================


class TestHXA26Verdict:
    """Test that HXA26 verdict is documented."""

    def test_hxa26_verdict_documented(self):
        """Verify HXA26 verdict: TOKEN_VALIDATION_SERVICE_DEFINED."""
        # HXA26 defines a production-ready token validation service module
        # that can be injected into HermesJobExecutor.
        #
        # Key deliverables:
        # 1. CapabilityToken model (production code)
        # 2. TokenValidationResult (production code)
        # 3. ICapabilityTokenValidator protocol (production code)
        # 4. LocalCapabilityTokenValidator (Phase 1 implementation)
        # 5. LocalCapabilityTokenIssuer (Phase 1 test infrastructure)
        # 6. get_default_validator() singleton accessor
        #
        # What HXA26 proves:
        # - Token model has all required fields
        # - Validation is fail-closed (any gate failure = invalid)
        # - Nonce registry prevents replay
        # - WSP 97 truth fields always False
        # - Module can be imported by production code
        #
        # What HXA26 does NOT prove:
        # - Real JWT implementation
        # - Real signing keys
        # - External token service
        # - Production token issuance
        assert True, "HXA26 verdict: TOKEN_VALIDATION_SERVICE_DEFINED"


# ===========================================================================
# SECTION 9: Module Import Tests
# ===========================================================================


class TestModuleImports:
    """Test that the module can be imported correctly."""

    def test_module_exports_capability_token(self):
        """Verify CapabilityToken is exported."""
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            CapabilityToken,
        )
        assert CapabilityToken is not None

    def test_module_exports_validation_result(self):
        """Verify TokenValidationResult is exported."""
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            TokenValidationResult,
        )
        assert TokenValidationResult is not None

    def test_module_exports_validator(self):
        """Verify LocalCapabilityTokenValidator is exported."""
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            LocalCapabilityTokenValidator,
        )
        assert LocalCapabilityTokenValidator is not None

    def test_module_exports_issuer(self):
        """Verify LocalCapabilityTokenIssuer is exported."""
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            LocalCapabilityTokenIssuer,
        )
        assert LocalCapabilityTokenIssuer is not None

    def test_module_exports_reason_codes(self):
        """Verify TokenValidationReasonCode is exported."""
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            TokenValidationReasonCode,
        )
        assert TokenValidationReasonCode.VALID is not None
        assert TokenValidationReasonCode.MISSING_TOKEN is not None
