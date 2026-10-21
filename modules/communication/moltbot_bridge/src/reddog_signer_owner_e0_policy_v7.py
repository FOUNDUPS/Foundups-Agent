"""Exact-Git archive and installed-source provenance for signer owner policy."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_v6 import (
    POLICY_FIELDS_V5,
    GRANT_SERVICE_FIELDS,
)


POLICY_SCHEMA_V7 = POLICY_PREFIX_V7 = "reddog-signer-owner-e0-policy.v7"
GRANT_SERVICE_GIT_PROVENANCE_FIELDS = frozenset(
    {
        "grant_authority_source_repo_root_digest",
        "grant_authority_source_commit_sha",
        "grant_authority_source_object_format",
        "grant_authority_source_policy_digest",
        "grant_authority_archive_source_descriptor_digest",
    }
)
POLICY_FIELDS_V7 = (
    POLICY_FIELDS_V5 | GRANT_SERVICE_FIELDS | GRANT_SERVICE_GIT_PROVENANCE_FIELDS
)
GRANT_SERVICE_GIT_PROVENANCE_DIGEST_FIELDS = (
    "grant_authority_source_repo_root_digest",
    "grant_authority_source_policy_digest",
    "grant_authority_archive_source_descriptor_digest",
)
POLICY_SCHEMA_V10 = "reddog-signer-owner-e0-policy.v10"
INSTALLED_DESCRIPTOR_FIELD = "grant_authority_installed_runtime_descriptor_digest"
POLICY_FIELDS_V10 = (POLICY_FIELDS_V7 - {
    "grant_authority_archive_source_descriptor_digest"}) | {INSTALLED_DESCRIPTOR_FIELD}
GRANT_SERVICE_INSTALLED_DIGEST_FIELDS = (
    "grant_authority_source_repo_root_digest", "grant_authority_source_policy_digest",
    INSTALLED_DESCRIPTOR_FIELD,
)


def require_grant_service_git_provenance_bindings(
    raw: Mapping[str, Any],
) -> None:
    """Reject incomplete or internally inconsistent signed Git authority."""

    if not _valid_source_identity(raw) or any(
        not is_sha256(raw.get(name)) for name in GRANT_SERVICE_GIT_PROVENANCE_DIGEST_FIELDS
    ):
        raise ValueError("signer_owner_e0_grant_service_git_provenance_invalid")


def _valid_source_identity(raw: Mapping[str, Any]) -> bool:
    object_format = raw.get("grant_authority_source_object_format")
    commit = raw.get("grant_authority_source_commit_sha")
    expected_length = 40 if object_format == "sha1" else 64
    return (object_format in {"sha1", "sha256"} and isinstance(commit, str)
            and len(commit) == expected_length
            and all(char in "0123456789abcdef" for char in commit))


def require_grant_service_installed_source_bindings(raw: Mapping[str, Any]) -> None:
    """V10 admits only initial LOW handshake scope, never archive/work authority."""
    if (not _valid_source_identity(raw)
            or any(not is_sha256(raw.get(name)) for name in GRANT_SERVICE_INSTALLED_DIGEST_FIELDS)
            or raw.get("generation") != 1
            or raw.get("allowed_operations") != ["signer_socket_peer_handshake"]
            or raw.get("allowed_authority_tiers") != ["LOW"]
            or raw.get("consensus_required_tiers") != []):
        raise ValueError("signer_owner_e0_installed_initial_scope_invalid")


__all__ = [
    "GRANT_SERVICE_GIT_PROVENANCE_DIGEST_FIELDS",
    "GRANT_SERVICE_GIT_PROVENANCE_FIELDS",
    "POLICY_FIELDS_V7",
    "POLICY_PREFIX_V7",
    "POLICY_SCHEMA_V7",
    "require_grant_service_git_provenance_bindings",
]
