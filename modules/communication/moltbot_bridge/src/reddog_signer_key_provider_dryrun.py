"""RedDog signer key provider boundary.

Slice: REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_PHASE1

This module validates the signer key-provider contract with an injected
WSP-71-like resolver. It can construct an ``Ed25519SignerBackend`` only when
the caller explicitly selects a supported provider mode and supplies a fresh
permission snapshot. It does not connect to a vault by itself, read environment
variables, load files, bind sockets, spawn processes, mutate repository state,
enqueue OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_public_key,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
    Ed25519SignerBackend,
    SignerAuditMacBuilder,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    architect_proposal_replay_store_binding_digest,
    architect_proposal_signer_policy_digest,
    architect_proposal_signer_instance_id,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    AtomicProposalAuthenticityNonceStore,
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    ControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveResult,
    hash_reference,
    parse_op_reference,
)


PROVIDER_MODE_TEST_ONLY_DRYRUN = "TEST_ONLY_DRYRUN"
PROVIDER_MODE_WSP71_PERMISSIONED = "WSP71_PERMISSIONED"

FAIL_PROVIDER_PROFILE_INVALID = "FAIL_PROVIDER_PROFILE_INVALID"
FAIL_PROVIDER_PERMISSION_DENIED = "FAIL_PROVIDER_PERMISSION_DENIED"
FAIL_PROVIDER_RESOLVER_UNAVAILABLE = "FAIL_PROVIDER_RESOLVER_UNAVAILABLE"
FAIL_PROVIDER_REFERENCE_INVALID = "FAIL_PROVIDER_REFERENCE_INVALID"
FAIL_PROVIDER_REFERENCE_FORBIDDEN = "FAIL_PROVIDER_REFERENCE_FORBIDDEN"
FAIL_PROVIDER_TTL_EXPIRED = "FAIL_PROVIDER_TTL_EXPIRED"
FAIL_PROVIDER_KEY_FORMAT = "FAIL_PROVIDER_KEY_FORMAT"
FAIL_PROVIDER_PUBLIC_KEY_MISMATCH = "FAIL_PROVIDER_PUBLIC_KEY_MISMATCH"
FAIL_PROVIDER_FINGERPRINT_MISMATCH = "FAIL_PROVIDER_FINGERPRINT_MISMATCH"
FAIL_PROVIDER_AUDIT_KEY_MISSING = "FAIL_PROVIDER_AUDIT_KEY_MISSING"
FAIL_PROVIDER_MOCK_IN_PRODUCTION = "FAIL_PROVIDER_MOCK_IN_PRODUCTION"

SIGNING_KEY_PREFIX = "ed25519-private-raw-b64-v1:"
AUDIT_KEY_PREFIX = "audit-mac-test-key-b64-v1:"
ED25519_PRIVATE_KEY_BYTES = 32
MIN_AUDIT_KEY_BYTES = 16


class SignerKeyResolver(Protocol):
    """Injected WSP 71-like resolver boundary."""

    def resolve(self, reference: str, requester_id: Optional[str] = None) -> ResolveResult:
        """Resolve an op:// reference or return a fail-closed result."""


@dataclass(frozen=True)
class SignerKeyProviderProfile:
    """Signer-owned key-provider profile for the dry-run provider."""

    signer_profile_id: str
    signer_agent_id: str
    signing_key_ref: str
    audit_mac_key_ref: str
    expected_public_key: str
    expected_key_fingerprint: str
    expected_key_epoch: str
    permission_snapshot_digest: str
    ttl_seconds: int


@dataclass(frozen=True)
class SignerKeyProviderDryRunResult:
    """Dry-run provider result. ``backend`` is intentionally non-serializable."""

    ok: bool
    rejection_code: Optional[str]
    signer_profile_id: str
    key_epoch: Optional[str]
    public_key: Optional[str]
    key_fingerprint: Optional[str]
    signing_key_ref_hash: Optional[str]
    audit_mac_key_ref_hash: Optional[str]
    ttl_remaining_seconds: Optional[int]
    secret_values_returned: bool
    backend: Optional[Ed25519SignerBackend] = field(default=None, repr=False, compare=False)

    def to_receipt(self) -> dict[str, Any]:
        """Return an audit-safe receipt with no backend or secret values."""

        return {
            "ok": self.ok,
            "rejection_code": self.rejection_code,
            "signer_profile_id": self.signer_profile_id,
            "key_epoch": self.key_epoch,
            "public_key": self.public_key,
            "key_fingerprint": self.key_fingerprint,
            "reference_hashes": {
                "signing_key_ref_hash": self.signing_key_ref_hash,
                "audit_mac_key_ref_hash": self.audit_mac_key_ref_hash,
            },
            "ttl_remaining_seconds": self.ttl_remaining_seconds,
            "secret_values_returned": False,
        }


@dataclass(frozen=True)
class _HmacAuditMacBuilder(SignerAuditMacBuilder):
    _audit_key: bytes = field(repr=False)

    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        message = "|".join(
            [
                request.payload_digest,
                request.nonce,
                request.requested_operation,
                peer.peer_principal_id,
                signature,
            ]
        ).encode("utf-8")
        digest = hmac.new(self._audit_key, message, hashlib.sha256).hexdigest()
        return "audit-mac-v1:" + digest


def _build_signer_backend_from_provider_core(
    profile: SignerKeyProviderProfile,
    resolver: SignerKeyResolver,
    *,
    provider_mode: str = "",
    allow_test_only_key_material: bool = False,
    permission_snapshot_fresh: bool = False,
    control_loop_anchor_store: ControlLoopAnchorStore | None = None,
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None = None,
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | None = None,
    proposal_authority_policy: ArchitectProposalSignerPolicy | None = None,
    proposal_nonce_store_path: Path | str | None = None,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None = None,
    proposal_replay_high_water_store_id: str | None = None,
    proposal_replay_high_water_durability_receipt_id: str | None = None,
    proposal_nonce_store_allowed_root: Path | str | None = None,
    proposal_nonce_store_repo_root: Path | str | None = None,
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization | None = None,
) -> SignerKeyProviderDryRunResult:
    """Internal key-resolution core; public callers cannot enable proposal mode.

    The default path rejects. A caller must explicitly opt into
    ``TEST_ONLY_DRYRUN`` or ``WSP71_PERMISSIONED`` and provide a fresh
    permission snapshot. ``TEST_ONLY_DRYRUN`` additionally requires
    ``allow_test_only_key_material``. ``WSP71_PERMISSIONED`` rejects the mock
    vault resolver and any test-only override flag.
    """

    if not isinstance(profile, SignerKeyProviderProfile):
        return _reject(FAIL_PROVIDER_PROFILE_INVALID)
    if not _provider_mode_authorized(
        provider_mode,
        allow_test_only_key_material=allow_test_only_key_material,
        resolver=resolver,
    ):
        return _reject(FAIL_PROVIDER_MOCK_IN_PRODUCTION, profile=profile)
    profile_rejection = validate_signer_key_provider_profile(profile)
    if profile_rejection is not None:
        return _reject(profile_rejection, profile=profile)
    if not permission_snapshot_fresh:
        return _reject(FAIL_PROVIDER_PERMISSION_DENIED, profile=profile)

    signing_result = _resolve(profile.signing_key_ref, profile.signer_agent_id, resolver)
    if not signing_result.success:
        return _reject(_resolve_rejection(signing_result), profile=profile, signing=signing_result)
    audit_result = _resolve(profile.audit_mac_key_ref, profile.signer_agent_id, resolver)
    if not audit_result.success:
        return _reject(_resolve_rejection(audit_result), profile=profile, signing=signing_result, audit=audit_result)
    if not _ttl_valid(signing_result, profile.ttl_seconds) or not _ttl_valid(audit_result, profile.ttl_seconds):
        return _reject(FAIL_PROVIDER_TTL_EXPIRED, profile=profile, signing=signing_result, audit=audit_result)

    signing_secret = signing_result.get_value()
    audit_secret = audit_result.get_value()
    private_key = _decode_ed25519_private_key(signing_secret)
    if private_key is None:
        return _reject(FAIL_PROVIDER_KEY_FORMAT, profile=profile, signing=signing_result, audit=audit_result)
    audit_key = _decode_audit_key(audit_secret)
    if audit_key is None:
        return _reject(FAIL_PROVIDER_AUDIT_KEY_MISSING, profile=profile, signing=signing_result, audit=audit_result)

    public_key = _public_key_text(private_key)
    if public_key != profile.expected_public_key:
        return _reject(FAIL_PROVIDER_PUBLIC_KEY_MISMATCH, profile=profile, signing=signing_result, audit=audit_result)
    fingerprint = public_key_fingerprint(public_key)
    if fingerprint != profile.expected_key_fingerprint:
        return _reject(FAIL_PROVIDER_FINGERPRINT_MISMATCH, profile=profile, signing=signing_result, audit=audit_result)
    effective_proposal_nonce_store = None
    if proposal_authority_policy is not None:
        try:
            high_water_store_matches = bool(
                isinstance(
                    proposal_replay_high_water_store,
                    ProposalReplayHighWaterStore,
                )
                and proposal_replay_high_water_store_id
                and hmac.compare_digest(
                    proposal_replay_high_water_store.store_id,
                    proposal_replay_high_water_store_id,
                )
                and isinstance(
                    proposal_policy_authorization,
                    ArchitectProposalPolicyAuthorization,
                )
                and hmac.compare_digest(
                    proposal_policy_authorization.proposal_policy_digest,
                    architect_proposal_signer_policy_digest(
                        proposal_authority_policy
                    ),
                )
                and (
                    provider_mode != PROVIDER_MODE_WSP71_PERMISSIONED
                    or (
                        proposal_replay_high_water_store.durable is True
                        and isinstance(
                            proposal_replay_high_water_durability_receipt_id,
                            str,
                        )
                        and _is_sha256_digest(
                            proposal_replay_high_water_durability_receipt_id
                        )
                        and hmac.compare_digest(
                            str(
                                proposal_replay_high_water_store
                                .durability_receipt_id
                            ),
                            proposal_replay_high_water_durability_receipt_id,
                        )
                    )
                )
            )
        except Exception:
            high_water_store_matches = False
        if (
            not high_water_store_matches
            or proposal_nonce_store_path is None
            or proposal_nonce_store_allowed_root is None
            or proposal_nonce_store_repo_root is None
        ):
            return _reject(
                FAIL_PROVIDER_PROFILE_INVALID,
                profile=profile,
                signing=signing_result,
                audit=audit_result,
            )
        try:
            effective_proposal_nonce_store = (
                AtomicProposalAuthenticityNonceStore(
                    proposal_nonce_store_path,
                    allowed_root=proposal_nonce_store_allowed_root,
                    repo_root=proposal_nonce_store_repo_root,
                    integrity_key=audit_key,
                    high_water_store=proposal_replay_high_water_store,
                    replay_store_binding_digest=(
                        architect_proposal_replay_store_binding_digest(
                            architect_proposal_signer_instance_id(
                                proposal_nonce_store_allowed_root,
                                profile.expected_public_key,
                                profile.expected_key_epoch,
                            ),
                            proposal_nonce_store_path,
                            proposal_replay_high_water_store_id,
                        )
                    ),
                )
            )
        except (OSError, TypeError, ValueError):
            return _reject(
                FAIL_PROVIDER_PROFILE_INVALID,
                profile=profile,
                signing=signing_result,
                audit=audit_result,
            )
    elif any(
        value is not None
        for value in (
            proposal_nonce_store_path,
            proposal_replay_high_water_store,
            proposal_replay_high_water_store_id,
            proposal_replay_high_water_durability_receipt_id,
            proposal_nonce_store_allowed_root,
            proposal_nonce_store_repo_root,
            proposal_policy_authorization,
        )
    ):
        return _reject(
            FAIL_PROVIDER_PROFILE_INVALID,
            profile=profile,
            signing=signing_result,
            audit=audit_result,
        )

    return SignerKeyProviderDryRunResult(
        ok=True,
        rejection_code=None,
        signer_profile_id=profile.signer_profile_id,
        key_epoch=profile.expected_key_epoch,
        public_key=public_key,
        key_fingerprint=fingerprint,
        signing_key_ref_hash=signing_result.reference_hash,
        audit_mac_key_ref_hash=audit_result.reference_hash,
        ttl_remaining_seconds=min(int(signing_result.ttl_remaining or 0), int(audit_result.ttl_remaining or 0)),
        secret_values_returned=False,
        backend=Ed25519SignerBackend(
            private_key=private_key,
            public_key=public_key,
            key_epoch=profile.expected_key_epoch,
            audit_mac_builder=_HmacAuditMacBuilder(audit_key),
            control_loop_anchor_store=control_loop_anchor_store,
            control_loop_authority_policy=control_loop_authority_policy,
            proposal_authority_policy=proposal_authority_policy,
            proposal_nonce_store=effective_proposal_nonce_store,
            verified_outcome_signer_policy=verified_outcome_signer_policy,
        ),
    )


def build_test_only_signer_backend_from_provider(
    profile: SignerKeyProviderProfile,
    resolver: SignerKeyResolver,
    *,
    provider_mode: str = "",
    allow_test_only_key_material: bool = False,
    permission_snapshot_fresh: bool = False,
    control_loop_anchor_store: ControlLoopAnchorStore | None = None,
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None = None,
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | None = None,
) -> SignerKeyProviderDryRunResult:
    """Build a generic signer backend without architect-proposal authority."""

    return _build_signer_backend_from_provider_core(
        profile,
        resolver,
        provider_mode=provider_mode,
        allow_test_only_key_material=allow_test_only_key_material,
        permission_snapshot_fresh=permission_snapshot_fresh,
        control_loop_anchor_store=control_loop_anchor_store,
        control_loop_authority_policy=control_loop_authority_policy,
        verified_outcome_signer_policy=verified_outcome_signer_policy,
    )


def _build_proposal_signer_backend_from_verified_runtime(
    profile: SignerKeyProviderProfile,
    resolver: SignerKeyResolver,
    *,
    provider_mode: str,
    allow_test_only_key_material: bool,
    permission_snapshot_fresh: bool,
    proposal_authority_policy: ArchitectProposalSignerPolicy,
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization,
    proposal_nonce_store_path: Path | str,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore,
    proposal_replay_high_water_store_id: str,
    proposal_replay_high_water_durability_receipt_id: str,
    proposal_nonce_store_allowed_root: Path | str,
    proposal_nonce_store_repo_root: Path | str,
) -> SignerKeyProviderDryRunResult:
    """Internal proposal constructor reached only after runtime authorization."""

    return _build_signer_backend_from_provider_core(
        profile,
        resolver,
        provider_mode=provider_mode,
        allow_test_only_key_material=allow_test_only_key_material,
        permission_snapshot_fresh=permission_snapshot_fresh,
        proposal_authority_policy=proposal_authority_policy,
        proposal_policy_authorization=proposal_policy_authorization,
        proposal_nonce_store_path=proposal_nonce_store_path,
        proposal_replay_high_water_store=proposal_replay_high_water_store,
        proposal_replay_high_water_store_id=(
            proposal_replay_high_water_store_id
        ),
        proposal_replay_high_water_durability_receipt_id=(
            proposal_replay_high_water_durability_receipt_id
        ),
        proposal_nonce_store_allowed_root=proposal_nonce_store_allowed_root,
        proposal_nonce_store_repo_root=proposal_nonce_store_repo_root,
    )


def build_signer_backend_from_provider(
    profile: SignerKeyProviderProfile,
    resolver: SignerKeyResolver,
    *,
    provider_mode: str = "",
    allow_test_only_key_material: bool = False,
    permission_snapshot_fresh: bool = False,
    control_loop_anchor_store: ControlLoopAnchorStore | None = None,
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None = None,
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | None = None,
) -> SignerKeyProviderDryRunResult:
    """Production-capable generic signer boundary; proposal mode is internal."""

    return _build_signer_backend_from_provider_core(
        profile,
        resolver,
        provider_mode=provider_mode,
        allow_test_only_key_material=allow_test_only_key_material,
        permission_snapshot_fresh=permission_snapshot_fresh,
        control_loop_anchor_store=control_loop_anchor_store,
        control_loop_authority_policy=control_loop_authority_policy,
        verified_outcome_signer_policy=verified_outcome_signer_policy,
    )


def _provider_mode_authorized(
    provider_mode: str,
    *,
    allow_test_only_key_material: bool,
    resolver: SignerKeyResolver,
) -> bool:
    if provider_mode == PROVIDER_MODE_TEST_ONLY_DRYRUN:
        return bool(allow_test_only_key_material)
    if provider_mode == PROVIDER_MODE_WSP71_PERMISSIONED:
        if allow_test_only_key_material:
            return False
        return not _resolver_is_mock_vault(resolver)
    return False


def _is_sha256_digest(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _resolver_is_mock_vault(resolver: object) -> bool:
    cls = resolver.__class__
    return cls.__name__ == "MockVaultResolver" or cls.__module__.endswith("vault_resolver")


def _resolve(reference: str, requester_id: str, resolver: SignerKeyResolver) -> ResolveResult:
    try:
        result = resolver.resolve(reference, requester_id=requester_id)
    except Exception:
        return ResolveResult(
            success=False,
            reference=reference,
            reference_hash=hash_reference(reference),
            error_message="resolver unavailable",
        )
    if not isinstance(result, ResolveResult):
        return ResolveResult(
            success=False,
            reference=reference,
            reference_hash=hash_reference(reference),
            error_message="resolver unavailable",
        )
    return result


def _resolve_rejection(result: ResolveResult) -> str:
    value = result.error_code.value if result.error_code else ""
    if value in {"RESOLVER_UNAVAILABLE", "SESSION_INVALID"}:
        return FAIL_PROVIDER_RESOLVER_UNAVAILABLE
    if value == "TTL_EXPIRED":
        return FAIL_PROVIDER_TTL_EXPIRED
    if value in {"INVALID_REFERENCE", "UNKNOWN_REFERENCE"}:
        return FAIL_PROVIDER_REFERENCE_INVALID
    return FAIL_PROVIDER_RESOLVER_UNAVAILABLE


def _ttl_valid(result: ResolveResult, profile_ttl: int) -> bool:
    if result.ttl_remaining is None:
        return False
    try:
        ttl = int(result.ttl_remaining)
    except Exception:
        return False
    return 0 < ttl <= profile_ttl


def _decode_ed25519_private_key(secret: object) -> Any | None:
    if not isinstance(secret, str) or not secret.startswith(SIGNING_KEY_PREFIX):
        return None
    try:
        raw = base64.b64decode(secret[len(SIGNING_KEY_PREFIX):], validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(raw) != ED25519_PRIVATE_KEY_BYTES:
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        return Ed25519PrivateKey.from_private_bytes(raw)
    except Exception:
        return None


def _decode_audit_key(secret: object) -> bytes | None:
    if not isinstance(secret, str) or not secret.startswith(AUDIT_KEY_PREFIX):
        return None
    try:
        raw = base64.b64decode(secret[len(AUDIT_KEY_PREFIX):], validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(raw) < MIN_AUDIT_KEY_BYTES:
        return None
    return raw


def _public_key_text(private_key: Any) -> str:
    from cryptography.hazmat.primitives import serialization

    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _reject(
    code: str,
    *,
    profile: Optional[SignerKeyProviderProfile] = None,
    signing: Optional[ResolveResult] = None,
    audit: Optional[ResolveResult] = None,
) -> SignerKeyProviderDryRunResult:
    return SignerKeyProviderDryRunResult(
        ok=False,
        rejection_code=str(code),
        signer_profile_id=profile.signer_profile_id if isinstance(profile, SignerKeyProviderProfile) else "",
        key_epoch=None,
        public_key=None,
        key_fingerprint=None,
        signing_key_ref_hash=(
            signing.reference_hash
            if isinstance(signing, ResolveResult)
            else hash_reference(profile.signing_key_ref)
            if isinstance(profile, SignerKeyProviderProfile)
            else None
        ),
        audit_mac_key_ref_hash=(
            audit.reference_hash
            if isinstance(audit, ResolveResult)
            else hash_reference(profile.audit_mac_key_ref)
            if isinstance(profile, SignerKeyProviderProfile)
            else None
        ),
        ttl_remaining_seconds=None,
        secret_values_returned=False,
        backend=None,
    )


def _profile_ascii_and_complete(profile: SignerKeyProviderProfile) -> bool:
    payload = asdict(profile)
    required = (
        "signer_profile_id",
        "signer_agent_id",
        "signing_key_ref",
        "audit_mac_key_ref",
        "expected_public_key",
        "expected_key_fingerprint",
        "expected_key_epoch",
        "permission_snapshot_digest",
    )
    if not all(isinstance(payload.get(key), str) and payload[key] for key in required):
        return False
    if not isinstance(profile.ttl_seconds, int):
        return False
    return _assert_ascii_deep(payload)


def validate_signer_key_provider_profile(
    profile: object,
) -> str | None:
    """Return the provider rejection code for invalid static profile data."""

    if not isinstance(profile, SignerKeyProviderProfile):
        return FAIL_PROVIDER_PROFILE_INVALID
    if not _profile_ascii_and_complete(profile):
        return FAIL_PROVIDER_PROFILE_INVALID
    if profile.signing_key_ref == profile.audit_mac_key_ref:
        return FAIL_PROVIDER_REFERENCE_FORBIDDEN
    if not parse_op_reference(profile.signing_key_ref) or not parse_op_reference(
        profile.audit_mac_key_ref
    ):
        return FAIL_PROVIDER_REFERENCE_INVALID
    if profile.ttl_seconds <= 0:
        return FAIL_PROVIDER_TTL_EXPIRED
    if decode_ed25519_public_key(profile.expected_public_key) is None:
        return FAIL_PROVIDER_PROFILE_INVALID
    return None


def _assert_ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _assert_ascii_deep(key) and _assert_ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_assert_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "AUDIT_KEY_PREFIX",
    "FAIL_PROVIDER_AUDIT_KEY_MISSING",
    "FAIL_PROVIDER_FINGERPRINT_MISMATCH",
    "FAIL_PROVIDER_KEY_FORMAT",
    "FAIL_PROVIDER_MOCK_IN_PRODUCTION",
    "FAIL_PROVIDER_PERMISSION_DENIED",
    "FAIL_PROVIDER_PROFILE_INVALID",
    "FAIL_PROVIDER_PUBLIC_KEY_MISMATCH",
    "FAIL_PROVIDER_REFERENCE_FORBIDDEN",
    "FAIL_PROVIDER_REFERENCE_INVALID",
    "FAIL_PROVIDER_RESOLVER_UNAVAILABLE",
    "FAIL_PROVIDER_TTL_EXPIRED",
    "PROVIDER_MODE_TEST_ONLY_DRYRUN",
    "PROVIDER_MODE_WSP71_PERMISSIONED",
    "SIGNING_KEY_PREFIX",
    "SignerKeyProviderDryRunResult",
    "SignerKeyProviderProfile",
    "build_signer_backend_from_provider",
    "build_test_only_signer_backend_from_provider",
    "validate_signer_key_provider_profile",
]
