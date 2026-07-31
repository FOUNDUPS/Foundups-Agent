"""Publish and atomically activate one signed signer-runtime generation."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_create_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    REQUIRED_RUNTIME_ARTIFACTS,
    RuntimeArtifactManifestError,
    canonical_signing_input,
    digest,
    validate_freshness,
    validate_signed_payload,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
    _describe_runtime_artifacts_unlocked,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_activation_lease import (
    runtime_artifact_activation_lease,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    _validate_bindings,
    _verify_signatures,
    produce_signed_runtime_artifact_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor, load_persisted_signer_runtime_generation,
    recover_signer_runtime_generation_with_outcome,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    SignerRuntimeAtomicProvisioningContext,
    SignerRuntimeAtomicProvisioningResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationBinding,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    REDDOG_RUNTIME_ARTIFACT_GENERATION_SEAL,
)


CONFIG_FILENAME = "signer_service_config.json"
RUN_PACKET_FILENAME = "signer_service_run_packet.json"


def provision_signer_runtime_generation(
    *,
    nonce: str,
    ttl_seconds: int,
    context: SignerRuntimeAtomicProvisioningContext,
) -> SignerRuntimeAtomicProvisioningResult:
    """Sign an already-built final root and activate its binding last."""

    manifest_path: str | None = None
    manifest_id: str | None = None
    runtime_root: Path | None = None
    try:
        signing = context.require_signing_context()
        runtime_root = _validated_roots(context)
        issued_at = _trusted_now()
        signing.authority_boundary.revalidate(
            signing.authority,
            now_epoch=issued_at,
        )
        produced = produce_signed_runtime_artifact_manifest(
            manifest_directory=runtime_root / MANIFEST_DIRECTORY_NAME,
            nonce=nonce,
            issued_at=issued_at,
            expires_at=issued_at + int(ttl_seconds),
            context=signing,
        )
        if not produced.accepted:
            return _recover_or_reject_production(
                context,
                runtime_root=runtime_root,
                nonce=nonce,
                manifest_id=produced.manifest_id,
                rejection_reasons=produced.rejection_reasons,
            )
        manifest_path = produced.output_path
        manifest_id = produced.manifest_id
        activation, recovered = _activate_manifest(
            context,
            runtime_root=runtime_root,
            manifest_path=manifest_path,
        )
        return _accepted(
            activation,
            manifest_path=manifest_path,
            manifest_id=manifest_id,
            recovered=recovered,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return _reject(
            (str(exc) or "signer_runtime_provisioning_rejected",),
            manifest_path=manifest_path,
            manifest_id=manifest_id,
            inactive_artifacts_preserved=_published_manifest_preserved(
                context,
                runtime_root,
                manifest_path=manifest_path,
                manifest_id=manifest_id,
            ),
        )


def _accepted(
    activation: SignerRuntimeGenerationActivation,
    *,
    manifest_path: str | None,
    manifest_id: str | None,
    recovered: bool,
) -> SignerRuntimeAtomicProvisioningResult:
    return SignerRuntimeAtomicProvisioningResult(
        accepted=True,
        manifest_path=manifest_path,
        manifest_id=manifest_id,
        generation=activation.generation,
        activation_revision=activation.revision,
        rejection_reasons=(),
        inactive_artifacts_preserved=False,
        recovered_existing_activation=recovered,
    )


def _recover_or_reject_production(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    nonce: str,
    manifest_id: str | None,
    rejection_reasons: tuple[str, ...],
) -> SignerRuntimeAtomicProvisioningResult:
    recovered = _recover_existing_activation(
        context, runtime_root=runtime_root, nonce=nonce
    )
    if recovered is not None:
        return recovered
    return _reject(
        rejection_reasons,
        manifest_path=None,
        manifest_id=manifest_id,
    )


def _validated_roots(
    context: SignerRuntimeAtomicProvisioningContext,
) -> Path:
    if not isinstance(context, SignerRuntimeAtomicProvisioningContext):
        raise ValueError("signer_runtime_provisioning_context_invalid")
    if type(context.generation_anchor) is not DurableSignerRuntimeGenerationAnchor:
        raise ValueError("signer_runtime_generation_anchor_invalid")
    signing = context.require_signing_context()
    authority = signing.authority_boundary.require(signing.authority)
    runtime_root = Path(authority["runtime_root"]).resolve()
    anchor_root = context.generation_anchor.authority_root.resolve()
    rollback_root = context.generation_anchor.rollback_domain_root.resolve()
    witness_root = (
        context.generation_anchor.witness_rollback_domain_root.resolve()
    )
    if any(
        _paths_overlap(runtime_root, protected)
        for protected in (anchor_root, rollback_root, witness_root)
    ):
        raise ValueError("signer_runtime_generation_anchor_not_independent")
    return runtime_root


def _verified_manifest(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    manifest_path: str | None,
    authority: Mapping[str, Any],
    now_epoch: int,
    allow_expired_recovery: bool = False,
) -> dict[str, Any]:
    if not manifest_path:
        raise RuntimeArtifactManifestError("manifest_output_missing")
    manifest = read_reddog_runtime_json_mapping(
        manifest_path,
        allowed_root=runtime_root,
    )
    payload = validate_signed_payload(manifest)
    _validate_bindings(payload, authority)
    if allow_expired_recovery:
        _validate_recovery_time(
            payload,
            now_epoch=now_epoch,
            max_ttl_seconds=int(authority["max_ttl_seconds"]),
        )
    else:
        validate_freshness(
            payload,
            now_epoch=now_epoch,
            max_ttl_seconds=int(authority["max_ttl_seconds"]),
        )
    current = tuple(
        item.to_dict()
        for item in _describe_runtime_artifacts_unlocked(authority)
    )
    if tuple(payload["artifacts"]) != current:
        raise RuntimeArtifactManifestError("manifest_artifacts_changed")
    _verify_signatures(
        payload,
        canonical_signing_input(payload),
        authority,
        context.require_signing_context().signature_verifier,
    )
    return payload


def _validate_recovery_time(
    payload: Mapping[str, Any],
    *,
    now_epoch: int,
    max_ttl_seconds: int,
) -> None:
    issued = payload.get("issued_at")
    expires = payload.get("expires_at")
    if (
        type(now_epoch) is not int
        or type(max_ttl_seconds) is not int
        or type(issued) is not int
        or type(expires) is not int
        or now_epoch <= 0
        or issued > now_epoch
        or expires <= issued
        or expires - issued > max_ttl_seconds
    ):
        raise RuntimeArtifactManifestError("manifest_recovery_time_invalid")


def _activate_manifest(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    manifest_path: str | None,
) -> tuple[SignerRuntimeGenerationActivation, bool]:
    signing = context.require_signing_context()
    authority_boundary = signing.authority_boundary
    authority_capability = signing.authority
    previous = load_persisted_signer_runtime_generation(context.generation_anchor)
    try:
        with authority_boundary.revalidation_fence(
            authority_capability,
            now_epoch=_trusted_now(),
        ) as authority:
            initial = _verified_manifest(
                context,
                runtime_root=runtime_root,
                manifest_path=manifest_path,
                authority=authority,
                now_epoch=_trusted_now(),
                allow_expired_recovery=True,
            )
            _create_or_verify_generation_seal(
                runtime_root,
                manifest=initial,
                repo_root=Path(authority["repo_root"]),
            )
            with runtime_artifact_activation_lease(
                _activation_paths(runtime_root, manifest_path),
                repo_root=authority["repo_root"],
                allowed_root=runtime_root,
            ):
                return _activate_under_lease(
                    context,
                    runtime_root=runtime_root,
                    manifest_path=manifest_path,
                    authority=authority,
                    initial_manifest_id=str(initial["manifest_id"]),
                )
    except (OSError, RuntimeError, TypeError, ValueError):
        recovered = _recover_new_commit(
            context,
            runtime_root=runtime_root,
            manifest_path=manifest_path,
            previous=previous,
        )
        if recovered is None:
            raise
        return recovered, True


def _activate_under_lease(
    context: SignerRuntimeAtomicProvisioningContext,
    *, runtime_root: Path,
    manifest_path: str | None,
    authority: Mapping[str, Any],
    initial_manifest_id: str,
) -> tuple[SignerRuntimeGenerationActivation, bool]:
    manifest = _verified_manifest(
        context,
        runtime_root=runtime_root,
        manifest_path=manifest_path,
        authority=authority,
        now_epoch=_trusted_now(),
        allow_expired_recovery=True,
    )
    if manifest["manifest_id"] != initial_manifest_id:
        raise ValueError("runtime_artifact_manifest_changed")
    recovered_committed: list[bool] = []
    verify_candidate_bytes = _activation_guard(
        context,
        runtime_root=runtime_root,
        manifest_path=manifest_path,
        authority=authority,
        manifest_id=str(manifest["manifest_id"]),
    )
    verify_committed_recovery = _activation_guard(
        context,
        runtime_root=runtime_root,
        manifest_path=manifest_path,
        authority=authority,
        manifest_id=str(manifest["manifest_id"]),
        allow_expired_recovery=True,
        verified_marker=recovered_committed,
    )
    current = context.generation_anchor.recover(
        commit_guard=verify_candidate_bytes,
        committed_witness_guard=verify_committed_recovery,
    )
    if _current_matches_manifest(current, manifest):
        if not recovered_committed:
            verify_candidate_bytes(current)
        return current, True
    fresh = _verified_manifest(
        context,
        runtime_root=runtime_root,
        manifest_path=manifest_path,
        authority=authority,
        now_epoch=_trusted_now(),
    )
    if fresh["manifest_id"] != manifest["manifest_id"]:
        raise ValueError("runtime_artifact_manifest_changed")
    manifest = fresh
    binding = _generation_binding(manifest, current)
    activation = context.generation_anchor.activate(
        binding,
        expected_revision=current.revision if current else None,
        commit_guard=verify_candidate_bytes,
    )
    return activation, False


def _recover_new_commit(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    manifest_path: str | None,
    previous: SignerRuntimeGenerationActivation | None,
) -> SignerRuntimeGenerationActivation | None:
    try:
        signing = context.require_signing_context()
        authority = signing.authority_boundary.require(signing.authority)
        manifest = _verified_manifest(
            context, runtime_root=runtime_root, manifest_path=manifest_path,
            authority=authority, now_epoch=_trusted_now(),
            allow_expired_recovery=True,
        )
        guard = _activation_guard(
            context, runtime_root=runtime_root, manifest_path=manifest_path,
            authority=authority, manifest_id=str(manifest["manifest_id"]),
            allow_expired_recovery=True,
        )
        outcome = recover_signer_runtime_generation_with_outcome(
            context.generation_anchor, commit_guard=guard,
            committed_witness_guard=guard,
        )
        current = outcome.activation
        if current is None or (
            previous is not None and current.revision == previous.revision
            and not outcome.committed_witness_recovered
        ):
            return None
        guard(current)
        return current
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _activation_guard(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    manifest_path: str | None,
    authority: Mapping[str, Any],
    manifest_id: str,
    allow_expired_recovery: bool = False,
    verified_marker: list[bool] | None = None,
) -> Callable[[SignerRuntimeGenerationActivation], None]:
    def verify(candidate: SignerRuntimeGenerationActivation) -> None:
        checked = _verified_manifest(
            context,
            runtime_root=runtime_root,
            manifest_path=manifest_path,
            authority=authority,
            now_epoch=_trusted_now(),
            allow_expired_recovery=allow_expired_recovery,
        )
        if checked["manifest_id"] != manifest_id:
            raise ValueError("runtime_artifact_manifest_changed")
        binding = _binding_from_manifest(
            checked,
            generation=candidate.generation,
        )
        _require_activation_matches(candidate, binding)
        if verified_marker is not None:
            verified_marker.append(True)

    return verify


def _activation_paths(
    runtime_root: Path,
    manifest_path: str | None,
) -> tuple[Path, ...]:
    if not manifest_path:
        raise ValueError("manifest_output_missing")
    return (
        *(runtime_root / name for name in REQUIRED_RUNTIME_ARTIFACTS),
        Path(manifest_path),
    )


def _create_or_verify_generation_seal(
    runtime_root: Path,
    *,
    manifest: Mapping[str, Any],
    repo_root: Path,
) -> None:
    seal_path = runtime_root / REDDOG_RUNTIME_ARTIFACT_GENERATION_SEAL
    body = {
        "schema_version": "reddog_runtime_artifact_generation_seal.v1",
        "manifest_id": manifest["manifest_id"],
        "artifact_generation_digest": manifest[
            "artifact_generation_digest"
        ],
        "runtime_root_digest": manifest["runtime_root_digest"],
    }
    seal = {**body, "seal_id": digest(body)}
    if seal_path.exists():
        current = read_reddog_runtime_json_mapping(
            seal_path,
            allowed_root=runtime_root,
        )
        if dict(current) != seal:
            raise ValueError("runtime_artifact_generation_seal_invalid")
        return
    atomic_create_confined_mapping(
        seal_path,
        seal,
        allowed_root=runtime_root,
        repo_root=repo_root,
    )


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        first == second
        or first in second.parents
        or second in first.parents
    )


def _current_matches_manifest(
    current: SignerRuntimeGenerationActivation | None,
    manifest: Mapping[str, Any],
) -> bool:
    if current is None or current.manifest_id != manifest["manifest_id"]:
        return False
    binding = _binding_from_manifest(
        manifest,
        generation=current.generation,
    )
    return _activation_matches(current, binding)


def _generation_binding(
    manifest: Mapping[str, Any],
    current: SignerRuntimeGenerationActivation | None,
) -> SignerRuntimeGenerationBinding:
    if (
        current is not None
        and current.artifact_generation_digest
        == manifest["artifact_generation_digest"]
    ):
        raise ValueError("signer_runtime_generation_replay")
    return _binding_from_manifest(
        manifest,
        generation=1 if current is None else current.generation + 1,
    )


def _binding_from_manifest(
    manifest: Mapping[str, Any],
    *,
    generation: int,
) -> SignerRuntimeGenerationBinding:
    descriptors = {
        str(item.get("filename") or ""): item
        for item in manifest["artifacts"]
        if isinstance(item, Mapping)
    }
    config = descriptors.get(CONFIG_FILENAME)
    run_packet = descriptors.get(RUN_PACKET_FILENAME)
    if not config or not run_packet:
        raise RuntimeArtifactManifestError(
            "manifest_launch_artifacts_missing"
        )
    return SignerRuntimeGenerationBinding(
        generation=generation,
        manifest_id=str(manifest["manifest_id"]),
        artifact_generation_digest=str(
            manifest["artifact_generation_digest"]
        ),
        config_digest=str(manifest["signer_service_config_digest"]),
        config_raw_digest=str(config["content_digest"]),
        run_packet_digest=str(run_packet["content_digest"]),
    )


def _recover_existing_activation(
    context: SignerRuntimeAtomicProvisioningContext,
    *,
    runtime_root: Path,
    nonce: str,
) -> SignerRuntimeAtomicProvisioningResult | None:
    try:
        paths = _recovery_manifest_paths(
            runtime_root,
            current=None,
            nonce=nonce,
        )
        if len(paths) != 1:
            return None
        activation, _ = _activate_manifest(
            context,
            runtime_root=runtime_root,
            manifest_path=str(paths[0]),
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    return SignerRuntimeAtomicProvisioningResult(
        accepted=True,
        manifest_path=str(paths[0]),
        manifest_id=activation.manifest_id,
        generation=activation.generation,
        activation_revision=activation.revision,
        rejection_reasons=(),
        inactive_artifacts_preserved=False,
        recovered_existing_activation=True,
    )


def _recovery_manifest_paths(
    runtime_root: Path,
    *,
    current: SignerRuntimeGenerationActivation | None,
    nonce: str,
) -> tuple[Path, ...]:
    directory = runtime_root / MANIFEST_DIRECTORY_NAME
    if current is not None:
        path = directory / f"{current.manifest_id[7:]}.json"
        try:
            payload = read_reddog_runtime_json_mapping(
                path,
                allowed_root=runtime_root,
            )
        except (OSError, TypeError, ValueError):
            return ()
        return (path,) if payload.get("nonce") == nonce else ()
    if not directory.is_dir() or directory.is_symlink():
        return ()
    candidates = tuple(sorted(directory.glob("*.json")))
    if len(candidates) > 32:
        raise ValueError("manifest_recovery_candidate_limit")
    matches: list[Path] = []
    for path in candidates:
        try:
            payload = read_reddog_runtime_json_mapping(
                path,
                allowed_root=runtime_root,
            )
        except (OSError, TypeError, ValueError):
            continue
        if payload.get("nonce") == nonce:
            matches.append(path)
    if len(matches) > 1:
        raise ValueError("manifest_recovery_ambiguous")
    return tuple(matches)


def _trusted_now() -> int:
    value = int(time.time())
    if value <= 0:
        raise ValueError("signer_runtime_trusted_clock_invalid")
    return value


def _published_manifest_preserved(
    context: SignerRuntimeAtomicProvisioningContext,
    runtime_root: Path | None,
    *,
    manifest_path: str | None,
    manifest_id: str | None,
) -> bool:
    if runtime_root is None or not manifest_path or not manifest_id:
        return False
    try:
        signing = context.require_signing_context()
        authority = signing.authority_boundary.require(signing.authority)
        payload = _verified_manifest(
            context, runtime_root=runtime_root, manifest_path=manifest_path,
            authority=authority, now_epoch=_trusted_now(),
            allow_expired_recovery=True,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return payload.get("manifest_id") == manifest_id


def _require_activation_matches(
    activation: SignerRuntimeGenerationActivation,
    binding: SignerRuntimeGenerationBinding,
) -> None:
    if not _activation_matches(activation, binding):
        raise ValueError("signer_runtime_generation_activation_mismatch")


def _activation_matches(
    activation: SignerRuntimeGenerationActivation,
    binding: SignerRuntimeGenerationBinding,
) -> bool:
    expected = asdict(binding)
    return {
        key: getattr(activation, key)
        for key in expected
    } == expected


def _reject(
    reasons: tuple[str, ...],
    *,
    manifest_path: str | None,
    manifest_id: str | None,
    inactive_artifacts_preserved: bool = False,
) -> SignerRuntimeAtomicProvisioningResult:
    return SignerRuntimeAtomicProvisioningResult(
        accepted=False,
        manifest_path=manifest_path,
        manifest_id=manifest_id,
        generation=None,
        activation_revision=None,
        rejection_reasons=tuple(reasons),
        inactive_artifacts_preserved=inactive_artifacts_preserved,
        recovered_existing_activation=False,
    )


__all__ = ["SignerRuntimeAtomicProvisioningContext",
           "SignerRuntimeAtomicProvisioningResult",
           "provision_signer_runtime_generation"]
