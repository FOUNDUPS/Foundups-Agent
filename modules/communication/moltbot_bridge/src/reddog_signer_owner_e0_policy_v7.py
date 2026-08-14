"""Additive v7 exact-Git provenance fields for signer owner policy."""

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


def require_grant_service_git_provenance_bindings(
    raw: Mapping[str, Any],
) -> None:
    """Reject incomplete or internally inconsistent signed Git authority."""

    object_format = raw.get("grant_authority_source_object_format")
    commit = raw.get("grant_authority_source_commit_sha")
    expected_length = 40 if object_format == "sha1" else 64
    if (
        object_format not in {"sha1", "sha256"}
        or not isinstance(commit, str)
        or len(commit) != expected_length
        or any(char not in "0123456789abcdef" for char in commit)
        or any(
            not is_sha256(raw.get(name))
            for name in GRANT_SERVICE_GIT_PROVENANCE_DIGEST_FIELDS
        )
    ):
        raise ValueError("signer_owner_e0_grant_service_git_provenance_invalid")


__all__ = [
    "GRANT_SERVICE_GIT_PROVENANCE_DIGEST_FIELDS",
    "GRANT_SERVICE_GIT_PROVENANCE_FIELDS",
    "POLICY_FIELDS_V7",
    "POLICY_PREFIX_V7",
    "POLICY_SCHEMA_V7",
    "require_grant_service_git_provenance_bindings",
]
