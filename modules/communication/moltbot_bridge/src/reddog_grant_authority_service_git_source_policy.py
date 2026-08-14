"""Canonical source-path policy for Git-provenanced grant archives."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    MAX_ARCHIVE_FILES,
    valid_archive_path,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import (
    portable_git_path,
)

SOURCE_POLICY_SCHEMA = "reddog_grant_authority_service_git_source_policy.v1"


def canonical_grant_service_git_sources(
    value: Mapping[str, str],
) -> Mapping[str, str]:
    """Return one strict one-to-one archive-to-repository source map."""
    sources = dict(value) if isinstance(value, Mapping) else {}
    if (
        "__main__.py" in sources
        or "reddog_grant_authority_service.py" not in sources
        or not 1 <= len(sources) < MAX_ARCHIVE_FILES
        or len(set(sources.values())) != len(sources)
        or any(
            not isinstance(archive_path, str)
            or not valid_archive_path(archive_path)
            or not archive_path.endswith(".py")
            or not isinstance(source_path, str)
            or not portable_git_path(source_path)
            for archive_path, source_path in sources.items()
        )
    ):
        raise RuntimeArtifactManifestError(
            "grant_service_archive_source_binding_invalid"
        )
    return MappingProxyType(
        {path: sources[path] for path in sorted(sources)}
    )


def grant_service_git_source_policy_digest(
    value: Mapping[str, str],
) -> str:
    """Bind the complete canonical source map for independent authorization."""
    sources = canonical_grant_service_git_sources(value)
    return digest({
        "schema_version": SOURCE_POLICY_SCHEMA, "sources": dict(sources),
    })


__all__ = [
    "SOURCE_POLICY_SCHEMA", "canonical_grant_service_git_sources",
    "grant_service_git_source_policy_digest",
]
