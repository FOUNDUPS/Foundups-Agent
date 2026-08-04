"""Fail-closed rehydration for verifier and held-out outcome receipts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields
from typing import Any, Mapping

from modules.infrastructure.wre_core.src.reddog_held_out_recursive_improvement_regression_gate import (
    HeldOutRecursiveImprovementRegressionReceipt,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AutonomousSliceVerifierReceipt,
)

_HEAD_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_VERIFIER_FIELDS = {item.name for item in fields(AutonomousSliceVerifierReceipt)}
_HELD_OUT_FIELDS = {
    item.name for item in fields(HeldOutRecursiveImprovementRegressionReceipt)
}


def rehydrate_verified_slice_receipt(
    value: Mapping[str, Any],
) -> AutonomousSliceVerifierReceipt:
    """Return one exact, canonically bound accepted verifier receipt."""

    payload = _exact(value, _VERIFIER_FIELDS, "verifier")
    receipt = AutonomousSliceVerifierReceipt(**payload)
    _validate_verifier(receipt)
    if receipt.receipt_id != _verifier_receipt_id(receipt):
        raise ValueError("verified_outcome_verifier_receipt_id_mismatch")
    return receipt


def rehydrate_held_out_outcome_receipt(
    value: Mapping[str, Any],
    *,
    verifier: AutonomousSliceVerifierReceipt,
) -> HeldOutRecursiveImprovementRegressionReceipt:
    """Return one exact held-out receipt bound to its verified source receipt."""

    payload = _exact(value, _HELD_OUT_FIELDS, "held_out")
    receipt = HeldOutRecursiveImprovementRegressionReceipt(**payload)
    _validate_held_out(receipt, verifier)
    if receipt.gate_id != _held_out_gate_id(receipt):
        raise ValueError("verified_outcome_held_out_receipt_id_mismatch")
    return receipt


def verified_outcome_evidence_bundle_digest(
    *,
    record: Mapping[str, Any],
    verifier_receipt: Mapping[str, Any],
    held_out_receipt: Mapping[str, Any],
) -> str:
    """Bind the admitted record and both independently rehydrated receipts."""

    return _digest(
        {
            "record": dict(record),
            "verifier_receipt": dict(verifier_receipt),
            "held_out_receipt": dict(held_out_receipt),
        }
    )


def _validate_verifier(receipt: AutonomousSliceVerifierReceipt) -> None:
    required = (
        receipt.work_order_id,
        receipt.slice_name,
        receipt.verifier_id,
        receipt.worker_id,
        receipt.assurance_reservation_id,
        receipt.verifier_task_id,
    )
    if not all(str(value).strip() for value in required):
        raise ValueError("verified_outcome_verifier_receipt_field_missing")
    if receipt.verifier_id == receipt.worker_id:
        raise ValueError("verified_outcome_verifier_not_independent")
    if receipt.accepted is not True or receipt.rejection_reasons:
        raise ValueError("verified_outcome_verifier_receipt_not_accepted")
    verifier_safety = (
        receipt.no_command_execution_performed,
        receipt.no_pr_publish_performed,
        receipt.no_merge_performed,
        receipt.no_pattern_memory_write_performed,
        receipt.no_reward_settlement_performed,
        receipt.no_holoindex_reindex_performed,
    )
    if any(value is not True for value in verifier_safety):
        raise ValueError("verified_outcome_verifier_safety_attestation_invalid")
    if not _HEAD_SHA.fullmatch(receipt.base_sha) or not _HEAD_SHA.fullmatch(receipt.head_sha):
        raise ValueError("verified_outcome_verifier_head_sha_invalid")
    if receipt.base_sha == receipt.head_sha or not receipt.changed_paths:
        raise ValueError("verified_outcome_verifier_change_evidence_invalid")
    digests = (
        receipt.assurance_reservation_digest,
        receipt.diff_digest,
        receipt.test_evidence_digest,
        receipt.signed_authority_digest,
        receipt.receipt_chain_terminal_hash,
        receipt.worktree_receipt_digest,
        receipt.holoindex_freshness_receipt_digest,
    )
    if not all(_DIGEST.fullmatch(str(value or "")) for value in digests):
        raise ValueError("verified_outcome_verifier_digest_invalid")
    _optional_pair(
        receipt.model_runtime_binding_receipt_id,
        receipt.model_runtime_binding_digest,
        "verifier_runtime_binding",
    )
    _optional_pair(
        receipt.memex_supply_receipt_id,
        receipt.memex_supply_digest,
        "verifier_memex_binding",
    )


def _validate_held_out(
    receipt: HeldOutRecursiveImprovementRegressionReceipt,
    verifier: AutonomousSliceVerifierReceipt,
) -> None:
    if receipt.rejection_reasons:
        raise ValueError("verified_outcome_held_out_receipt_not_accepted")
    if receipt.pattern_memory_admission_requested is not True:
        raise ValueError("verified_outcome_held_out_admission_not_requested")
    if receipt.pattern_memory_admission_allowed is not True:
        raise ValueError("verified_outcome_held_out_admission_not_allowed")
    if type(receipt.regression_test_count) is not int or receipt.regression_test_count <= 0:
        raise ValueError("verified_outcome_held_out_test_count_invalid")
    held_out_safety = (
        receipt.no_command_execution_performed,
        receipt.no_test_execution_performed,
        receipt.no_pattern_memory_write_performed,
        receipt.no_pr_publish_performed,
        receipt.no_merge_performed,
        receipt.no_holoindex_reindex_performed,
    )
    if any(value is not True for value in held_out_safety):
        raise ValueError("verified_outcome_held_out_safety_attestation_invalid")
    expected = (
        verifier.receipt_id,
        verifier.work_order_id,
        verifier.slice_name,
        verifier.head_sha,
    )
    actual = (
        receipt.verifier_receipt_id,
        receipt.work_order_id,
        receipt.slice_name,
        receipt.candidate_head_sha,
    )
    if actual != expected:
        raise ValueError("verified_outcome_held_out_verifier_binding_mismatch")
    digests = (
        receipt.held_out_suite_digest,
        receipt.baseline_digest,
        receipt.candidate_digest,
        receipt.holoindex_freshness_receipt_digest,
    )
    if not all(_DIGEST.fullmatch(str(value or "")) for value in digests):
        raise ValueError("verified_outcome_held_out_digest_invalid")
    _optional_pair(
        receipt.model_runtime_binding_receipt_id,
        receipt.model_runtime_binding_digest,
        "held_out_runtime_binding",
    )
    verifier_runtime = (
        verifier.model_runtime_binding_receipt_id,
        verifier.model_runtime_binding_digest,
    )
    held_out_runtime = (
        receipt.model_runtime_binding_receipt_id,
        receipt.model_runtime_binding_digest,
    )
    if verifier_runtime != held_out_runtime:
        raise ValueError("verified_outcome_runtime_binding_mismatch")


def _verifier_receipt_id(receipt: AutonomousSliceVerifierReceipt) -> str:
    payload = receipt.to_dict()
    for key in (
        "receipt_id",
        "accepted",
        "no_command_execution_performed",
        "no_pr_publish_performed",
        "no_merge_performed",
        "no_pattern_memory_write_performed",
        "no_reward_settlement_performed",
        "no_holoindex_reindex_performed",
    ):
        payload.pop(key, None)
    payload["model_runtime_binding_receipt_id"] = (
        receipt.model_runtime_binding_receipt_id or ""
    )
    payload["memex_supply_receipt_id"] = receipt.memex_supply_receipt_id or ""
    return "wre_slice_verify_" + _digest(payload).removeprefix("sha256:")[:16]


def _held_out_gate_id(receipt: HeldOutRecursiveImprovementRegressionReceipt) -> str:
    payload = receipt.to_dict()
    for key in (
        "gate_id",
        "regression_test_count",
        "no_command_execution_performed",
        "no_test_execution_performed",
        "no_pattern_memory_write_performed",
        "no_pr_publish_performed",
        "no_merge_performed",
        "no_holoindex_reindex_performed",
    ):
        payload.pop(key, None)
    payload["model_runtime_binding_receipt_id"] = (
        receipt.model_runtime_binding_receipt_id or ""
    )
    return "held_out_recursive_gate_" + _digest(payload).removeprefix("sha256:")[:16]


def _optional_pair(receipt_id: Any, digest: Any, label: str) -> None:
    populated = bool(str(receipt_id or "")) or bool(str(digest or ""))
    if populated and (not str(receipt_id or "") or not _DIGEST.fullmatch(str(digest or ""))):
        raise ValueError(f"verified_outcome_{label}_invalid")


def _exact(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"verified_outcome_{label}_receipt_schema_invalid")
    return dict(value)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "rehydrate_held_out_outcome_receipt",
    "rehydrate_verified_slice_receipt",
    "verified_outcome_evidence_bundle_digest",
]
