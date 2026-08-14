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
    REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS,
    REQUIRED_RUNTIME_ARTIFACTS,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
    SCHEMA_VERSION,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
    SIGNER_ROLE,
    SIGNING_OPERATION,
    SIGNING_PREFIX,
    SIGNING_PREFIX_V2,
    SIGNING_PREFIX_V3,
    RuntimeArtifactManifestError,
    canonical_json,
    canonical_signing_input,
    digest,
    manifest_id_for,
    raw_digest,
    require_text,
    required_runtime_artifacts_for,
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
RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION_V2 = SCHEMA_VERSION_V2
RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION_V3 = SCHEMA_VERSION_V3
RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION = SIGNING_OPERATION
RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX = SIGNING_PREFIX
RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX_V2 = SIGNING_PREFIX_V2
RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX_V3 = SIGNING_PREFIX_V3
DEFAULT_MANIFEST_MAX_TTL_SECONDS = DEFAULT_MAX_TTL_SECONDS
REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING = (
    "REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING"
)
REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY = (
    "REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY"
)


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
    runtime_profile: str | None = None,
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
            runtime_profile=runtime_profile,
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
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
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
    required_artifacts = required_runtime_artifacts_for(payload)
    git_provenance = payload.get("schema_version") == SCHEMA_VERSION_V3
    current = tuple(
        item.to_dict()
        for item in describe_runtime_artifacts(
            authority,
            authority_boundary,
            required_artifacts=required_artifacts,
            git_provenance_archive=git_provenance,
        )
    )
    if tuple(payload["artifacts"]) != current:
        raise RuntimeArtifactManifestError("manifest_artifacts_changed")
    _require_current_git_provenance(
        payload, authority, authority_boundary
    )
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
        raw = _unsigned_input_json(request.signing_input)
        if raw is None:
            return None
        import json

        payload = json.loads(raw)
        if not _request_matches(request, payload, raw, checked):
            return None
        unsigned = validate_unsigned_payload(payload)
        _validate_bindings(unsigned, checked)
        validate_freshness(
            unsigned,
            now_epoch=now_epoch,
            max_ttl_seconds=int(checked["max_ttl_seconds"]),
        )
        required_artifacts = required_runtime_artifacts_for(unsigned)
        git_provenance = unsigned.get("schema_version") == SCHEMA_VERSION_V3
        if tuple(unsigned["artifacts"]) != tuple(
            item.to_dict()
            for item in describe_runtime_artifacts(
                authority,
                authority_boundary,
                required_artifacts=required_artifacts,
                git_provenance_archive=git_provenance,
            )
        ):
            return None
        _require_current_git_provenance(
            unsigned, authority, authority_boundary
        )
        return unsigned
    except Exception:
        return None


def _request_matches(
    request: SigningRequest,
    payload: object,
    raw: str,
    authority: Mapping[str, Any],
) -> bool:
    if not isinstance(payload, Mapping):
        return False
    return bool(
        raw == canonical_json(payload)
        and request.signing_input == canonical_signing_input(payload)
        and request.requested_operation == SIGNING_OPERATION
        and request.signer_role == SIGNER_ROLE
        and request.signer_public_key == authority["signer_public_key"]
        and request.requester_principal_id == authority["issuer_principal_id"]
        and request.key_epoch == authority["key_epoch"]
        and request.consensus_receipt_digest
        == authority["consensus_receipt_digest"]
        and request.nonce == payload.get("nonce")
        and request.payload_digest
        == digest({"signing_input": request.signing_input})
    )


def prepare_runtime_artifact_manifest_signing(
    backend: Any,
    request: SigningRequest,
) -> tuple[dict[str, Any] | None, str | None, str]:
    """Validate a manifest request and reserve its signer-side nonce."""
    if request.requested_operation != RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION:
        return None, None, ""
    authority = backend.runtime_artifact_manifest_authority
    boundary = backend.runtime_artifact_manifest_authority_boundary
    if authority is None or boundary is None:
        return None, None, "REJECT_ED25519_SIGNER_DOMAIN_MISMATCH"
    payload = validate_runtime_artifact_manifest_signing_request(
        request, authority, boundary, now_epoch=int(backend.proposal_clock())
    )
    if payload is None:
        return None, None, "REJECT_ED25519_SIGNER_REQUEST_INVALID"
    store = backend.runtime_artifact_manifest_nonce_store
    if store is None:
        return None, None, REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING
    try:
        reservation = store.reserve(
            str(payload["nonce"]),
            expires_at=int(payload["expires_at"]),
            subject=":".join(
                (
                    "runtime-artifact-manifest",
                    public_key_fingerprint(backend.public_key),
                    str(payload["issuer_principal_id"]),
                    str(payload["queue_item_id"]),
                    str(payload["work_state_revision"]),
                )
            ),
        )
    except Exception:
        reservation = None
    if not reservation:
        return None, None, REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY
    return payload, reservation, ""


def rollback_runtime_artifact_manifest_reservation(
    backend: Any, reservation: str | None
) -> None:
    store = backend.runtime_artifact_manifest_nonce_store
    if reservation is None or store is None:
        return
    try:
        store.rollback(reservation)
    except Exception:
        pass


def commit_runtime_artifact_manifest_reservation(
    backend: Any, reservation: str | None
) -> bool:
    if reservation is None:
        return True
    store = backend.runtime_artifact_manifest_nonce_store
    if store is None:
        return False
    try:
        store.commit(reservation)
        return True
    except Exception:
        rollback_runtime_artifact_manifest_reservation(backend, reservation)
        return False


def _unsigned_manifest(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
    values: Mapping[str, Any],
    *,
    nonce: str,
    issued_at: int,
    expires_at: int,
    runtime_profile: str | None = None,
) -> dict[str, Any]:
    schema_version, required_artifacts = _manifest_profile(runtime_profile)
    git_provenance = schema_version == SCHEMA_VERSION_V3
    artifacts = _artifact_descriptors(
        authority,
        boundary,
        required_artifacts=required_artifacts,
        git_provenance_archive=git_provenance,
    )
    payload = _base_unsigned_payload(
        values,
        schema_version=schema_version,
        artifacts=artifacts,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    if runtime_profile is not None:
        payload["runtime_profile"] = runtime_profile
    if git_provenance:
        payload.update(_current_git_provenance(authority, boundary))
    payload["manifest_id"] = manifest_id_for(payload)
    payload["revision"] = payload["manifest_id"][7:]
    return validate_unsigned_payload(payload)


def _base_unsigned_payload(
    values: Mapping[str, Any], *, schema_version: str,
    artifacts: tuple[dict[str, Any], ...], nonce: str,
    issued_at: int, expires_at: int,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
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
        "signer_key_fingerprint": public_key_fingerprint(values["signer_public_key"]),
        "key_epoch": values["key_epoch"],
        "consensus_receipt_digest": values["consensus_receipt_digest"],
        "authority_profile_digest": values["authority_profile_digest"],
        "authority_profile_source_receipt_id": values["authority_profile_source_receipt_id"],
        "signer_service_config_digest": values["signer_service_config_digest"],
        "nonce": require_text(nonce),
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def _current_git_provenance(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
) -> Mapping[str, Any]:
    from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_provenance_admission import (
        derive_current_grant_service_git_provenance,
    )

    return derive_current_grant_service_git_provenance(
        authority, boundary
    )


def _artifact_descriptors(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
    *,
    required_artifacts: tuple[str, ...] = REQUIRED_RUNTIME_ARTIFACTS,
    git_provenance_archive: bool = False,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        item.to_dict()
        for item in describe_runtime_artifacts(
            authority,
            boundary,
            required_artifacts=required_artifacts,
            git_provenance_archive=git_provenance_archive,
        )
    )


def _manifest_profile(
    runtime_profile: str | None,
) -> tuple[str, tuple[str, ...]]:
    if runtime_profile is None:
        return SCHEMA_VERSION, REQUIRED_RUNTIME_ARTIFACTS
    if runtime_profile == RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE:
        return SCHEMA_VERSION_V2, REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS
    if (
        runtime_profile
        == RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
    ):
        return SCHEMA_VERSION_V3, REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS
    raise RuntimeArtifactManifestError("manifest_schema_invalid")


def _unsigned_input_json(signing_input: str) -> str | None:
    for prefix in (SIGNING_PREFIX, SIGNING_PREFIX_V2, SIGNING_PREFIX_V3):
        if signing_input.startswith(prefix):
            return signing_input[len(prefix) :]
    return None


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


def _require_current_git_provenance(
    payload: Mapping[str, Any],
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION_V3:
        return
    from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_provenance_admission import (
        derive_current_grant_service_git_provenance,
        require_matching_git_provenance,
    )

    require_matching_git_provenance(
        payload,
        derive_current_grant_service_git_provenance(authority, boundary),
    )


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
    "RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION_V2",
    "RUNTIME_ARTIFACT_MANIFEST_SCHEMA_VERSION_V3",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX_V2",
    "RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX_V3",
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
