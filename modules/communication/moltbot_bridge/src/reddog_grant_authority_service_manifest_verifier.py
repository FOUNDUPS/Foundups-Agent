"""Re-verify one E0-bound grant-service manifest from root-owned storage."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
    validate_grant_service_config,
    validate_grant_service_run_packet,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_manifest_signature import (
    verify_grant_service_manifest_signatures,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    DEFAULT_MAX_TTL_SECONDS,
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    MAX_ARTIFACT_BYTES,
    REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    SCHEMA_VERSION_V2,
    RuntimeArtifactManifestError,
    raw_digest,
    runtime_artifact_size_limit,
    validate_freshness,
    validate_signed_payload,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)


def verify_current_grant_service_artifacts(
    *, repo_root: Path, grant_root: Path, policy: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Verify the exact E0-named manifest and all three grant artifacts."""

    with reddog_runtime_artifact_generation_lock(
        grant_root, repo_root=repo_root, allow_sealed=True
    ):
        manifest = _read_manifest(repo_root, grant_root, policy)
        _verify_manifest_bindings(manifest, repo_root, grant_root, policy)
        verify_grant_service_manifest_signatures(manifest)
        artifacts = _read_artifacts(manifest, repo_root, grant_root)
        return MappingProxyType(_verified_values(manifest, artifacts, policy))
def _read_manifest(
    repo: Path, root: Path, policy: Mapping[str, Any]
) -> dict[str, Any]:
    manifest_id = str(policy["grant_authority_manifest_id"])
    target = validate_runtime_artifact_path(
        root / MANIFEST_DIRECTORY_NAME / f"{manifest_id[7:]}.json",
        repo_root=repo,
        allowed_root=root,
    )
    raw = _read_bytes(target, repo, root, MAX_ARTIFACT_BYTES)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArtifactManifestError("grant_service_manifest_malformed") from exc
    return validate_signed_payload(value)


def _verify_manifest_bindings(
    manifest: Mapping[str, Any], repo: Path, root: Path,
    policy: Mapping[str, Any],
) -> None:
    expected = {
        "schema_version": SCHEMA_VERSION_V2,
        "runtime_profile": RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
        "manifest_id": policy["grant_authority_manifest_id"],
        "artifact_generation_digest": policy[
            "grant_authority_artifact_generation_digest"
        ],
        "repo_root_digest": raw_digest(
            str(repo.resolve()).encode("utf-8")
        ),
        "runtime_root_digest": raw_digest(str(root).encode("utf-8")),
        "signer_service_config_digest": policy["config_digest"],
        "signer_public_key": policy["target_signer_public_key"],
        "signer_key_fingerprint": policy["target_signer_key_fingerprint"],
        "key_epoch": policy["target_signer_key_epoch"],
    }
    if any(manifest.get(name) != value for name, value in expected.items()):
        raise RuntimeArtifactManifestError("grant_service_manifest_binding_mismatch")
    validate_freshness(
        manifest, now_epoch=_now_epoch(),
        max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS,
    )


def _read_artifacts(
    manifest: Mapping[str, Any], repo: Path, root: Path
) -> dict[str, Any]:
    descriptors = tuple(manifest["artifacts"])
    if tuple(item["filename"] for item in descriptors) != (
        REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS
    ):
        raise RuntimeArtifactManifestError("grant_service_artifact_set_invalid")
    raw = {
        str(item["filename"]): _read_bytes(
            root / str(item["filename"]), repo, root,
            runtime_artifact_size_limit(str(item["filename"])),
        )
        for item in descriptors
    }
    for item in descriptors:
        body = raw[str(item["filename"])]
        if len(body) != item["byte_count"] or raw_digest(body) != item["content_digest"]:
            raise RuntimeArtifactManifestError("grant_service_artifact_changed")
    config = validate_grant_service_config(
        json.loads(raw[GRANT_AUTHORITY_SERVICE_CONFIG].decode("utf-8"))
    )
    config_digest = raw_digest(raw[GRANT_AUTHORITY_SERVICE_CONFIG])
    archive_digest = raw_digest(raw[GRANT_AUTHORITY_SERVICE_ARCHIVE])
    if config["archive_digest"] != archive_digest:
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    run_packet = validate_grant_service_run_packet(
        json.loads(raw[GRANT_AUTHORITY_SERVICE_RUN_PACKET].decode("utf-8")),
        config_digest=config_digest, archive_digest=archive_digest,
    )
    return {
        "config": config,
        "config_digest": config_digest,
        "run_packet": run_packet,
        "run_packet_digest": raw_digest(
            raw[GRANT_AUTHORITY_SERVICE_RUN_PACKET]
        ),
        "archive_digest": archive_digest,
    }


def _verified_values(
    manifest: Mapping[str, Any], artifacts: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    config = artifacts["config"]
    run_packet = artifacts["run_packet"]
    if (
        artifacts["config_digest"] != policy["grant_authority_config_digest"]
        or artifacts["run_packet_digest"]
        != policy["grant_authority_run_packet_digest"]
    ):
        raise RuntimeArtifactManifestError("grant_service_policy_artifact_mismatch")
    return {
        "manifest_id": manifest["manifest_id"],
        "artifact_generation_digest": manifest["artifact_generation_digest"],
        "config": config, "run_packet": run_packet,
        "service_archive_digest": artifacts["archive_digest"],
    }


def _read_bytes(path: Path, repo: Path, root: Path, maximum: int) -> bytes:
    target = validate_runtime_artifact_path(
        path, repo_root=repo, allowed_root=root
    )
    if target.is_symlink() or not target.is_file():
        raise RuntimeArtifactManifestError("grant_service_artifact_missing")
    return secure_read_confined_bytes(
        target, allowed_root=root, max_bytes=maximum
    )[0]
def _now_epoch() -> int:
    return int(time.time())


__all__ = ["verify_current_grant_service_artifacts"]
