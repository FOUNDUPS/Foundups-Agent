"""Canonical codec for authenticated signer-generation transactions."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
)


def decode_high_water(
    value: Any,
) -> SignerRuntimeGenerationHighWater | None:
    return None if value is None else decode_required_high_water(value)


def decode_required_high_water(
    value: Any,
) -> SignerRuntimeGenerationHighWater:
    if not isinstance(value, Mapping) or set(value) != {
        "generation",
        "revision",
    }:
        raise ValueError("generation_high_water_value_invalid")
    result = SignerRuntimeGenerationHighWater(
        generation=value.get("generation"),
        revision=value.get("revision"),
    )
    validate_optional_high_water(result)
    return result


def validate_next_high_water(
    expected: SignerRuntimeGenerationHighWater | None,
    value: SignerRuntimeGenerationHighWater | None,
) -> None:
    validate_optional_high_water(expected)
    validate_optional_high_water(value)
    if value is None or value.generation != (
        1 if expected is None else expected.generation + 1
    ):
        raise ValueError("generation_high_water_not_monotonic")


def validate_optional_high_water(
    value: SignerRuntimeGenerationHighWater | None,
) -> None:
    if value is None:
        return
    if (
        not isinstance(value, SignerRuntimeGenerationHighWater)
        or type(value.generation) is not int
        or value.generation < 1
        or not _revision_value(value.revision)
    ):
        raise ValueError("generation_high_water_value_invalid")


def decode_pending(
    value: Any,
) -> SignerRuntimeGenerationPendingAdvance | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "transaction_id",
        "expected",
        "next_value",
        "previous_anchor_state_json",
    }:
        raise ValueError("generation_high_water_pending_invalid")
    pending = SignerRuntimeGenerationPendingAdvance(
        transaction_id=_sha256(value.get("transaction_id")),
        expected=decode_high_water(value.get("expected")),
        next_value=decode_required_high_water(value.get("next_value")),
        previous_anchor_state_json=validate_previous_anchor_state_json(
            value.get("previous_anchor_state_json")
        ),
    )
    validate_pending(pending)
    return pending


def require_pending(
    entry: Mapping[str, Any], transaction_id: str
) -> SignerRuntimeGenerationPendingAdvance:
    pending = decode_pending(entry.get("pending"))
    if pending is None or pending.transaction_id != transaction_id:
        raise RuntimeError("generation_high_water_transaction_conflict")
    return pending


def validate_pending(value: SignerRuntimeGenerationPendingAdvance) -> None:
    if not isinstance(value, SignerRuntimeGenerationPendingAdvance):
        raise ValueError("generation_high_water_pending_invalid")
    _sha256(value.transaction_id)
    validate_next_high_water(value.expected, value.next_value)
    validate_previous_anchor_state_json(value.previous_anchor_state_json)


def pending_dict(
    value: SignerRuntimeGenerationPendingAdvance,
) -> dict[str, Any]:
    validate_pending(value)
    return {
        "transaction_id": value.transaction_id,
        "expected": (
            None if value.expected is None else asdict(value.expected)
        ),
        "next_value": asdict(value.next_value),
        "previous_anchor_state_json": value.previous_anchor_state_json,
    }


def validate_previous_anchor_state_json(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or len(value) > 65536
    ):
        raise ValueError("generation_high_water_previous_anchor_state_invalid")
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "generation_high_water_previous_anchor_state_invalid"
        ) from exc
    if not isinstance(decoded, Mapping) or _canonical_json(decoded) != value:
        raise ValueError("generation_high_water_previous_anchor_state_invalid")
    return value


def _revision_value(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value != "0" * 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _sha256(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or value[7:] == "0" * 64
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ValueError("generation_high_water_transaction_id_invalid")
    return value


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


__all__ = [
    "decode_high_water",
    "decode_pending",
    "decode_required_high_water",
    "pending_dict",
    "require_pending",
    "validate_next_high_water",
    "validate_optional_high_water",
    "validate_pending",
    "validate_previous_anchor_state_json",
]
