"""Signature verification for E0-endorsed grant-service manifests."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)


def verify_grant_service_manifest_signatures(
    manifest: Mapping[str, Any],
) -> None:
    """Verify signer identity consistency, signature, and audit attestation."""

    verifier = Ed25519SignatureVerifier()
    signing_input = canonical_signing_input(manifest)
    signature = str(manifest["signature"])
    public_key = str(manifest["signer_public_key"])
    if (
        manifest["signer_key_fingerprint"]
        != public_key_fingerprint(public_key)
        or not verifier.verify(public_key, signing_input, signature)
    ):
        raise RuntimeArtifactManifestError(
            "grant_service_manifest_signature_invalid"
        )
    attestation = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=signature,
        audit_mac=str(manifest["signer_audit_mac"]),
        signer_public_key=public_key,
        key_epoch=str(manifest["key_epoch"]),
        requester_principal_id=str(manifest["issuer_principal_id"]),
        domain_prefix=RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    )
    if not verifier.verify(
        public_key,
        attestation,
        str(manifest["signer_audit_attestation_signature"]),
    ):
        raise RuntimeArtifactManifestError(
            "grant_service_manifest_attestation_invalid"
        )


__all__ = ["verify_grant_service_manifest_signatures"]
