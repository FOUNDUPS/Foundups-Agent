"""Identity and freshness validation for resolve-per-sign results."""

from __future__ import annotations

from typing import Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyProviderDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    constant_time_compare,
)

_AUDIT_MAC_PREFIX = "audit-mac-v1:"


class ResolvePerSignIdentity(Protocol):
    signer_profile_id: str
    signing_key_ref_hash: str
    audit_mac_key_ref_hash: str
    key_epoch: str
    signer_public_key: str
    signer_key_fingerprint: str
    signer_agent_id: str
    permission_snapshot_digest: str


def provider_result_matches(
    result: object, binding: ResolvePerSignIdentity
) -> bool:
    if type(result) is not SignerKeyProviderDryRunResult:
        return False
    pairs = (
        (result.signer_profile_id, binding.signer_profile_id),
        (result.key_epoch, binding.key_epoch),
        (result.signing_key_ref_hash, binding.signing_key_ref_hash),
        (result.audit_mac_key_ref_hash, binding.audit_mac_key_ref_hash),
        (result.public_key, binding.signer_public_key),
        (result.key_fingerprint, binding.signer_key_fingerprint),
    )
    return bool(
        result.ok is True
        and result.secret_values_returned is False
        and type(result.ttl_remaining_seconds) is int
        and result.ttl_remaining_seconds > 0
        and all(_same(actual, expected) for actual, expected in pairs)
    )


def factory_binding_matches(
    factory: object, binding: ResolvePerSignIdentity
) -> bool:
    try:
        values = (
            (getattr(factory, "signer_agent_id", None), binding.signer_agent_id),
            (getattr(factory, "permission_snapshot_digest", None),
             binding.permission_snapshot_digest),
        )
    except Exception:
        return False
    return all(_same(actual, expected) for actual, expected in values)


def response_matches(
    response: object, request: SigningRequest, binding: ResolvePerSignIdentity
) -> bool:
    if type(response) is not SigningResponse:
        return False
    if response.no_secret_material_returned is not True:
        return False
    if response.accepted is not True:
        return False
    try:
        derived_fingerprint = public_key_fingerprint(response.signer_public_key)
    except Exception:
        return False
    pairs = (
        (response.signer_public_key, request.signer_public_key),
        (response.signer_public_key, binding.signer_public_key),
        (response.key_fingerprint, binding.signer_key_fingerprint),
        (response.key_epoch, binding.key_epoch),
        (
            response.key_fingerprint,
            derived_fingerprint,
        ),
    )
    return bool(
        response.boundary_attested is True
        and response.requester_identity_attested is True
        and response.signer_loads_no_untrusted_code is True
        and type(response.rejection_code) is str
        and response.rejection_code == ""
        and type(response.audit_attestation_signature) is str
        and response.audit_attestation_signature == ""
        and _valid_audit_mac(response.audit_mac)
        and all(_same(actual, expected) for actual, expected in pairs)
    )


def backend_identity_matches(
    backend: object, binding: ResolvePerSignIdentity
) -> bool:
    try:
        values = (
            (getattr(backend, "public_key", None), binding.signer_public_key),
            (getattr(backend, "key_epoch", None), binding.key_epoch),
        )
    except Exception:
        return False
    return all(_same(actual, expected) for actual, expected in values)


def signature_matches(
    response: object,
    request: SigningRequest,
    verifier: SignatureVerifier,
    binding: ResolvePerSignIdentity,
) -> bool:
    if type(response) is not SigningResponse or response.accepted is not True:
        return False
    try:
        return verifier.verify(
            binding.signer_public_key,
            request.signing_input,
            response.signature,
        ) is True
    except Exception:
        return False


def _same(actual: object, expected: str) -> bool:
    try:
        return type(actual) is str and constant_time_compare(actual, expected)
    except Exception:
        return False


def _valid_audit_mac(value: object) -> bool:
    if type(value) is not str or not value.startswith(_AUDIT_MAC_PREFIX):
        return False
    digest = value[len(_AUDIT_MAC_PREFIX):]
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


__all__ = [
    "backend_identity_matches",
    "factory_binding_matches",
    "provider_result_matches",
    "response_matches",
    "signature_matches",
]
