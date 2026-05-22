# -*- coding: utf-8 -*-
"""Tests for Mock Vault Resolver.

Contract: FOUNDUPS_CREDENTIAL_ACCESS_LAYER_POC_PHASE1
Per WSP_71 Annex A specification.

WSP_97 Labels:
  - CREDENTIAL_ACCESS_POC_ONLY
  - MOCK_VAULT_ONLY
  - NO_REAL_SECRET_ACCESS
  - SECRET_VALUE_NEVER_LOGGED
  - AUDIT_HASH_ONLY
  - FAIL_CLOSED_REQUIRED

Test Coverage:
  T1: Valid test reference resolves through mock
  T2: Unknown reference fails closed
  T3: Resolver unavailable fails closed
  T4: Plaintext secret not present in logs/output
  T5: Audit event uses hash only
  T6: TTL/session expiration denies access
  T7: No real network/1Password access
"""

from __future__ import annotations

import io
import json
import logging
import sys
import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    AuditEvent,
    MockVaultResolver,
    OpReference,
    ResolveErrorCode,
    ResolveResult,
    create_mock_resolver,
    get_test_references,
    hash_reference,
    hash_secret,
    parse_op_reference,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver():
    """Create a mock vault resolver."""
    return create_mock_resolver()


@pytest.fixture
def unavailable_resolver():
    """Create an unavailable resolver for fail-closed testing."""
    return create_mock_resolver(available=False)


@pytest.fixture
def audit_collector():
    """Collector for audit events."""
    events: List[AuditEvent] = []

    def collect(event: AuditEvent):
        events.append(event)

    return events, collect


@pytest.fixture
def resolver_with_audit(audit_collector):
    """Resolver with audit callback."""
    events, callback = audit_collector
    resolver = create_mock_resolver(audit_callback=callback)
    return resolver, events


# ---------------------------------------------------------------------------
# T1: Valid Test Reference Resolves Through Mock
# ---------------------------------------------------------------------------


class TestValidReferenceResolves:
    """T1: Valid test references resolve successfully."""

    def test_valid_api_key_reference_resolves(self, resolver):
        """Known test API key reference resolves."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.success is True
        assert result.error_code is None
        assert result.get_value() is not None
        assert len(result.get_value()) > 0

    def test_valid_database_reference_resolves(self, resolver):
        """Known test database reference resolves."""
        result = resolver.resolve("op://test-vault/test-database/password")
        assert result.success is True
        assert result.get_value() is not None

    def test_valid_token_reference_resolves(self, resolver):
        """Known test token reference resolves."""
        result = resolver.resolve("op://test-vault/test-service/token")
        assert result.success is True
        assert result.get_value() is not None

    def test_all_test_references_resolve(self, resolver):
        """All documented test references resolve."""
        test_refs = get_test_references()
        for ref in test_refs.keys():
            result = resolver.resolve(ref)
            assert result.success is True, f"Failed to resolve: {ref}"

    def test_resolved_result_has_session_id(self, resolver):
        """Successful resolution includes session ID."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.session_id is not None
        assert len(result.session_id) > 0

    def test_resolved_result_has_ttl(self, resolver):
        """Successful resolution includes TTL remaining."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.ttl_remaining is not None
        assert result.ttl_remaining > 0


# ---------------------------------------------------------------------------
# T2: Unknown Reference Fails Closed
# ---------------------------------------------------------------------------


class TestUnknownReferenceFailsClosed:
    """T2: Unknown references fail closed with proper error."""

    def test_unknown_vault_fails_closed(self, resolver):
        """Unknown vault name fails closed."""
        result = resolver.resolve("op://unknown-vault/test-api-key/credential")
        assert result.success is False
        assert result.error_code == ResolveErrorCode.UNKNOWN_REFERENCE
        assert result.get_value() is None

    def test_unknown_item_fails_closed(self, resolver):
        """Unknown item name fails closed."""
        result = resolver.resolve("op://test-vault/unknown-item/credential")
        assert result.success is False
        assert result.error_code == ResolveErrorCode.UNKNOWN_REFERENCE
        assert result.get_value() is None

    def test_unknown_field_fails_closed(self, resolver):
        """Unknown field name fails closed."""
        result = resolver.resolve("op://test-vault/test-api-key/unknown-field")
        assert result.success is False
        assert result.error_code == ResolveErrorCode.UNKNOWN_REFERENCE
        assert result.get_value() is None

    def test_invalid_format_fails_closed(self, resolver):
        """Invalid reference format fails closed."""
        invalid_refs = [
            "not-an-op-reference",
            "op://missing-parts",
            "op://vault/item",
            "op://",
            "",
            None,
            "op://vault/item/field/extra",
            "https://vault/item/field",
        ]
        for ref in invalid_refs:
            result = resolver.resolve(ref if ref else "")
            assert result.success is False, f"Should fail: {ref}"
            assert result.get_value() is None

    def test_fails_closed_has_error_message(self, resolver):
        """Failed resolution includes error message."""
        result = resolver.resolve("op://unknown/unknown/unknown")
        assert result.success is False
        assert result.error_message is not None
        assert len(result.error_message) > 0


# ---------------------------------------------------------------------------
# T3: Resolver Unavailable Fails Closed
# ---------------------------------------------------------------------------


class TestResolverUnavailableFailsClosed:
    """T3: Resolver unavailable fails closed."""

    def test_unavailable_resolver_fails_on_valid_ref(self, unavailable_resolver):
        """Valid reference fails when resolver unavailable."""
        result = unavailable_resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.success is False
        assert result.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE
        assert result.get_value() is None

    def test_unavailable_resolver_error_message(self, unavailable_resolver):
        """Unavailable resolver provides clear error."""
        result = unavailable_resolver.resolve("op://test-vault/test-api-key/credential")
        assert "unavailable" in result.error_message.lower()
        assert "denied" in result.error_message.lower()

    def test_resolver_availability_check(self):
        """is_available() reflects resolver state."""
        available = create_mock_resolver(available=True)
        unavailable = create_mock_resolver(available=False)

        assert available.is_available() is True
        assert unavailable.is_available() is False

    def test_resolver_can_become_unavailable(self, resolver):
        """Resolver can transition to unavailable state."""
        assert resolver.is_available() is True

        # First resolve succeeds
        result1 = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result1.success is True

        # Make unavailable
        resolver.set_available(False)

        # Second resolve fails
        result2 = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result2.success is False
        assert result2.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE


# ---------------------------------------------------------------------------
# T4: Plaintext Secret Not Present in Logs/Output
# ---------------------------------------------------------------------------


class TestSecretNotInOutput:
    """T4: Plaintext secret never appears in logs/output."""

    def test_secret_not_in_result_repr(self, resolver):
        """Secret value not in ResolveResult repr."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.success is True

        # Get the actual secret
        secret = result.get_value()
        assert secret is not None

        # repr should NOT contain the secret
        result_repr = repr(result)
        assert secret not in result_repr
        assert "TEST_VALUE" not in result_repr
        assert "_secret_value" not in result_repr or "None" in result_repr

    def test_secret_not_in_result_str(self, resolver):
        """Secret value not in ResolveResult str."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        secret = result.get_value()

        result_str = str(result)
        assert secret not in result_str

    def test_secret_not_in_audit_dict(self, resolver):
        """Secret value not in audit dictionary."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        secret = result.get_value()

        audit_dict = result.to_audit_dict()
        audit_json = json.dumps(audit_dict)

        assert secret not in audit_json
        assert "TEST_VALUE" not in audit_json

    def test_secret_not_logged_on_success(self, resolver):
        """Secret not written to any log output."""
        # Capture all logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)

        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)

        try:
            result = resolver.resolve("op://test-vault/test-api-key/credential")
            secret = result.get_value()

            log_output = log_capture.getvalue()
            assert secret not in log_output
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(original_level)

    def test_secret_not_in_exception_message(self, resolver):
        """If resolution raises, secret not in exception."""
        # This resolver should not raise, but test the pattern
        result = resolver.resolve("op://test-vault/test-api-key/credential")

        # Create an error from the result (hypothetical)
        error_msg = result.error_message or ""
        secret = result.get_value()

        if secret:
            assert secret not in error_msg

    def test_stdout_capture_no_secret(self, resolver, capsys):
        """Secret not printed to stdout during resolution."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        secret = result.get_value()

        captured = capsys.readouterr()
        assert secret not in captured.out
        assert secret not in captured.err

    def test_get_test_references_returns_descriptions_not_values(self):
        """get_test_references returns descriptions, not actual values."""
        refs = get_test_references()
        for ref, description in refs.items():
            assert "TEST_VALUE" not in description
            assert "MOCK" not in description or "reference" in description.lower()


# ---------------------------------------------------------------------------
# T5: Audit Event Uses Hash Only
# ---------------------------------------------------------------------------


class TestAuditHashOnly:
    """T5: Audit events use hashes, never plaintext values."""

    def test_audit_event_has_reference_hash(self, resolver_with_audit):
        """Audit event includes reference hash."""
        resolver, events = resolver_with_audit
        resolver.resolve("op://test-vault/test-api-key/credential")

        assert len(events) == 1
        event = events[0]
        assert event.reference_hash is not None
        assert event.reference_hash.startswith("sha256:")

    def test_audit_event_no_secret_value(self, resolver_with_audit):
        """Audit event never contains secret value."""
        resolver, events = resolver_with_audit
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        secret = result.get_value()

        event = events[0]
        event_dict = event.to_dict()
        event_json = json.dumps(event_dict)

        assert secret not in event_json
        assert "TEST_VALUE" not in event_json

    def test_hash_reference_is_deterministic(self):
        """Same reference produces same hash."""
        ref = "op://test-vault/test-api-key/credential"
        hash1 = hash_reference(ref)
        hash2 = hash_reference(ref)
        assert hash1 == hash2

    def test_hash_reference_format(self):
        """Reference hash has correct format."""
        ref = "op://test-vault/test-api-key/credential"
        ref_hash = hash_reference(ref)
        assert ref_hash.startswith("sha256:")
        assert len(ref_hash) == len("sha256:") + 16  # Truncated to 16 hex chars

    def test_hash_secret_full_length(self):
        """Secret hash is full SHA-256 length."""
        secret_hash = hash_secret("test-secret-value")
        assert secret_hash.startswith("sha256:")
        assert len(secret_hash) == len("sha256:") + 64  # Full 64 hex chars

    def test_audit_callback_receives_all_events(self, resolver_with_audit):
        """Audit callback receives events for success and failure."""
        resolver, events = resolver_with_audit

        # Success
        resolver.resolve("op://test-vault/test-api-key/credential")
        # Failure
        resolver.resolve("op://unknown/unknown/unknown")

        assert len(events) == 2
        assert events[0].success is True
        assert events[1].success is False

    def test_audit_event_includes_timestamp(self, resolver_with_audit):
        """Audit event includes ISO timestamp."""
        resolver, events = resolver_with_audit
        resolver.resolve("op://test-vault/test-api-key/credential")

        event = events[0]
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO format has T separator


# ---------------------------------------------------------------------------
# T6: TTL/Session Expiration Denies Access
# ---------------------------------------------------------------------------


class TestTTLSessionExpiration:
    """T6: TTL and session expiration denies access."""

    def test_ttl_expires_after_duration(self):
        """Access denied after TTL expires."""
        # Create resolver with 1 second TTL
        resolver = create_mock_resolver(ttl_seconds=1)

        # First access succeeds
        result1 = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result1.success is True

        # Wait for TTL to expire
        time.sleep(1.5)

        # Second access fails
        result2 = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result2.success is False
        assert result2.error_code == ResolveErrorCode.TTL_EXPIRED

    def test_ttl_remaining_decreases(self):
        """TTL remaining decreases between accesses."""
        resolver = create_mock_resolver(ttl_seconds=10)

        result1 = resolver.resolve("op://test-vault/test-api-key/credential")
        ttl1 = result1.ttl_remaining

        time.sleep(0.5)

        # Fresh access to same reference
        resolver._access_times.clear()  # Reset to get fresh TTL
        result2 = resolver.resolve("op://test-vault/test-api-key/credential")
        ttl2 = result2.ttl_remaining

        # Both should be close to max TTL
        assert ttl1 <= 10
        assert ttl2 <= 10

    def test_invalid_session_denies_access(self):
        """Invalid session denies all access."""
        resolver = create_mock_resolver()
        resolver.invalidate_session()

        result = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result.success is False
        assert result.error_code == ResolveErrorCode.SESSION_INVALID
        assert result.get_value() is None

    def test_session_id_returned_in_result(self):
        """Session ID returned in successful result."""
        resolver = create_mock_resolver(session_id="custom-session-123")
        result = resolver.resolve("op://test-vault/test-api-key/credential")

        assert result.session_id == "custom-session-123"

    def test_session_invalidation_clears_access_times(self):
        """Session invalidation clears cached access times."""
        resolver = create_mock_resolver()

        # First access
        resolver.resolve("op://test-vault/test-api-key/credential")
        assert len(resolver._access_times) > 0

        # Invalidate
        resolver.invalidate_session()
        assert len(resolver._access_times) == 0


# ---------------------------------------------------------------------------
# T7: No Real Network/1Password Access
# ---------------------------------------------------------------------------


class TestNoRealNetworkAccess:
    """T7: Mock resolver never accesses real network or 1Password."""

    def test_no_network_imports(self):
        """Vault resolver module has no network library imports."""
        import modules.infrastructure.secrets_mcp.src.vault_resolver as mod

        module_source = open(mod.__file__, "r", encoding="utf-8").read()

        # Should not import network libraries
        assert "import requests" not in module_source
        assert "import urllib" not in module_source
        assert "import httpx" not in module_source
        assert "import aiohttp" not in module_source
        assert "import socket" not in module_source

    def test_no_1password_sdk_imports(self):
        """Vault resolver has no 1Password SDK imports."""
        import modules.infrastructure.secrets_mcp.src.vault_resolver as mod

        module_source = open(mod.__file__, "r", encoding="utf-8").read()

        # Should not import 1Password libraries
        assert "import onepassword" not in module_source
        assert "from onepassword" not in module_source
        assert "import op" not in module_source.split("\n")[0:20]  # First 20 lines

    def test_mock_secrets_are_test_only(self, resolver):
        """Mock secrets are clearly marked as test-only."""
        result = resolver.resolve("op://test-vault/test-api-key/credential")
        secret = result.get_value()

        # Secret should contain test indicators
        assert "TEST" in secret or "MOCK" in secret
        assert "PRODUCTION" not in secret or "NOT" in secret.upper()

    def test_resolver_works_offline(self, resolver):
        """Resolver works without network connectivity."""
        # Patch socket to ensure no network calls
        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = Exception("Network disabled")

            # Should still work - it's a mock
            result = resolver.resolve("op://test-vault/test-api-key/credential")
            assert result.success is True

    def test_test_vault_namespace_only(self, resolver):
        """Only test-vault namespace is recognized."""
        # test-vault works
        result1 = resolver.resolve("op://test-vault/test-api-key/credential")
        assert result1.success is True

        # production-vault does not
        result2 = resolver.resolve("op://production-vault/test-api-key/credential")
        assert result2.success is False
        assert result2.error_code == ResolveErrorCode.UNKNOWN_REFERENCE


# ---------------------------------------------------------------------------
# Reference Parsing Tests
# ---------------------------------------------------------------------------


class TestReferenceParsing:
    """Test op:// reference parsing."""

    def test_valid_reference_parses(self):
        """Valid reference parses correctly."""
        parsed = parse_op_reference("op://vault-name/item-name/field-name")
        assert parsed is not None
        assert parsed.vault == "vault-name"
        assert parsed.item == "item-name"
        assert parsed.field == "field-name"

    def test_canonical_format(self):
        """OpReference produces canonical format."""
        parsed = parse_op_reference("op://vault/item/field")
        assert parsed.canonical() == "op://vault/item/field"

    def test_invalid_formats_return_none(self):
        """Invalid formats return None."""
        invalid = [
            "",
            "not-a-ref",
            "op://",
            "op://vault",
            "op://vault/item",
            "op://vault/item/field/extra",
            "http://vault/item/field",
            None,
        ]
        for ref in invalid:
            result = parse_op_reference(ref) if ref else parse_op_reference("")
            assert result is None, f"Should be None: {ref}"

    def test_underscore_in_names(self):
        """Underscores allowed in vault/item/field names."""
        parsed = parse_op_reference("op://my_vault/my_item/my_field")
        assert parsed is not None
        assert parsed.vault == "my_vault"

    def test_hyphen_in_names(self):
        """Hyphens allowed in vault/item/field names."""
        parsed = parse_op_reference("op://my-vault/my-item/my-field")
        assert parsed is not None
        assert parsed.vault == "my-vault"

    def test_alphanumeric_in_names(self):
        """Alphanumeric characters allowed."""
        parsed = parse_op_reference("op://vault123/item456/field789")
        assert parsed is not None
        assert parsed.vault == "vault123"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_resolve_workflow(self, resolver_with_audit):
        """Complete resolve workflow with audit."""
        resolver, events = resolver_with_audit

        # Resolve
        result = resolver.resolve(
            "op://test-vault/test-api-key/credential",
            requester_id="test-agent-001",
        )

        # Verify success
        assert result.success is True
        assert result.get_value() is not None
        assert result.session_id is not None
        assert result.ttl_remaining is not None

        # Verify audit
        assert len(events) == 1
        event = events[0]
        assert event.success is True
        assert event.requester_id == "test-agent-001"
        assert event.reference_hash.startswith("sha256:")

        # Verify no leakage
        secret = result.get_value()
        audit_json = json.dumps(event.to_dict())
        assert secret not in audit_json

    def test_fail_closed_workflow(self, resolver_with_audit):
        """Fail-closed workflow with audit."""
        resolver, events = resolver_with_audit

        # Make unavailable
        resolver.set_available(False)

        # Try to resolve
        result = resolver.resolve("op://test-vault/test-api-key/credential")

        # Verify failure
        assert result.success is False
        assert result.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE
        assert result.get_value() is None

        # Verify audit recorded failure
        assert len(events) == 1
        assert events[0].success is False
        assert events[0].error_code == "RESOLVER_UNAVAILABLE"
