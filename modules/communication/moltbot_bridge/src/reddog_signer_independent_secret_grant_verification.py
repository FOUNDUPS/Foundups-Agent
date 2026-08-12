"""Public-only verification for independently issued secret grants."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    ExpectedSignerSecretGrantBinding,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
    signer_secret_access_request_digest,
    validated_signer_secret_grant,
    verify_expected_signer_secret_grant,
    verify_signer_secret_grant_issuer,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


def require_secret_grant_signer_response(
    response: object,
    request: SigningRequest,
    *,
    authority_public_key: str,
    authority_key_epoch: str,
) -> None:
    """Verify both public signer signatures and every boundary flag."""

    if type(response) is not SigningResponse or response.accepted is not True:
        raise ValueError("secret_grant_signer_rejected")
    checks = (
        response.boundary_attested is True,
        response.requester_identity_attested is True,
        response.signer_loads_no_untrusted_code is True,
        response.no_secret_material_returned is True,
        constant_time_compare(response.signer_public_key, authority_public_key),
        constant_time_compare(response.key_epoch, authority_key_epoch),
        constant_time_compare(
            response.key_fingerprint,
            public_key_fingerprint(authority_public_key),
        ),
        bool(response.audit_mac),
        Ed25519SignatureVerifier().verify(
            authority_public_key, request.signing_input, response.signature
        ),
        _audit_attestation_valid(
            response,
            request,
            authority_public_key=authority_public_key,
            authority_key_epoch=authority_key_epoch,
        ),
    )
    if not all(checks):
        raise ValueError("secret_grant_signer_response_invalid")


def require_final_secret_grant(
    grant: Mapping[str, Any],
    request: SigningRequest,
    binding: ResolvePerSignBinding,
    owner_resolver: Any,
    *,
    now_epoch: int,
) -> None:
    """Rehydrate and verify the final grant before returning it to a caller."""

    checked = validated_signer_secret_grant(grant, now_epoch)
    if not constant_time_compare(
        str(checked["grant_id"]), signer_secret_access_grant_id(checked)
    ):
        raise ValueError("secret_grant_id_invalid")
    verify_expected_signer_secret_grant(
        checked,
        ExpectedSignerSecretGrantBinding(
            **asdict(binding),
            signing_request_digest=signer_secret_access_request_digest(
                request.to_dict()
            ),
            requested_operation=request.requested_operation,
            authority_tier=request.authority_tier,
            attested_peer_principal_id=request.requester_principal_id,
        ),
    )
    verify_signer_secret_grant_issuer(checked, owner_resolver)
    if not Ed25519SignatureVerifier().verify(
        str(checked["issuer_public_key"]),
        canonical_signer_secret_access_grant_input(checked),
        str(checked["signature"]),
    ):
        raise ValueError("secret_grant_signature_invalid")


def _audit_attestation_valid(
    response: SigningResponse,
    request: SigningRequest,
    *,
    authority_public_key: str,
    authority_key_epoch: str,
) -> bool:
    try:
        signing_input = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=response.signature,
            audit_mac=response.audit_mac,
            signer_public_key=authority_public_key,
            key_epoch=authority_key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
        )
    except (TypeError, ValueError):
        return False
    return Ed25519SignatureVerifier().verify(
        authority_public_key,
        signing_input,
        response.audit_attestation_signature,
    )


__all__ = [
    "require_final_secret_grant",
    "require_secret_grant_signer_response",
]
