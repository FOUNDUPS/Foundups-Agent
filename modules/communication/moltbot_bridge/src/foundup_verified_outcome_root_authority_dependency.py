"""Validated construction of root verified-outcome service dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
    validate_root_authority_state_paths,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


@dataclass(frozen=True)
class RootAuthorityServiceDependencies:
    state: RootVerifiedOutcomeAuthorityState
    snapshot_supplier: Callable[[], RootAuthoritySnapshot]
    socket_path: str
    signer_uid: int
    signer_gid: int
    signer_principal_id: str


def build_root_authority_service_dependencies(
    raw: Mapping[str, Any],
    *,
    repo: Path,
    snapshot_supplier: Callable[[], RootAuthoritySnapshot],
) -> RootAuthorityServiceDependencies:
    paths = _state_paths(raw, repo=repo)
    validate_root_authority_state_paths(
        paths["state_root"],
        paths["state_witness_root"],
        paths["installation_root"],
        files=tuple(
            paths[name]
            for name in (
                "state_path",
                "state_witness_path",
                "installation_path",
            )
        ),
    )
    stores = tuple(
        _state_store(raw, paths=paths, repo=repo, prefix=prefix)
        for prefix in ("state", "state_witness", "installation")
    )
    return RootAuthorityServiceDependencies(
        state=RootVerifiedOutcomeAuthorityState(
            *stores, repo_root=repo, require_root_ownership=True
        ),
        snapshot_supplier=snapshot_supplier,
        socket_path=str(raw["authority_socket_path"]),
        signer_uid=int(raw["signer_uid"]),
        signer_gid=int(raw["signer_gid"]),
        signer_principal_id=str(raw["signer_principal_id"]),
    )


def _state_store(
    raw: Mapping[str, Any],
    *,
    paths: Mapping[str, Path],
    repo: Path,
    prefix: str,
) -> SqliteMonotonicAuthorityStore:
    return SqliteMonotonicAuthorityStore(
        paths[f"{prefix}_path"],
        allowed_root=paths[f"{prefix}_root"],
        repo_root=repo,
        store_id=str(raw[f"{prefix}_store_id"]),
        durability_receipt_id=str(raw[f"{prefix}_durability_receipt_id"]),
    )


def _state_paths(raw: Mapping[str, Any], *, repo: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for prefix in ("state", "state_witness", "installation"):
        root = validate_runtime_root_path(raw[f"{prefix}_root"], repo_root=repo)
        result[f"{prefix}_root"] = root
        result[f"{prefix}_path"] = validate_runtime_artifact_path(
            raw[f"{prefix}_path"], allowed_root=root, repo_root=repo
        )
    return result


__all__ = [
    "RootAuthorityServiceDependencies",
    "build_root_authority_service_dependencies",
]
