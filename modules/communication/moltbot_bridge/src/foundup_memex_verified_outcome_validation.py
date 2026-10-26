"""Exact schema, scope, and lineage validation for verified Memex outcomes."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_id,
)


VERIFIED_OUTCOME_RECORD_SCHEMA = "reddog_verified_recursive_improvement_outcome.v1"
VERIFIED_OUTCOME_BINDING_SCHEMA = "foundup_memex_verified_outcome_binding.v2"
_HEAD_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RECORD_FIELDS = {
    "schema_version",
    "record_type",
    "work_order_id",
    "slice_name",
    "gate_id",
    "ratchet_id",
    "verifier_receipt_id",
    "improvement_job_id",
    "held_out_suite_id",
    "held_out_suite_digest",
    "model_runtime_binding_receipt_id",
    "model_runtime_binding_digest",
    "candidate_head_sha",
    "regression_test_count",
    "pattern_memory_admission_allowed",
    "gate_result_digest",
    "admission_metadata",
}
_BINDING_FIELDS = {
    "schema_version",
    "foundup_id",
    "snapshot_id",
    "snapshot_content_digest",
    "work_order_id",
    "slice_id",
    "job_id",
    "worker_id",
    "verifier_id",
    "head_sha",
    "runtime_binding_receipt_id",
    "runtime_binding_digest",
    "verification_receipt_digest",
    "held_out_receipt_digest",
    "verified_at",
}


class VerifiedOutcomeSource(Protocol):
    def load_verified_outcome(self, record_id: str) -> Mapping[str, Any] | None: ...


def load_validated_outcome(
    *,
    source: VerifiedOutcomeSource,
    record_id: str,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
    max_age_seconds: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Load one exact record and enforce its assignment bindings."""

    record = _load_exact_record(source, record_id)
    binding = _exact_mapping(record.get("admission_metadata"), _BINDING_FIELDS, "binding")
    _validate_record(record, binding, record_id)
    _require_equal(binding, "foundup_id", expected_foundup_id)
    _require_equal(binding, "snapshot_id", expected_snapshot_id)
    _require_equal(binding, "snapshot_content_digest", expected_snapshot_content_digest)
    _validate_verified_at(binding["verified_at"], now_epoch, max_age_seconds)
    return record, binding


def validate_outcome_evidence_links(
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
    verifier: Mapping[str, Any],
    held_out: Mapping[str, Any],
) -> None:
    """Bind the record to exact verifier, held-out, worker, and runtime evidence."""

    exact_binding = {
        "work_order_id": record["work_order_id"],
        "slice_id": record["slice_name"],
        "job_id": record["improvement_job_id"],
        "head_sha": record["candidate_head_sha"],
        "runtime_binding_receipt_id": record["model_runtime_binding_receipt_id"],
        "runtime_binding_digest": record["model_runtime_binding_digest"],
        "verification_receipt_digest": _digest(verifier),
        "held_out_receipt_digest": _digest(held_out),
    }
    for key, expected in exact_binding.items():
        if binding[key] != expected:
            raise ValueError(f"verified_outcome_{key}_mismatch")
    if binding["worker_id"] != verifier["worker_id"] or binding["verifier_id"] != verifier["verifier_id"]:
        raise ValueError("verified_outcome_verifier_identity_mismatch")
    _validate_verifier_links(record, verifier)
    _validate_held_out_links(record, held_out)


def verified_at_epoch(value: Any) -> int:
    """Parse one timezone-aware verification timestamp."""

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("verified_outcome_verified_at_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("verified_outcome_verified_at_invalid")
    return int(parsed.astimezone(timezone.utc).timestamp())


def _validate_verifier_links(record: Mapping[str, Any], verifier: Mapping[str, Any]) -> None:
    required = (
        ("work_order_id", "work_order_id"),
        ("slice_name", "slice_name"),
        ("verifier_receipt_id", "receipt_id"),
        ("candidate_head_sha", "head_sha"),
    )
    if any(record[left] != verifier[right] for left, right in required):
        raise ValueError("verified_outcome_verifier_receipt_binding_mismatch")
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


def _validate_held_out_links(record: Mapping[str, Any], held_out: Mapping[str, Any]) -> None:
    required = (
        ("gate_id", "gate_id"),
        ("held_out_suite_id", "held_out_suite_id"),
        ("held_out_suite_digest", "held_out_suite_digest"),
        ("candidate_head_sha", "candidate_head_sha"),
    )
    if any(record[left] != held_out[right] for left, right in required):
        raise ValueError("verified_outcome_held_out_receipt_binding_mismatch")
    lineage = (
        ("improvement_job_id", "improvement_job_id"),
        ("ratchet_id", "ratchet_id"),
        ("regression_test_count", "regression_test_count"),
        ("model_runtime_binding_receipt_id", "model_runtime_binding_receipt_id"),
        ("model_runtime_binding_digest", "model_runtime_binding_digest"),
    )
    if any(record[left] != (held_out[right] or "") for left, right in lineage):
        raise ValueError("verified_outcome_held_out_lineage_mismatch")


def _load_exact_record(source: VerifiedOutcomeSource, record_id: str) -> Mapping[str, Any]:
    if not record_id or source is None:
        raise ValueError("verified_outcome_source_required")
    return _exact_mapping(source.load_verified_outcome(record_id), _RECORD_FIELDS, "record")


def _exact_mapping(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"verified_outcome_{label}_schema_invalid")
    return dict(value)


def _validate_record(record: Mapping[str, Any], binding: Mapping[str, Any], record_id: str) -> None:
    required = (
        "work_order_id",
        "slice_name",
        "gate_id",
        "ratchet_id",
        "verifier_receipt_id",
        "held_out_suite_id",
        "improvement_job_id",
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


def _require_equal(value: Mapping[str, Any], key: str, expected: str) -> None:
    if not expected or value.get(key) != expected:
        raise ValueError(f"verified_outcome_{key}_mismatch")


def _validate_verified_at(value: Any, now_epoch: int, max_age_seconds: int) -> None:
    age = now_epoch - verified_at_epoch(value)
    if age < 0 or age > max_age_seconds:
        raise ValueError("verified_outcome_verification_expired")


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VERIFIED_OUTCOME_BINDING_SCHEMA",
    "VERIFIED_OUTCOME_RECORD_SCHEMA",
    "VerifiedOutcomeSource",
    "load_validated_outcome",
    "validate_outcome_evidence_links",
    "verified_at_epoch",
]
