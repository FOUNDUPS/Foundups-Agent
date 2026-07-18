"""Read-only authenticated preflight for live-canary control state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_head_store import (
    load_control_receipt_head,
    verify_control_receipt_head_against_chain,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_chain import (
    verify_control_receipt_chain_against_profile,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_signing_context import (
    validate_authority_profile_source,
    validate_promoted_authority_profile_source,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    AtomicSignerControlLoopAnchorStore,
)


def verify_live_canary_control_prestate(
    *,
    runtime_root: Path,
    receipts: Sequence[Mapping[str, Any]],
    authority_profile: Mapping[str, Any],
    authority_profile_source: Mapping[str, Any],
    expected_source_receipt_id: str,
    signer_anchor_path: Path,
) -> None:
    validate_authority_profile_source(
        authority_profile_source, expected_source_receipt_id
    )
    validate_promoted_authority_profile_source(
        authority_profile, authority_profile_source
    )
    verify_control_receipt_chain_against_profile(receipts, authority_profile)
    _, _, head = load_control_receipt_head(
        runtime_root / "authority_runtime_state.json"
    )
    current_ids, child_receipts, child_evidence = _chain_evidence(receipts)
    if head is None:
        if current_ids:
            raise ValueError("resident_control_loop_head_missing_for_existing_chain")
        if signer_anchor_path.exists():
            raise ValueError("signer_control_loop_anchor_ahead_of_resident_chain")
        return
    verify_control_receipt_head_against_chain(
        head,
        receipt_ids=current_ids,
        child_receipt_ids=child_receipts,
        child_evidence_digests=child_evidence,
    )
    _verify_signer_anchor(
        signer_anchor_path,
        receipts=receipts,
        current_ids=current_ids,
        child_receipts=child_receipts,
        child_evidence=child_evidence,
    )


def _chain_evidence(
    receipts: Sequence[Mapping[str, Any]],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    current = tuple(
        receipt
        for receipt in receipts
        if receipt.get("schema_version") == "reddog_resident_control_loop_receipt.v2"
    )
    return (
        tuple(str(receipt["receipt_id"]) for receipt in current),
        tuple(
            str(value)
            for receipt in current
            for value in tuple(receipt.get("child_execution_receipt_ids") or ())
        ),
        tuple(
            str(value)
            for receipt in current
            for value in tuple(
                receipt.get("child_execution_evidence_digests") or ()
            )
        ),
    )


def _verify_signer_anchor(
    path: Path,
    *,
    receipts: Sequence[Mapping[str, Any]],
    current_ids: tuple[str, ...],
    child_receipts: tuple[str, ...],
    child_evidence: tuple[str, ...],
) -> None:
    state = AtomicSignerControlLoopAnchorStore(path).load()
    if not state:
        raise ValueError("signer_control_loop_anchor_missing")
    if (
        state.get("sequence_number") != len(current_ids)
        or state.get("receipt_id") != current_ids[-1]
        or dict(state.get("signed_receipt") or {}) != dict(receipts[-1])
        or set(state.get("consumed_child_receipt_ids") or ())
        != set(child_receipts)
        or set(state.get("consumed_child_evidence_digests") or ())
        != set(child_evidence)
    ):
        raise ValueError("signer_control_loop_anchor_chain_mismatch")


__all__ = ["verify_live_canary_control_prestate"]
