"""Revocation-anchor operations on the existing root authority service."""

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
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    OP_ADVANCE,
    RootRevocationRequest,
    RootRevocationResponse,
    STATUS_ACCEPT,
    STATUS_REJECT,
    canonical_signer_input,
    request_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_validation import (
    validate_root_revocation_operation,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerIdentity,
)

MAX_CLOCK_SKEW_SECONDS = 30


def handle_root_revocation_request(
    raw: bytes, *, peer: KernelPeerIdentity,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier, revocation_authority: object,
    now_epoch: int,
) -> bytes:
    """Validate current authority and derive one root transition server-side."""

    try:
        request = request_from_bytes(raw)
        snapshot = validated_root_authority_identity_snapshot(
            state, snapshot_supplier=snapshot_supplier, now_epoch=now_epoch
        )
        _require_transport(request, snapshot, peer=peer, now_epoch=now_epoch)
        with validate_root_revocation_operation(
            request, snapshot=snapshot, state=state,
            authority=revocation_authority, now_epoch=now_epoch,
        ) as operation:
            current = state.load(operation.binding_digest)
            if request.operation == OP_ADVANCE:
                current = _advance(state, current, operation)
        return _accept(request, current).to_bytes()
    except Exception:
        if "request" not in locals():
            return b'{"status":"REJECT"}\n'
        return _reject(request).to_bytes()


def _require_transport(
    request: RootRevocationRequest, snapshot: object, *,
    peer: KernelPeerIdentity, now_epoch: int,
) -> None:
    if (
        request.descriptor_id != snapshot.descriptor["descriptor_id"]
        or request.owner_config_id != snapshot.owner_config_id
        or abs(now_epoch - request.issued_at) > MAX_CLOCK_SKEW_SECONDS
    ):
        raise ValueError("root_revocation_transport_context_invalid")
    require_root_authority_peer(peer, snapshot)
    require_root_authority_signer_proof(
        snapshot, canonical_signer_input(request), request.signer_instance_signature
    )


def _advance(state, current, operation) -> ProposalReplayHighWater:
    wanted = operation.wanted
    assert wanted is not None
    if current == wanted:
        return current
    if current != operation.expected:
        raise RuntimeError("root_revocation_cas_conflict")
    try:
        state.advance_revocation(
            operation.binding_digest, expected=current, next_value=wanted
        )
    except RuntimeError:
        if state.load(operation.binding_digest) != wanted:
            raise
    if state.load(operation.binding_digest) != wanted:
        raise RuntimeError("root_revocation_cas_unverified")
    return wanted


def _accept(request, value) -> RootRevocationResponse:
    snapshot_id = None if value is None else "sha256:" + value.state_revision
    return RootRevocationResponse(
        status=STATUS_ACCEPT, request_id=request.request_id,
        descriptor_id=request.descriptor_id, owner_config_id=request.owner_config_id,
        policy_id=request.policy_id, binding_digest=request.binding_digest,
        snapshot_id=snapshot_id,
        state="ADVANCED" if request.operation == OP_ADVANCE else "LOADED",
        sequence=None if value is None else value.sequence,
        revision=None if value is None else value.state_revision,
    )


def _reject(request) -> RootRevocationResponse:
    return RootRevocationResponse(
        status=STATUS_REJECT, request_id=request.request_id,
        descriptor_id=request.descriptor_id, owner_config_id=request.owner_config_id,
        policy_id=request.policy_id, binding_digest=request.binding_digest,
        snapshot_id=None, state="REJECTED",
        reason="root_revocation_request_rejected",
    )


__all__ = ["MAX_CLOCK_SKEW_SECONDS", "handle_root_revocation_request"]
