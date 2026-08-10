"""RedDog OpenClaw read-only audit swarm runtime.

This module turns an accepted context-snapshot Fusion/assignment gate decision
into deterministic read-only audit assignments. It does not spawn workers, call
models, enqueue OpenClaw, dispatch Hermes, execute shell commands, mutate work
state, or write repository files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    FUSION_ASSIGNMENT_GATE_PASSED,
    DeterminationContextBinding,
    FusionAssignmentGateDecision,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    ContextView,
    EvidenceBundle,
    OperationalContextSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest as grounding_digest,
    validate_grounded_target_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import ModelRuntimeBindingDecision
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)


READONLY_AUDIT_SWARM_PLANNED = "READONLY_AUDIT_SWARM_PLANNED"
READONLY_AUDIT_SWARM_REJECTED = "READONLY_AUDIT_SWARM_REJECTED"
READONLY_AUDIT_REPORTS_ACCEPTED = "READONLY_AUDIT_REPORTS_ACCEPTED"
READONLY_AUDIT_REPORTS_REJECTED = "READONLY_AUDIT_REPORTS_REJECTED"

DEFAULT_AUDIT_LANES = (
    "repo_code_audit",
    "external_research_audit",
    "runtime_freshness_audit",
    "skill_gap_audit",
    "security_governance_audit",
)

LANE_REQUIRED_SOURCE = {
    "repo_code_audit": "repo",
    "external_research_audit": "holoindex",
    "runtime_freshness_audit": "work_state",
    "skill_gap_audit": "holoindex",
    "security_governance_audit": "work_state",
}

FORBIDDEN_ACTIONS = (
    "repo_write",
    "shell_execute",
    "git_push",
    "git_commit",
    "openclaw_enqueue",
    "hermes_dispatch",
    "holoindex_reindex",
    "queue_mutation",
    "worker_spawn",
)

MAX_ASSIGNMENT_TARGETS = 32
MAX_REPORT_BYTES = 48_000
RUNTIME_SURFACE_READONLY_AUDIT = "reddog_readonly_audit_worker"


@dataclass(frozen=True)
class ReadOnlyAuditAssignment:
    """One read-only worker assignment packet."""

    assignment_id: str
    lane_id: str
    worker_role: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    context_view_id: str
    evidence_bundle_id: str
    determination_id: str
    required_source: str
    allowed_read_targets: tuple[str, ...]
    grounding_receipt_id: str = ""
    grounding_receipt_digest: str = ""
    wsp15_allocation_receipt_id: str = ""
    wsp15_allocation_digest: str = ""
    model_runtime_binding_receipt_id: str = ""
    model_runtime_binding_digest: str = ""
    forbidden_actions: tuple[str, ...] = FORBIDDEN_ACTIONS
    no_worker_spawn_performed: bool = True
    no_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_queue_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditSwarmReceipt:
    """Receipt proving a read-only audit swarm was planned, not executed."""

    swarm_id: str
    status: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    context_view_id: str
    evidence_bundle_id: str
    determination_id: str
    requested_operation: str
    assignment_ids: tuple[str, ...]
    lanes: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    grounding_receipt_id: str = ""
    grounding_receipt_digest: str = ""
    grounding_receipt: Mapping[str, Any] = field(default_factory=dict)
    grounding_work_focus: str = ""
    wsp15_allocation_receipt_id: str = ""
    wsp15_allocation_digest: str = ""
    wsp15_allocation_receipt: Mapping[str, Any] = field(default_factory=dict)
    model_runtime_binding_receipt_id: str = ""
    model_runtime_binding_digest: str = ""
    model_runtime_binding_receipt: Mapping[str, Any] = field(default_factory=dict)
    no_model_call_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_queue_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditSwarmPlan:
    """Planning result for the read-only audit swarm."""

    accepted: bool
    status: str
    receipt: ReadOnlyAuditSwarmReceipt
    assignments: tuple[ReadOnlyAuditAssignment, ...]
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict(),
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "rejection_reasons": list(self.rejection_reasons),
        }


@dataclass(frozen=True)
class ReadOnlyAuditReportBundle:
    """Verified shape of returned read-only audit reports."""

    bundle_id: str
    swarm_id: str
    report_digests: tuple[str, ...]
    lanes_reported: tuple[str, ...]
    missing_lanes: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    no_report_execution_claimed: bool = True
    no_report_repo_mutation_claimed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditReportValidationResult:
    """Validation result for returned read-only audit reports."""

    accepted: bool
    status: str
    bundle: Optional[ReadOnlyAuditReportBundle]
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "bundle": self.bundle.to_dict() if self.bundle else None,
            "rejection_reasons": list(self.rejection_reasons),
        }


def plan_reddog_openclaw_readonly_audit_swarm(
    *,
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    gate_decision: FusionAssignmentGateDecision | None,
    audit_lanes: Sequence[str] = DEFAULT_AUDIT_LANES,
    allowed_read_targets: Sequence[str] = (),
    wsp15_allocation_receipt: Mapping[str, Any] | None = None,
    grounding_receipt: Mapping[str, Any] | None = None,
    grounding_work_focus: str = "",
    model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    require_model_runtime_binding: bool = False,
) -> ReadOnlyAuditSwarmPlan:
    """Plan read-only audit assignments from an already accepted context gate."""

    reasons: list[str] = []
    if snapshot is None:
        reasons.append("missing_snapshot")
    if context_view is None:
        reasons.append("missing_context_view")
    if evidence_bundle is None:
        reasons.append("missing_evidence_bundle")
    if gate_decision is None:
        reasons.append("missing_gate_decision")
    binding = gate_decision.determination_binding if gate_decision else None
    if gate_decision and (not gate_decision.accepted or gate_decision.status != FUSION_ASSIGNMENT_GATE_PASSED):
        reasons.append("fusion_assignment_gate_not_passed")
    if binding is None:
        reasons.append("missing_determination_binding")

    normalized_lanes = _normalize_lanes(audit_lanes)
    if not normalized_lanes:
        reasons.append("missing_audit_lanes")
    unknown_lanes = tuple(lane for lane in normalized_lanes if lane not in LANE_REQUIRED_SOURCE)
    for lane in unknown_lanes:
        reasons.append(f"unknown_audit_lane:{lane}")
    missing_default = tuple(lane for lane in DEFAULT_AUDIT_LANES if lane not in normalized_lanes)
    for lane in missing_default:
        reasons.append(f"missing_required_audit_lane:{lane}")

    targets = _normalize_targets(allowed_read_targets)
    allocation_id = ""
    allocation_digest = ""
    if wsp15_allocation_receipt:
        allocation_id = str(wsp15_allocation_receipt.get("receipt_id") or "").strip()
        allocation_digest = _digest(wsp15_allocation_receipt)
    runtime_binding_data, runtime_binding_id, runtime_binding_digest = _runtime_binding(
        model_runtime_binding_receipt,
        reasons,
        required=require_model_runtime_binding,
    )
    if runtime_binding_id and wsp15_allocation_receipt:
        if str(wsp15_allocation_receipt.get("model_runtime_binding_receipt_id") or "") != runtime_binding_id:
            reasons.append("wsp15_model_runtime_binding_receipt_mismatch")
        if str(wsp15_allocation_receipt.get("model_runtime_binding_digest") or "") != runtime_binding_digest:
            reasons.append("wsp15_model_runtime_binding_digest_mismatch")
    grounding_data = dict(grounding_receipt) if isinstance(grounding_receipt, Mapping) else {}
    grounding_id = ""
    grounding_receipt_digest = ""
    if grounding_receipt is not None:
        grounding_validation = validate_grounded_target_receipt(
            grounding_receipt,
            work_focus=grounding_work_focus,
        )
        if not grounding_validation.accepted or grounding_validation.verified is None:
            reasons.extend(grounding_validation.rejection_reasons)
        else:
            grounding_id = grounding_validation.verified.receipt_id
            grounding_receipt_digest = grounding_digest(grounding_data)
            targets = _normalize_targets((*targets, *grounding_validation.verified.allowed_read_targets))
    if len(targets) > MAX_ASSIGNMENT_TARGETS:
        reasons.append("too_many_allowed_read_targets")

    if not reasons and snapshot and context_view and evidence_bundle and binding:
        _validate_binding(
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            binding=binding,
            reasons=reasons,
        )
        fresh_sources = {
            receipt.source
            for receipt in snapshot.source_receipts
            if receipt.required and receipt.freshness == "FRESH"
        }
        for lane in normalized_lanes:
            required_source = LANE_REQUIRED_SOURCE[lane]
            if required_source not in fresh_sources:
                reasons.append(f"lane_required_source_not_fresh:{lane}:{required_source}")

    reasons = _dedupe(reasons)
    if reasons:
        return _rejected_plan(
            reasons=reasons,
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            binding=binding,
            lanes=normalized_lanes,
        )

    assert snapshot is not None
    assert context_view is not None
    assert evidence_bundle is not None
    assert binding is not None
    assignments = tuple(
        _build_assignment(
            lane_id=lane,
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            binding=binding,
            allowed_read_targets=targets,
            wsp15_allocation_receipt_id=allocation_id,
            wsp15_allocation_digest=allocation_digest,
            grounding_receipt_id=grounding_id,
            grounding_receipt_digest=grounding_receipt_digest,
            model_runtime_binding_receipt_id=runtime_binding_id,
            model_runtime_binding_digest=runtime_binding_digest,
        )
        for lane in normalized_lanes
    )
    swarm_id = _digest(
        {
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "context_view_id": context_view.context_view_id,
            "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
            "determination_id": binding.determination_id,
            "wsp15_allocation_receipt_id": allocation_id,
            "wsp15_allocation_digest": allocation_digest,
            "grounding_receipt_id": grounding_id,
            "grounding_receipt_digest": grounding_receipt_digest,
            "model_runtime_binding_receipt_id": runtime_binding_id,
            "model_runtime_binding_digest": runtime_binding_digest,
            "assignment_ids": [assignment.assignment_id for assignment in assignments],
        }
    )
    receipt = ReadOnlyAuditSwarmReceipt(
        swarm_id=swarm_id,
        status=READONLY_AUDIT_SWARM_PLANNED,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id,
        determination_id=binding.determination_id,
        requested_operation=binding.requested_operation,
        grounding_receipt_id=grounding_id,
        grounding_receipt_digest=grounding_receipt_digest,
        grounding_receipt=grounding_data,
        grounding_work_focus=str(grounding_work_focus or ""),
        wsp15_allocation_receipt_id=allocation_id,
        wsp15_allocation_digest=allocation_digest,
        wsp15_allocation_receipt=dict(wsp15_allocation_receipt or {}),
        model_runtime_binding_receipt_id=runtime_binding_id,
        model_runtime_binding_digest=runtime_binding_digest,
        model_runtime_binding_receipt=runtime_binding_data,
        assignment_ids=tuple(assignment.assignment_id for assignment in assignments),
        lanes=tuple(assignment.lane_id for assignment in assignments),
        rejection_reasons=(),
    )
    return ReadOnlyAuditSwarmPlan(
        accepted=True,
        status=READONLY_AUDIT_SWARM_PLANNED,
        receipt=receipt,
        assignments=assignments,
        rejection_reasons=(),
    )


def validate_reddog_openclaw_readonly_audit_reports(
    *,
    plan: ReadOnlyAuditSwarmPlan,
    reports: Sequence[Mapping[str, Any]],
) -> ReadOnlyAuditReportValidationResult:
    """Validate returned audit report metadata without executing or trusting it."""

    reasons: list[str] = []
    if not plan.accepted:
        reasons.append("swarm_plan_not_accepted")
    report_by_assignment: dict[str, Mapping[str, Any]] = {}
    for index, report in enumerate(reports):
        if not isinstance(report, Mapping):
            reasons.append(f"report_not_mapping:{index}")
            continue
        assignment_id = str(report.get("assignment_id") or "").strip()
        if not assignment_id:
            reasons.append(f"report_missing_assignment_id:{index}")
            continue
        if assignment_id in report_by_assignment:
            reasons.append(f"duplicate_assignment_report:{assignment_id}")
            continue
        report_by_assignment[assignment_id] = report

    report_digests: list[str] = []
    lanes_reported: list[str] = []
    missing_lanes: list[str] = []
    for assignment in plan.assignments:
        report = report_by_assignment.get(assignment.assignment_id)
        if not report:
            missing_lanes.append(assignment.lane_id)
            reasons.append(f"missing_report_for_lane:{assignment.lane_id}")
            continue
        reasons.extend(_validate_report(assignment, report))
        lanes_reported.append(assignment.lane_id)
        report_digests.append(_digest(_report_digest_payload(report)))

    reasons = _dedupe(reasons)
    bundle = ReadOnlyAuditReportBundle(
        bundle_id=_digest(
            {
                "swarm_id": plan.receipt.swarm_id,
                "report_digests": sorted(report_digests),
                "lanes_reported": sorted(lanes_reported),
                "missing_lanes": sorted(missing_lanes),
                "rejection_reasons": reasons,
            }
        ),
        swarm_id=plan.receipt.swarm_id,
        report_digests=tuple(sorted(report_digests)),
        lanes_reported=tuple(sorted(lanes_reported)),
        missing_lanes=tuple(sorted(missing_lanes)),
        rejection_reasons=tuple(reasons),
    )
    return ReadOnlyAuditReportValidationResult(
        accepted=not reasons,
        status=READONLY_AUDIT_REPORTS_ACCEPTED if not reasons else READONLY_AUDIT_REPORTS_REJECTED,
        bundle=bundle,
        rejection_reasons=tuple(reasons),
    )


def _build_assignment(
    *,
    lane_id: str,
    snapshot: OperationalContextSnapshot,
    context_view: ContextView,
    evidence_bundle: EvidenceBundle,
    binding: DeterminationContextBinding,
    allowed_read_targets: tuple[str, ...],
    wsp15_allocation_receipt_id: str,
    wsp15_allocation_digest: str,
    grounding_receipt_id: str,
    grounding_receipt_digest: str,
    model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str,
) -> ReadOnlyAuditAssignment:
    payload = {
        "lane_id": lane_id,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "context_view_id": context_view.context_view_id,
        "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
        "determination_id": binding.determination_id,
        "wsp15_allocation_receipt_id": wsp15_allocation_receipt_id,
        "wsp15_allocation_digest": wsp15_allocation_digest,
        "grounding_receipt_id": grounding_receipt_id,
        "grounding_receipt_digest": grounding_receipt_digest,
        "model_runtime_binding_receipt_id": model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": model_runtime_binding_digest,
        "required_source": LANE_REQUIRED_SOURCE[lane_id],
        "allowed_read_targets": allowed_read_targets,
    }
    return ReadOnlyAuditAssignment(
        assignment_id="readonly_audit_" + _digest(payload).removeprefix("sha256:")[:16],
        lane_id=lane_id,
        worker_role=f"readonly_{lane_id}",
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id,
        determination_id=binding.determination_id,
        wsp15_allocation_receipt_id=wsp15_allocation_receipt_id,
        wsp15_allocation_digest=wsp15_allocation_digest,
        grounding_receipt_id=grounding_receipt_id,
        grounding_receipt_digest=grounding_receipt_digest,
        model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        model_runtime_binding_digest=model_runtime_binding_digest,
        required_source=LANE_REQUIRED_SOURCE[lane_id],
        allowed_read_targets=allowed_read_targets,
    )


def _rejected_plan(
    *,
    reasons: Sequence[str],
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    binding: DeterminationContextBinding | None,
    lanes: Sequence[str],
) -> ReadOnlyAuditSwarmPlan:
    receipt = ReadOnlyAuditSwarmReceipt(
        swarm_id=_digest(
            {
                "status": READONLY_AUDIT_SWARM_REJECTED,
                "snapshot_receipt_id": snapshot.snapshot_receipt_id if snapshot else "",
                "context_view_id": context_view.context_view_id if context_view else "",
                "evidence_bundle_id": evidence_bundle.evidence_bundle_id if evidence_bundle else "",
                "determination_id": binding.determination_id if binding else "",
                "lanes": list(lanes),
                "rejection_reasons": list(reasons),
            }
        ),
        status=READONLY_AUDIT_SWARM_REJECTED,
        snapshot_receipt_id=snapshot.snapshot_receipt_id if snapshot else "",
        snapshot_content_digest=snapshot.snapshot_content_digest if snapshot else "",
        context_view_id=context_view.context_view_id if context_view else "",
        evidence_bundle_id=evidence_bundle.evidence_bundle_id if evidence_bundle else "",
        determination_id=binding.determination_id if binding else "",
        requested_operation=binding.requested_operation if binding else "",
        wsp15_allocation_receipt_id="",
        wsp15_allocation_digest="",
        wsp15_allocation_receipt={},
        model_runtime_binding_receipt_id="",
        model_runtime_binding_digest="",
        model_runtime_binding_receipt={},
        assignment_ids=(),
        lanes=tuple(lanes),
        rejection_reasons=tuple(reasons),
    )
    return ReadOnlyAuditSwarmPlan(
        accepted=False,
        status=READONLY_AUDIT_SWARM_REJECTED,
        receipt=receipt,
        assignments=(),
        rejection_reasons=tuple(reasons),
    )


def _runtime_binding(
    value: Mapping[str, Any] | None,
    reasons: list[str],
    *,
    required: bool,
) -> tuple[dict[str, Any], str, str]:
    if value is None:
        if required:
            reasons.append("missing_model_runtime_binding_receipt")
        return {}, "", ""
    if not isinstance(value, Mapping):
        reasons.append("invalid_model_runtime_binding_receipt")
        return {}, "", ""
    try:
        data = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        receipt = rehydrate_model_runtime_binding_receipt(data)
    except Exception:
        reasons.append("invalid_model_runtime_binding_receipt")
        return {}, "", ""
    if (
        receipt.decision != ModelRuntimeBindingDecision.BOUND
        or not receipt.principal_model
        or receipt.runtime_surface != RUNTIME_SURFACE_READONLY_AUDIT
    ):
        reasons.append("model_runtime_binding_surface_mismatch")
        return {}, "", ""
    return data, receipt.receipt_id, canonical_model_runtime_binding_digest(receipt)


def _validate_binding(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: ContextView,
    evidence_bundle: EvidenceBundle,
    binding: DeterminationContextBinding,
    reasons: list[str],
) -> None:
    if binding.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("binding_snapshot_mismatch")
    if binding.snapshot_content_digest != snapshot.snapshot_content_digest:
        reasons.append("binding_snapshot_content_mismatch")
    if binding.context_view_id != context_view.context_view_id:
        reasons.append("binding_context_view_mismatch")
    if binding.evidence_bundle_id != evidence_bundle.evidence_bundle_id:
        reasons.append("binding_evidence_bundle_mismatch")
    if context_view.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("context_view_snapshot_mismatch")
    if evidence_bundle.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("evidence_bundle_snapshot_mismatch")
    if evidence_bundle.context_view_id != context_view.context_view_id:
        reasons.append("evidence_bundle_context_view_mismatch")


def _validate_report(assignment: ReadOnlyAuditAssignment, report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if str(report.get("lane_id") or "") != assignment.lane_id:
        reasons.append(f"report_lane_mismatch:{assignment.lane_id}")
    if str(report.get("snapshot_receipt_id") or "") != assignment.snapshot_receipt_id:
        reasons.append(f"report_snapshot_mismatch:{assignment.lane_id}")
    if report.get("repo_mutation_performed") is True:
        reasons.append(f"report_claims_repo_mutation:{assignment.lane_id}")
    if report.get("execution_performed") is True:
        reasons.append(f"report_claims_execution:{assignment.lane_id}")
    if report.get("openclaw_enqueue_performed") is True:
        reasons.append(f"report_claims_openclaw_enqueue:{assignment.lane_id}")
    evidence_refs = report.get("evidence_refs") or ()
    if isinstance(evidence_refs, str) or not isinstance(evidence_refs, Sequence) or not evidence_refs:
        reasons.append(f"report_missing_evidence_refs:{assignment.lane_id}")
    report_text = str(report.get("summary") or "")
    if len(report_text.encode("utf-8")) > MAX_REPORT_BYTES:
        reasons.append(f"report_too_large:{assignment.lane_id}")
    return reasons


def _report_digest_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "assignment_id": str(report.get("assignment_id") or ""),
        "lane_id": str(report.get("lane_id") or ""),
        "snapshot_receipt_id": str(report.get("snapshot_receipt_id") or ""),
        "evidence_refs": tuple(str(ref) for ref in (report.get("evidence_refs") or ())),
        "findings_digest": _digest(report.get("findings") or ()),
        "summary_digest": _digest(str(report.get("summary") or "")),
    }


def _normalize_lanes(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_dedupe(str(value or "").strip().lower() for value in values if str(value or "").strip()))


def _normalize_targets(values: Sequence[str]) -> tuple[str, ...]:
    targets = []
    for value in values:
        text = str(value or "").replace("\\", "/").strip()
        if not text or text.startswith("/") or text.startswith("../") or "/../" in text:
            continue
        targets.append(text)
    return tuple(_dedupe(targets))


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return tuple(ordered)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "DEFAULT_AUDIT_LANES",
    "FORBIDDEN_ACTIONS",
    "READONLY_AUDIT_REPORTS_ACCEPTED",
    "READONLY_AUDIT_REPORTS_REJECTED",
    "READONLY_AUDIT_SWARM_PLANNED",
    "READONLY_AUDIT_SWARM_REJECTED",
    "ReadOnlyAuditAssignment",
    "ReadOnlyAuditReportBundle",
    "ReadOnlyAuditReportValidationResult",
    "ReadOnlyAuditSwarmPlan",
    "ReadOnlyAuditSwarmReceipt",
    "plan_reddog_openclaw_readonly_audit_swarm",
    "validate_reddog_openclaw_readonly_audit_reports",
]
