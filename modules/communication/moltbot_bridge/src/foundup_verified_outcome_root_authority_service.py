"""Root-owned reserve/commit service for verified FoundUp outcomes."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    validate_root_verified_outcome_descriptor,
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_protocol import (
    OP_COMMIT,
    RootAuthorityRequest,
    RootAuthorityResponse,
    STATUS_ACCEPT,
    STATUS_REJECT,
    canonical_signer_instance_input,
    request_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
    authorization_binding,
    state_revision,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerIdentity,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)


STATE_RESERVED = "RESERVED_BURNED"
STATE_COMMITTED = "COMMITTED"
STATE_REJECTED = "REJECTED"


@dataclass(frozen=True)
class RootAuthoritySnapshot:
    owner_config_id: str
    authority_generation_sequence: int
    state_binding_digest: str
    signer_principal_id: str
    signer_uid: int
    signer_gid: int
    descriptor: Mapping[str, object]


SnapshotSupplier = Callable[[], RootAuthoritySnapshot]


def initialize_root_authority_state(
    state: RootVerifiedOutcomeAuthorityState,
    snapshot: RootAuthoritySnapshot,
    *,
    now_epoch: int,
) -> None:
    """Provision one root-owned generation and replay anchor explicitly."""

    descriptor = validate_root_verified_outcome_descriptor_public(
        snapshot.descriptor, now_epoch=now_epoch
    )
    _require_snapshot_identity(snapshot, descriptor, state=state)
    if (
        descriptor["replay_store_id"] != state.store_id
        or descriptor["replay_store_durability_receipt_id"]
        != state.durability_receipt_id
    ):
        raise ValueError("root_authority_state_store_binding_invalid")
    binding = str(descriptor["replay_anchor_binding_digest"])
    wanted = ProposalReplayHighWater(
        int(descriptor["replay_anchor_sequence"]),
        str(descriptor["replay_anchor_revision"]),
    )
    installation_revision = state_revision(
        {
            "owner_config_id": snapshot.owner_config_id,
            "authority_generation_sequence": (
                snapshot.authority_generation_sequence
            ),
            "replay_binding": binding,
            "replay_anchor": {
                "sequence": wanted.sequence,
                "state_revision": wanted.state_revision,
            },
        }
    )
    state.initialize(
        generation=ProposalReplayHighWater(
            snapshot.authority_generation_sequence,
            snapshot.owner_config_id[7:],
        ),
        replay_binding=binding,
        replay_anchor=wanted,
        installation_revision=installation_revision,
    )


def handle_root_authority_request(
    raw: bytes,
    *,
    peer: KernelPeerIdentity,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    now_epoch: int,
) -> bytes:
    """Handle one bounded request; malformed input receives no trusted receipt."""

    try:
        request = request_from_bytes(raw)
        snapshot = _current_snapshot(
            state, snapshot_supplier=snapshot_supplier, now_epoch=now_epoch
        )
        _require_peer(peer, snapshot)
        grant = _matching_grant(request, snapshot)
        response = (
            _commit(request, grant, snapshot, state)
            if request.operation == OP_COMMIT
            else _reserve(request, grant, snapshot, state)
        )
    except Exception:
        if "request" not in locals():
            return b'{"status":"REJECT"}\n'
        response = _reject(request, "root_authority_request_rejected")
    return response.to_bytes()


def _current_snapshot(
    state: RootVerifiedOutcomeAuthorityState,
    *,
    snapshot_supplier: SnapshotSupplier,
    now_epoch: int,
) -> RootAuthoritySnapshot:
    snapshot = snapshot_supplier()
    if not isinstance(snapshot, RootAuthoritySnapshot):
        raise ValueError("root_authority_snapshot_invalid")
    descriptor = validate_root_verified_outcome_descriptor(
        snapshot.descriptor, replay_store=state, now_epoch=now_epoch
    )
    _require_snapshot_identity(snapshot, descriptor, state=state)
    state.observe_generation(
        snapshot.authority_generation_sequence, snapshot.owner_config_id
    )
    return RootAuthoritySnapshot(
        owner_config_id=snapshot.owner_config_id,
        authority_generation_sequence=snapshot.authority_generation_sequence,
        state_binding_digest=snapshot.state_binding_digest,
        signer_principal_id=snapshot.signer_principal_id,
        signer_uid=snapshot.signer_uid,
        signer_gid=snapshot.signer_gid,
        descriptor=descriptor,
    )


def _require_snapshot_identity(
    snapshot: RootAuthoritySnapshot,
    descriptor: Mapping[str, object],
    *,
    state: RootVerifiedOutcomeAuthorityState,
) -> None:
    if (
        descriptor["authority_generation_sequence"]
        != snapshot.authority_generation_sequence
        or snapshot.state_binding_digest != state.state_binding_digest
        or not snapshot.signer_principal_id
        or not snapshot.signer_principal_id.isascii()
        or type(snapshot.signer_uid) is not int
        or snapshot.signer_uid <= 0
        or type(snapshot.signer_gid) is not int
        or snapshot.signer_gid <= 0
    ):
        raise ValueError("root_authority_snapshot_binding_invalid")


def _matching_grant(
    request: RootAuthorityRequest, snapshot: RootAuthoritySnapshot
) -> Mapping[str, object]:
    descriptor = snapshot.descriptor
    if (
        request.descriptor_id != descriptor["descriptor_id"]
        or request.owner_config_id != snapshot.owner_config_id
    ):
        raise ValueError("root_authority_request_context_mismatch")
    if not Ed25519SignatureVerifier().verify(
        str(descriptor["signer_public_key"]),
        canonical_signer_instance_input(request),
        request.signer_instance_signature,
    ):
        raise ValueError("root_authority_signer_proof_invalid")
    grant = next(
        (
            item
            for item in descriptor["grants"]
            if item["authorization_id"] == request.authorization_id
        ),
        None,
    )
    if not isinstance(grant, Mapping) or any(
        (
            grant["receipt_id"] != request.receipt_id,
            grant["work_order_id"] != request.work_order_id,
            grant["evidence_digest"] != request.evidence_digest,
            not int(grant["issued_at"]) <= request.issued_at < int(grant["expires_at"]),
        )
    ):
        raise ValueError("root_authority_grant_mismatch")
    return grant


def _reserve(
    request: RootAuthorityRequest,
    grant: Mapping[str, object],
    snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState,
) -> RootAuthorityResponse:
    reservation_id = "sha256:" + secrets.token_hex(32)
    payload = _reservation_payload(request, reservation_id)
    state.advance(
        authorization_binding(request.authorization_id),
        expected=None,
        next_value=ProposalReplayHighWater(1, state_revision(payload)),
    )
    return _accept(request, snapshot, reservation_id, STATE_RESERVED)


def _commit(
    request: RootAuthorityRequest,
    _grant: Mapping[str, object],
    snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState,
) -> RootAuthorityResponse:
    assert request.reservation_id and request.signature_digest
    payload = _reservation_payload(request, request.reservation_id)
    expected = ProposalReplayHighWater(1, state_revision(payload))
    committed = ProposalReplayHighWater(
        2,
        state_revision(
            {**payload, "signature_digest": request.signature_digest}
        ),
    )
    state.advance(
        authorization_binding(request.authorization_id),
        expected=expected,
        next_value=committed,
    )
    return _accept(request, snapshot, request.reservation_id, STATE_COMMITTED)


def _reservation_payload(
    request: RootAuthorityRequest, reservation_id: str
) -> dict[str, object]:
    return {
        "descriptor_id": request.descriptor_id,
        "owner_config_id": request.owner_config_id,
        "authorization_id": request.authorization_id,
        "receipt_id": request.receipt_id,
        "work_order_id": request.work_order_id,
        "evidence_digest": request.evidence_digest,
        "issued_at": request.issued_at,
        "reservation_id": reservation_id,
    }


def _require_peer(peer: KernelPeerIdentity, snapshot: RootAuthoritySnapshot) -> None:
    if (
        not isinstance(peer, KernelPeerIdentity)
        or peer.attestation.boundary_attested is not True
        or peer.attestation.peer_principal_id != snapshot.signer_principal_id
        or peer.uid != snapshot.signer_uid
        or peer.gid != snapshot.signer_gid
        or "kernel" not in peer.attestation.credential_source.lower()
    ):
        raise ValueError("root_authority_signer_peer_invalid")


def _accept(
    request: RootAuthorityRequest,
    snapshot: RootAuthoritySnapshot,
    reservation_id: str,
    state: str,
) -> RootAuthorityResponse:
    return RootAuthorityResponse(
        status=STATUS_ACCEPT,
        request_id=request.request_id,
        descriptor_id=str(snapshot.descriptor["descriptor_id"]),
        owner_config_id=snapshot.owner_config_id,
        authorization_id=request.authorization_id,
        reservation_id=reservation_id,
        state=state,
    )


def _reject(request: RootAuthorityRequest, reason: str) -> RootAuthorityResponse:
    return RootAuthorityResponse(
        status=STATUS_REJECT,
        request_id=request.request_id,
        descriptor_id=request.descriptor_id,
        owner_config_id=request.owner_config_id,
        authorization_id=request.authorization_id,
        reservation_id=None,
        state=STATE_REJECTED,
        reason=reason,
    )


__all__ = [
    "RootAuthoritySnapshot",
    "STATE_COMMITTED",
    "STATE_REJECTED",
    "STATE_RESERVED",
    "handle_root_authority_request",
    "initialize_root_authority_state",
]
