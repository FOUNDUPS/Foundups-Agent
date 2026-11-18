"""Build a grant-service archive only from exact committed Git blobs."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MAIN,
    MAX_ARCHIVE_CONTENT_BYTES,
    MAX_ARCHIVE_FILE_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_contract import (
    build_git_provenance_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    canonical_grant_service_git_sources,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.infrastructure.wre_core.src.wre_git_blob_batch_reader import (
    read_exact_git_blobs,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import (
    exact_git_tree_manifest,
)


def build_grant_service_archive_from_git(
    *, repo_root: Path | str, source_commit_sha: str,
    sources: Mapping[str, str],
) -> bytes:
    """Build canonical archive bytes without reading the checkout worktree."""
    try:
        return _build(repo_root, source_commit_sha, sources)
    except RuntimeArtifactManifestError:
        raise
    except Exception as exc:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_git_source_invalid"
        ) from exc


def _build(
    repo_root: Path | str, source_commit_sha: str, sources: Mapping[str, str],
) -> bytes:
    repo = Path(repo_root).resolve(strict=True)
    manifest = exact_git_tree_manifest(repo, source_commit_sha)
    normalized = canonical_grant_service_git_sources(sources)
    payloads = {"__main__.py": ARCHIVE_MAIN}
    bindings: dict[str, dict[str, str]] = {}
    objects: dict[str, str] = {}
    for archive_path, source_path in normalized.items():
        object_id = manifest.blobs.get(source_path)
        if object_id is None:
            raise RuntimeArtifactManifestError(
                "grant_service_archive_git_source_missing"
            )
        objects[archive_path] = object_id
        bindings[archive_path] = {
            "source_path": source_path,
            "source_object_id": object_id,
        }
    payloads.update(read_exact_git_blobs(
        repo, objects, object_format=manifest.object_format,
        max_blob_bytes=MAX_ARCHIVE_FILE_BYTES,
        max_total_bytes=MAX_ARCHIVE_CONTENT_BYTES - len(ARCHIVE_MAIN),
    ))
    return build_git_provenance_grant_service_archive(
        payloads, source_commit_sha=manifest.commit_sha,
        source_object_format=manifest.object_format,
        source_bindings=bindings,
    )


__all__ = ["build_grant_service_archive_from_git"]
