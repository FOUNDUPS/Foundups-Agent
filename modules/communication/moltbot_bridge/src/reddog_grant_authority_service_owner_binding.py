"""Root-owned grant-service runtime assignment from owner config v3."""

from __future__ import annotations

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)


def grant_authority_owner_runtime_root(
    owner_config_path: Path | str,
    repo_root: Path,
    expected_owner_config_id: str,
) -> Path:
    """Load and validate the existing owner-config grant assignment."""

    from .reddog_signer_independent_grant_authority_client_supply import (
        validate_independent_grant_authority_owner_config,
    )
    from .reddog_signer_system_service_manifest_selection_loader import (
        SCHEMA_VERSION_V3,
        _load_owner_config,
    )

    path = Path(owner_config_path).resolve()
    owner = _load_owner_config(path, repo=repo_root)
    if (
        owner.get("schema_version") != SCHEMA_VERSION_V3
        or owner.get("config_id") != expected_owner_config_id
    ):
        raise RuntimeArtifactManifestError(
            "grant_authority_owner_binding_mismatch"
        )
    validate_independent_grant_authority_owner_config(
        owner, repo=repo_root, owner_root=path.parent
    )
    return Path(owner["independent_grant_authority"]["authority_root"]).resolve()


__all__ = ["grant_authority_owner_runtime_root"]
