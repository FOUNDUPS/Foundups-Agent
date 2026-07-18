"""Strict scalar-field validation for resident control-loop receipts."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping


def validate_current_receipt_fields(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload.get("accepted"), bool):
        raise ValueError("resident_control_loop_receipt_accepted_invalid")
    _validate_text_fields(payload)
    _validate_count_fields(payload)
    _validate_boolean_fields(payload)


def _validate_text_fields(payload: Mapping[str, Any]) -> None:
    required = (
        ("receipt_id", 160), ("cycle_id", 160), ("nonce", 192),
        ("legacy_prefix_digest", 80), ("status", 80), ("created_at", 80),
        ("repo_root_digest", 64), ("source_receipt_ids_digest", 80),
        ("child_execution_evidence_digest", 80), ("authentication_status", 32),
    )
    for key, limit in required:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"resident_control_loop_receipt_{key}_invalid")
    optional = (
        ("previous_receipt_id", 160), ("issuer_principal_id", 256),
        ("signer_public_key", 512), ("signer_key_fingerprint", 160),
        ("key_epoch", 160), ("consensus_receipt_digest", 256),
        ("authority_profile_digest", 80),
        ("authority_profile_source_receipt_id", 80), ("signature", 512),
        ("signer_audit_mac", 512), ("signer_audit_attestation_signature", 512),
    )
    if any(
        not isinstance(payload.get(key), str) or len(payload.get(key)) > limit
        for key, limit in optional
    ):
        raise ValueError("resident_control_loop_receipt_text_invalid")


def _validate_count_fields(payload: Mapping[str, Any]) -> None:
    fields = (
        "sequence_number", "rounds", "serial_progress", "claim_progress",
        "authority_issuance_count",
        "worker_claim_count", "worker_execution_count", "worker_completion_count",
        "worker_requeue_count", "worker_failure_count", "worktree_creation_count",
        "bounded_file_edit_count", "slice_verification_count", "draft_pr_publish_count",
        "pattern_memory_admission_count", "worker_process_spawn_count",
        "shell_command_count", "worker_effects_unverified_count",
        "child_execution_evidence_count",
    )
    for key in fields:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("resident_control_loop_receipt_integer_invalid")


def _validate_boolean_fields(payload: Mapping[str, Any]) -> None:
    fields = (
        "control_lock_acquired", "authority_issued", "worker_claim_performed",
        "worker_execution_performed", "worktree_creation_observed",
        "bounded_file_edit_observed", "slice_verification_observed",
        "draft_pr_publish_observed", "pattern_memory_admission_observed",
        "worker_process_spawn_observed", "shell_command_execution_observed",
    )
    if any(not isinstance(payload.get(key), bool) for key in fields):
        raise ValueError("resident_control_loop_receipt_boolean_invalid")


def strict_string_tuple(value: Any, max_chars: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("resident_control_loop_receipt_list_invalid")
    values = tuple(value)
    if len(values) > 128 or any(
        not isinstance(item, str) or not item.strip() or len(item.strip()) > max_chars
        for item in values
    ):
        raise ValueError("resident_control_loop_receipt_list_invalid")
    return tuple(item.strip() for item in values)


def strict_nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("resident_control_loop_receipt_integer_invalid")
    return value


def parse_receipt_line(raw: str, line_number: int) -> dict[str, Any]:
    if len(raw.encode("utf-8")) > 64 * 1024:
        raise ValueError(f"resident_control_loop_receipt_line_too_large:{line_number}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"resident_control_loop_receipt_chain_invalid_json:{line_number}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"resident_control_loop_receipt_chain_invalid:{line_number}")
    return payload


def validated_receipt_identity(
    payload: Mapping[str, Any],
    line_number: int,
    seen_ids: set[str],
    receipt_id_builder: Callable[[Mapping[str, Any]], str],
) -> tuple[Any, str]:
    schema = payload.get("schema_version")
    receipt_id = str(payload.get("receipt_id") or "").strip()
    if not receipt_id:
        raise ValueError(f"resident_control_loop_receipt_id_missing:{line_number}")
    if receipt_id in seen_ids:
        raise ValueError(f"resident_control_loop_receipt_id_duplicate:{line_number}")
    if receipt_id != receipt_id_builder(payload):
        raise ValueError(f"resident_control_loop_receipt_digest_invalid:{line_number}")
    return schema, receipt_id


__all__ = [
    "parse_receipt_line",
    "strict_nonnegative_int",
    "strict_string_tuple",
    "validate_current_receipt_fields",
    "validated_receipt_identity",
]
