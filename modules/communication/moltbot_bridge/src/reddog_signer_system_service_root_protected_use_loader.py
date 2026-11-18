"""Focused root protected-use capability loader for the signer service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_runtime_materializer import (
    materialize_root_protected_use_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    _load_owner_config,
)


def load_system_service_root_protected_use_authority(
    *, owner_config_path: Path | str, repo_root: Path,
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    request_signer: Callable[[str], str], now_epoch: int | None = None,
) -> Any:
    """Mint the opaque atomic protected-use client from root owner state."""

    repo = Path(repo_root).resolve()
    owner = _load_owner_config(owner_config_path, repo=repo)
    return materialize_root_protected_use_authority(
        owner=owner, repo=repo, policy=policy, binding=binding,
        request_signer=request_signer, now_epoch=now_epoch,
    )


__all__ = ["load_system_service_root_protected_use_authority"]
