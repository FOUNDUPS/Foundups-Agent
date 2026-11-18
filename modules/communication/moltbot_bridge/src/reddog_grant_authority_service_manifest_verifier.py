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
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_provenance_admission import (
    PROVENANCE_BINDING_FIELDS,
    derive_grant_service_git_provenance,
    require_matching_git_provenance,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
    validate_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    DEFAULT_MAX_TTL_SECONDS,
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    MAX_ARTIFACT_BYTES,
    REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
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
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_SCHEMA_V7, POLICY_SCHEMA_V8, POLICY_SCHEMA_V9, POLICY_SCHEMA_V10, POLICY_SCHEMA_V11,
)


def verify_current_grant_service_artifacts(
    *, repo_root: Path, grant_root: Path, policy: Mapping[str, Any],
    owner_config_path: Path | str | None = None,
) -> Mapping[str, Any]:
    """Verify the exact E0-named manifest and all three grant artifacts."""

    if policy.get("schema_version") == POLICY_SCHEMA_V10:
        return _verify_installed_current(repo_root, grant_root, policy, owner_config_path)
    if policy.get("schema_version") == POLICY_SCHEMA_V11:
        return _verify_installed_work_current(repo_root, grant_root, policy, owner_config_path)
    with reddog_runtime_artifact_generation_lock(
        grant_root, repo_root=repo_root, allow_sealed=True
    ):
        manifest = _read_manifest(repo_root, grant_root, policy)
        _verify_manifest_bindings(manifest, repo_root, grant_root, policy)
        verify_grant_service_manifest_signatures(manifest)
        artifacts = _read_artifacts(
            manifest, repo_root, grant_root, policy
        )
        return MappingProxyType(_verified_values(manifest, artifacts, policy))


def _verify_installed_current(repo, root, policy, owner_path):
    """Verify protected enrollment metadata, not this caller's runtime confinement."""
    from .reddog_initial_runtime_manifest_authority import verify_initial_runtime_manifest_approval
    from .reddog_grant_authority_service_owner_binding import grant_authority_owner_runtime_root
    from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
    if owner_path is None:
        raise RuntimeArtifactManifestError("grant_installed_profile_not_enrolled")
    if grant_authority_owner_runtime_root(owner_path, repo, policy["owner_config_id"]) != root:
        raise RuntimeArtifactManifestError("grant_installed_owner_root_mismatch")
    owner = _load_owner_config(owner_path, repo=repo)
    with reddog_runtime_artifact_generation_lock(root, repo_root=repo, allow_sealed=True):
        manifest = _read_manifest(repo, root, policy)
        _installed_manifest_bindings(manifest, repo, root, policy)
        # The owner selects this fixed path; candidate manifests cannot choose a trust file.
        approval_inputs = dict(approval_path=root / "initial-approval.json",
            repo_root=repo, expected_approval_digest=manifest["enrollment_approval_digest"], manifest=manifest)
        verify_initial_runtime_manifest_approval(**approval_inputs)
        artifacts = _read_installed_artifacts(manifest, repo, root)
        _installed_config_bindings(artifacts["config"], policy)
        source = _installed_source_policy(owner, repo, policy, artifacts["source_descriptor"])
        if (artifacts["config_digest"] != policy["grant_authority_config_digest"]
                or artifacts["run_packet_digest"] != policy["grant_authority_run_packet_digest"]):
            raise RuntimeArtifactManifestError("grant_service_policy_artifact_mismatch")
        if _load_owner_config(owner_path, repo=repo) != owner:
            raise RuntimeArtifactManifestError("grant_installed_owner_changed")
        verify_initial_runtime_manifest_approval(**approval_inputs)
        validate_freshness(manifest, now_epoch=_now_epoch(), max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS)
        return MappingProxyType({"manifest_id": manifest["manifest_id"],
            "artifact_generation_digest": manifest["artifact_generation_digest"],
            **artifacts, **source})


def _installed_manifest_bindings(manifest, repo, root, policy):
    from .reddog_runtime_artifact_manifest_contract import (
        SCHEMA_VERSION_INITIAL_V2, RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE,
    )
    expected = {"schema_version": SCHEMA_VERSION_INITIAL_V2,
        "runtime_profile": RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE,
        "manifest_id": policy["grant_authority_manifest_id"],
        "artifact_generation_digest": policy["grant_authority_artifact_generation_digest"],
        "repo_root_digest": raw_digest(str(repo.resolve()).encode()),
        "runtime_root_digest": raw_digest(str(root).encode()),
        "owner_config_id": policy["owner_config_id"],
        "signer_service_config_digest": policy["grant_authority_config_digest"],
        "source_commit_sha": policy["grant_authority_source_commit_sha"],
        "grant_authority_installed_runtime_descriptor_digest": policy["grant_authority_installed_runtime_descriptor_digest"]}
    if (any(manifest.get(k) != v for k,v in expected.items())
            or type(policy.get("generation")) is not int or policy["generation"] != 1
            or tuple(policy.get("allowed_operations", ())) != ("signer_socket_peer_handshake",)
            or tuple(policy.get("allowed_authority_tiers", ())) != ("LOW",)
            or tuple(policy.get("consensus_required_tiers", ())) != ()):
        raise RuntimeArtifactManifestError("grant_installed_manifest_binding_mismatch")
    validate_freshness(manifest, now_epoch=_now_epoch(), max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS)


def _verify_installed_work_current(repo, root, policy, owner_path):
    """Verify non-initial work metadata inside the caller's authenticated E0 lease."""
    from .reddog_grant_authority_service_owner_binding import grant_authority_owner_runtime_root
    from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
    if owner_path is None:
        raise RuntimeArtifactManifestError("grant_installed_work_owner_missing")
    if grant_authority_owner_runtime_root(owner_path, repo, policy["owner_config_id"]) != root:
        raise RuntimeArtifactManifestError("grant_installed_owner_root_mismatch")
    owner = _load_owner_config(owner_path, repo=repo)
    started = _now_epoch()
    with reddog_runtime_artifact_generation_lock(root, repo_root=repo, allow_sealed=True):
        manifest = _read_manifest(repo, root, policy)
        _installed_work_manifest_bindings(manifest, repo, root, policy)
        verify_grant_service_manifest_signatures(manifest)
        artifacts = _read_installed_artifacts(manifest, repo, root)
        _installed_config_bindings(artifacts["config"], policy)
        source = _installed_source_policy(owner, repo, policy, artifacts["source_descriptor"])
        if (artifacts["config"]["owner_config_id"] != policy["owner_config_id"]
                or artifacts["config_digest"] != policy["grant_authority_config_digest"]
                or artifacts["run_packet_digest"] != policy["grant_authority_run_packet_digest"]):
            raise RuntimeArtifactManifestError("grant_service_policy_artifact_mismatch")
        if _load_owner_config(owner_path, repo=repo) != owner:
            raise RuntimeArtifactManifestError("grant_installed_owner_changed")
        now = _now_epoch()
        if now < started or not policy["issued_at"] <= now < policy["expires_at"]:
            raise RuntimeArtifactManifestError("grant_installed_work_time_invalid")
        validate_freshness(manifest, now_epoch=now, max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS)
        return MappingProxyType({"manifest_id": manifest["manifest_id"],
            "artifact_generation_digest": manifest["artifact_generation_digest"],
            **artifacts, **source})


def _installed_work_manifest_bindings(manifest, repo, root, policy):
    from .reddog_runtime_artifact_manifest_contract import RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE
    from .reddog_signer_owner_e0_policy_v7 import require_grant_service_installed_work_bindings
    require_grant_service_installed_work_bindings(policy)
    expected = {"schema_version": SCHEMA_VERSION_V2,
        "runtime_profile": RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE,
        "manifest_id": policy["grant_authority_manifest_id"],
        "artifact_generation_digest": policy["grant_authority_artifact_generation_digest"],
        "repo_root_digest": raw_digest(str(repo.resolve()).encode()),
        "runtime_root_digest": raw_digest(str(root).encode()),
        "signer_service_config_digest": policy["config_digest"],
        "signer_public_key": policy["target_signer_public_key"],
        "signer_key_fingerprint": policy["target_signer_key_fingerprint"],
        "key_epoch": policy["target_signer_key_epoch"]}
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise RuntimeArtifactManifestError("grant_installed_work_manifest_binding_mismatch")
    validate_freshness(manifest, now_epoch=_now_epoch(), max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS)


def _read_installed_artifacts(manifest, repo, root):
    from .reddog_grant_authority_service_artifact_contract import validate_installed_grant_service_artifacts
    from .reddog_runtime_artifact_manifest_io import (
        validate_initial_installed_manifest_artifacts, validate_installed_work_artifacts,
    )
    raw = {item["filename"]: _read_bytes(root / item["filename"], repo, root,
        runtime_artifact_size_limit(item["filename"])) for item in manifest["artifacts"]}
    if any(len(raw[item["filename"]]) != item["byte_count"]
           or raw_digest(raw[item["filename"]]) != item["content_digest"] for item in manifest["artifacts"]):
        raise RuntimeArtifactManifestError("grant_service_artifact_changed")
    if manifest["schema_version"] == SCHEMA_VERSION_V2:
        validate_installed_work_artifacts({"repo_root": repo,
            "signer_public_key": manifest["signer_public_key"]}, raw)
    else:
        validate_initial_installed_manifest_artifacts(manifest, raw)
    return validate_installed_grant_service_artifacts(raw)


def _installed_source_policy(owner, repo, policy, descriptor):
    from .reddog_grant_authority_source_policy_authority import validate_grant_authority_source_policy_owner_config
    from .reddog_grant_authority_installed_source_contract import installed_grant_source_digest
    source = validate_grant_authority_source_policy_owner_config(owner, repo=repo)
    expected = {"grant_authority_source_repo_root_digest": source["repo_root_digest"],
        "grant_authority_source_commit_sha": descriptor["source_commit_sha"],
        "grant_authority_source_object_format": descriptor["source_object_format"],
        "grant_authority_source_policy_digest": source["source_policy_digest"],
        "grant_authority_installed_runtime_descriptor_digest": installed_grant_source_digest(descriptor)}
    if (owner["config_id"] != policy["owner_config_id"]
            or any(policy[k] != v for k,v in expected.items())
            or not set(source["sources"].values()) <= set(descriptor["source_files"])
            or source["sources"]["reddog_grant_authority_service.py"] !=
               "modules/communication/moltbot_bridge/src/reddog_grant_authority_service.py"):
        raise RuntimeArtifactManifestError("grant_installed_source_policy_mismatch")
    return expected


def _installed_config_bindings(config, policy):
    fields = ("signer_agent_id", "signer_profile_id", "public_key", "key_fingerprint", "key_epoch",
        "signing_key_ref_hash", "audit_mac_key_ref_hash", "permission_snapshot_digest", "permission_snapshot_receipt_id")
    if any(config[name] != policy["grant_authority_" + name] for name in fields):
        raise RuntimeArtifactManifestError("grant_installed_config_identity_mismatch")
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
    provenance = policy.get("schema_version") in {POLICY_SCHEMA_V7, POLICY_SCHEMA_V8, POLICY_SCHEMA_V9}
    expected = {
        "schema_version": (
            SCHEMA_VERSION_V3 if provenance else SCHEMA_VERSION_V2
        ),
        "runtime_profile": (
            RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
            if provenance
            else RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE
        ),
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
    if provenance:
        expected.update(
            {name: policy[name] for name in PROVENANCE_BINDING_FIELDS}
        )
    if any(manifest.get(name) != value for name, value in expected.items()):
        raise RuntimeArtifactManifestError("grant_service_manifest_binding_mismatch")
    validate_freshness(
        manifest, now_epoch=_now_epoch(),
        max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS,
    )


def _read_artifacts(
    manifest: Mapping[str, Any], repo: Path, root: Path,
    policy: Mapping[str, Any],
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
    provenance = _verify_archive_provenance(
        raw[GRANT_AUTHORITY_SERVICE_ARCHIVE], repo, policy
    )
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
        "git_provenance": provenance,
    }


def _verify_archive_provenance(
    raw: bytes, repo: Path, policy: Mapping[str, Any]
) -> Mapping[str, Any]:
    if policy.get("schema_version") not in {POLICY_SCHEMA_V7, POLICY_SCHEMA_V8, POLICY_SCHEMA_V9}:
        validate_grant_service_archive(raw)
        return {}
    provenance = derive_grant_service_git_provenance(
        raw,
        repo_root=repo,
        expected_repo_root_digest=str(
            policy["grant_authority_source_repo_root_digest"]
        ),
        expected_source_commit_sha=str(
            policy["grant_authority_source_commit_sha"]
        ),
    )
    require_matching_git_provenance(provenance, policy)
    return provenance


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
        **dict(artifacts["git_provenance"]),
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
