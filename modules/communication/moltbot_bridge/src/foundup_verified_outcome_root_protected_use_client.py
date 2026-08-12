"""Opaque signer-side client for root-linearized protected use."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    RootAuthorityExchange,
    _lookup_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client_exchange import (
    exchange_protected_use,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
    OP_ACQUIRE,
    OP_FINISH,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_capability_state import (
    freeze_owner_e0_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    validated_signer_owner_e0_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    _build_process_local_registry,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class _ClientState:
    descriptor: Mapping[str, Any]
    owner_config_id: str
    policy: Mapping[str, Any]
    binding: SignerGrantRevocationAuthorityBinding
    exchange: RootAuthorityExchange
    request_signer: Callable[[str], str]


_issue_client, _lookup_client = _build_process_local_registry(
    "root_protected_use_client_unverified"
)
del _build_process_local_registry


class RootProtectedUseAuthority:
    """Factory-issued RPC capability that encloses one exact callback."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "RootProtectedUseAuthority":
        raise TypeError("root_protected_use_client_factory_required")

    def authorize_use(
        self, *, grant_id: str, key_epoch: str,
        signing_request_digest: str, grant_expires_at: int,
        action: Callable[[], _T],
    ) -> _T:
        import secrets

        if not callable(action):
            raise ValueError("root_protected_use_action_invalid")
        use_nonce = secrets.token_hex(32)
        acquired = _acquire(
            self, grant_id, key_epoch, signing_request_digest,
            use_nonce, grant_expires_at,
        )
        try:
            result = action()
        except BaseException:
            _finish(
                self, grant_id, key_epoch, signing_request_digest,
                use_nonce, grant_expires_at, acquired,
            )
            raise
        _finish(
            self, grant_id, key_epoch, signing_request_digest,
            use_nonce, grant_expires_at, acquired,
        )
        return result

    def __copy__(self) -> "RootProtectedUseAuthority":
        raise TypeError("root_protected_use_client_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootProtectedUseAuthority":
        raise TypeError("root_protected_use_client_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("root_protected_use_client_pickle_forbidden")


def _create_root_protected_use_authority(
    descriptor: Mapping[str, Any], *, owner_config_id: str,
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    exchange: RootAuthorityExchange, request_signer: Callable[[str], str],
    now_epoch: int,
) -> RootProtectedUseAuthority:
    checked = validated_signer_owner_e0_policy(policy, now_epoch=now_epoch)
    root_descriptor = validate_root_verified_outcome_descriptor_public(
        descriptor, now_epoch=now_epoch
    )
    if not _valid_dependencies(
        checked, root_descriptor, owner_config_id, binding, exchange,
        request_signer,
    ):
        raise ValueError("root_protected_use_client_invalid")
    authority = object.__new__(RootProtectedUseAuthority)
    _issue_client(authority, _ClientState(
        descriptor=root_descriptor, owner_config_id=owner_config_id,
        policy=freeze_owner_e0_policy(checked), binding=binding,
        exchange=exchange, request_signer=request_signer,
    ))
    return authority


def _valid_dependencies(
    policy: Mapping[str, Any], descriptor: Mapping[str, Any], owner_config_id: str,
    binding: object, exchange: object, request_signer: object,
) -> bool:
    return bool(
        type(binding) is SignerGrantRevocationAuthorityBinding
        and type(exchange) is RootAuthorityExchange and callable(request_signer)
        and _lookup_exchange(exchange).expected_uid == 0
        and owner_config_id == policy["owner_config_id"]
        and policy["target_signer_public_key"] == descriptor["signer_public_key"]
        and binding.policy_id == policy["policy_id"]
    )


def _finish(
    authority: object, grant_id: str, key_epoch: str,
    request_digest: str, use_nonce: str, expires_at: int,
    acquired: ProposalReplayHighWater,
) -> None:
    failure: Exception | None = None
    for _attempt in range(2):
        try:
            finished = _exchange(
                authority, OP_FINISH, grant_id, key_epoch, request_digest,
                use_nonce, expires_at, acquired,
            )
            if finished.sequence != acquired.sequence + 1:
                raise ValueError("root_protected_use_finish_invalid")
            return
        except Exception as exc:
            failure = exc
    assert failure is not None
    raise failure


def _acquire(
    authority: object, grant_id: str, key_epoch: str,
    request_digest: str, use_nonce: str, expires_at: int,
) -> ProposalReplayHighWater:
    failure: Exception | None = None
    for _attempt in range(2):
        try:
            return _exchange(
                authority, OP_ACQUIRE, grant_id, key_epoch, request_digest,
                use_nonce, expires_at, None,
            )
        except Exception as exc:
            failure = exc
    assert failure is not None
    raise failure


def _exchange(
    authority: object, operation: str, grant_id: str, key_epoch: str,
    request_digest: str, use_nonce: str, expires_at: int,
    acquired: ProposalReplayHighWater | None,
) -> ProposalReplayHighWater:
    state = _lookup_client(authority)
    return exchange_protected_use(
        descriptor=state.descriptor, owner_config_id=state.owner_config_id,
        policy=state.policy, binding=state.binding, transport=state.exchange,
        request_signer=state.request_signer, operation=operation,
        grant_id=grant_id, key_epoch=key_epoch,
        signing_request_digest=request_digest, use_nonce=use_nonce,
        grant_expires_at=expires_at, acquired=acquired,
    )


__all__ = ["RootProtectedUseAuthority"]
