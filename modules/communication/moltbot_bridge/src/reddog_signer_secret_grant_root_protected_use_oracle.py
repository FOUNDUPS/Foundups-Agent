"""Composed E0 oracle using the existing root protected-use service."""

from __future__ import annotations

from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    RootProtectedUseAuthority,
    _lookup_client,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_capability_state import (
    freeze_owner_e0_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
    expected_snapshot_binding,
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

    def matches_owner(
        self, *, policy: Mapping[str, Any],
        binding: SignerGrantRevocationAuthorityBinding,
    ) -> bool:
        """Match both oracle halves to one leased owner without performing I/O."""
        try:
            if self._protected_use is None:
                from .foundup_verified_outcome_root_revocation_client import _lookup_client as lookup_anchor
                from .foundup_verified_outcome_root_revocation_protocol import GRANT_ROLE
                anchor = lookup_anchor(self._durable.anchor)
                return bool(type(self) is RootAuthorizedSignerGrantRevocationOracle
                    and type(self._durable) is UncomposedDurableSignerGrantRevocationOracle
                    and type(binding) is SignerGrantRevocationAuthorityBinding
                    and self._durable.binding == binding == anchor.binding
                    and self._durable.expected == expected_snapshot_binding(policy, binding)
                    and anchor.requester_role == GRANT_ROLE
                    and anchor.owner_config_id == policy["owner_config_id"]
                    and anchor.policy == freeze_owner_e0_policy(policy))
            client = _lookup_client(self._protected_use)
            return bool(
                type(self) is RootAuthorizedSignerGrantRevocationOracle
                and type(self._durable) is UncomposedDurableSignerGrantRevocationOracle
                and type(binding) is SignerGrantRevocationAuthorityBinding
                and self._durable.binding == binding
                and self._durable.expected == expected_snapshot_binding(policy, binding)
                and client.binding == binding
                and client.owner_config_id == policy["owner_config_id"]
                and client.policy == freeze_owner_e0_policy(policy)
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def is_revoked(self, *, grant_id: str, key_epoch: str, at_epoch: int) -> bool:
        return self._durable.is_revoked(
            grant_id=grant_id, key_epoch=key_epoch, at_epoch=at_epoch
        )

    def is_key_epoch_revoked(self, *, key_epoch: str, at_epoch: int) -> bool:
        return self._durable.is_key_epoch_revoked(
            key_epoch=key_epoch, at_epoch=at_epoch
        )

    @property
    def binding(self):
        return self._durable.binding

    def authorize_key_epoch_use(
        self, *, key_epoch: str, at_epoch: int, expires_at: int,
        action: Callable[[], _T],
    ) -> _T:
        if self._protected_use is None:
            from .foundup_verified_outcome_root_revocation_client import _lookup_client as lookup_anchor
            anchor = lookup_anchor(self._durable.anchor)
            if (not self.matches_owner(policy=anchor.policy, binding=anchor.binding)
                    or key_epoch != anchor.policy["grant_authority_key_epoch"]):
                raise ValueError("grant_issuer_oracle_epoch_invalid")
        return self._durable.authorize_key_epoch_use(
            key_epoch=key_epoch, at_epoch=at_epoch,
            expires_at=expires_at, action=action,
        )

    def authorize_grant_use(
        self, grant: Mapping[str, Any], action: Callable[[], _T]
    ) -> _T:
        if self._protected_use is None:
            raise ValueError("grant_issuer_oracle_cannot_authorize_target_grant")
        return self._protected_use.authorize_use(
            grant_id=str(grant["grant_id"]),
            key_epoch=str(grant["key_epoch"]),
            signing_request_digest=str(grant["signing_request_digest"]),
            grant_expires_at=int(grant["expires_at"]),
            action=action,
        )


def build_grant_issuer_revocation_oracle(*, durable, policy, binding):
    """Issuer-only oracle using an authenticated LOAD client, no dummy control."""
    if type(durable) is not UncomposedDurableSignerGrantRevocationOracle:
        raise ValueError("grant_issuer_oracle_dependency_invalid")
    oracle = object.__new__(RootAuthorizedSignerGrantRevocationOracle)
    oracle._durable, oracle._protected_use = durable, None
    if not oracle.matches_owner(policy=policy, binding=binding):
        raise ValueError("grant_issuer_oracle_owner_mismatch")
    return oracle


__all__ = ["RootAuthorizedSignerGrantRevocationOracle", "build_grant_issuer_revocation_oracle"]
