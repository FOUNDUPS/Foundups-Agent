"""Authenticated, one-shot verified outcomes for resident FoundUp Memex views."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
    rehydrate_held_out_outcome_receipt,
    rehydrate_verified_slice_receipt,
    verified_outcome_evidence_bundle_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    ReceiptSignatureVerifier,
    SignedReceipt,
    verify_signed_receipt_chain,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_digest,
    reddog_verified_pattern_memory_record_id,
)

VERIFIED_OUTCOME_RECORD_SCHEMA = "reddog_verified_recursive_improvement_outcome.v1"
VERIFIED_OUTCOME_BINDING_SCHEMA = "foundup_memex_verified_outcome_binding.v1"
_HEAD_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RECORD_FIELDS = {
    "schema_version", "record_type", "work_order_id", "slice_name", "gate_id",
    "ratchet_id", "verifier_receipt_id", "improvement_job_id",
    "held_out_suite_id", "held_out_suite_digest",
    "model_runtime_binding_receipt_id", "model_runtime_binding_digest",
    "candidate_head_sha", "regression_test_count",
    "pattern_memory_admission_allowed", "gate_result_digest", "admission_metadata",
}
_BINDING_FIELDS = {
    "schema_version", "foundup_id", "snapshot_id", "snapshot_content_digest",
    "worker_id", "verifier_id", "verified_at",
}


class VerifiedOutcomeSource(Protocol):
    def load_verified_outcome(self, record_id: str) -> Mapping[str, Any] | None: ...


class VerifiedOutcomeReplayStore(Protocol):
    def consume_once(self, receipt_id: str) -> bool: ...


class VerifiedFoundUpOutcomeCapability:
    """Opaque handle accepted only by the verifier instance that minted it."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_factory_required")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("verified_foundup_outcome_capability_is_immutable")

    def __copy__(self) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("verified_foundup_outcome_capability_pickle_forbidden")


@dataclass(frozen=True)
class _OutcomeSeal:
    projection: Mapping[str, Any]
    projection_digest: str
    replay_store: VerifiedOutcomeReplayStore
    replay_receipt_id: str


_LOCK = threading.Lock()
_CAPABILITIES: weakref.WeakKeyDictionary[VerifiedFoundUpOutcomeCapability, _OutcomeSeal] = (
    weakref.WeakKeyDictionary()
)


def verify_and_issue_foundup_memex_outcome(
    *,
    source: VerifiedOutcomeSource,
    record_id: str,
    verification_receipt: Mapping[str, Any],
    held_out_receipt: Mapping[str, Any],
    signed_receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    reddog_public_key: str,
    signature_verifier: ReceiptSignatureVerifier,
    reddog_id: str,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    replay_store: VerifiedOutcomeReplayStore,
    now_epoch: int, max_age_seconds: int = 600,
) -> VerifiedFoundUpOutcomeCapability:
    _validate_trust_dependencies(source, replay_store, signature_verifier)
    record, binding = _validated_record_and_binding(
        source=source,
        record_id=record_id,
        expected_foundup_id=expected_foundup_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_snapshot_content_digest=expected_snapshot_content_digest,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )
    verifier = rehydrate_verified_slice_receipt(verification_receipt)
    held_out = rehydrate_held_out_outcome_receipt(
        held_out_receipt,
        verifier=verifier,
    )
    _validate_evidence_links(record, binding, verifier.to_dict(), held_out.to_dict())
    signed_digest = verified_outcome_evidence_bundle_digest(
        record=record,
        verifier_receipt=verifier.to_dict(),
        held_out_receipt=held_out.to_dict(),
    )
    terminal, chain = _verify_signed_bundle(
        signed_receipts=signed_receipts,
        reddog_public_key=reddog_public_key,
        signature_verifier=signature_verifier,
        work_order_id=str(record["work_order_id"]),
        reddog_id=reddog_id,
        signed_digest=signed_digest,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )
    return _mint_capability(
        _projection(
            record,
            binding,
            record_id,
            reddog_verified_pattern_memory_record_digest(record),
            signed_digest,
            terminal,
            chain,
        ),
        replay_store=replay_store,
        replay_receipt_id=terminal.receipt_id,
    )


def _verify_signed_bundle(
    *,
    signed_receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    reddog_public_key: str,
    signature_verifier: ReceiptSignatureVerifier,
    work_order_id: str,
    reddog_id: str,
    signed_digest: str,
    now_epoch: int,
    max_age_seconds: int,
) -> tuple[SignedReceipt, Any]:
    chain = verify_signed_receipt_chain(
        signed_receipts,
        reddog_public_key=reddog_public_key,
        signature_verifier=signature_verifier,
        work_order_id=work_order_id,
        reddog_id=reddog_id,
        now=now_epoch,
        allow_empty=False,
    )
    if chain.decision != SIGNED_RECEIPT_CHAIN_ACCEPT or not chain.accepted:
        raise ValueError("verified_outcome_signed_receipt_chain_rejected")
    terminal = _terminal_receipt(signed_receipts)
    if terminal.covered_action_digest != signed_digest:
        raise ValueError("verified_outcome_signed_digest_mismatch")
    if now_epoch - terminal.issued_at < 0 or now_epoch - terminal.issued_at > max_age_seconds:
        raise ValueError("verified_outcome_signature_expired")
    return terminal, chain


def _mint_capability(
    projection: Mapping[str, Any],
    *,
    replay_store: VerifiedOutcomeReplayStore,
    replay_receipt_id: str,
) -> VerifiedFoundUpOutcomeCapability:
    capability = object.__new__(VerifiedFoundUpOutcomeCapability)
    with _LOCK:
        _CAPABILITIES[capability] = _OutcomeSeal(
            projection=projection,
            projection_digest=_digest(projection),
            replay_store=replay_store,
            replay_receipt_id=replay_receipt_id,
        )
    return capability


def consume_verified_foundup_memex_outcome(
    capability: Any,
    *,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
) -> Mapping[str, Any] | None:
    """Consume one capability and return its immutable public projection."""

    if type(capability) is not VerifiedFoundUpOutcomeCapability:
        return None
    with _LOCK:
        seal = _CAPABILITIES.get(capability)
        if seal is None or _digest(seal.projection) != seal.projection_digest:
            return None
        projection = dict(seal.projection)
        expected = (
            expected_foundup_id,
            expected_snapshot_id,
            expected_snapshot_content_digest,
        )
        actual = (
            projection.get("foundup_id"),
            projection.get("snapshot_id"),
            projection.get("snapshot_content_digest"),
        )
        if actual != expected:
            return None
        _CAPABILITIES.pop(capability, None)
        if seal.replay_store.consume_once(seal.replay_receipt_id) is not True:
            return None
    return copy.deepcopy(projection)


def is_verified_foundup_memex_outcome_capability(value: Any) -> bool:
    return type(value) is VerifiedFoundUpOutcomeCapability


def _validate_trust_dependencies(source: Any, replay_store: Any, verifier: Any) -> None:
    required = (
        getattr(source, "load_verified_outcome", None),
        getattr(replay_store, "consume_once", None),
        getattr(verifier, "verify", None),
    )
    if not all(callable(item) for item in required):
        raise ValueError("verified_outcome_trust_dependency_invalid")


def _validated_record_and_binding(
    *,
    source: VerifiedOutcomeSource,
    record_id: str,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
    max_age_seconds: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    record = _load_exact_record(source, record_id)
    binding = _exact_mapping(record.get("admission_metadata"), _BINDING_FIELDS, "binding")
    _validate_record(record, binding, record_id)
    _require_equal(binding, "foundup_id", expected_foundup_id)
    _require_equal(binding, "snapshot_id", expected_snapshot_id)
    _require_equal(binding, "snapshot_content_digest", expected_snapshot_content_digest)
    _validate_verified_at(binding["verified_at"], now_epoch, max_age_seconds)
    return record, binding


def _validate_evidence_links(
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
    verifier: Mapping[str, Any],
    held_out: Mapping[str, Any],
) -> None:
    if (
        binding["worker_id"] != verifier["worker_id"]
        or binding["verifier_id"] != verifier["verifier_id"]
    ):
        raise ValueError("verified_outcome_verifier_identity_mismatch")
    required = (
        ("work_order_id", "work_order_id"),
        ("slice_name", "slice_name"),
        ("verifier_receipt_id", "receipt_id"),
        ("candidate_head_sha", "head_sha"),
    )
    if any(record[left] != verifier[right] for left, right in required):
        raise ValueError("verified_outcome_verifier_receipt_binding_mismatch")
    held_out_required = (
        ("gate_id", "gate_id"),
        ("held_out_suite_id", "held_out_suite_id"),
        ("held_out_suite_digest", "held_out_suite_digest"),
        ("candidate_head_sha", "candidate_head_sha"),
    )
    if any(record[left] != held_out[right] for left, right in held_out_required):
        raise ValueError("verified_outcome_held_out_receipt_binding_mismatch")
    exact_held_out = (
        ("improvement_job_id", "improvement_job_id"),
        ("ratchet_id", "ratchet_id"),
        ("regression_test_count", "regression_test_count"),
        ("model_runtime_binding_receipt_id", "model_runtime_binding_receipt_id"),
        ("model_runtime_binding_digest", "model_runtime_binding_digest"),
    )
    if any(record[left] != (held_out[right] or "") for left, right in exact_held_out):
        raise ValueError("verified_outcome_held_out_lineage_mismatch")
    verifier_runtime = (
        verifier["model_runtime_binding_receipt_id"] or "",
        verifier["model_runtime_binding_digest"],
    )
    record_runtime = (
        record["model_runtime_binding_receipt_id"],
        record["model_runtime_binding_digest"],
    )
    if record_runtime != verifier_runtime:
        raise ValueError("verified_outcome_verifier_runtime_binding_mismatch")


def _load_exact_record(source: VerifiedOutcomeSource, record_id: str) -> Mapping[str, Any]:
    if not record_id or source is None:
        raise ValueError("verified_outcome_source_required")
    value = source.load_verified_outcome(record_id)
    return _exact_mapping(value, _RECORD_FIELDS, "record")


def _exact_mapping(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"verified_outcome_{label}_schema_invalid")
    return dict(value)


def _validate_record(record: Mapping[str, Any], binding: Mapping[str, Any], record_id: str) -> None:
    required = (
        "work_order_id", "slice_name", "gate_id", "ratchet_id",
        "verifier_receipt_id", "held_out_suite_id", "improvement_job_id",
    )
    if record.get("schema_version") != VERIFIED_OUTCOME_RECORD_SCHEMA:
        raise ValueError("verified_outcome_record_schema_invalid")
    if record.get("record_type") != "reddog_verified_recursive_improvement_outcome":
        raise ValueError("verified_outcome_record_type_invalid")
    if any(not str(record.get(key) or "").strip() for key in required):
        raise ValueError("verified_outcome_required_field_missing")
    if record.get("pattern_memory_admission_allowed") is not True:
        raise ValueError("verified_outcome_not_admitted")
    for key in ("held_out_suite_digest", "gate_result_digest"):
        if not _DIGEST.fullmatch(str(record.get(key) or "")):
            raise ValueError(f"verified_outcome_{key}_invalid")
    runtime_id = str(record.get("model_runtime_binding_receipt_id") or "")
    runtime_digest = str(record.get("model_runtime_binding_digest") or "")
    if bool(runtime_id) != bool(runtime_digest) or (runtime_digest and not _DIGEST.fullmatch(runtime_digest)):
        raise ValueError("verified_outcome_runtime_binding_invalid")
    if not _HEAD_SHA.fullmatch(str(record.get("candidate_head_sha") or "")):
        raise ValueError("verified_outcome_head_sha_invalid")
    if type(record.get("regression_test_count")) is not int or record["regression_test_count"] <= 0:
        raise ValueError("verified_outcome_regression_count_invalid")
    if binding.get("schema_version") != VERIFIED_OUTCOME_BINDING_SCHEMA:
        raise ValueError("verified_outcome_binding_schema_invalid")
    if any(not str(binding.get(key) or "").strip() for key in _BINDING_FIELDS - {"schema_version"}):
        raise ValueError("verified_outcome_binding_field_missing")
    if binding["worker_id"] == binding["verifier_id"]:
        raise ValueError("verified_outcome_verifier_not_independent")
    if reddog_verified_pattern_memory_record_id(record) != record_id:
        raise ValueError("verified_outcome_record_id_mismatch")


def _terminal_receipt(receipts: Sequence[SignedReceipt | Mapping[str, Any]]) -> SignedReceipt:
    raw = receipts[-1]
    if isinstance(raw, SignedReceipt):
        return raw
    return SignedReceipt(
        receipt_id=str(raw["receipt_id"]), work_order_id=str(raw["work_order_id"]),
        reddog_id=str(raw["reddog_id"]), prev_receipt_hash=raw.get("prev_receipt_hash"),
        covered_action_digest=str(raw["covered_action_digest"]),
        reward_account=raw.get("reward_account"), issued_at=int(raw["issued_at"]),
        signature=str(raw["signature"]),
    )


def _projection(
    record: Mapping[str, Any], binding: Mapping[str, Any], record_id: str,
    record_digest: str, evidence_bundle_digest: str,
    terminal: SignedReceipt, chain: Any,
) -> Mapping[str, Any]:
    return {
        "foundup_id": binding["foundup_id"],
        "snapshot_id": binding["snapshot_id"],
        "snapshot_content_digest": binding["snapshot_content_digest"],
        "outcome_id": record_id,
        "work_order_id": record["work_order_id"],
        "slice_name": record["slice_name"],
        "worker_id": binding["worker_id"],
        "verifier_id": binding["verifier_id"],
        "verification_receipt_id": record["verifier_receipt_id"],
        "held_out_receipt_id": record["gate_id"],
        "held_out_suite_id": record["held_out_suite_id"],
        "head_sha": record["candidate_head_sha"],
        "content_digest": record_digest,
        "evidence_bundle_digest": evidence_bundle_digest,
        "signed_receipt_id": terminal.receipt_id,
        "signed_receipt_terminal_hash": chain.terminal_receipt_hash,
        "verified_at": binding["verified_at"],
        "scope_origin": "verified_capability",
        "accepted": True,
        "held_out_passed": True,
    }


def _require_equal(value: Mapping[str, Any], key: str, expected: str) -> None:
    if not expected or value.get(key) != expected:
        raise ValueError(f"verified_outcome_{key}_mismatch")


def _validate_verified_at(value: Any, now_epoch: int, max_age_seconds: int) -> None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("verified_outcome_verified_at_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("verified_outcome_verified_at_invalid")
    age = now_epoch - int(parsed.astimezone(timezone.utc).timestamp())
    if age < 0 or age > max_age_seconds:
        raise ValueError("verified_outcome_verification_expired")


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VERIFIED_OUTCOME_BINDING_SCHEMA", "VERIFIED_OUTCOME_RECORD_SCHEMA",
    "VerifiedFoundUpOutcomeCapability", "VerifiedOutcomeReplayStore",
    "VerifiedOutcomeSource", "consume_verified_foundup_memex_outcome",
    "is_verified_foundup_memex_outcome_capability",
    "verify_and_issue_foundup_memex_outcome",
]
