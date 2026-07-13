"""RedDog context snapshot Fusion and assignment gate.

This pure gate consumes a previously built operational context snapshot and
decides whether Fusion and worker assignment may proceed. It does not call a
model, spawn workers, enqueue OpenClaw, dispatch Hermes, or mutate work state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    ASSIGNMENT_CONTEXT_VALID,
    ContextView,
    EvidenceBundle,
    OperationalContextSnapshot,
    SourceReceipt,
    validate_context_before_assignment,
)


FUSION_ASSIGNMENT_GATE_PASSED = "FUSION_ASSIGNMENT_GATE_PASSED"
FUSION_ASSIGNMENT_GATE_REJECTED = "FUSION_ASSIGNMENT_GATE_REJECTED"


@dataclass(frozen=True)
class DeterminationContextBinding:
    """Binding that every downstream model result/work order must carry."""

    determination_id: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    context_view_id: str
    evidence_bundle_id: str
    requested_operation: str
    prompt_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FusionAssignmentGateDecision:
    """Fail-closed decision for Fusion and assignment."""

    accepted: bool
    status: str
    fusion_allowed: bool
    assignment_allowed: bool
    determination_binding: Optional[DeterminationContextBinding]
    rejection_reasons: tuple[str, ...]
    source_receipt_digests: tuple[str, ...]
    no_model_call_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "fusion_allowed": self.fusion_allowed,
            "assignment_allowed": self.assignment_allowed,
            "determination_binding": (
                self.determination_binding.to_dict() if self.determination_binding else None
            ),
            "rejection_reasons": list(self.rejection_reasons),
            "source_receipt_digests": list(self.source_receipt_digests),
            "no_model_call_performed": self.no_model_call_performed,
            "no_worker_spawn_performed": self.no_worker_spawn_performed,
            "no_queue_mutation_performed": self.no_queue_mutation_performed,
            "no_execution_performed": self.no_execution_performed,
        }


def evaluate_context_snapshot_fusion_assignment_gate(
    *,
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    current_repo_head_sha: str,
    current_work_state_revision: str,
    current_breadcrumb_high_watermark: str | None = None,
    requested_operation: str,
    prompt_text: str = "",
    now_iso: str | None = None,
    require_assignment: bool = True,
) -> FusionAssignmentGateDecision:
    """Return a deterministic gate decision before Fusion or assignment."""

    reasons: list[str] = []
    if snapshot is None:
        reasons.append("missing_snapshot")
    if context_view is None:
        reasons.append("missing_context_view")
    if evidence_bundle is None:
        reasons.append("missing_evidence_bundle")
    if not requested_operation.strip():
        reasons.append("missing_requested_operation")

    if reasons or snapshot is None or context_view is None or evidence_bundle is None:
        return _reject(reasons, snapshot)

    _validate_binding_shapes(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        reasons=reasons,
    )
    _validate_source_receipts(snapshot.source_receipts, reasons)
    if not evidence_bundle.report_digests and not evidence_bundle.external_research_receipts:
        reasons.append("empty_evidence_bundle")

    assignment_check = validate_context_before_assignment(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        current_repo_head_sha=current_repo_head_sha,
        current_work_state_revision=current_work_state_revision,
        current_breadcrumb_high_watermark=current_breadcrumb_high_watermark,
        now_iso=now_iso,
    )
    if assignment_check.status != ASSIGNMENT_CONTEXT_VALID:
        reasons.extend(assignment_check.rejection_reasons)

    if reasons:
        return _reject(reasons, snapshot)

    prompt_digest = _digest(
        {
            "prompt_text": prompt_text,
            "requested_operation": requested_operation,
            "context_view_id": context_view.context_view_id,
            "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
        }
    )
    determination_id = _digest(
        {
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
            "context_view_id": context_view.context_view_id,
            "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
            "requested_operation": requested_operation,
            "prompt_digest": prompt_digest,
        }
    )
    binding = DeterminationContextBinding(
        determination_id=determination_id,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id,
        requested_operation=requested_operation,
        prompt_digest=prompt_digest,
    )
    return FusionAssignmentGateDecision(
        accepted=True,
        status=FUSION_ASSIGNMENT_GATE_PASSED,
        fusion_allowed=True,
        assignment_allowed=require_assignment,
        determination_binding=binding,
        rejection_reasons=(),
        source_receipt_digests=tuple(receipt.content_digest for receipt in snapshot.source_receipts),
    )


def _validate_binding_shapes(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: ContextView,
    evidence_bundle: EvidenceBundle,
    reasons: list[str],
) -> None:
    if context_view.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("context_view_snapshot_mismatch")
    if context_view.snapshot_content_digest != snapshot.snapshot_content_digest:
        reasons.append("context_view_content_mismatch")
    if evidence_bundle.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("evidence_bundle_snapshot_mismatch")
    if evidence_bundle.context_view_id != context_view.context_view_id:
        reasons.append("evidence_bundle_context_view_mismatch")


def _validate_source_receipts(receipts: Sequence[SourceReceipt], reasons: list[str]) -> None:
    if not receipts:
        reasons.append("missing_source_receipts")
        return
    for receipt in receipts:
        if receipt.required and receipt.freshness != "FRESH":
            reasons.append(f"required_source_not_fresh:{receipt.source}")
        if receipt.required and receipt.rejection_reasons:
            for reason in receipt.rejection_reasons:
                reasons.append(f"{receipt.source}:{reason}")


def _reject(
    reasons: Sequence[str],
    snapshot: OperationalContextSnapshot | None,
) -> FusionAssignmentGateDecision:
    return FusionAssignmentGateDecision(
        accepted=False,
        status=FUSION_ASSIGNMENT_GATE_REJECTED,
        fusion_allowed=False,
        assignment_allowed=False,
        determination_binding=None,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        source_receipt_digests=tuple(
            receipt.content_digest for receipt in snapshot.source_receipts
        )
        if snapshot
        else (),
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "FUSION_ASSIGNMENT_GATE_PASSED",
    "FUSION_ASSIGNMENT_GATE_REJECTED",
    "DeterminationContextBinding",
    "FusionAssignmentGateDecision",
    "evaluate_context_snapshot_fusion_assignment_gate",
]
