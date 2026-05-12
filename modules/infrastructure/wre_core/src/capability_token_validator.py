#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capability Token Validation Service (Phase 1)

HXA26 moves token validation from test-only (HXA21) to production code structure.
This module provides the CapabilityToken model, TokenValidationResult, and
CapabilityTokenValidator that can be injected into HermesJobExecutor.

WSP 97 Truth Boundaries:
  - This is Phase 1: test infrastructure only
  - No real secrets or signing keys
  - No external network calls
  - No production token issuance
  - All tokens are dry-run-only by default

Key Principle: FAIL-CLOSED
  - Missing token -> invalid
  - Missing signature -> invalid
  - Signature not verified -> invalid
  - Expired token -> invalid
  - Wrong audience -> invalid
  - Replayed nonce -> invalid
  - Action not allowed -> invalid
  - Scope not allowed -> invalid
  - Path outside allowed roots -> invalid
  - Blocked path -> invalid
  - dry_run_only token cannot authorize live operation

Slice: HXA26_TOKEN_VALIDATION_SERVICE_PHASE1
Worker: 0102
"""

from __future__ import annotations

import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set


# ===========================================================================
# SECTION 1: Token Validation Reason Codes
# ===========================================================================


class TokenValidationReasonCode(str, Enum):
    """Machine-readable token validation reason codes."""

    # Valid
    VALID = "VALID"
    VALID_DRY_RUN_ONLY = "VALID_DRY_RUN_ONLY"

    # Invalid - Missing Fields
    MISSING_TOKEN = "MISSING_TOKEN"
    MISSING_SIGNATURE = "MISSING_SIGNATURE"
    SIGNATURE_NOT_VERIFIED = "SIGNATURE_NOT_VERIFIED"

    # Invalid - Temporal
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_NOT_YET_VALID = "TOKEN_NOT_YET_VALID"

    # Invalid - Identity
    WRONG_AUDIENCE = "WRONG_AUDIENCE"
    WRONG_ISSUER = "WRONG_ISSUER"
    WRONG_SUBJECT = "WRONG_SUBJECT"

    # Invalid - Replay Protection
    REPLAY_DETECTED = "REPLAY_DETECTED"
    NONCE_MISSING = "NONCE_MISSING"

    # Invalid - Authorization
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    SCOPE_NOT_ALLOWED = "SCOPE_NOT_ALLOWED"
    PATH_OUTSIDE_ALLOWED_ROOTS = "PATH_OUTSIDE_ALLOWED_ROOTS"
    PATH_IN_BLOCKED_LIST = "PATH_IN_BLOCKED_LIST"

    # Invalid - Execution Mode
    DRY_RUN_ONLY_BLOCKS_LIVE = "DRY_RUN_ONLY_BLOCKS_LIVE"


# ===========================================================================
# SECTION 2: Capability Token Model
# ===========================================================================


@dataclass
class CapabilityToken:
    """
    Capability token model for authorization of destructive actions.

    This model defines the contract for capability tokens used by:
    - Repo creation (HXA19)
    - Production source modification (HXA20)
    - Destructive action guard (HXA22)
    - D3+ sandbox execution (HXA25)

    WSP 97: Phase 1 tokens are test-only. No real secrets, no real signing.
    """

    # === Identity ===
    token_id: str
    """Unique token identifier. Format: cap_{timestamp_hex}_{random_hex}"""

    issuer: str
    """Token issuer identity. Example: "wre-local-test-issuer"."""

    subject: str
    """Token subject (who the token is for). Example: "agent_0102"."""

    audience: str
    """Intended audience. Example: "wre-local"."""

    # === Authorization ===
    scopes: List[str] = field(default_factory=list)
    """Granted scopes. Example: ["repo:read", "source:dry-run"]."""

    allowed_actions: List[str] = field(default_factory=list)
    """Allowed actions. Example: ["build_foundup", "validate_foundup"]."""

    allowed_paths: List[str] = field(default_factory=list)
    """Allowed path roots. Example: ["/tmp/test", "modules/foundups"]."""

    blocked_paths: List[str] = field(default_factory=list)
    """Blocked paths (override allowed). Example: [".env", "secrets/"]."""

    # === Execution Mode ===
    dry_run_only: bool = True
    """If True, this token CANNOT authorize live operations. Default: True (safe)."""

    # === Temporal Validity ===
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """Token issuance timestamp."""

    expires_at: Optional[datetime] = None
    """Token expiration timestamp. None = no expiry (but short-lived preferred)."""

    # === Replay Protection ===
    nonce: str = field(default_factory=lambda: secrets.token_hex(16))
    """Unique nonce to prevent token replay. Must be checked against registry."""

    # === Signature (Phase 1: Fake for Testing) ===
    signature_present: bool = False
    """Whether a signature is present (not the actual signature)."""

    signature_verified: bool = False
    """Whether signature verification passed (fake verification in Phase 1)."""

    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.expires_at is None:
            return False  # No expiry set
        now = datetime.now(timezone.utc)
        return now > self.expires_at

    def is_not_yet_valid(self) -> bool:
        """Check if token is not yet valid (issued in future)."""
        now = datetime.now(timezone.utc)
        return self.issued_at > now

    def action_allowed(self, requested_action: str) -> bool:
        """Check if requested action is in allowed_actions list."""
        if not self.allowed_actions:
            return False  # Fail-closed: no actions = none allowed
        return requested_action in self.allowed_actions

    def scope_allowed(self, requested_scope: str) -> bool:
        """Check if requested scope is in scopes list."""
        if not self.scopes:
            return False  # Fail-closed: no scopes = none allowed
        return requested_scope in self.scopes

    def path_allowed(self, target_path: str) -> bool:
        """
        Check if target path is within allowed roots and not blocked.

        Fail-closed: empty allowed_paths = no paths allowed.
        Blocked paths override allowed paths.
        """
        if not target_path:
            return False

        # Normalize path
        normalized = os.path.normpath(target_path).replace("\\", "/")

        # Check blocked paths first (override)
        for blocked in self.blocked_paths:
            blocked_clean = os.path.normpath(blocked).replace("\\", "/")
            if normalized == blocked_clean:
                return False
            if normalized.startswith(blocked_clean + "/"):
                return False
            # Check filename patterns (e.g., ".env")
            if "/" not in blocked_clean:
                if normalized.endswith("/" + blocked_clean) or normalized == blocked_clean:
                    return False
                # Check if filename component matches
                basename = os.path.basename(normalized)
                if basename == blocked_clean:
                    return False

        # Check allowed paths
        if not self.allowed_paths:
            return False  # Fail-closed: empty allowed = all blocked

        for allowed_root in self.allowed_paths:
            allowed_clean = os.path.normpath(allowed_root).replace("\\", "/")
            if normalized.startswith(allowed_clean + "/") or normalized == allowed_clean:
                return True

        return False

    def redacted_repr(self) -> str:
        """
        Return a redacted string representation for logging.

        NEVER include full token_id, nonce, or any sensitive fields.
        """
        token_id_prefix = self.token_id[:8] if len(self.token_id) >= 8 else "REDACTED"
        return (
            f"CapabilityToken(id={token_id_prefix}..., "
            f"issuer={self.issuer}, "
            f"subject={self.subject}, "
            f"dry_run_only={self.dry_run_only}, "
            f"expired={self.is_expired()}, "
            f"signature_verified={self.signature_verified})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging (redacted for security)."""
        token_id_prefix = self.token_id[:8] if len(self.token_id) >= 8 else "REDACTED"
        return {
            "token_id": f"{token_id_prefix}...",
            "issuer": self.issuer,
            "subject": self.subject,
            "audience": self.audience,
            "scopes": self.scopes,
            "allowed_actions": self.allowed_actions,
            "allowed_paths_count": len(self.allowed_paths),
            "blocked_paths_count": len(self.blocked_paths),
            "dry_run_only": self.dry_run_only,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "nonce": "REDACTED",  # Never expose nonce
            "signature_present": self.signature_present,
            "signature_verified": self.signature_verified,
        }


# ===========================================================================
# SECTION 3: Token Validation Result
# ===========================================================================


@dataclass
class TokenValidationResult:
    """
    Result of capability token validation.

    WSP 97 Truth: Returns explicit validation status with all failure reasons.
    Validation does NOT imply verification_complete, cabr_ready, or payout_ready.
    """

    # === Validation Status ===
    token_valid: bool = False
    """Whether token passes all validation checks."""

    reason_code: TokenValidationReasonCode = TokenValidationReasonCode.MISSING_TOKEN
    """Primary validation failure reason code."""

    # === Field Validation ===
    missing_fields: List[str] = field(default_factory=list)
    """List of missing required fields."""

    denied_scopes: List[str] = field(default_factory=list)
    """List of requested scopes that were denied."""

    # === Temporal Validation ===
    expired: bool = False
    """Whether token has expired."""

    # === Replay Validation ===
    replay_detected: bool = False
    """Whether nonce was already used (replay attack)."""

    # === Authorization Validation ===
    action_allowed: bool = False
    """Whether requested action is allowed by token."""

    path_allowed: bool = False
    """Whether requested path is allowed by token."""

    # === Live Operation Block ===
    dry_run_only_blocked_live: bool = False
    """True if dry_run_only token tried to authorize live operation."""

    # === WSP 97 Truth Fields (ALWAYS False at validation time) ===
    verification_complete: bool = False
    """WSP 97: Always False. Token validation does NOT imply verification."""

    cabr_ready: bool = False
    """WSP 97: Always False. Token does NOT enable CABR claims."""

    payout_ready: bool = False
    """WSP 97: Always False. Token does NOT enable payout claims."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/API response."""
        return {
            "token_valid": self.token_valid,
            "reason_code": self.reason_code.value,
            "missing_fields": self.missing_fields,
            "denied_scopes": self.denied_scopes,
            "expired": self.expired,
            "replay_detected": self.replay_detected,
            "action_allowed": self.action_allowed,
            "path_allowed": self.path_allowed,
            "dry_run_only_blocked_live": self.dry_run_only_blocked_live,
            # WSP 97 Truth: Always False at validation time
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
        }


# ===========================================================================
# SECTION 4: Token Validator Protocol (Interface)
# ===========================================================================


class ICapabilityTokenValidator(Protocol):
    """
    Interface for capability token validators.

    Allows different implementations:
    - LocalCapabilityTokenValidator (Phase 1 - in-memory, no real crypto)
    - JWTCapabilityTokenValidator (future - real JWT validation)
    - ExternalCapabilityTokenValidator (future - external token service)
    """

    def validate_token(
        self,
        token: Optional[CapabilityToken],
        requested_action: Optional[str] = None,
        requested_scope: Optional[str] = None,
        target_path: Optional[str] = None,
        is_live_operation: bool = False,
    ) -> TokenValidationResult:
        """Validate a capability token for a requested operation."""
        ...

    def register_nonce(self, nonce: str) -> bool:
        """Register a nonce to prevent replay. Returns True if new, False if replay."""
        ...

    def clear_nonces(self) -> None:
        """Clear the nonce registry (for testing)."""
        ...


# ===========================================================================
# SECTION 5: Local Capability Token Validator (Phase 1)
# ===========================================================================


class LocalCapabilityTokenValidator:
    """
    Local capability token validator with in-memory nonce registry.

    This validator NEVER makes external calls or uses real crypto.
    It is Phase 1 infrastructure for validating the token contract.

    WSP 97: This is Phase 1 infrastructure. NOT for production live operations.
    """

    def __init__(
        self,
        expected_audience: str = "wre-local",
        expected_issuer: str = "wre-local-test-issuer",
    ):
        """
        Initialize the validator.

        Args:
            expected_audience: Expected audience for valid tokens
            expected_issuer: Expected issuer for valid tokens
        """
        self.expected_audience = expected_audience
        self.expected_issuer = expected_issuer
        self.used_nonces: Set[str] = set()

    def register_nonce(self, nonce: str) -> bool:
        """
        Register a nonce to prevent replay.

        Args:
            nonce: The nonce to register

        Returns:
            True if nonce is new (first use), False if replay detected
        """
        if nonce in self.used_nonces:
            return False
        self.used_nonces.add(nonce)
        return True

    def clear_nonces(self) -> None:
        """Clear the nonce registry (for testing)."""
        self.used_nonces.clear()

    def validate_token(
        self,
        token: Optional[CapabilityToken],
        requested_action: Optional[str] = None,
        requested_scope: Optional[str] = None,
        target_path: Optional[str] = None,
        is_live_operation: bool = False,
    ) -> TokenValidationResult:
        """
        Validate a capability token for a requested operation.

        Fail-closed validation:
          - Missing token -> invalid
          - Missing signature -> invalid
          - Signature not verified -> invalid
          - Expired token -> invalid
          - Wrong audience -> invalid
          - Replayed nonce -> invalid
          - Requested action not in allowed_actions -> invalid
          - Requested scope not in scopes -> invalid
          - Target path outside allowed_paths -> invalid
          - Target path in blocked_paths -> invalid
          - dry_run_only token cannot authorize live operation

        Args:
            token: CapabilityToken to validate (None = missing token)
            requested_action: Action to authorize (optional)
            requested_scope: Scope to check (optional)
            target_path: Path to authorize (optional)
            is_live_operation: If True, dry_run_only tokens are rejected

        Returns:
            TokenValidationResult with validation status and details

        WSP 97: This does NOT perform real signature verification in Phase 1.
        """
        # Gate 1: Missing token
        if token is None:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.MISSING_TOKEN,
                missing_fields=["token"],
            )

        # Gate 2: Missing signature
        if not token.signature_present:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.MISSING_SIGNATURE,
                missing_fields=["signature"],
            )

        # Gate 3: Signature not verified
        if not token.signature_verified:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.SIGNATURE_NOT_VERIFIED,
            )

        # Gate 4: Token expired
        if token.is_expired():
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.TOKEN_EXPIRED,
                expired=True,
            )

        # Gate 5: Token not yet valid
        if token.is_not_yet_valid():
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.TOKEN_NOT_YET_VALID,
            )

        # Gate 6: Wrong audience
        if token.audience != self.expected_audience:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.WRONG_AUDIENCE,
            )

        # Gate 7: Wrong issuer
        if token.issuer != self.expected_issuer:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.WRONG_ISSUER,
            )

        # Gate 8: Nonce replay check
        if not token.nonce:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.NONCE_MISSING,
                missing_fields=["nonce"],
            )

        if token.nonce in self.used_nonces:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.REPLAY_DETECTED,
                replay_detected=True,
            )

        # Gate 9: Action allowed (if requested)
        action_allowed_result = True
        if requested_action is not None:
            action_allowed_result = token.action_allowed(requested_action)
            if not action_allowed_result:
                return TokenValidationResult(
                    token_valid=False,
                    reason_code=TokenValidationReasonCode.ACTION_NOT_ALLOWED,
                    action_allowed=False,
                )

        # Gate 10: Scope allowed (if requested)
        denied_scopes: List[str] = []
        if requested_scope is not None:
            if not token.scope_allowed(requested_scope):
                denied_scopes.append(requested_scope)
                return TokenValidationResult(
                    token_valid=False,
                    reason_code=TokenValidationReasonCode.SCOPE_NOT_ALLOWED,
                    denied_scopes=denied_scopes,
                )

        # Gate 11: Path allowed (if requested)
        path_allowed_result = True
        if target_path is not None:
            path_allowed_result = token.path_allowed(target_path)
            if not path_allowed_result:
                # Determine if it's blocked or outside allowed roots
                normalized = os.path.normpath(target_path).replace("\\", "/")
                blocked_explicitly = False
                for blocked in token.blocked_paths:
                    blocked_clean = os.path.normpath(blocked).replace("\\", "/")
                    if normalized == blocked_clean or normalized.startswith(blocked_clean + "/"):
                        blocked_explicitly = True
                        break
                    if "/" not in blocked_clean and os.path.basename(normalized) == blocked_clean:
                        blocked_explicitly = True
                        break

                if blocked_explicitly:
                    return TokenValidationResult(
                        token_valid=False,
                        reason_code=TokenValidationReasonCode.PATH_IN_BLOCKED_LIST,
                        path_allowed=False,
                    )
                else:
                    return TokenValidationResult(
                        token_valid=False,
                        reason_code=TokenValidationReasonCode.PATH_OUTSIDE_ALLOWED_ROOTS,
                        path_allowed=False,
                    )

        # Gate 12: dry_run_only blocks live operation
        if is_live_operation and token.dry_run_only:
            return TokenValidationResult(
                token_valid=False,
                reason_code=TokenValidationReasonCode.DRY_RUN_ONLY_BLOCKS_LIVE,
                dry_run_only_blocked_live=True,
            )

        # All gates passed - register nonce to prevent replay
        self.used_nonces.add(token.nonce)

        # Determine result code
        if token.dry_run_only:
            reason_code = TokenValidationReasonCode.VALID_DRY_RUN_ONLY
        else:
            reason_code = TokenValidationReasonCode.VALID

        return TokenValidationResult(
            token_valid=True,
            reason_code=reason_code,
            action_allowed=action_allowed_result,
            path_allowed=path_allowed_result,
            # WSP 97 Truth: Always False
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )


# ===========================================================================
# SECTION 6: Token Issuer (Phase 1 - Test Only)
# ===========================================================================


class LocalCapabilityTokenIssuer:
    """
    Local token issuer for test infrastructure.

    This issuer NEVER uses real secrets or signing keys.
    All tokens are fake/test-only for validating the token shape contract.

    WSP 97: This is Phase 1 test infrastructure. NOT for production use.
    """

    def __init__(self, issuer_id: str = "wre-local-test-issuer"):
        """
        Initialize the issuer.

        Args:
            issuer_id: Issuer identity string
        """
        self.issuer_id = issuer_id
        self.issued_tokens: List[str] = []

    def issue_token(
        self,
        subject: str,
        audience: str,
        scopes: Optional[List[str]] = None,
        allowed_actions: Optional[List[str]] = None,
        allowed_paths: Optional[List[str]] = None,
        blocked_paths: Optional[List[str]] = None,
        dry_run_only: bool = True,
        validity_duration: timedelta = timedelta(hours=1),
    ) -> CapabilityToken:
        """
        Issue a test token.

        Args:
            subject: Token subject (who the token is for)
            audience: Intended audience
            scopes: Granted scopes
            allowed_actions: Allowed actions
            allowed_paths: Allowed path roots
            blocked_paths: Blocked paths
            dry_run_only: If True, token cannot authorize live operations
            validity_duration: How long the token is valid

        Returns:
            CapabilityToken with fake signature

        WSP 97: This does NOT create a real signed token.
        """
        now = datetime.now(timezone.utc)
        token_id = f"cap_{secrets.token_hex(4)}_{secrets.token_hex(4)}"

        token = CapabilityToken(
            token_id=token_id,
            issuer=self.issuer_id,
            subject=subject,
            audience=audience,
            scopes=scopes or [],
            allowed_actions=allowed_actions or [],
            allowed_paths=allowed_paths or [],
            blocked_paths=blocked_paths or [],
            dry_run_only=dry_run_only,
            issued_at=now,
            expires_at=now + validity_duration,
            nonce=secrets.token_hex(16),
            signature_present=True,  # Fake signature
            signature_verified=True,  # Fake verification
        )

        self.issued_tokens.append(token.token_id)
        return token


# ===========================================================================
# SECTION 7: Default Validator Instance
# ===========================================================================


# Default validator instance for injection
_default_validator: Optional[LocalCapabilityTokenValidator] = None


def get_default_validator() -> LocalCapabilityTokenValidator:
    """
    Get the default validator instance.

    Returns:
        LocalCapabilityTokenValidator singleton instance
    """
    global _default_validator
    if _default_validator is None:
        _default_validator = LocalCapabilityTokenValidator()
    return _default_validator


def reset_default_validator() -> None:
    """
    Reset the default validator instance (for testing).
    """
    global _default_validator
    _default_validator = None


# ===========================================================================
# SECTION 8: Action Class Scope Mappings (HXA29)
# ===========================================================================


# Map action classes to their authorized scopes
# D3 scopes authorize ONLY D3 actions (sandbox/evidence/dry-run)
# D4 scopes authorize D4 actions (repo/source/git) but blocked by guard
# D5 scopes authorize D5 actions (external/api) but blocked by guard
# D6 scopes authorize D6 actions (delete/irreversible) but blocked by guard
ACTION_CLASS_SCOPES: Dict[str, List[str]] = {
    "D0_OBSERVE": ["d0:observe", "d0:read", "d0:status"],
    "D1_READ": ["d1:read", "d1:fetch", "d1:load"],
    "D2_SIMULATE": ["d2:simulate", "d2:plan", "d2:preview"],
    "D3_WRITE_SANDBOX": ["d3:sandbox", "d3:evidence", "d3:dry-run"],
    "D4_WRITE_REPO": ["d4:repo", "d4:source", "d4:git"],
    "D5_EXTERNAL_SIDE_EFFECT": ["d5:external", "d5:api", "d5:webhook"],
    "D6_IRREVERSIBLE": ["d6:delete", "d6:irreversible", "d6:payout"],
}


# Reverse mapping: scope -> action class
SCOPE_TO_ACTION_CLASS: Dict[str, str] = {}
for action_class, scopes in ACTION_CLASS_SCOPES.items():
    for scope in scopes:
        SCOPE_TO_ACTION_CLASS[scope] = action_class


def validate_scope_for_action_class(
    scope: str,
    action_class: Any,  # DestructiveActionClass from destructive_action_guard
) -> bool:
    """
    Validate that a scope authorizes a specific action class.

    HXA29 Scope Validation Rules:
      - D3 scopes (d3:sandbox, d3:evidence, d3:dry-run) authorize ONLY D3 actions
      - D3 scopes do NOT authorize D4/D5/D6 actions
      - D4 scopes authorize D4 actions (but guard still blocks in Phase 1)
      - D5 scopes authorize D5 actions (but guard still blocks in Phase 1)
      - D6 scopes authorize D6 actions (but guard still blocks in Phase 1)
      - Unknown scopes fail closed (return False)

    Key Principle: Scope authorization is separate from guard policy.
    Even if scope authorizes action, guard may still block in Phase 1.

    Args:
        scope: The scope string to validate (e.g., "d3:sandbox")
        action_class: The DestructiveActionClass being requested

    Returns:
        True if scope authorizes the action class, False otherwise

    Example:
        >>> validate_scope_for_action_class("d3:sandbox", DestructiveActionClass.D3_WRITE_SANDBOX)
        True
        >>> validate_scope_for_action_class("d3:sandbox", DestructiveActionClass.D4_WRITE_REPO)
        False
    """
    # Fail-closed: unknown scope does not authorize any action
    if scope not in SCOPE_TO_ACTION_CLASS:
        return False

    # Get the action class that this scope authorizes
    authorized_class = SCOPE_TO_ACTION_CLASS[scope]

    # Get the requested action class name
    # Handle both enum and string
    if hasattr(action_class, "value"):
        requested_class = action_class.value
    else:
        requested_class = str(action_class)

    # Scope only authorizes its own action class
    # D3 scopes do NOT authorize D4/D5/D6
    return authorized_class == requested_class
