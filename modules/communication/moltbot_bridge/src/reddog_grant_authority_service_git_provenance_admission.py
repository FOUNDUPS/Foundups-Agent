"""Authenticated exact-Git provenance admission for grant archives."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MANIFEST,
    MAX_ARCHIVE_CONTENT_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
    _read_canonical_entries,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_contract import (
    validate_git_provenance_archive_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_validation import (
    validate_grant_service_archive_git_provenance,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    RuntimeArtifactManifestError,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)


PROVENANCE_BINDING_FIELDS = frozenset(
    {
        "grant_authority_source_repo_root_digest",
        "grant_authority_source_commit_sha",
        "grant_authority_source_object_format",
        "grant_authority_source_policy_digest",
        "grant_authority_archive_source_descriptor_digest",
    }
)


def derive_grant_service_git_provenance(
    raw: bytes,
    *,
    repo_root: Path | str,
    expected_repo_root_digest: str,
    expected_source_commit_sha: str,
) -> Mapping[str, Any]:
    """Derive a claim from v2 bytes, then verify it against exact Git."""

    try:
        manifest, sources = _archive_provenance_claim(raw)
        policy_digest = grant_service_git_source_policy_digest(sources)
        validate_grant_service_archive_git_provenance(
            raw,
            repo_root=repo_root,
            expected_repo_root_digest=expected_repo_root_digest,
            expected_source_commit_sha=expected_source_commit_sha,
            expected_object_format=str(manifest["source_object_format"]),
            expected_sources=sources,
            expected_source_policy_digest=policy_digest,
        )
        return MappingProxyType(
            {
                "grant_authority_source_repo_root_digest": (
                    expected_repo_root_digest
                ),
                "grant_authority_source_commit_sha": (
                    expected_source_commit_sha
                ),
                "grant_authority_source_object_format": str(
                    manifest["source_object_format"]
                ),
                "grant_authority_source_policy_digest": policy_digest,
                "grant_authority_archive_source_descriptor_digest": str(
                    manifest["archive_source_descriptor_digest"]
                ),
            }
        )
    except RuntimeArtifactManifestError:
        raise
    except Exception as exc:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_provenance_invalid"
        ) from exc


def _archive_provenance_claim(
    raw: bytes,
) -> tuple[Mapping[str, Any], dict[str, str]]:
    entries = _read_canonical_entries(raw)
    parsed = json.loads(entries[ARCHIVE_MANIFEST].decode("ascii"))
    manifest = validate_git_provenance_archive_manifest(parsed)
    sources = {
        str(item["path"]): str(item["source_path"])
        for item in manifest["files"]
        if item["source_kind"] == "git_blob"
    }
    return manifest, sources


def derive_current_grant_service_git_provenance(
    authority: object,
    boundary: Any,
) -> Mapping[str, Any]:
    """Read the confined archive under one opaque authenticated authority."""

    values = boundary.require(authority)
    repo = Path(values["repo_root"]).resolve()
    runtime = Path(values["runtime_root"]).resolve()
    target = validate_runtime_artifact_path(
        runtime / GRANT_AUTHORITY_SERVICE_ARCHIVE,
        repo_root=repo,
        allowed_root=runtime,
    )
    raw = secure_read_confined_bytes(
        target,
        allowed_root=runtime,
        max_bytes=MAX_ARCHIVE_CONTENT_BYTES,
    )[0]
    return derive_grant_service_git_provenance(
        raw,
        repo_root=repo,
        expected_repo_root_digest=str(values["repo_root_digest"]),
        expected_source_commit_sha=str(values["authorized_base_sha"]),
    )


def require_matching_git_provenance(
    candidate: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """Require an exact field-for-field provenance match."""

    if any(candidate.get(name) != expected.get(name) for name in PROVENANCE_BINDING_FIELDS):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_authority_mismatch"
        )


__all__ = [
    "PROVENANCE_BINDING_FIELDS",
    "derive_current_grant_service_git_provenance",
    "derive_grant_service_git_provenance",
    "require_matching_git_provenance",
]
