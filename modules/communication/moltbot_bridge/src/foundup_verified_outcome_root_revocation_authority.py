"""Opaque server authority for current-generation revocation validation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    ValidatedOwnerE0Lease,
    lease_validated_owner_e0_current_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    _build_process_local_registry,
)


@dataclass(frozen=True)
class _AuthorityState:
    owner_config_path: Path
    repo_root: Path


_issue_authority, _lookup_authority = _build_process_local_registry(
    "root_revocation_service_authority_unverified"
)
del _build_process_local_registry


class RootRevocationServiceAuthority:
    """Process-local proof that root selected the policy validation source."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_factory_required")

    def __copy__(self) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("root_revocation_service_authority_pickle_forbidden")


def _create_root_revocation_service_authority(
    *, owner_config_path: Path | str, repo_root: Path | str,
) -> RootRevocationServiceAuthority:
    repo = Path(repo_root).resolve()
    owner = Path(owner_config_path).resolve()
    if repo == owner or repo in owner.parents:
        raise ValueError("root_revocation_owner_config_path_invalid")
    authority = object.__new__(RootRevocationServiceAuthority)
    _issue_authority(authority, _AuthorityState(owner, repo))
    return authority


@contextmanager
def lease_root_revocation_policy(
    authority: object, policy: Mapping[str, Any],
) -> Iterator[ValidatedOwnerE0Lease]:
    state = _lookup_authority(authority)
    with lease_validated_owner_e0_current_admission(
        owner_config_path=state.owner_config_path,
        repo_root=state.repo_root,
        policy=policy,
    ) as lease:
        yield lease


def root_revocation_authority_repo(authority: object) -> Path:
    return _lookup_authority(authority).repo_root


__all__ = [
    "RootRevocationServiceAuthority",
    "lease_root_revocation_policy",
    "root_revocation_authority_repo",
]
