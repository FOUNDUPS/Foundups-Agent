"""Confined reads and immutable publication for runtime manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthority,
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    MAX_ARTIFACT_BYTES,
    REQUIRED_RUNTIME_ARTIFACTS,
    SCHEMA_VERSION_V3,
    RuntimeArtifactDescriptor,
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    raw_digest,
    required_runtime_artifacts_for,
    runtime_artifact_size_limit,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_create_confined_mapping,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)


MANIFEST_DIRECTORY_NAME = "signed_runtime_artifact_manifests"


def describe_runtime_artifacts(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
    *,
    required_artifacts: tuple[str, ...] = REQUIRED_RUNTIME_ARTIFACTS,
    git_provenance_archive: bool = False,
) -> tuple[RuntimeArtifactDescriptor, ...]:
    """Read the exact canonical artifact set under one shared lock."""

    values = boundary.require(authority)
    runtime = Path(values["runtime_root"]).resolve()
    with reddog_runtime_artifact_generation_lock(
        runtime,
        repo_root=values["repo_root"],
        allow_sealed=True,
    ):
        return _describe_runtime_artifacts_unlocked(
            values,
            required_artifacts=required_artifacts,
            git_provenance_archive=git_provenance_archive,
        )


def _describe_runtime_artifacts_unlocked(
    values: Mapping[str, Any],
    *,
    required_artifacts: tuple[str, ...] = REQUIRED_RUNTIME_ARTIFACTS,
    git_provenance_archive: bool = False,
) -> tuple[RuntimeArtifactDescriptor, ...]:
    runtime = Path(values["runtime_root"]).resolve()
    descriptors: list[RuntimeArtifactDescriptor] = []
    mappings: dict[str, dict[str, Any]] = {}
    for filename in required_artifacts:
        path = _artifact_path(values, filename)
        if path.is_symlink() or not path.is_file():
            raise RuntimeArtifactManifestError(
                f"manifest_artifact_invalid:{filename}"
            )
        raw, _ = secure_read_confined_bytes(
            path,
            allowed_root=runtime,
            max_bytes=runtime_artifact_size_limit(filename),
        )
        if filename == GRANT_AUTHORITY_SERVICE_ARCHIVE:
            if not git_provenance_archive:
                from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
                    validate_grant_service_archive,
                )

                validate_grant_service_archive(raw)
        else:
            mapping = _json_mapping(raw, filename)
            _validate_bound_artifact(values, filename, mapping)
            mappings[filename] = mapping
        descriptors.append(
            RuntimeArtifactDescriptor(
                filename=filename,
                byte_count=len(raw),
                content_digest=raw_digest(raw),
            )
        )
    result = tuple(descriptors)
    if GRANT_AUTHORITY_SERVICE_ARCHIVE in required_artifacts:
        _validate_grant_artifact_set(result, mappings)
    return result


def publish_content_addressed_manifest(
    *,
    manifest_directory: Path | str,
    manifest: Mapping[str, Any],
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
) -> Path:
    """Create one immutable content-addressed manifest; never overwrite."""

    values = boundary.require(authority)
    target = _manifest_target(manifest_directory, manifest, values)
    _publish_current_generation(target, manifest, values)
    return target


def _manifest_target(
    manifest_directory: Path | str,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> Path:
    directory = validate_runtime_artifact_path(
        manifest_directory,
        repo_root=Path(authority["repo_root"]).resolve(),
        allowed_root=Path(authority["runtime_root"]).resolve(),
    )
    expected_directory = (
        Path(authority["runtime_root"]).resolve() / MANIFEST_DIRECTORY_NAME
    )
    if directory != expected_directory:
        raise RuntimeArtifactManifestError("manifest_directory_invalid")
    manifest_id = str(manifest.get("manifest_id") or "")
    if not manifest_id.startswith("sha256:"):
        raise RuntimeArtifactManifestError("manifest_id_invalid")
    return validate_runtime_artifact_path(
        directory / f"{manifest_id[7:]}.json",
        repo_root=Path(authority["repo_root"]).resolve(),
        allowed_root=Path(authority["runtime_root"]).resolve(),
    )


def _publish_current_generation(
    target: Path,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    runtime = Path(authority["runtime_root"]).resolve()
    required_artifacts = required_runtime_artifacts_for(manifest)
    try:
        with reddog_runtime_artifact_generation_lock(
            runtime, repo_root=authority["repo_root"]
        ):
            current = tuple(
                item.to_dict()
                for item in _describe_runtime_artifacts_unlocked(
                    authority,
                    required_artifacts=required_artifacts,
                    git_provenance_archive=(
                        manifest.get("schema_version") == SCHEMA_VERSION_V3
                    ),
                )
            )
            if tuple(manifest.get("artifacts") or ()) != current:
                raise RuntimeArtifactManifestError(
                    "manifest_artifacts_changed"
                )
            atomic_create_confined_mapping(
                target,
                manifest,
                allowed_root=authority["runtime_root"],
                repo_root=authority["repo_root"],
            )
    except RuntimeError as exc:
        if str(exc) == "revision_conflict":
            raise RuntimeArtifactManifestError(
                "manifest_already_exists"
            ) from exc
        raise


def _artifact_path(
    authority: Mapping[str, Any],
    filename: str,
) -> Path:
    return validate_runtime_artifact_path(
        Path(authority["runtime_root"]) / filename,
        repo_root=Path(authority["repo_root"]).resolve(),
        allowed_root=Path(authority["runtime_root"]).resolve(),
    )


def _validate_bound_artifact(
    authority: Mapping[str, Any],
    filename: str,
    value: Mapping[str, Any],
) -> None:
    if filename == "authority_profile.json":
        if digest(value) != authority["authority_profile_digest"]:
            raise RuntimeArtifactManifestError("manifest_profile_changed")
    elif filename == "signer_service_config.json":
        if digest(value) != authority["signer_service_config_digest"]:
            raise RuntimeArtifactManifestError("manifest_config_changed")
    elif filename == "authoritative_work_state.json":
        if value.get("revision") != authority["work_state_revision"]:
            raise RuntimeArtifactManifestError("manifest_state_changed")
        matches = [
            item
            for item in value.get("wre_queue_items") or ()
            if isinstance(item, Mapping)
            and item.get("queue_item_id") == authority["queue_item_id"]
        ]
        if len(matches) != 1:
            raise RuntimeArtifactManifestError("manifest_queue_changed")
    elif filename == GRANT_AUTHORITY_SERVICE_CONFIG:
        from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
            validate_grant_service_config,
        )

        validate_grant_service_config(value)


def _validate_grant_artifact_set(
    descriptors: tuple[RuntimeArtifactDescriptor, ...],
    mappings: Mapping[str, Mapping[str, Any]],
) -> None:
    from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
        validate_grant_service_run_packet,
    )

    by_name = {item.filename: item.content_digest for item in descriptors}
    config = mappings.get(GRANT_AUTHORITY_SERVICE_CONFIG, {})
    if config.get("archive_digest") != by_name.get(
        GRANT_AUTHORITY_SERVICE_ARCHIVE
    ):
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    validate_grant_service_run_packet(
        mappings.get(GRANT_AUTHORITY_SERVICE_RUN_PACKET, {}),
        config_digest=by_name.get(GRANT_AUTHORITY_SERVICE_CONFIG, ""),
        archive_digest=by_name.get(GRANT_AUTHORITY_SERVICE_ARCHIVE, ""),
    )


def _json_mapping(raw: bytes, filename: str) -> dict[str, Any]:
    if not raw or len(raw) >= MAX_ARTIFACT_BYTES:
        raise RuntimeArtifactManifestError(
            f"manifest_artifact_invalid:{filename}"
        )
    try:
        value = json.loads(raw.decode("utf-8"))
        canonical_json(value)
    except Exception as exc:
        raise RuntimeArtifactManifestError(
            f"manifest_artifact_malformed:{filename}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeArtifactManifestError(
            f"manifest_artifact_malformed:{filename}"
        )
    return value


__all__ = [
    "MANIFEST_DIRECTORY_NAME",
    "describe_runtime_artifacts",
    "publish_content_addressed_manifest",
]
