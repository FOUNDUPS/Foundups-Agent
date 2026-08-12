"""Exact operation router for the existing root authority socket service."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    SnapshotSupplier,
    handle_root_authority_request,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    is_revocation_wire_message,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_service import (
    handle_root_revocation_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerIdentity,
)


def handle_root_authority_wire_request(
    raw: bytes,
    *,
    peer: KernelPeerIdentity,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    revocation_authority: object | None,
    now_epoch: int,
) -> bytes:
    common = dict(
        peer=peer, state=state, snapshot_supplier=snapshot_supplier,
        now_epoch=now_epoch,
    )
    if is_revocation_wire_message(raw):
        if revocation_authority is None:
            return b'{"status":"REJECT"}\n'
        return handle_root_revocation_request(
            raw, revocation_authority=revocation_authority, **common
        )
    return handle_root_authority_request(raw, **common)


__all__ = ["handle_root_authority_wire_request"]
