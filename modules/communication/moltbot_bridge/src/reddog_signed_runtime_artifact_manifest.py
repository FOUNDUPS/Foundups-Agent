"""Produce and verify signed immutable RedDog runtime-artifact manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthority,
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    DEFAULT_MAX_TTL_SECONDS,
    REQUIRED_RUNTIME_ARTIFACTS,
    SCHEMA_VERSION,
    SIGNER_ROLE,
    SIGNING_OPERATION,
    SIGNING_PREFIX,
    RuntimeArtifactManifestError,
    canonical_json,
    canonical_signing_input,
    digest,
    manifest_id_for,
    raw_digest,
    require_text,
    validate_freshness,
    validate_signed_payload,
    validate_unsigned_payload,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
    describe_runtime_artifacts,
    publish_content_addressed_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION = SCHEMA_VERSION
RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION = SIGNING_OPERATION
RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX = SIGNING_PREFIX
DEFAULT_MANIFEST_MAX_TTL_SECONDS = DEFAULT_MAX_TTL_SECONDS


@dataclass(frozen=True)
class RuntimeArtifactManifestSigningContext:
    signer: IsolatedSignerClient
    signature_verifier: SignatureVerifier
    authority: RuntimeArtifactManifestAuthority
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary
    authority_tier: str


@dataclass(frozen=True)
class SignedRuntimeArtifactManifestResult:
    accepted: bool
    output_path: str | None
    manifest_id: str | None
    rejection_reasons: tuple[str, ...]
    no_repo_mutation_performed: bool = True
    no_execution_performed: bool = True
    no_authority_minted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def produce_signed_runtime_artifact_manifest(
    *,
    manifest_directory: Path | str,
    nonce: str,
    issued_at: int,
    expires_at: int,
    context: RuntimeArtifactManifestSigningContext,
) -> SignedRuntimeArtifactManifestResult:
    """Build, sign, verify, and create one content-addressed manifest."""

    try:
        authority = context.authority_boundary.require(context.authority)
        payload = _unsigned_manifest(
            context.authority,
            context.authority_boundary,
            authority,
            nonce=nonce,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        signing_input = canonical_signing_input(payload)
        response = context.signer.sign(
            _signing_request(payload, signing_input, context)
        )
        signed = _verified_response(
            payload, signing_input, response, context
        )
        verify_signed_runtime_artifact_manifest(
            signed,
            authority=context.authority,
            authority_boundary=context.authority_boundary,
            now_epoch=issued_at,
            signature_verifier=context.signature_verifier,
        )
        target = publish_content_addressed_manifest(
            manifest_directory=manifest_directory,
            manifest=signed,
            authority=context.authority,
            boundary=context.authority_boundary,
        )
        return SignedRuntimeArtifactManifestResult(
            accepted=True,
            output_path=str(target),
            manifest_id=str(signed["manifest_id"]),
            rejection_reasons=(),
        )
    except (OSError, TypeError, ValueError) as exc:
        return _reject(str(exc) or "runtime_artifact_manifest_rejected")


def verify_signed_runtime_artifact_manifest(
    value: Mapping[str, Any],
    *,
    authority: RuntimeArtifactManifestAuthority,
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary,
    now_epoch: int,
    signature_verifier: SignatureVerifier,
) -> dict[str, Any]:
    """Verify signature and compare the manifest with current artifact bytes."""

    checked = authority_boundary.require(authority)
    payload = validate_signed_payload(value)
    _validate_bindings(payload, checked)
    validate_freshness(
        payload,
        now_epoch=now_epoch,
        max_ttl_seconds=int(checked["max_ttl_seconds"]),
    )
    current = tuple(
        item.to_dict()
        for item in describe_runtime_artifacts(authority, authority_boundary)
    )
    if tuple(payload["artifacts"]) != current:
        raise RuntimeArtifactManifestError("manifest_artifacts_changed")
    signing_input = canonical_signing_input(payload)
    _verify_signatures(
        payload, signing_input, checked, signature_verifier
    )
    return payload


def validate_runtime_artifact_manifest_signing_request(
    request: SigningRequest,
    authority: RuntimeArtifactManifestAuthority,
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary,
    *,
    now_epoch: int,
) -> dict[str, Any] | None:
    """Reconstruct and validate signer input under the opaque authority."""

    try:
        checked = authority_boundary.require(authority)
        if not request.signing_input.startswith(SIGNING_PREFIX):
            return None
        raw = request.signing_input[len(SIGNING_PREFIX) :]
        import json

        payload = json.loads(raw)
        if (
            not isinstance(payload, Mapping)
            or raw != canonical_json(payload)
            or request.requested_operation != SIGNING_OPERATION
            or request.signer_role != SIGNER_ROLE
            or request.signer_public_key != checked["signer_public_key"]
            or request.requester_principal_id
            != checked["issuer_principal_id"]
            or request.key_epoch != checked["key_epoch"]
            or request.consensus_receipt_digest
            != checked["consensus_receipt_digest"]
            or request.nonce != payload.get("nonce")
            or request.payload_digest
            != digest({"signing_input": request.signing_input})
        ):
            return None
        unsigned = validate_unsigned_payload(payload)
        _validate_bindings(unsigned, checked)
        validate_freshness(
            unsigned,
            now_epoch=now_epoch,
            max_ttl_seconds=int(checked["max_ttl_seconds"]),
        )
        if tuple(unsigned["artifacts"]) != tuple(
            item.to_dict()
            for item in describe_runtime_artifacts(
                authority, authority_boundary
            )
        ):
            return None
        return unsigned
    except Exception:
        return None


def _unsigned_manifest(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
    values: Mapping[str, Any],
    *,
    nonce: str,
    issued_at: int,
    expires_at: int,
) -> dict[str, Any]:
    artifacts = _artifact_descriptors(authority, boundary)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": "",
        "revision": "",
        "repo_root_digest": raw_digest(
            str(Path(values["repo_root"]).resolve()).encode("utf-8")
        ),
        "runtime_root_digest": raw_digest(
            str(Path(values["runtime_root"]).resolve()).encode("utf-8")
        ),
        "queue_item_id": values["queue_item_id"],
        "work_state_revision": values["work_state_revision"],
        "work_authority_digest": values["work_authority_digest"],
        "publication_receipt_id": values["publication_receipt_id"],
        "publication_binding_digest": values["publication_binding_digest"],
        "artifact_count": len(artifacts),
        "artifact_generation_digest": digest(artifacts),
        "artifacts": artifacts,
        "issuer_principal_id": values["issuer_principal_id"],
        "signer_public_key": values["signer_public_key"],
        "signer_key_fingerprint": public_key_fingerprint(
            values["signer_public_key"]
        ),
        "key_epoch": values["key_epoch"],
        "consensus_receipt_digest": values["consensus_receipt_digest"],
        "authority_profile_digest": values["authority_profile_digest"],
        "authority_profile_source_receipt_id":
            values["authority_profile_source_receipt_id"],
        "signer_service_config_digest":
            values["signer_service_config_digest"],
        "nonce": require_text(nonce),
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    payload["manifest_id"] = manifest_id_for(payload)
    payload["revision"] = payload["manifest_id"][7:]
    return validate_unsigned_payload(payload)


def _artifact_descriptors(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        item.to_dict()
        for item in describe_runtime_artifacts(authority, boundary)
    )


def _validate_bindings(
    payload: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    expected = {
        "queue_item_id": authority["queue_item_id"],
        "work_state_revision": authority["work_state_revision"],
        "work_authority_digest": authority["work_authority_digest"],
        "publication_receipt_id": authority["publication_receipt_id"],
        "publication_binding_digest": authority["publication_binding_digest"],
        "issuer_principal_id": authority["issuer_principal_id"],
        "signer_public_key": authority["signer_public_key"],
        "key_epoch": authority["key_epoch"],
        "consensus_receipt_digest": authority["consensus_receipt_digest"],
        "authority_profile_digest": authority["authority_profile_digest"],
        "authority_profile_source_receipt_id": (
            authority["authority_profile_source_receipt_id"]
        ),
        "signer_service_config_digest": (
            authority["signer_service_config_digest"]
        ),
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise RuntimeArtifactManifestError("manifest_binding_mismatch")


def _signing_request(
    payload: Mapping[str, Any],
    signing_input: str,
    context: RuntimeArtifactManifestSigningContext,
) -> SigningRequest:
    authority = context.authority_boundary.require(context.authority)
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=digest({"signing_input": signing_input}),
        signer_role=SIGNER_ROLE,
        signer_public_key=authority["signer_public_key"],
        requester_principal_id=authority["issuer_principal_id"],
        nonce=str(payload["nonce"]),
        key_epoch=authority["key_epoch"],
        requested_operation=SIGNING_OPERATION,
        authority_tier=context.authority_tier,
        consensus_receipt_digest=authority["consensus_receipt_digest"],
    )


def _verified_response(
    payload: Mapping[str, Any],
    signing_input: str,
    response: Any,
    context: RuntimeArtifactManifestSigningContext,
) -> dict[str, Any]:
    authority = context.authority_boundary.require(context.authority)
    signed = {
        **payload,
        "signature": str(response.signature or ""),
        "signer_audit_mac": str(response.audit_mac or ""),
        "signer_audit_attestation_signature": str(
            response.audit_attestation_signature or ""
        ),
    }
    if not all(
        (
            response.accepted,
            response.signer_public_key == authority["signer_public_key"],
            response.key_epoch == authority["key_epoch"],
            response.boundary_attested,
            response.requester_identity_attested,
            response.signer_loads_no_untrusted_code,
            response.no_secret_material_returned,
        )
    ):
        raise RuntimeArtifactManifestError("manifest_signing_rejected")
    _verify_signatures(
        signed, signing_input, authority, context.signature_verifier
    )
    return signed


def _verify_signatures(
    payload: Mapping[str, Any],
    signing_input: str,
    authority: Mapping[str, Any],
    verifier: SignatureVerifier,
) -> None:
    signature = str(payload["signature"])
    if not verifier.verify(
        authority["signer_public_key"], signing_input, signature
    ):
        raise RuntimeArtifactManifestError("manifest_signature_invalid")
    attestation = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=signature,
        audit_mac=str(payload["signer_audit_mac"]),
        signer_public_key=authority["signer_public_key"],
        key_epoch=authority["key_epoch"],
        requester_principal_id=authority["issuer_principal_id"],
        domain_prefix=(
            RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX
        ),
    )
    if not verifier.verify(
        authority["signer_public_key"],
        attestation,
        str(payload["signer_audit_attestation_signature"]),
    ):
        raise RuntimeArtifactManifestError(
            "manifest_audit_attestation_invalid"
        )


def _reject(reason: str) -> SignedRuntimeArtifactManifestResult:
    return SignedRuntimeArtifactManifestResult(
        accepted=False,
        output_path=None,
        manifest_id=None,
        rejection_reasons=(reason,),
    )


__all__ = [
    "DEFAULT_MANIFEST_MAX_TTL_SECONDS",
    "MANIFEST_DIRECTORY_NAME",
    "REQUIRED_RUNTIME_ARTIFACTS",
    "RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX",
    "RuntimeArtifactManifestAuthority",
    "RuntimeArtifactManifestError",
    "RuntimeArtifactManifestSigningContext",
    "SignedRuntimeArtifactManifestResult",
    "canonical_signing_input",
    "describe_runtime_artifacts",
    "produce_signed_runtime_artifact_manifest",
    "validate_runtime_artifact_manifest_signing_request",
    "verify_signed_runtime_artifact_manifest",
]
