"""Durable authority-store adapter for authenticated Memex outcomes."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AuthorityRuntimeStore,
)


OUTCOME_AUTHORITY_STATE_SCHEMA = "foundup_memex_verified_outcome_authority_state.v1"
OUTCOME_EVIDENCE_ENVELOPE_SCHEMA = "foundup_memex_verified_outcome_evidence.v1"
_STATE_KEY = "foundup_memex_verified_outcome_authority"


class AuthorityRuntimeVerifiedOutcomeStore:
    """Use one existing authority store for evidence and one-use replay."""

    def __init__(self, store: AuthorityRuntimeStore) -> None:
        if not callable(getattr(store, "load", None)) or not callable(
            getattr(store, "commit", None)
        ):
            raise ValueError("verified_outcome_authority_store_invalid")
        self._store = store

    def publish(self, envelope: Mapping[str, Any]) -> str:
        payload = _validated_envelope(envelope)
        record_id = str(payload["record_id"])
        current = self._store.load()
        state = _state_from(current)
        evidence = dict(state["evidence"])
        existing = evidence.get(record_id)
        if existing is not None:
            if existing != payload:
                raise ValueError("verified_outcome_evidence_conflict")
            return record_id
        evidence[record_id] = payload
        state["evidence"] = evidence
        updated = dict(current)
        updated[_STATE_KEY] = state
        self._store.commit(updated, expected_revision=current.get("revision"))
        return record_id

    def load_envelope(self, record_id: str) -> Mapping[str, Any] | None:
        if not str(record_id or "").strip():
            return None
        try:
            state = _state_from(self._store.load())
            envelope = state["evidence"].get(record_id)
            return copy.deepcopy(_validated_envelope(envelope))
        except (RuntimeError, TypeError, ValueError):
            return None

    def load_verified_outcome(self, record_id: str) -> Mapping[str, Any] | None:
        envelope = self.load_envelope(record_id)
        if envelope is None:
            return None
        return copy.deepcopy(envelope["record"])

    def consume_once(self, receipt_id: str) -> bool:
        candidate = str(receipt_id or "").strip()
        if not candidate:
            return False
        try:
            current = self._store.load()
            state = _state_from(current)
            consumed = list(state["consumed_receipt_ids"])
            if candidate in set(consumed):
                return False
            consumed.append(candidate)
            state["consumed_receipt_ids"] = consumed
            updated = dict(current)
            updated[_STATE_KEY] = state
            self._store.commit(updated, expected_revision=current.get("revision"))
            return True
        except (RuntimeError, TypeError, ValueError):
            return False


def build_outcome_evidence_envelope(
    *,
    record_id: str,
    record: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    held_out_receipt: Mapping[str, Any],
    signed_receipt: Mapping[str, Any],
    issuer_principal_id: str,
    issuer_principal_provider: str,
    reddog_id: str,
    signer_key_fingerprint: str,
    key_epoch: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": OUTCOME_EVIDENCE_ENVELOPE_SCHEMA,
        "record_id": record_id,
        "record": dict(record),
        "verification_receipt": dict(verification_receipt),
        "held_out_receipt": dict(held_out_receipt),
        "signed_receipts": [dict(signed_receipt)],
        "issuer_principal_id": issuer_principal_id,
        "issuer_principal_provider": issuer_principal_provider,
        "reddog_id": reddog_id,
        "signer_key_fingerprint": signer_key_fingerprint,
        "key_epoch": key_epoch,
    }
    payload["envelope_digest"] = _digest(payload)
    return _validated_envelope(payload)


def _state_from(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    raw = snapshot.get(_STATE_KEY)
    if raw is None:
        return {
            "schema_version": OUTCOME_AUTHORITY_STATE_SCHEMA,
            "evidence": {},
            "consumed_receipt_ids": [],
        }
    if (
        not isinstance(raw, Mapping)
        or set(raw) != {"schema_version", "evidence", "consumed_receipt_ids"}
        or raw.get("schema_version") != OUTCOME_AUTHORITY_STATE_SCHEMA
        or not isinstance(raw.get("evidence"), Mapping)
        or not isinstance(raw.get("consumed_receipt_ids"), list)
        or len(set(map(str, raw["consumed_receipt_ids"])))
        != len(raw["consumed_receipt_ids"])
    ):
        raise ValueError("verified_outcome_authority_state_invalid")
    return copy.deepcopy(dict(raw))


def _validated_envelope(value: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "record_id",
        "record",
        "verification_receipt",
        "held_out_receipt",
        "signed_receipts",
        "issuer_principal_id",
        "issuer_principal_provider",
        "reddog_id",
        "signer_key_fingerprint",
        "key_epoch",
        "envelope_digest",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError("verified_outcome_evidence_schema_invalid")
    payload = copy.deepcopy(dict(value))
    if payload["schema_version"] != OUTCOME_EVIDENCE_ENVELOPE_SCHEMA:
        raise ValueError("verified_outcome_evidence_schema_invalid")
    if not all(
        str(payload.get(key) or "").strip()
        for key in (
            "record_id",
            "issuer_principal_id",
            "issuer_principal_provider",
            "reddog_id",
            "signer_key_fingerprint",
            "key_epoch",
        )
    ):
        raise ValueError("verified_outcome_evidence_binding_missing")
    if (
        not isinstance(payload["record"], Mapping)
        or not isinstance(payload["verification_receipt"], Mapping)
        or not isinstance(payload["held_out_receipt"], Mapping)
        or not isinstance(payload["signed_receipts"], list)
        or len(payload["signed_receipts"]) != 1
        or not isinstance(payload["signed_receipts"][0], Mapping)
    ):
        raise ValueError("verified_outcome_evidence_payload_invalid")
    claimed = str(payload.pop("envelope_digest"))
    if claimed != _digest(payload):
        raise ValueError("verified_outcome_evidence_digest_invalid")
    payload["envelope_digest"] = claimed
    return payload


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "AuthorityRuntimeVerifiedOutcomeStore",
    "OUTCOME_AUTHORITY_STATE_SCHEMA",
    "OUTCOME_EVIDENCE_ENVELOPE_SCHEMA",
    "build_outcome_evidence_envelope",
]
