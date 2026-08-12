"""Root service operations for atomic signer protected use."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    SnapshotSupplier,
    require_root_authority_peer,
    require_root_authority_signer_proof,
    validated_root_authority_identity_snapshot,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
    OP_ACQUIRE,
    RootProtectedUseRequest,
    RootProtectedUseResponse,
    STATUS_ACCEPT,
    STATUS_REJECT,
    canonical_signer_input,
    finish_revision_for,
    request_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_authority_validation import (
    validate_protected_use_acquire,
    validate_protected_use_finish_context,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    MAX_GRANT_TTL_SECONDS,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerIdentity,
)

MAX_CLOCK_SKEW_SECONDS = 30


def handle_root_protected_use_request(
    raw: bytes,
    *,
    peer: KernelPeerIdentity,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    revocation_authority: object,
    now_epoch: int,
) -> bytes:
    """Acquire or finish one root-linearized signer-use interval."""

    try:
        request = request_from_bytes(raw)
        snapshot = validated_root_authority_identity_snapshot(
            state, snapshot_supplier=snapshot_supplier, now_epoch=now_epoch
        )
        _require_transport(request, snapshot, peer=peer, now_epoch=now_epoch)
        if request.operation == OP_ACQUIRE:
            value = _acquire(
                request,
                snapshot=snapshot,
                state=state,
                authority=revocation_authority,
                now_epoch=now_epoch,
            )
            response_state = "ACQUIRED"
        else:
            value = _finish(
                request,
                snapshot=snapshot,
                state=state,
                authority=revocation_authority,
            )
            response_state = "FINISHED"
        return _accept(request, value, response_state).to_bytes()
    except Exception:
        if "request" not in locals():
            return b'{"status":"REJECT"}\n'
        return _reject(request).to_bytes()


def _require_transport(
    request: RootProtectedUseRequest,
    snapshot: object,
    *,
    peer: KernelPeerIdentity,
    now_epoch: int,
) -> None:
    if (
        request.descriptor_id != snapshot.descriptor["descriptor_id"]
        or request.owner_config_id != snapshot.owner_config_id
        or abs(now_epoch - request.issued_at) > MAX_CLOCK_SKEW_SECONDS
    ):
        raise ValueError("root_protected_use_transport_context_invalid")
    require_root_authority_peer(peer, snapshot)
    require_root_authority_signer_proof(
        snapshot,
        canonical_signer_input(request),
        request.signer_instance_signature,
    )


def _acquire(
    request: RootProtectedUseRequest,
    *,
    snapshot: object,
    state: RootVerifiedOutcomeAuthorityState,
    authority: object,
    now_epoch: int,
) -> ProposalReplayHighWater:
    if not 0 < request.grant_expires_at - now_epoch <= MAX_GRANT_TTL_SECONDS:
        raise ValueError("root_protected_use_grant_expired")
    with validate_protected_use_acquire(
        request,
        snapshot=snapshot,
        state=state,
        authority=authority,
        now_epoch=now_epoch,
    ) as checked:
        return state.acquire_protected_use(
            expected_generation=ProposalReplayHighWater(
                snapshot.authority_generation_sequence,
                snapshot.owner_config_id[7:],
            ),
            revocation_binding=checked.revocation_binding,
            expected_revocation=checked.expected_revocation,
            protected_use_binding=request.protected_use_id,
            use_revision=request.protected_use_id[7:],
        )


def _finish(
    request: RootProtectedUseRequest,
    *,
    snapshot: object,
    state: RootVerifiedOutcomeAuthorityState,
    authority: object,
) -> ProposalReplayHighWater:
    validate_protected_use_finish_context(
        request, snapshot=snapshot, state=state, authority=authority
    )
    assert request.acquired_sequence is not None
    assert request.acquired_revision is not None
    if request.acquired_revision != request.protected_use_id[7:]:
        raise ValueError("root_protected_use_finish_binding_invalid")
    expected = ProposalReplayHighWater(
        request.acquired_sequence, request.acquired_revision
    )
    return state.finish_protected_use(
        expected=expected,
        finish_revision=finish_revision_for(
            request.protected_use_id,
            request.acquired_sequence,
            request.acquired_revision,
        ),
    )


def _accept(
    request: RootProtectedUseRequest,
    value: ProposalReplayHighWater,
    response_state: str,
) -> RootProtectedUseResponse:
    return RootProtectedUseResponse(
        status=STATUS_ACCEPT,
        request_id=request.request_id,
        descriptor_id=request.descriptor_id,
        owner_config_id=request.owner_config_id,
        policy_id=request.policy_id,
        binding_digest=request.binding_digest,
        protected_use_id=request.protected_use_id,
        state=response_state,
        sequence=value.sequence,
        revision=value.state_revision,
    )


def _reject(request: RootProtectedUseRequest) -> RootProtectedUseResponse:
    return RootProtectedUseResponse(
        status=STATUS_REJECT,
        request_id=request.request_id,
        descriptor_id=request.descriptor_id,
        owner_config_id=request.owner_config_id,
        policy_id=request.policy_id,
        binding_digest=request.binding_digest,
        protected_use_id=request.protected_use_id,
        state="REJECTED",
        reason="root_protected_use_request_rejected",
    )


__all__ = ["MAX_CLOCK_SKEW_SECONDS", "handle_root_protected_use_request"]
