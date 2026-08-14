"""Root-owned grant-service runtime assignment from owner config v3/v4."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
    CONFIG_SCHEMA_V2,
    validate_grant_service_config,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_provenance_admission import (
    derive_current_grant_service_git_provenance,
)

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_CONFIG,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
    SCHEMA_VERSION_V3,
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


OWNER_OPERATION_LOCK = ".reddog-grant-owner-operation.lock"


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
        SCHEMA_VERSION_V4,
        _load_owner_config,
    )

    path = Path(owner_config_path).resolve()
    owner = _load_owner_config(path, repo=repo_root)
    if (
        owner.get("schema_version") not in {SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}
        or owner.get("config_id") != expected_owner_config_id
    ):
        raise RuntimeArtifactManifestError(
            "grant_authority_owner_binding_mismatch"
        )
    validate_independent_grant_authority_owner_config(
        owner, repo=repo_root, owner_root=path.parent
    )
    return Path(owner["independent_grant_authority"]["authority_root"]).resolve()


@contextmanager
def grant_authority_owner_operation_fence(
    owner_config_path: Path | str, *, repo_root: Path | str
) -> Iterator[None]:
    """Serialize provisioning with compliant root-owner rotation."""

    owner = Path(owner_config_path).resolve()
    with confined_runtime_operation_lock(
        owner.parent / OWNER_OPERATION_LOCK,
        repo_root=Path(repo_root).resolve(),
        allowed_root=owner.parent,
    ):
        yield


def require_grant_authority_provisioning_binding(
    *, owner_config_path: Path | str, repo_root: Path | str,
    runtime_root: Path | str, source_policy: Mapping[str, Any],
    manifest_authority: object, manifest_boundary: Any,
    manifest: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Bind current owner, exact-Git archive, config v2, and manifest v3."""

    repo = Path(repo_root).resolve()
    runtime = Path(runtime_root).resolve()
    owner_id = str(source_policy.get("owner_config_id") or "")
    if grant_authority_owner_runtime_root(
        owner_config_path, repo, owner_id
    ) != runtime:
        raise RuntimeArtifactManifestError("grant_authority_owner_root_mismatch")
    provenance = derive_current_grant_service_git_provenance(
        manifest_authority, manifest_boundary
    )
    expected = {
        "grant_authority_source_repo_root_digest": source_policy.get(
            "repo_root_digest"
        ),
        "grant_authority_source_policy_digest": source_policy.get(
            "source_policy_digest"
        ),
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise RuntimeArtifactManifestError("grant_source_policy_binding_mismatch")
    config = validate_grant_service_config(
        read_reddog_runtime_json_mapping(
            runtime / GRANT_AUTHORITY_SERVICE_CONFIG, allowed_root=runtime
        )
    )
    config_expected = {
        "schema_version": CONFIG_SCHEMA_V2,
        "source_policy_owner_config_id": owner_id,
        "source_policy_repo_root_digest": source_policy.get("repo_root_digest"),
        "source_policy_digest": source_policy.get("source_policy_digest"),
    }
    if any(config.get(key) != value for key, value in config_expected.items()):
        raise RuntimeArtifactManifestError("grant_source_policy_config_mismatch")
    if manifest is not None:
        manifest_expected = {
            "schema_version": SCHEMA_VERSION_V3,
            "runtime_profile": RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
            **expected,
        }
        if any(manifest.get(key) != value for key, value in manifest_expected.items()):
            raise RuntimeArtifactManifestError("grant_source_policy_manifest_mismatch")
    return provenance


__all__ = [
    "OWNER_OPERATION_LOCK",
    "grant_authority_owner_operation_fence",
    "grant_authority_owner_runtime_root",
    "require_grant_authority_provisioning_binding",
]
