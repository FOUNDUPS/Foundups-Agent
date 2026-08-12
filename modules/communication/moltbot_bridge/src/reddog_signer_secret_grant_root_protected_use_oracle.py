"""Composed E0 oracle using the existing root protected-use service."""

from __future__ import annotations

from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    RootProtectedUseAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_durable_oracle import (
    UncomposedDurableSignerGrantRevocationOracle,
)

_T = TypeVar("_T")


class RootAuthorizedSignerGrantRevocationOracle:
    """Pair durable revocation reads with root-linearized callback admission."""

    __slots__ = ("_durable", "_protected_use")

    def __init__(
        self,
        *,
        durable: UncomposedDurableSignerGrantRevocationOracle,
        protected_use: RootProtectedUseAuthority,
    ) -> None:
        if (
            type(durable) is not UncomposedDurableSignerGrantRevocationOracle
            or type(protected_use) is not RootProtectedUseAuthority
        ):
            raise ValueError("root_authorized_revocation_oracle_invalid")
        self._durable = durable
        self._protected_use = protected_use

    def is_revoked(self, *, grant_id: str, key_epoch: str, at_epoch: int) -> bool:
        return self._durable.is_revoked(
            grant_id=grant_id, key_epoch=key_epoch, at_epoch=at_epoch
        )

    def authorize_grant_use(
        self, grant: Mapping[str, Any], action: Callable[[], _T]
    ) -> _T:
        return self._protected_use.authorize_use(
            grant_id=str(grant["grant_id"]),
            key_epoch=str(grant["key_epoch"]),
            signing_request_digest=str(grant["signing_request_digest"]),
            grant_expires_at=int(grant["expires_at"]),
            action=action,
        )


__all__ = ["RootAuthorizedSignerGrantRevocationOracle"]
