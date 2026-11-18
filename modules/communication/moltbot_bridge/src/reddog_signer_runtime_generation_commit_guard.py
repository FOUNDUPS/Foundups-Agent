"""Rollback a candidate signer generation when final verification fails."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationPendingAdvance,
    TransactionalSignerRuntimeGenerationHighWaterStore,
)


def run_commit_guard_or_rollback(
    anchor: Any,
    *,
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    pending: SignerRuntimeGenerationPendingAdvance,
    activation: SignerRuntimeGenerationActivation,
    previous_state: Mapping[str, Any],
    commit_guard: Callable[[SignerRuntimeGenerationActivation], None] | None,
) -> None:
    """Commit guard success or restore both authority stores before rejection."""

    if commit_guard is None:
        return
    try:
        commit_guard(activation)
    except Exception:
        _rollback_candidate_anchor(
            anchor,
            activation=activation,
            previous_state=previous_state,
        )
        store.abort_prepared(anchor._anchor_id, pending.transaction_id)
        _verify_transaction_cleared(
            store,
            anchor_id=anchor._anchor_id,
            expected=pending.expected,
        )
        raise


def decode_previous_anchor_state(
    pending: SignerRuntimeGenerationPendingAdvance,
) -> dict[str, Any]:
    """Decode the signer-authenticated canonical rollback snapshot."""

    value = pending.previous_anchor_state_json
    if not isinstance(value, str) or not value.isascii() or len(value) > 65536:
        raise ValueError("generation_anchor_previous_state_invalid")
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("generation_anchor_previous_state_invalid") from exc
    if (
        not isinstance(decoded, Mapping)
        or json.dumps(
            decoded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        != value
    ):
        raise ValueError("generation_anchor_previous_state_invalid")
    return dict(decoded)


def encode_anchor_state(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def validate_pending_generation(
    value: Any,
    *,
    expected: SignerRuntimeGenerationHighWater | None,
    next_value: SignerRuntimeGenerationHighWater | None,
    previous_anchor_state_json: str | None = None,
) -> None:
    if (
        not isinstance(value, SignerRuntimeGenerationPendingAdvance)
        or value.expected != expected
        or value.next_value != next_value
        or not _is_sha256(value.transaction_id)
        or value.transaction_id == "sha256:" + "0" * 64
        or (
            previous_anchor_state_json is not None
            and value.previous_anchor_state_json
            != previous_anchor_state_json
        )
    ):
        raise ValueError("generation_anchor_pending_invalid")
    decode_previous_anchor_state(value)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _rollback_candidate_anchor(
    anchor: Any,
    *,
    activation: SignerRuntimeGenerationActivation,
    previous_state: Mapping[str, Any],
) -> None:
    previous = dict(previous_state)
    previous_revision = previous.pop("revision", None)
    if previous:
        restored = anchor._store.commit(
            previous,
            expected_revision=activation.revision,
        )
        if restored != previous_revision:
            raise RuntimeError("generation_anchor_rollback_unverified")
    else:
        anchor._store.remove(expected_revision=activation.revision)
    if anchor._decode(anchor._store.load()) != anchor._decode(previous_state):
        raise RuntimeError("generation_anchor_rollback_unverified")


def _verify_transaction_cleared(
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    *,
    anchor_id: str,
    expected: object,
) -> None:
    if store.pending(anchor_id) is not None or store.load(anchor_id) != expected:
        raise RuntimeError("generation_anchor_high_water_unverified")


__all__ = [
    "decode_previous_anchor_state",
    "encode_anchor_state",
    "run_commit_guard_or_rollback",
    "validate_pending_generation",
]
