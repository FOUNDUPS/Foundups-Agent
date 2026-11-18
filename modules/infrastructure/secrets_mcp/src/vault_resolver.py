# -*- coding: utf-8 -*-
"""Mock Vault Resolver for Credential Access Layer PoC.

Contract: FOUNDUPS_CREDENTIAL_ACCESS_LAYER_POC_PHASE1
Per WSP_71 Annex A specification.

WSP_97 Labels:
  - CREDENTIAL_ACCESS_POC_ONLY
  - MOCK_VAULT_ONLY
  - NO_REAL_SECRET_ACCESS
  - NO_1PASSWORD_CONFIGURATION
  - FAIL_CLOSED_REQUIRED
  - SECRET_VALUE_NEVER_LOGGED
  - AUDIT_HASH_ONLY
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OP_REFERENCE_PATTERN = re.compile(
    r"^op://(?P<vault>[a-zA-Z0-9_-]+)/(?P<item>[a-zA-Z0-9_-]+)/(?P<field>[a-zA-Z0-9_-]+)$"
)

DEFAULT_TTL_SECONDS = 300  # 5 minutes per WSP_71 Annex A


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


class ResolveErrorCode(Enum):
    """Error codes for credential resolution failures."""

    INVALID_REFERENCE = "INVALID_REFERENCE"
    UNKNOWN_REFERENCE = "UNKNOWN_REFERENCE"
    RESOLVER_UNAVAILABLE = "RESOLVER_UNAVAILABLE"
    TTL_EXPIRED = "TTL_EXPIRED"
    SESSION_INVALID = "SESSION_INVALID"
    COMMAND_FAILED = "COMMAND_FAILED"
    OUTPUT_TOO_LARGE = "OUTPUT_TOO_LARGE"


@dataclass(frozen=True)
class OpReference:
    """Parsed op:// reference."""

    vault: str
    item: str
    field: str
    raw: str

    def canonical(self) -> str:
        """Return canonical reference string."""
        return f"op://{self.vault}/{self.item}/{self.field}"


@dataclass
class ResolveResult:
    """Result of a credential resolution attempt."""

    success: bool
    reference: str
    reference_hash: str
    error_code: Optional[ResolveErrorCode] = None
    error_message: Optional[str] = None
    ttl_remaining: Optional[int] = None
    session_id: Optional[str] = None
    _secret_value: Optional[str] = field(default=None, repr=False)

    def get_value(self) -> Optional[str]:
        """Get secret value (internal use only, never log this)."""
        return self._secret_value

    def to_audit_dict(self) -> Dict[str, Any]:
        """Return audit-safe dictionary (no secret value)."""
        return {
            "success": self.success,
            "reference": self.reference,
            "reference_hash": self.reference_hash,
            "error_code": self.error_code.value if self.error_code else None,
            "error_message": self.error_message,
            "ttl_remaining": self.ttl_remaining,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@dataclass
class AuditEvent:
    """Audit event for credential access (hash-only, no secret values)."""

    event_type: str
    reference: str
    reference_hash: str
    session_id: Optional[str]
    success: bool
    error_code: Optional[str]
    timestamp: str
    ttl_applied: Optional[int] = None
    requester_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "event_type": self.event_type,
            "reference": self.reference,
            "reference_hash": self.reference_hash,
            "session_id": self.session_id,
            "success": self.success,
            "error_code": self.error_code,
            "timestamp": self.timestamp,
            "ttl_applied": self.ttl_applied,
            "requester_id": self.requester_id,
        }


# ---------------------------------------------------------------------------
# Reference Parsing
# ---------------------------------------------------------------------------


def parse_op_reference(reference: str) -> Optional[OpReference]:
    """Parse an op:// reference string.

    Args:
        reference: String in format op://vault/item/field

    Returns:
        OpReference if valid, None if invalid format
    """
    if not reference or not isinstance(reference, str):
        return None

    match = OP_REFERENCE_PATTERN.match(reference.strip())
    if not match:
        return None

    return OpReference(
        vault=match.group("vault"),
        item=match.group("item"),
        field=match.group("field"),
        raw=reference.strip(),
    )


def hash_reference(reference: str) -> str:
    """Create SHA-256 hash of reference for audit logging.

    Args:
        reference: The op:// reference string

    Returns:
        Hash in format sha256:{first_16_chars}
    """
    digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def hash_secret(value: str) -> str:
    """Create SHA-256 hash of secret value for rotation detection.

    NEVER log the actual value - only the hash.

    Args:
        value: The secret value (never log this)

    Returns:
        Hash in format sha256:{full_digest}
    """
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# Mock Vault Resolver
# ---------------------------------------------------------------------------


class MockVaultResolver:
    """Mock vault resolver for PoC testing.

    CRITICAL CONSTRAINTS:
    - Only resolves known test references
    - Never connects to real 1Password
    - Fails closed on any error
    - Never logs secret values
    - Enforces TTL/session boundaries

    Test references use format:
        op://test-vault/test-item/test-field
    """

    # Test-only references (not real secrets)
    _TEST_SECRETS: Dict[str, str] = {
        "op://test-vault/test-api-key/credential": "TEST_VALUE_DO_NOT_USE_IN_PRODUCTION",
        "op://test-vault/test-database/password": "TEST_DB_PW_MOCK_ONLY",
        "op://test-vault/test-service/token": "TEST_TOKEN_MOCK_RESOLVER",
    }

    def __init__(
        self,
        available: bool = True,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        session_id: Optional[str] = None,
        audit_callback: Optional[Callable[[AuditEvent], None]] = None,
    ):
        """Initialize mock resolver.

        Args:
            available: Whether resolver is available (for testing fail-closed)
            ttl_seconds: TTL for resolved credentials
            session_id: Session identifier for boundary enforcement
            audit_callback: Optional callback for audit events
        """
        self._available = available
        self._ttl_seconds = ttl_seconds
        self._session_id = session_id or f"mock-session-{int(time.time())}"
        self._audit_callback = audit_callback
        self._session_start = time.time()
        self._access_times: Dict[str, float] = {}

    def is_available(self) -> bool:
        """Check if resolver is available."""
        return self._available

    def set_available(self, available: bool) -> None:
        """Set resolver availability (for testing)."""
        self._available = available

    def get_session_id(self) -> str:
        """Get current session ID."""
        return self._session_id

    def invalidate_session(self) -> None:
        """Invalidate current session (for testing)."""
        self._session_id = ""
        self._access_times.clear()

    def _emit_audit(
        self,
        event_type: str,
        reference: str,
        success: bool,
        error_code: Optional[ResolveErrorCode] = None,
        ttl_applied: Optional[int] = None,
        requester_id: Optional[str] = None,
    ) -> AuditEvent:
        """Emit audit event (hash-only, never log secret values)."""
        event = AuditEvent(
            event_type=event_type,
            reference=reference,
            reference_hash=hash_reference(reference),
            session_id=self._session_id,
            success=success,
            error_code=error_code.value if error_code else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ttl_applied=ttl_applied,
            requester_id=requester_id,
        )
        if self._audit_callback:
            self._audit_callback(event)
        return event

    def _check_ttl(self, reference: str) -> Tuple[bool, Optional[int]]:
        """Check if TTL is valid for reference.

        Returns:
            Tuple of (is_valid, remaining_seconds)
        """
        if reference not in self._access_times:
            return True, self._ttl_seconds

        last_access = self._access_times[reference]
        elapsed = time.time() - last_access
        remaining = self._ttl_seconds - int(elapsed)

        if remaining <= 0:
            return False, 0

        return True, remaining

    def resolve(
        self,
        reference: str,
        requester_id: Optional[str] = None,
    ) -> ResolveResult:
        """Resolve an op:// reference to its secret value.

        FAIL-CLOSED BEHAVIOR:
        - Invalid reference format → error
        - Unknown reference → error
        - Resolver unavailable → error
        - TTL expired → error
        - Session invalid → error

        Args:
            reference: The op:// reference string
            requester_id: Optional identifier for audit trail

        Returns:
            ResolveResult with success/failure and (if success) the secret value
        """
        ref_hash = hash_reference(reference)

        # Fail closed: resolver unavailable
        if not self._available:
            self._emit_audit(
                "resolve_attempt",
                reference,
                success=False,
                error_code=ResolveErrorCode.RESOLVER_UNAVAILABLE,
                requester_id=requester_id,
            )
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=ref_hash,
                error_code=ResolveErrorCode.RESOLVER_UNAVAILABLE,
                error_message="Vault resolver is unavailable. Access denied.",
                session_id=self._session_id,
            )

        # Fail closed: invalid session
        if not self._session_id:
            self._emit_audit(
                "resolve_attempt",
                reference,
                success=False,
                error_code=ResolveErrorCode.SESSION_INVALID,
                requester_id=requester_id,
            )
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=ref_hash,
                error_code=ResolveErrorCode.SESSION_INVALID,
                error_message="Session invalid. Access denied.",
            )

        # Fail closed: invalid reference format
        parsed = parse_op_reference(reference)
        if not parsed:
            self._emit_audit(
                "resolve_attempt",
                reference,
                success=False,
                error_code=ResolveErrorCode.INVALID_REFERENCE,
                requester_id=requester_id,
            )
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=ref_hash,
                error_code=ResolveErrorCode.INVALID_REFERENCE,
                error_message=f"Invalid reference format: {reference}",
                session_id=self._session_id,
            )

        # Check TTL
        ttl_valid, ttl_remaining = self._check_ttl(reference)
        if not ttl_valid:
            self._emit_audit(
                "resolve_attempt",
                reference,
                success=False,
                error_code=ResolveErrorCode.TTL_EXPIRED,
                requester_id=requester_id,
            )
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=ref_hash,
                error_code=ResolveErrorCode.TTL_EXPIRED,
                error_message="Credential TTL expired. Re-authentication required.",
                ttl_remaining=0,
                session_id=self._session_id,
            )

        # Fail closed: unknown reference
        canonical = parsed.canonical()
        if canonical not in self._TEST_SECRETS:
            self._emit_audit(
                "resolve_attempt",
                reference,
                success=False,
                error_code=ResolveErrorCode.UNKNOWN_REFERENCE,
                requester_id=requester_id,
            )
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=ref_hash,
                error_code=ResolveErrorCode.UNKNOWN_REFERENCE,
                error_message=f"Unknown reference: {canonical}",
                session_id=self._session_id,
            )

        # Success: resolve test secret
        self._access_times[reference] = time.time()
        secret_value = self._TEST_SECRETS[canonical]

        self._emit_audit(
            "resolve_success",
            reference,
            success=True,
            ttl_applied=self._ttl_seconds,
            requester_id=requester_id,
        )

        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=ref_hash,
            ttl_remaining=ttl_remaining,
            session_id=self._session_id,
            _secret_value=secret_value,
        )


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def create_mock_resolver(
    available: bool = True,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    session_id: Optional[str] = None,
    audit_callback: Optional[Callable[[AuditEvent], None]] = None,
) -> MockVaultResolver:
    """Create a mock vault resolver for testing.

    Args:
        available: Whether resolver should be available
        ttl_seconds: TTL for resolved credentials
        session_id: Optional session identifier
        audit_callback: Optional callback for audit events

    Returns:
        Configured MockVaultResolver instance
    """
    return MockVaultResolver(
        available=available,
        ttl_seconds=ttl_seconds,
        session_id=session_id,
        audit_callback=audit_callback,
    )


def get_test_references() -> Dict[str, str]:
    """Get list of valid test references (not values).

    Returns dictionary mapping reference to description (not actual value).
    """
    return {
        "op://test-vault/test-api-key/credential": "Test API key reference",
        "op://test-vault/test-database/password": "Test database password reference",
        "op://test-vault/test-service/token": "Test service token reference",
    }
