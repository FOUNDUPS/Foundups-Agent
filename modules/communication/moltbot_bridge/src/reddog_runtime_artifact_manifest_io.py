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
    MAX_ARTIFACT_BYTES,
    REQUIRED_RUNTIME_ARTIFACTS,
    RuntimeArtifactDescriptor,
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    raw_digest,
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
) -> tuple[RuntimeArtifactDescriptor, ...]:
    """Read the exact canonical artifact set under one shared lock."""

    values = boundary.require(authority)
    runtime = Path(values["runtime_root"]).resolve()
    with reddog_runtime_artifact_generation_lock(
        runtime, repo_root=values["repo_root"]
    ):
        return _describe_runtime_artifacts_unlocked(values)


def _describe_runtime_artifacts_unlocked(
    values: Mapping[str, Any],
) -> tuple[RuntimeArtifactDescriptor, ...]:
    runtime = Path(values["runtime_root"]).resolve()
    descriptors: list[RuntimeArtifactDescriptor] = []
    for filename in REQUIRED_RUNTIME_ARTIFACTS:
        path = _artifact_path(values, filename)
        if path.is_symlink() or not path.is_file():
            raise RuntimeArtifactManifestError(
                f"manifest_artifact_invalid:{filename}"
            )
        raw, _ = secure_read_confined_bytes(
            path,
            allowed_root=runtime,
            max_bytes=MAX_ARTIFACT_BYTES,
        )
        mapping = _json_mapping(raw, filename)
        _validate_bound_artifact(values, filename, mapping)
        descriptors.append(
            RuntimeArtifactDescriptor(
                filename=filename,
                byte_count=len(raw),
                content_digest=raw_digest(raw),
            )
        )
    return tuple(descriptors)


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
    try:
        with reddog_runtime_artifact_generation_lock(
            runtime, repo_root=authority["repo_root"]
        ):
            current = tuple(
                item.to_dict()
                for item in _describe_runtime_artifacts_unlocked(authority)
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
