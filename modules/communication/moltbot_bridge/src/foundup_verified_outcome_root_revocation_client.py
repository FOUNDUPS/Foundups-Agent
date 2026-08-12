"""Opaque signer-side client for root-owned revocation anchor state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    RootAuthorityExchange,
    _lookup_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    OP_ADVANCE,
    OP_LOAD,
    RootRevocationRequest,
    canonical_signer_input,
    request_id_for,
    response_from_bytes,
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


@dataclass(frozen=True)
class _ClientState:
    descriptor: Mapping[str, Any]
    owner_config_id: str
    policy: Mapping[str, Any]
    binding: SignerGrantRevocationAuthorityBinding
    exchange: RootAuthorityExchange
    request_signer: Callable[[str], str]


_issue_client, _lookup_client = _build_process_local_registry(
    "root_revocation_anchor_client_unverified"
)
del _build_process_local_registry


class RootRevocationAnchorAuthority:
    """Factory-issued RPC capability with no local root-state object."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "RootRevocationAnchorAuthority":
        raise TypeError("root_revocation_anchor_client_factory_required")

    def load(self) -> ProposalReplayHighWater | None:
        return _exchange(self, operation=OP_LOAD, snapshot_id=None)

    def advance_snapshot(self, snapshot_id: str) -> ProposalReplayHighWater:
        value = _exchange(self, operation=OP_ADVANCE, snapshot_id=snapshot_id)
        if value is None:
            raise ValueError("root_revocation_anchor_advance_empty")
        return value

    def __copy__(self) -> "RootRevocationAnchorAuthority":
        raise TypeError("root_revocation_anchor_client_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootRevocationAnchorAuthority":
        raise TypeError("root_revocation_anchor_client_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("root_revocation_anchor_client_pickle_forbidden")


def _create_root_revocation_anchor_authority(
    descriptor: Mapping[str, Any], *, owner_config_id: str,
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    exchange: RootAuthorityExchange, request_signer: Callable[[str], str],
    now_epoch: int,
) -> RootRevocationAnchorAuthority:
    checked = validated_signer_owner_e0_policy(policy, now_epoch=now_epoch)
    root_descriptor = validate_root_verified_outcome_descriptor_public(
        descriptor, now_epoch=now_epoch
    )
    if (
        type(binding) is not SignerGrantRevocationAuthorityBinding
        or type(exchange) is not RootAuthorityExchange
        or not callable(request_signer)
        or _lookup_exchange(exchange).expected_uid != 0
        or owner_config_id != checked["owner_config_id"]
        or checked["target_signer_public_key"] != root_descriptor["signer_public_key"]
        or binding.policy_id != checked["policy_id"]
    ):
        raise ValueError("root_revocation_anchor_client_invalid")
    authority = object.__new__(RootRevocationAnchorAuthority)
    _issue_client(authority, _ClientState(
        descriptor=root_descriptor, owner_config_id=owner_config_id,
        policy=freeze_owner_e0_policy(checked), binding=binding,
        exchange=exchange, request_signer=request_signer,
    ))
    return authority


def root_revocation_anchor_bindings(authority: object) -> Mapping[str, str]:
    state = _lookup_client(authority)
    return {
        "store_id": state.binding.anchor_store_id,
        "durability_receipt_id": state.binding.anchor_durability_receipt_id,
        "state_binding_digest": state.binding.anchor_state_binding_digest,
        "binding_digest": state.binding.anchor_binding_digest(),
    }


def _exchange(
    authority: object, *, operation: str, snapshot_id: str | None,
) -> ProposalReplayHighWater | None:
    import secrets
    import time

    state = _lookup_client(authority)
    request = RootRevocationRequest(
        operation=operation, request_id="sha256:" + "0" * 64,
        request_nonce=secrets.token_hex(32),
        descriptor_id=str(state.descriptor["descriptor_id"]),
        owner_config_id=state.owner_config_id,
        policy_id=str(state.policy["policy_id"]),
        binding_digest=state.binding.anchor_binding_digest(),
        policy=dict(state.policy), snapshot_id=snapshot_id,
        issued_at=int(time.time()), signer_instance_signature=_placeholder(),
    )
    signature = state.request_signer(canonical_signer_input(request))
    request = replace(request, signer_instance_signature=signature)
    request = replace(request, request_id=request_id_for(asdict(request)))
    response = response_from_bytes(state.exchange.exchange(request.to_bytes()))
    expected_state = "ADVANCED" if operation == OP_ADVANCE else "LOADED"
    if not _matches(response, request, expected_state):
        raise ValueError("root_revocation_anchor_request_rejected")
    if response.sequence is None:
        return None
    assert response.revision is not None
    return ProposalReplayHighWater(response.sequence, response.revision)


def _matches(response: Any, request: RootRevocationRequest, state: str) -> bool:
    expected_snapshot = request.snapshot_id if request.operation == OP_ADVANCE else None
    return bool(
        response.accepted and response.request_id == request.request_id
        and response.descriptor_id == request.descriptor_id
        and response.owner_config_id == request.owner_config_id
        and response.policy_id == request.policy_id
        and response.binding_digest == request.binding_digest
        and response.state == state
        and (expected_snapshot is None or response.snapshot_id == expected_snapshot)
    )


def _placeholder() -> str:
    return "ed25519-sig-v1:" + "A" * 86


__all__ = ["RootRevocationAnchorAuthority", "root_revocation_anchor_bindings"]
