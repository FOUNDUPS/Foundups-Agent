"""Verified v2 grounding evidence supplied to RedDog model-backed audits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    PER_FILE_READ_BYTES,
    TOTAL_READ_BUDGET_BYTES,
    secure_read_repo_head_file,
)
from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    BOUNDED_SCHEMA_VERSION,
    VerifiedGroundedSemanticEvidence,
    VerifiedGroundedTargetReceipt,
    canonical_digest,
    rehydrate_grounded_semantic_evidence,
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    ReadOnlyAuditTaskRejectReason,
    ReadOnlyTargetEvidence,
    _ReadOnlyTargetSnapshot,
)


@dataclass(frozen=True)
class ValidatedTaskGrounding:
    receipt: VerifiedGroundedTargetReceipt
    semantic_evidence: VerifiedGroundedSemanticEvidence | None


def validate_task_grounding(
    task_context: Mapping[str, Any], assignment: Mapping[str, Any], repo_root: Path
) -> tuple[ValidatedTaskGrounding | None, tuple[str, ...]]:
    receipt = task_context.get("grounding_receipt")
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != BOUNDED_SCHEMA_VERSION:
        return None, (ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID,)
    validation = validate_grounded_target_receipt(
        receipt, work_focus=str(task_context.get("work_focus") or "")
    )
    if not validation.accepted or validation.verified is None:
        return None, tuple(validation.rejection_reasons or ("grounding_receipt_rejected",))
    verified = validation.verified
    if not _repository_state_matches(receipt, repo_root):
        return None, (ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID,)
    if not _assignment_bindings_match(task_context, assignment, verified):
        return None, ("grounding_assignment_binding_mismatch",)
    typed = task_context.get("typed_targets")
    if not isinstance(typed, Mapping) or canonical_digest(typed) != verified.typed_targets_digest:
        return None, ("grounding_typed_targets_binding_mismatch",)
    try:
        semantic = _rehydrate_if_required(receipt, verified, task_context, repo_root)
    except (OSError, TypeError, ValueError):
        return None, (ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID,)
    return ValidatedTaskGrounding(verified, semantic), ()


def grounding_changed_after_model(
    expected: ValidatedTaskGrounding | None,
    task_context: Mapping[str, Any],
    assignment: Mapping[str, Any],
    repo_root: Path,
) -> bool:
    if expected is None:
        return False
    actual, reasons = validate_task_grounding(task_context, assignment, repo_root)
    return bool(reasons or actual != expected)


def verified_grounding_snapshots(
    grounding: ValidatedTaskGrounding | None,
    *,
    repo_root: Path,
    bound_snapshots: Sequence[_ReadOnlyTargetSnapshot],
) -> tuple[tuple[_ReadOnlyTargetSnapshot, ...] | None, str]:
    if grounding is None:
        return None, ""
    snapshots = list(bound_snapshots)
    seen = {item.evidence.path for item in snapshots}
    consumed = sum(item.evidence.bytes_read for item in snapshots)
    if grounding.semantic_evidence is not None:
        for record in grounding.semantic_evidence.records:
            if record.path in seen:
                return None, ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID
            snapshots.append(_semantic_snapshot(record))
            seen.add(record.path)
            consumed += record.bytes
    return _append_repo_targets(grounding, repo_root, snapshots, seen, consumed)


def holo_receipt_matches_grounding(
    holo_receipt: Mapping[str, Any], grounding: ValidatedTaskGrounding | None
) -> bool:
    if grounding is None or grounding.semantic_evidence is None:
        return True
    proof = grounding.semantic_evidence
    return bool(
        holo_receipt.get("freshness_generation_id") == proof.holoindex_generation_id
        and holo_receipt.get("freshness_receipt_digest")
        == proof.holoindex_freshness_receipt_digest
        and holo_receipt.get("repo_head_sha") == proof.repo_head_sha
        and holo_receipt.get("repo_root_digest") == proof.repo_root_digest
    )


def optional_model_binding_fields(
    grounding, memex_receipt, memex_bundle, external_receipt, external_bundle, selection
):
    fields = {}
    if grounding is not None:
        fields["grounding_receipt_id"] = grounding.receipt.receipt_id
        fields["grounding_repo_head_sha"] = grounding.receipt.receipt.get("repo_state_head_sha")
        fields["grounding_repo_root_digest"] = grounding.receipt.receipt.get("repo_state_root_digest")
        if grounding.semantic_evidence is not None:
            fields["grounding_holoindex_generation_id"] = grounding.semantic_evidence.holoindex_generation_id
    optional = (
        ("memex_query_receipt_id", memex_receipt, "receipt_id"),
        ("memex_evidence_bundle_id", memex_bundle, "bundle_id"),
        ("external_research_query_receipt_id", external_receipt, "receipt_id"),
        ("external_research_evidence_bundle_id", external_bundle, "bundle_id"),
    )
    fields.update({key: value.get(source) for key, value, source in optional if value is not None})
    if selection:
        fields.update({
            "model_selection": dict(selection),
            "model_selection_receipt_id": selection.get("receipt_id"),
            "model_selection_digest": selection.get("digest"),
            "model_runtime_binding_receipt_id": selection.get("model_runtime_binding_receipt_id"),
            "model_runtime_binding_digest": selection.get("model_runtime_binding_digest"),
        })
    return fields


def _assignment_bindings_match(task_context, assignment, verified) -> bool:
    digest = canonical_digest(verified.receipt)
    bindings = (
        (task_context.get("grounding_receipt_id"), verified.receipt_id),
        (assignment.get("grounding_receipt_id"), verified.receipt_id),
        (task_context.get("grounding_receipt_digest"), digest),
        (assignment.get("grounding_receipt_digest"), digest),
    )
    allowed = {
        str(value).replace("\\", "/").strip()
        for value in assignment.get("allowed_read_targets", ()) if str(value).strip()
    }
    return (
        all(str(value or "") == expected for value, expected in bindings)
        and set(verified.allowed_read_targets).issubset(allowed)
    )


def _repository_state_matches(receipt, repo_root) -> bool:
    return bool(
        receipt.get("repo_state_head_sha") == read_git_head_sha(repo_root)
        and receipt.get("repo_state_root_digest") == repository_root_digest(repo_root)
    )


def _rehydrate_if_required(receipt, verified, task_context, repo_root):
    if not verified.semantic_targets:
        return None
    return rehydrate_grounded_semantic_evidence(
        receipt,
        work_focus=str(task_context.get("work_focus") or ""),
        repo_root=repo_root,
    )


def _append_repo_targets(grounding, repo_root, snapshots, seen, consumed):
    expected_head = grounding.receipt.receipt.get("repo_state_head_sha")
    for raw_target in grounding.receipt.repo_file_targets:
        path = str(raw_target).split("#", 1)[0]
        if path in seen:
            continue
        read = secure_read_repo_head_file(
            repo_root, path, byte_cap=PER_FILE_READ_BYTES,
            remaining_budget=TOTAL_READ_BUDGET_BYTES - consumed,
        )
        if read.get("ok") is not True:
            return None, ReadOnlyAuditTaskRejectReason.GROUNDING_EVIDENCE_CHANGED
        if read.get("repo_head_sha") != expected_head:
            return None, ReadOnlyAuditTaskRejectReason.GROUNDING_EVIDENCE_CHANGED
        snapshot = _head_snapshot(read)
        snapshots.append(snapshot)
        seen.add(path)
        consumed += snapshot.evidence.bytes_read
    if consumed > TOTAL_READ_BUDGET_BYTES:
        return None, ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID
    return tuple(snapshots), ""


def _semantic_snapshot(record: Any) -> _ReadOnlyTargetSnapshot:
    text = str(record.content)
    return _ReadOnlyTargetSnapshot(
        evidence=_evidence(record.path, record.digest, record.bytes, text, record.truncated),
        text=text,
    )


def _head_snapshot(read: Mapping[str, Any]) -> _ReadOnlyTargetSnapshot:
    text = str(read.get("content") or "")
    return _ReadOnlyTargetSnapshot(
        evidence=_evidence(
            read.get("path"), read.get("digest"), read.get("bytes"), text,
            read.get("truncated"),
        ),
        text=text,
    )


def _evidence(path, digest, byte_count, text, truncated) -> ReadOnlyTargetEvidence:
    return ReadOnlyTargetEvidence(
        path=str(path or ""), digest=str(digest or ""), bytes_read=int(byte_count or 0),
        line_count=text.count("\n") + (1 if text else 0), truncated=bool(truncated),
    )


__all__ = [
    "ValidatedTaskGrounding", "grounding_changed_after_model",
    "holo_receipt_matches_grounding", "validate_task_grounding",
    "optional_model_binding_fields", "verified_grounding_snapshots",
]
