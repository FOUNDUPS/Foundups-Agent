"""Materialize root authority service dependencies from authenticated owner state."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_dependency import (
    RootAuthorityServiceDependencies,
    build_root_authority_service_dependencies,
    state_binding_from_owner_config,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)

OwnerSupplier = Callable[[], Mapping[str, Any]]


def materialize_root_authority_service_dependencies(
    *, owner_config_path: Path | str, repo: Path,
    owner_supplier: OwnerSupplier,
) -> RootAuthorityServiceDependencies:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
        _create_root_revocation_service_authority,
    )

    owner = owner_supplier()
    raw = _root_policy(owner)

    def supply() -> RootAuthoritySnapshot:
        current = owner_supplier()
        current_raw = _root_policy(current)
        descriptor = dict(current_raw["descriptor"])
        return RootAuthoritySnapshot(
            owner_config_id=str(current["config_id"]),
            authority_generation_sequence=int(
                descriptor["authority_generation_sequence"]
            ),
            state_binding_digest=state_binding_from_owner_config(
                current_raw, repo=repo
            ),
            signer_principal_id=str(current_raw["signer_principal_id"]),
            signer_uid=int(current_raw["signer_uid"]),
            signer_gid=int(current_raw["signer_gid"]),
            descriptor=descriptor,
        )

    return build_root_authority_service_dependencies(
        raw, repo=repo, snapshot_supplier=supply,
        revocation_authority=_create_root_revocation_service_authority(
            owner_config_path=owner_config_path, repo_root=repo,
        ),
    )


def materialize_revocation_anchor_authority(
    *, owner: Mapping[str, Any], repo: Path, policy: Mapping[str, Any],
    binding: SignerGrantRevocationAuthorityBinding,
    request_signer: Callable[[str], str], now_epoch: int | None,
) -> Any:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
        _create_root_revocation_anchor_authority,
    )

    raw = _root_policy(owner)
    exchange = build_root_authority_socket_exchange(
        repo_root=repo, socket_path=raw["authority_socket_path"],
        expected_server_uid=int(raw["authority_service_uid"]),
    )
    return _create_root_revocation_anchor_authority(
        raw["descriptor"], owner_config_id=str(owner["config_id"]),
        policy=policy, binding=binding, exchange=exchange,
        request_signer=request_signer,
        now_epoch=int(time.time()) if now_epoch is None else now_epoch,
    )


def _root_policy(owner: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = owner.get("verified_outcome_authority")
    if not isinstance(raw, Mapping) or not isinstance(raw.get("descriptor"), Mapping):
        raise RuntimeArtifactManifestError("verified_outcome_authority_missing")
    return raw


__all__ = [
    "materialize_revocation_anchor_authority",
    "materialize_root_authority_service_dependencies",
]
