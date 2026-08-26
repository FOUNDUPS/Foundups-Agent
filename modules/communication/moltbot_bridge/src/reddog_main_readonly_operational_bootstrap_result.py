"""Result schema and bounded projections for the RedDog main bootstrap."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

if TYPE_CHECKING:
    from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
        BackendArchitectDeterminationResult,
    )
    from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
        FusionAssignmentGateDecision,
    )
    from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
        ReadOnlyAuditSwarmEnqueueResult,
    )
    from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
        ReadOnlyAuditSwarmPlan,
    )
    from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
        EvidenceBundle,
        OperationalContextSnapshot,
    )
    from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
        OperationalMemexTaskEnrichmentResult,
    )
    from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
        ReadOnlyAuditDecisionPersistResult,
    )
    from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
        ReadOnlyAuditDecisionReceipt,
    )
    from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
        ReadOnlyAuditReportCollectionResult,
    )


REDDOG_MAIN_BOOTSTRAP_READY = "REDDOG_MAIN_BOOTSTRAP_READY"
REDDOG_MAIN_BOOTSTRAP_NOT_READY = "REDDOG_MAIN_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class RedDogMainReadonlyBootstrapResult:
    """Result emitted by the startup bootstrap check."""

    ready: bool
    status: str
    snapshot_receipt_id: Optional[str]
    context_view_id: Optional[str]
    evidence_bundle_id: Optional[str]
    determination_id: Optional[str]
    swarm_id: Optional[str]
    assignment_count: int
    rejection_reasons: tuple[str, ...]
    changed_paths: tuple[str, ...]
    allowed_read_targets: tuple[str, ...]
    wsp15_allocation_receipt: Optional[Mapping[str, Any]] = None
    assignment_ids: tuple[str, ...] = ()
    report_collection_attempted: bool = False
    report_collection_status: Optional[str] = None
    report_collection_report_count: int = 0
    report_bundle_id: Optional[str] = None
    report_collection_rejection_reasons: tuple[str, ...] = ()
    readonly_audit_decision_attempted: bool = False
    readonly_audit_decision_status: Optional[str] = None
    readonly_audit_decision_action: Optional[str] = None
    readonly_audit_decision_id: Optional[str] = None
    readonly_audit_decision_next_slice: Optional[str] = None
    readonly_audit_decision_rejection_reasons: tuple[str, ...] = ()
    readonly_audit_decision_persist_attempted: bool = False
    readonly_audit_decision_persist_status: Optional[str] = None
    readonly_audit_decision_persist_stored: bool = False
    readonly_audit_decision_persist_rejection_reasons: tuple[str, ...] = ()
    backend_architect_determination_attempted: bool = False
    backend_architect_determination_status: Optional[str] = None
    backend_architect_determination_action: Optional[str] = None
    backend_architect_determination_id: Optional[str] = None
    backend_architect_determination_next_slice: Optional[str] = None
    backend_architect_determination_queue_candidate_count: int = 0
    backend_architect_determination_persist_stored: bool = False
    backend_architect_determination_rejection_reasons: tuple[str, ...] = ()
    enqueue_attempted: bool = False
    enqueue_decision: Optional[str] = None
    enqueue_receipt_id: Optional[str] = None
    enqueue_task_count: int = 0
    enqueue_rejection_reasons: tuple[str, ...] = ()
    memex_snapshot_supply_attempted: bool = False
    memex_snapshot_supply_status: Optional[str] = None
    memex_snapshot_supply_view_id: Optional[str] = None
    memex_snapshot_supply_receipt: Optional[Mapping[str, Any]] = None
    memex_snapshot_supply_rejection_reasons: tuple[str, ...] = ()
    no_model_call_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_queue_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _report_projection(
    collection: ReadOnlyAuditReportCollectionResult | None,
) -> dict[str, Any]:
    bundle = collection.validation.bundle if collection and collection.validation else None
    return {
        "report_collection_attempted": collection is not None,
        "report_collection_status": collection.status if collection else None,
        "report_collection_report_count": collection.report_count if collection else 0,
        "report_bundle_id": bundle.bundle_id if bundle else None,
        "report_collection_rejection_reasons": collection.rejection_reasons if collection else (),
    }


def _decision_projection(
    decision: ReadOnlyAuditDecisionReceipt | None,
    persisted: ReadOnlyAuditDecisionPersistResult | None,
) -> dict[str, Any]:
    return {
        "readonly_audit_decision_attempted": decision is not None,
        "readonly_audit_decision_status": decision.status if decision else None,
        "readonly_audit_decision_action": decision.action if decision else None,
        "readonly_audit_decision_id": decision.decision_id if decision else None,
        "readonly_audit_decision_next_slice": decision.next_slice_name if decision else None,
        "readonly_audit_decision_rejection_reasons": decision.rejection_reasons if decision else (),
        "readonly_audit_decision_persist_attempted": persisted is not None,
        "readonly_audit_decision_persist_status": persisted.status if persisted else None,
        "readonly_audit_decision_persist_stored": persisted.stored if persisted else False,
        "readonly_audit_decision_persist_rejection_reasons": persisted.rejection_reasons if persisted else (),
    }


def _architect_projection(
    architect: BackendArchitectDeterminationResult | None,
) -> dict[str, Any]:
    receipt = architect.receipt if architect else None
    return {
        "backend_architect_determination_attempted": architect is not None,
        "backend_architect_determination_status": architect.status if architect else None,
        "backend_architect_determination_action": receipt.action if receipt else None,
        "backend_architect_determination_id": receipt.determination_receipt_id if receipt else None,
        "backend_architect_determination_next_slice": receipt.next_slice_name if receipt else None,
        "backend_architect_determination_queue_candidate_count": architect.queue_candidate_count if architect else 0,
        "backend_architect_determination_persist_stored": architect.persist_result.stored if architect else False,
        "backend_architect_determination_rejection_reasons": architect.rejection_reasons if architect else (),
    }


def _enqueue_projection(
    enqueue: ReadOnlyAuditSwarmEnqueueResult | None,
    *,
    attempted: bool,
    accepted_tasks_only: bool,
) -> dict[str, Any]:
    include_tasks = bool(enqueue and (enqueue.accepted or not accepted_tasks_only))
    return {
        "enqueue_attempted": attempted,
        "enqueue_decision": enqueue.decision if enqueue else None,
        "enqueue_receipt_id": enqueue.receipt.enqueue_receipt_id if enqueue else None,
        "enqueue_task_count": len(enqueue.tasks) if include_tasks else 0,
        "enqueue_rejection_reasons": enqueue.rejection_reasons if enqueue else (),
    }


def _memex_projection(
    memex: OperationalMemexTaskEnrichmentResult | None,
) -> dict[str, Any]:
    return {
        "memex_snapshot_supply_attempted": memex is not None,
        "memex_snapshot_supply_status": memex.status if memex else None,
        "memex_snapshot_supply_view_id": memex.memex_view_id if memex else None,
        "memex_snapshot_supply_receipt": dict(memex.supply_receipt or {}) if memex else None,
        "memex_snapshot_supply_rejection_reasons": memex.rejection_reasons if memex else (),
    }


def _no_model_call(
    architect: BackendArchitectDeterminationResult | None,
) -> bool:
    return not bool(architect and architect.receipt.model_result_digest)


def build_ready_bootstrap_result(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: Any,
    evidence_bundle: EvidenceBundle,
    gate: FusionAssignmentGateDecision,
    plan: ReadOnlyAuditSwarmPlan,
    changed_paths: Sequence[str],
    allowed_read_targets: Sequence[str],
    wsp15_allocation_receipt: Mapping[str, Any],
    collection_result: ReadOnlyAuditReportCollectionResult | None,
    decision_result: ReadOnlyAuditDecisionReceipt | None,
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None,
    architect_result: BackendArchitectDeterminationResult | None,
    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None,
    enqueue_attempted: bool,
    memex_supply_result: OperationalMemexTaskEnrichmentResult | None = None,
) -> RedDogMainReadonlyBootstrapResult:
    assert gate.determination_binding is not None
    accepted = bool(enqueue_result and enqueue_result.accepted)
    return RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id,
        determination_id=gate.determination_binding.determination_id,
        swarm_id=plan.receipt.swarm_id,
        assignment_count=len(plan.assignments),
        rejection_reasons=(),
        changed_paths=tuple(changed_paths),
        allowed_read_targets=tuple(allowed_read_targets),
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        assignment_ids=tuple(assignment.assignment_id for assignment in plan.assignments),
        **_report_projection(collection_result),
        **_decision_projection(decision_result, decision_persist_result),
        **_architect_projection(architect_result),
        **_enqueue_projection(
            enqueue_result,
            attempted=enqueue_attempted,
            accepted_tasks_only=False,
        ),
        **_memex_projection(memex_supply_result),
        no_openclaw_enqueue_performed=not accepted,
        no_queue_mutation_performed=not accepted,
        no_model_call_performed=_no_model_call(architect_result),
    )


def build_not_ready_bootstrap_result(
    *,
    reasons: Sequence[str],
    changed_paths: Sequence[str],
    allowed_read_targets: Sequence[str],
    wsp15_allocation_receipt: Mapping[str, Any] | None = None,
    snapshot: OperationalContextSnapshot | None = None,
    evidence_bundle: EvidenceBundle | None = None,
    gate: FusionAssignmentGateDecision | None = None,
    swarm_plan: ReadOnlyAuditSwarmPlan | None = None,
    collection_result: ReadOnlyAuditReportCollectionResult | None = None,
    decision_result: ReadOnlyAuditDecisionReceipt | None = None,
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None = None,
    architect_result: BackendArchitectDeterminationResult | None = None,
    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None = None,
    memex_supply_result: OperationalMemexTaskEnrichmentResult | None = None,
) -> RedDogMainReadonlyBootstrapResult:
    binding = gate.determination_binding if gate and gate.determination_binding else None
    return RedDogMainReadonlyBootstrapResult(
        ready=False,
        status=REDDOG_MAIN_BOOTSTRAP_NOT_READY,
        snapshot_receipt_id=snapshot.snapshot_receipt_id if snapshot else None,
        context_view_id=binding.context_view_id if binding else None,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id if evidence_bundle else None,
        determination_id=binding.determination_id if binding else None,
        swarm_id=swarm_plan.receipt.swarm_id if swarm_plan else None,
        assignment_count=len(swarm_plan.assignments) if swarm_plan else 0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        changed_paths=tuple(changed_paths),
        allowed_read_targets=tuple(allowed_read_targets),
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        assignment_ids=tuple(assignment.assignment_id for assignment in swarm_plan.assignments) if swarm_plan else (),
        **_report_projection(collection_result),
        **_decision_projection(decision_result, decision_persist_result),
        **_architect_projection(architect_result),
        **_enqueue_projection(
            enqueue_result,
            attempted=enqueue_result is not None,
            accepted_tasks_only=True,
        ),
        **_memex_projection(memex_supply_result),
        no_model_call_performed=_no_model_call(architect_result),
    )


__all__ = [
    "REDDOG_MAIN_BOOTSTRAP_NOT_READY",
    "REDDOG_MAIN_BOOTSTRAP_READY",
    "RedDogMainReadonlyBootstrapResult",
    "build_not_ready_bootstrap_result",
    "build_ready_bootstrap_result",
]
