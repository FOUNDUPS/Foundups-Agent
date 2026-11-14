"""Generic state walker for resident control-loop receipt chains."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_validation import (
    parse_receipt_line,
    validated_receipt_identity,
)


def validate_control_receipt_chain_state(
    existing: str,
    *,
    current_schema: str,
    legacy_schema: str,
    receipt_id_builder: Callable[[Mapping[str, Any]], str],
    legacy_digest_builder: Callable[[Any], str],
    verify_current: Callable[[Mapping[str, Any]], Any],
) -> dict[str, Any]:
    state = _new_state(legacy_digest_builder)
    for line_number, raw in enumerate(existing.splitlines(), start=1):
        if not raw.strip():
            continue
        payload = parse_receipt_line(raw, line_number)
        schema, receipt_id = validated_receipt_identity(
            payload, line_number, state["seen_ids"], receipt_id_builder
        )
        if schema == legacy_schema:
            _consume_legacy(payload, line_number, state, legacy_digest_builder)
        elif schema == current_schema:
            _consume_current(
                verify_current(payload), line_number, receipt_id, state
            )
        else:
            raise ValueError(f"resident_control_loop_receipt_schema_invalid:{line_number}")
        state["seen_ids"].add(receipt_id)
        state["last_receipt_id"] = receipt_id
    return _public_state(state)


def _new_state(legacy_digest_builder: Callable[[Any], str]) -> dict[str, Any]:
    return {
        "seen_ids": set(), "cycle_ids": set(), "nonces": set(),
        "child_receipt_ids": set(), "child_evidence_digests": set(),
        "legacy_payloads": [], "legacy_prefix_digest": legacy_digest_builder(()),
        "last_receipt_id": "", "current_seen": False,
        "current_receipt_ids": [],
    }


def _consume_legacy(
    payload: Mapping[str, Any], line_number: int, state: dict[str, Any],
    legacy_digest_builder: Callable[[Any], str],
) -> None:
    if state["current_seen"]:
        raise ValueError(f"resident_control_loop_receipt_legacy_after_v2:{line_number}")
    state["legacy_payloads"].append(payload)
    state["legacy_prefix_digest"] = legacy_digest_builder(state["legacy_payloads"])


def _consume_current(
    receipt: Any, line_number: int, receipt_id: str, state: dict[str, Any]
) -> None:
    expected_sequence = len(state["current_receipt_ids"]) + 1
    if receipt.sequence_number != expected_sequence:
        raise ValueError(f"resident_control_loop_receipt_sequence_invalid:{line_number}")
    if receipt.previous_receipt_id != state["last_receipt_id"]:
        raise ValueError(f"resident_control_loop_receipt_previous_link_invalid:{line_number}")
    if receipt.legacy_prefix_digest != state["legacy_prefix_digest"]:
        raise ValueError(f"resident_control_loop_receipt_legacy_digest_invalid:{line_number}")
    if receipt.cycle_id in state["cycle_ids"] or receipt.nonce in state["nonces"]:
        raise ValueError(f"resident_control_loop_receipt_replay:{line_number}")
    if state["child_receipt_ids"].intersection(receipt.child_execution_receipt_ids):
        raise ValueError(f"resident_control_loop_receipt_child_receipt_replay:{line_number}")
    if state["child_evidence_digests"].intersection(receipt.child_execution_evidence_digests):
        raise ValueError(f"resident_control_loop_receipt_child_evidence_replay:{line_number}")
    state["current_seen"] = True
    state["cycle_ids"].add(receipt.cycle_id)
    state["nonces"].add(receipt.nonce)
    state["child_receipt_ids"].update(receipt.child_execution_receipt_ids)
    state["child_evidence_digests"].update(receipt.child_execution_evidence_digests)
    state["current_receipt_ids"].append(receipt_id)


def _public_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "last_receipt_id": state["last_receipt_id"],
        "legacy_prefix_digest": state["legacy_prefix_digest"],
        "cycle_ids": frozenset(state["cycle_ids"]),
        "nonces": frozenset(state["nonces"]),
        "child_receipt_ids": frozenset(state["child_receipt_ids"]),
        "child_evidence_digests": frozenset(state["child_evidence_digests"]),
        "current_receipt_ids": tuple(state["current_receipt_ids"]),
    }


__all__ = ["validate_control_receipt_chain_state"]
