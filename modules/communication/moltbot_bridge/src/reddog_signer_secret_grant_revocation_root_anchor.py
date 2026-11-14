"""Shared root-anchor checks for signer grant revocation state."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    RootRevocationAnchorAuthority,
    root_revocation_anchor_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)


def require_revocation_root_anchor(
    binding: SignerGrantRevocationAuthorityBinding,
    anchor: object,
) -> None:
    """Require a factory-issued client pinned to the signed root identity."""

    if type(anchor) is not RootRevocationAnchorAuthority:
        raise ValueError("revocation_root_anchor_invalid")
    values = root_revocation_anchor_bindings(anchor)
    expected = {
        "store_id": binding.anchor_store_id,
        "durability_receipt_id": binding.anchor_durability_receipt_id,
        "state_binding_digest": binding.anchor_state_binding_digest,
        "binding_digest": binding.anchor_binding_digest(),
    }
    if values != expected or values["store_id"] == binding.witness_store_id:
        raise ValueError("revocation_root_anchor_invalid")


def revocation_high_water(
    value: Mapping[str, Any] | None,
) -> ProposalReplayHighWater | None:
    return None if value is None else required_revocation_high_water(value)


def required_revocation_high_water(
    value: Mapping[str, Any],
) -> ProposalReplayHighWater:
    return ProposalReplayHighWater(
        sequence=int(value["sequence"]),
        state_revision=str(value["snapshot_id"]).removeprefix("sha256:"),
    )


def next_revocation_sequence(value: Mapping[str, Any] | None) -> int:
    return 1 if value is None else int(value["sequence"]) + 1


__all__ = [
    "next_revocation_sequence",
    "required_revocation_high_water",
    "require_revocation_root_anchor",
    "revocation_high_water",
]
