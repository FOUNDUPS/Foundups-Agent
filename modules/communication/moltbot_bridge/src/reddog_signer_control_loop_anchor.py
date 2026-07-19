"""Signer-owned monotonic anchor for authenticated control-loop receipts."""

from __future__ import annotations

import json
import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AtomicJsonAuthorityRuntimeStore,
)


SIGNER_CONTROL_LOOP_ANCHOR_SCHEMA_VERSION = "reddog_signer_control_loop_anchor.v1"
_MAX_HISTORY_ITEMS = 4096


@dataclass(frozen=True)
class ControlLoopAnchorPreparation:
    expected_revision: str | None
    replay_response: Mapping[str, Any] | None = None


class ControlLoopAnchorStore(Protocol):
    def prepare(self, payload: Mapping[str, Any]) -> ControlLoopAnchorPreparation: ...

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None: ...


class AtomicSignerControlLoopAnchorStore:
    """Persist the signer high-water witness outside resident runtime state."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).resolve()
        self._store = AtomicJsonAuthorityRuntimeStore(
            self.path,
            allowed_root=self.path.parent,
        )

    def prepare(self, payload: Mapping[str, Any]) -> ControlLoopAnchorPreparation:
        state = self._store.load()
        return _prepare_candidate(state, payload)

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None:
        current = self._store.load()
        if current.get("revision") != expected_revision:
            raise ValueError("signer_control_loop_anchor_revision_conflict")
        prepared = _prepare_candidate(current, payload)
        if prepared.replay_response is not None:
            if dict(prepared.replay_response) != dict(response):
                raise ValueError("signer_control_loop_anchor_replay_response_conflict")
            return
        self._store.commit(
            _next_anchor_state(current, payload, response),
            expected_revision=expected_revision,
        )

    def load(self) -> dict[str, Any]:
        state = self._store.load()
        _validate_anchor_state(state, allow_empty=True)
        return state


class InMemorySignerControlLoopAnchorStore:
    """Deterministic signer-anchor test implementation."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._lock = threading.Lock()

    def prepare(self, payload: Mapping[str, Any]) -> ControlLoopAnchorPreparation:
        with self._lock:
            return _prepare_candidate(dict(self._state), payload)

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None:
        with self._lock:
            if self._state.get("revision") != expected_revision:
                raise ValueError("signer_control_loop_anchor_revision_conflict")
            prepared = _prepare_candidate(self._state, payload)
            if prepared.replay_response is not None:
                if dict(prepared.replay_response) != dict(response):
                    raise ValueError("signer_control_loop_anchor_replay_response_conflict")
                return
            next_state = _next_anchor_state(self._state, payload, response)
            next_state["revision"] = _canonical(next_state)
            self._state = next_state

    def load(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state, sort_keys=True))


def _prepare_candidate(
    state: Mapping[str, Any], payload: Mapping[str, Any]
) -> ControlLoopAnchorPreparation:
    _validate_anchor_state(state, allow_empty=True)
    candidate = dict(payload)
    expected_revision = state.get("revision")
    if not state:
        if candidate.get("sequence_number") != 1 or candidate.get("previous_receipt_id"):
            raise ValueError("signer_control_loop_anchor_sequence_invalid")
        return ControlLoopAnchorPreparation(expected_revision=None)

    signed_receipt = dict(state["signed_receipt"])
    previous_payload = {
        key: value
        for key, value in signed_receipt.items()
        if key not in {
            "signature",
            "signer_audit_mac",
            "signer_audit_attestation_signature",
        }
    }
    if candidate == previous_payload:
        return ControlLoopAnchorPreparation(
            expected_revision=str(expected_revision),
            replay_response=dict(state["signing_response"]),
        )
    if (
        candidate.get("sequence_number") != int(state["sequence_number"]) + 1
        or candidate.get("previous_receipt_id") != state["receipt_id"]
        or candidate.get("cycle_id") in state["cycle_ids"]
        or candidate.get("nonce") in state["nonces"]
    ):
        raise ValueError("signer_control_loop_anchor_rollback_detected")
    _reject_reused_child_evidence(state, candidate)
    return ControlLoopAnchorPreparation(expected_revision=str(expected_revision))


def _next_anchor_state(
    state: Mapping[str, Any],
    payload: Mapping[str, Any],
    response: Mapping[str, Any],
) -> dict[str, Any]:
    cycle_ids = [*state.get("cycle_ids", ()), str(payload["cycle_id"])]
    nonces = [*state.get("nonces", ()), str(payload["nonce"])]
    child_receipts = [
        *state.get("consumed_child_receipt_ids", ()),
        *payload.get("child_execution_receipt_ids", ()),
    ]
    child_digests = [
        *state.get("consumed_child_evidence_digests", ()),
        *payload.get("child_execution_evidence_digests", ()),
    ]
    if any(
        len(values) > _MAX_HISTORY_ITEMS
        for values in (cycle_ids, nonces, child_receipts, child_digests)
    ):
        raise ValueError("signer_control_loop_anchor_capacity_exceeded")
    signed_receipt = {
        **dict(payload),
        "signature": response["signature"],
        "signer_audit_mac": response["audit_mac"],
        "signer_audit_attestation_signature": response[
            "audit_attestation_signature"
        ],
    }
    return {
        "schema_version": SIGNER_CONTROL_LOOP_ANCHOR_SCHEMA_VERSION,
        "sequence_number": int(payload["sequence_number"]),
        "receipt_id": str(payload["receipt_id"]),
        "cycle_ids": cycle_ids,
        "nonces": nonces,
        "consumed_child_receipt_ids": child_receipts,
        "consumed_child_evidence_digests": child_digests,
        "signed_receipt": signed_receipt,
        "signing_response": dict(response),
    }


def _reject_reused_child_evidence(
    state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    prior_receipts = set(state["consumed_child_receipt_ids"])
    prior_digests = set(state["consumed_child_evidence_digests"])
    if prior_receipts.intersection(candidate.get("child_execution_receipt_ids", ())):
        raise ValueError("signer_control_loop_anchor_child_receipt_replay")
    if prior_digests.intersection(candidate.get("child_execution_evidence_digests", ())):
        raise ValueError("signer_control_loop_anchor_child_evidence_replay")


def _validate_anchor_state(state: Mapping[str, Any], *, allow_empty: bool) -> None:
    if not state and allow_empty:
        return
    required = {
        "schema_version",
        "sequence_number",
        "receipt_id",
        "cycle_ids",
        "nonces",
        "consumed_child_receipt_ids",
        "consumed_child_evidence_digests",
        "signed_receipt",
        "signing_response",
        "revision",
    }
    if set(state) != required or state.get("schema_version") != (
        SIGNER_CONTROL_LOOP_ANCHOR_SCHEMA_VERSION
    ):
        raise ValueError("signer_control_loop_anchor_state_invalid")
    sequence = state.get("sequence_number")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError("signer_control_loop_anchor_state_invalid")
    for key in (
        "cycle_ids",
        "nonces",
        "consumed_child_receipt_ids",
        "consumed_child_evidence_digests",
    ):
        values = state.get(key)
        if not isinstance(values, list) or len(values) > _MAX_HISTORY_ITEMS:
            raise ValueError("signer_control_loop_anchor_state_invalid")
        if len(values) != len(set(values)):
            raise ValueError("signer_control_loop_anchor_state_invalid")
    if not isinstance(state.get("signed_receipt"), Mapping) or not isinstance(
        state.get("signing_response"), Mapping
    ):
        raise ValueError("signer_control_loop_anchor_state_invalid")


def _canonical(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "AtomicSignerControlLoopAnchorStore",
    "ControlLoopAnchorPreparation",
    "ControlLoopAnchorStore",
    "InMemorySignerControlLoopAnchorStore",
    "SIGNER_CONTROL_LOOP_ANCHOR_SCHEMA_VERSION",
]
