"""Signed snapshot and staging helpers for root revocation tests."""

from __future__ import annotations

import time
from dataclasses import fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    expected_snapshot_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    SNAPSHOT_SCHEMA,
    canonical_signer_grant_revocation_snapshot_input,
    signer_grant_revocation_snapshot_id,
)


def signed_snapshot(runtime_state: Mapping[str, Any], sequence: int = 1) -> dict[str, Any]:
    now = int(time.time())
    expected = expected_snapshot_binding(
        runtime_state["policy"], runtime_state["binding"]
    )
    value = {
        "schema_version": SNAPSHOT_SCHEMA,
        "snapshot_id": "sha256:" + "0" * 64,
        **{field.name: getattr(expected, field.name) for field in fields(expected)},
        "sequence": sequence,
        "issued_at": now - 2,
        "expires_at": now + 120,
        "revoked_grant_ids": [],
        "revoked_key_epochs": [],
        "signature": "pending",
    }
    value["snapshot_id"] = signer_grant_revocation_snapshot_id(value)
    value["signature"] = encode_ed25519_signature(
        runtime_state["revocation_private"].sign(
            canonical_signer_grant_revocation_snapshot_input(value).encode("ascii")
        )
    )
    return value


def stage(runtime_state: Mapping[str, Any], snapshot: Mapping[str, Any]) -> None:
    runtime_state["store"]._prepare_under_lock(snapshot)
    high = ProposalReplayHighWater(
        int(snapshot["sequence"]), str(snapshot["snapshot_id"])[7:]
    )
    current = runtime_state["store"].state().current
    expected = None if current is None else ProposalReplayHighWater(
        int(current["sequence"]), str(current["snapshot_id"])[7:]
    )
    runtime_state["witness"].advance(
        runtime_state["binding"].witness_binding_digest(),
        expected=expected,
        next_value=high,
    )


__all__ = ["signed_snapshot", "stage"]
