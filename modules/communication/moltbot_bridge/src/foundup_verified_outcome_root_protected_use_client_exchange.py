"""Request/response exchange helpers for root protected-use clients."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    RootAuthorityExchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
    OP_ACQUIRE,
    RootProtectedUseRequest,
    canonical_signer_input,
    finish_revision_for,
    protected_use_id_for,
    request_id_for,
    response_from_bytes,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)


def exchange_protected_use(
    *,
    descriptor: Mapping[str, Any],
    owner_config_id: str,
    policy: Mapping[str, Any],
    binding: SignerGrantRevocationAuthorityBinding,
    transport: RootAuthorityExchange,
    request_signer: Callable[[str], str],
    operation: str,
    grant_id: str,
    key_epoch: str,
    signing_request_digest: str,
    use_nonce: str,
    grant_expires_at: int,
    acquired: ProposalReplayHighWater | None,
) -> ProposalReplayHighWater:
    import secrets
    import time

    request = _unsigned_request(
        descriptor=descriptor, owner_config_id=owner_config_id,
        policy=policy, binding=binding, operation=operation,
        grant_id=grant_id, key_epoch=key_epoch,
        signing_request_digest=signing_request_digest, use_nonce=use_nonce,
        grant_expires_at=grant_expires_at, acquired=acquired,
        request_nonce=secrets.token_hex(32), issued_at=int(time.time()),
    )
    signature = request_signer(canonical_signer_input(request))
    request = replace(request, signer_instance_signature=signature)
    request = replace(request, request_id=request_id_for(asdict(request)))
    response = response_from_bytes(transport.exchange(request.to_bytes()))
    expected_state = "ACQUIRED" if operation == OP_ACQUIRE else "FINISHED"
    if not _matches(response, request, expected_state):
        raise ValueError("root_protected_use_request_rejected")
    assert response.sequence is not None and response.revision is not None
    return ProposalReplayHighWater(response.sequence, response.revision)


def _unsigned_request(
    *,
    descriptor: Mapping[str, Any], owner_config_id: str,
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    operation: str, grant_id: str, key_epoch: str,
    signing_request_digest: str, use_nonce: str, grant_expires_at: int,
    acquired: ProposalReplayHighWater | None, request_nonce: str, issued_at: int,
) -> RootProtectedUseRequest:
    values = {
        "descriptor_id": str(descriptor["descriptor_id"]),
        "owner_config_id": owner_config_id,
        "policy_id": str(policy["policy_id"]),
        "binding_digest": binding.anchor_binding_digest(),
        "grant_id": grant_id,
        "key_epoch": key_epoch,
        "signing_request_digest": signing_request_digest,
        "use_nonce": use_nonce,
        "grant_expires_at": grant_expires_at,
    }
    return RootProtectedUseRequest(
        operation=operation, request_id="sha256:" + "0" * 64,
        request_nonce=request_nonce, policy=dict(policy),
        protected_use_id=protected_use_id_for(values),
        acquired_sequence=None if acquired is None else acquired.sequence,
        acquired_revision=None if acquired is None else acquired.state_revision,
        issued_at=issued_at, signer_instance_signature=_placeholder(), **values,
    )


def _matches(response: Any, request: RootProtectedUseRequest, state: str) -> bool:
    base = bool(
        response.accepted and response.request_id == request.request_id
        and response.descriptor_id == request.descriptor_id
        and response.owner_config_id == request.owner_config_id
        and response.policy_id == request.policy_id
        and response.binding_digest == request.binding_digest
        and response.protected_use_id == request.protected_use_id
        and response.state == state
    )
    if state == "ACQUIRED":
        return base and response.revision == request.protected_use_id[7:]
    if request.acquired_sequence is None or request.acquired_revision is None:
        return False
    return bool(
        base
        and response.sequence == request.acquired_sequence + 1
        and response.revision == finish_revision_for(
            request.protected_use_id,
            request.acquired_sequence,
            request.acquired_revision,
        )
    )


def _placeholder() -> str:
    return "ed25519-sig-v1:" + "A" * 86


__all__ = ["exchange_protected_use"]
