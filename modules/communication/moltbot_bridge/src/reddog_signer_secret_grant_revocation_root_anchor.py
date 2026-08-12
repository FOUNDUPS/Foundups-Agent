"""Shared root-anchor checks for signer grant revocation state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)


def require_revocation_root_anchor(
    binding: SignerGrantRevocationAuthorityBinding,
    anchor: ProposalReplayHighWaterStore,
) -> None:
    """Require the exact signed, durable three-domain anchor identity."""

    if (
        type(anchor) is not RootVerifiedOutcomeAuthorityState
        or anchor.durable is not True
        or anchor.store_id != binding.anchor_store_id
        or anchor.durability_receipt_id != binding.anchor_durability_receipt_id
        or getattr(anchor, "state_binding_digest", None)
        != binding.anchor_state_binding_digest
        or anchor.store_id == binding.witness_store_id
        or any(
            _overlap(root, candidate)
            for root in anchor.rollback_domain_roots
            for candidate in (binding.primary_root, binding.witness_root)
        )
    ):
        raise ValueError("revocation_root_anchor_invalid")


def _overlap(left: object, right: object) -> bool:
    first = Path(str(left)).resolve()
    second = Path(str(right)).resolve()
    return first == second or first in second.parents or second in first.parents


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
