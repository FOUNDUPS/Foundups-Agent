"""Authenticated-input validation for exact-Git grant-service archives."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MANIFEST,
    MAX_ARCHIVE_CONTENT_BYTES,
    MAX_ARCHIVE_FILE_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
    _read_canonical_entries,
    _verify_descriptors,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_contract import (
    ARCHIVE_SCHEMA_V2,
    validate_git_provenance_archive_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    canonical_grant_service_git_sources,
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_import_closure import (
    validate_grant_service_static_imports,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    raw_digest,
)
from modules.infrastructure.wre_core.src.wre_git_blob_batch_reader import (
    read_exact_git_blobs,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import (
    exact_git_tree_manifest,
)


def validate_grant_service_archive_git_provenance(
    raw: bytes, *, repo_root: Path | str, expected_repo_root_digest: str,
    expected_source_commit_sha: str, expected_object_format: str,
    expected_sources: Mapping[str, str], expected_source_policy_digest: str,
) -> Mapping[str, Any]:
    """Prove archive members against independently supplied source authority."""
    try:
        repo = Path(repo_root).resolve(strict=True)
        sources = canonical_grant_service_git_sources(expected_sources)
        _verify_expected_authority(
            repo, sources, expected_repo_root_digest,
            expected_source_policy_digest,
        )
        entries = _read_canonical_entries(raw)
        manifest = _git_manifest(entries)
        _verify_manifest_authority(
            manifest, sources, expected_source_commit_sha,
            expected_object_format,
        )
        _verify_descriptors(entries, manifest)
        validate_grant_service_static_imports(entries)
        _verify_git_objects(entries, manifest, repo)
        return MappingProxyType(manifest)
    except RuntimeArtifactManifestError:
        raise
    except Exception as exc:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_provenance_invalid"
        ) from exc


def _git_manifest(entries: Mapping[str, bytes]) -> dict[str, Any]:
    try:
        raw = entries[ARCHIVE_MANIFEST]
        value = json.loads(raw.decode("ascii"))
        if not isinstance(value, Mapping):
            raise TypeError("manifest not mapping")
        if value.get("schema_version") != ARCHIVE_SCHEMA_V2:
            raise RuntimeArtifactManifestError(
                "grant_service_archive_git_provenance_missing"
            )
        checked = validate_git_provenance_archive_manifest(value)
    except RuntimeArtifactManifestError:
        raise
    except (KeyError, UnicodeDecodeError, TypeError, ValueError) as exc:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_manifest_invalid"
        ) from exc
    if raw != canonical_json(checked).encode("ascii"):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_manifest_invalid"
        )
    return checked


def _verify_expected_authority(
    repo: Path, sources: Mapping[str, str], expected_root_digest: str,
    expected_policy_digest: str,
) -> None:
    if (
        raw_digest(str(repo).encode("utf-8")) != expected_root_digest
        or grant_service_git_source_policy_digest(sources)
        != expected_policy_digest
    ):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_authority_mismatch"
        )


def _verify_manifest_authority(
    manifest: Mapping[str, Any], sources: Mapping[str, str],
    expected_commit: str, expected_format: str,
) -> None:
    observed_sources = {
        str(item["path"]): str(item["source_path"])
        for item in manifest["files"] if item["source_kind"] == "git_blob"
    }
    if (
        manifest["source_commit_sha"] != expected_commit
        or manifest["source_object_format"] != expected_format
        or observed_sources != dict(sources)
    ):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_authority_mismatch"
        )


def _verify_git_objects(
    entries: Mapping[str, bytes], manifest: Mapping[str, Any], repo: Path,
) -> None:
    tree = exact_git_tree_manifest(repo, str(manifest["source_commit_sha"]))
    objects = {
        str(item["path"]): str(item["source_object_id"])
        for item in manifest["files"] if item["source_kind"] == "git_blob"
    }
    expected = {
        str(item["path"]): tree.blobs.get(str(item["source_path"]))
        for item in manifest["files"] if item["source_kind"] == "git_blob"
    }
    if tree.object_format != manifest["source_object_format"] or objects != expected:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_provenance_mismatch"
        )
    blobs = read_exact_git_blobs(
        repo, objects, object_format=tree.object_format,
        max_blob_bytes=MAX_ARCHIVE_FILE_BYTES,
        max_total_bytes=MAX_ARCHIVE_CONTENT_BYTES,
    )
    if any(blobs[path] != entries[path] for path in objects):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_provenance_mismatch"
        )


__all__ = ["validate_grant_service_archive_git_provenance"]
