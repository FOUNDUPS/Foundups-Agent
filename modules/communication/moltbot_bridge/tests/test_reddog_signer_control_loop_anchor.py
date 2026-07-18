"""Tests for the signer-owned control-loop monotonic anchor."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    AtomicSignerControlLoopAnchorStore,
)


def _payload(sequence: int, previous: str = "") -> dict[str, object]:
    return {
        "sequence_number": sequence,
        "previous_receipt_id": previous,
        "receipt_id": f"receipt-{sequence}",
        "cycle_id": f"cycle-{sequence}",
        "nonce": f"nonce-{sequence}",
        "child_execution_receipt_ids": [f"child-{sequence}"],
        "child_execution_evidence_digests": [f"digest-{sequence}"],
    }


def _response(sequence: int) -> dict[str, str]:
    return {
        "signature": f"signature-{sequence}",
        "audit_mac": f"audit-{sequence}",
        "audit_attestation_signature": f"attestation-{sequence}",
    }


def _commit(store: AtomicSignerControlLoopAnchorStore, payload: dict[str, object]) -> None:
    prepared = store.prepare(payload)
    store.commit(
        payload,
        _response(int(payload["sequence_number"])),
        expected_revision=prepared.expected_revision,
    )


def test_anchor_rejects_resident_rollback_but_allows_exact_recovery(
    tmp_path: Path,
) -> None:
    store = AtomicSignerControlLoopAnchorStore(tmp_path / "signer" / "anchor.json")
    first = _payload(1)
    second = _payload(2, "receipt-1")
    _commit(store, first)
    _commit(store, second)

    replay = store.prepare(second)
    assert replay.replay_response == _response(2)
    store.commit(second, _response(2), expected_revision=replay.expected_revision)

    rolled_back_candidate = {
        **_payload(2, "receipt-1"),
        "receipt_id": "different-receipt-2",
        "cycle_id": "different-cycle-2",
        "nonce": "different-nonce-2",
    }
    with pytest.raises(ValueError, match="rollback_detected"):
        store.prepare(rolled_back_candidate)


def test_anchor_rejects_reused_child_evidence(tmp_path: Path) -> None:
    store = AtomicSignerControlLoopAnchorStore(tmp_path / "signer" / "anchor.json")
    first = _payload(1)
    _commit(store, first)
    second = _payload(2, "receipt-1")
    second["child_execution_receipt_ids"] = first[
        "child_execution_receipt_ids"
    ]
    with pytest.raises(ValueError, match="child_receipt_replay"):
        store.prepare(second)


def test_anchor_state_tamper_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "signer" / "anchor.json"
    store = AtomicSignerControlLoopAnchorStore(path)
    _commit(store, _payload(1))
    path.write_text('{"schema_version":"forged"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="state_invalid"):
        store.load()
