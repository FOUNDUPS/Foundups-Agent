"""RedDog main read-only operational bootstrap.

This module composes the already-built RedDog context snapshot, Fusion
assignment gate, and OpenClaw read-only audit swarm planner into a startup
check for ``main.py``. By default it plans only; when explicitly enabled by
the host it publishes the accepted read-only audit plan as pending AgentDB
tasks. It does not call models, spawn workers, dispatch Hermes, write repo
files, create worktrees, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt, freshness_receipt_path
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    FusionAssignmentGateDecision,
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
    ReadOnlyAuditSwarmPlan,
    plan_reddog_openclaw_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    AgentDbReadOnlyAuditTaskWriter,
    ReadOnlyAuditSwarmEnqueueResult,
    ReadOnlyAuditTaskWriter,
    enqueue_reddog_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    AgentDbReadOnlyAuditReportStore,
    ReadOnlyAuditReportCollectionResult,
    ReadOnlyAuditReportStore,
    collect_reddog_readonly_audit_report_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ReadOnlyAuditDecisionReceipt,
    decide_reddog_readonly_audit_next_action,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    AgentDbReadOnlyAuditDecisionStore,
    ReadOnlyAuditDecisionPersistResult,
    ReadOnlyAuditDecisionStore,
    persist_reddog_readonly_audit_decision,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    EvidenceBundle,
    OperationalContextSnapshot,
    build_evidence_bundle,
    build_operational_context_snapshot,
    load_authoritative_work_state,
    load_existing_holoindex_receipt,
    observe_repo_state,
)


REDDOG_MAIN_BOOTSTRAP_READY = "REDDOG_MAIN_BOOTSTRAP_READY"
REDDOG_MAIN_BOOTSTRAP_NOT_READY = "REDDOG_MAIN_BOOTSTRAP_NOT_READY"
REDDOG_MAIN_BOOTSTRAP_DISABLED = "REDDOG_MAIN_BOOTSTRAP_DISABLED"

DEFAULT_BOOTSTRAP_CHANGED_PATHS = (
    "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",
    "docs/0102_session_briefings/work_ledger.schema.json",
    "holo_index/adaptive_learning/breadcrumb_tracer.py",
    "modules/communication/moltbot_bridge/src/reddog_operational_context_snapshot.py",
    "modules/communication/moltbot_bridge/src/reddog_context_snapshot_fusion_assignment_gate.py",
    "modules/communication/moltbot_bridge/src/reddog_openclaw_readonly_audit_swarm_runtime.py",
)

DEFAULT_BOOTSTRAP_READ_TARGETS = DEFAULT_BOOTSTRAP_CHANGED_PATHS


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
    enqueue_attempted: bool = False
    enqueue_decision: Optional[str] = None
    enqueue_receipt_id: Optional[str] = None
    enqueue_task_count: int = 0
    enqueue_rejection_reasons: tuple[str, ...] = ()
    no_model_call_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_queue_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_readonly_operational_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None = None,
    holoindex_receipt_path: Path | str | None = None,
    holoindex_ssd_path: Path | str | None = None,
    changed_paths: Sequence[str] = DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    allowed_read_targets: Sequence[str] = DEFAULT_BOOTSTRAP_READ_TARGETS,
    requested_operation: str = "main_startup_readonly_operational_audit",
    prompt_text: str = "main.py read-only RedDog operational bootstrap",
    now_iso: str | None = None,
    repo_state_override: Mapping[str, Any] | None = None,
    work_state_snapshot_override: Mapping[str, Any] | None = None,
    holoindex_receipt_override: HoloIndexFreshnessReceipt | Mapping[str, Any] | None = None,
    audit_lanes: Sequence[str] = DEFAULT_AUDIT_LANES,
    enqueue_readonly_audit_tasks: bool = False,
    enqueue_writer: ReadOnlyAuditTaskWriter | None = None,
    seen_assignment_ids: Optional[set[str]] = None,
    collect_readonly_audit_reports: bool = False,
    report_store: ReadOnlyAuditReportStore | None = None,
    persist_readonly_audit_decision: bool = False,
    decision_store: ReadOnlyAuditDecisionStore | None = None,
) -> RedDogMainReadonlyBootstrapResult:
    """Build a read-only startup plan or explain why it is not ready."""

    paths = _normalize_paths(changed_paths)
    targets = _normalize_paths(allowed_read_targets)
    reasons: list[str] = []

    work_state_snapshot = work_state_snapshot_override
    if work_state_snapshot is None:
        if not work_state_path:
            reasons.append("missing_authoritative_work_state_path")
        else:
            path = Path(work_state_path)
            if not path.exists() or not path.is_file():
                reasons.append("missing_authoritative_work_state")
            else:
                try:
                    work_state_snapshot = load_authoritative_work_state(path)
                except Exception:
                    reasons.append("malformed_authoritative_work_state")

    holo_receipt = holoindex_receipt_override
    if holo_receipt is None:
        receipt_path = _resolve_holoindex_receipt_path(
            receipt_path=holoindex_receipt_path,
            ssd_path=holoindex_ssd_path,
        )
        if receipt_path is None:
            reasons.append("missing_holoindex_freshness_receipt_path")
        elif not receipt_path.exists() or not receipt_path.is_file():
            reasons.append("missing_holoindex_freshness_receipt")
        else:
            try:
                holo_receipt = load_existing_holoindex_receipt(receipt_path)
            except Exception:
                reasons.append("malformed_holoindex_freshness_receipt")

    if reasons:
        return _not_ready(
            reasons=reasons,
            changed_paths=paths,
            allowed_read_targets=targets,
        )

    assert work_state_snapshot is not None
    repo_state = dict(repo_state_override) if repo_state_override is not None else observe_repo_state(Path(repo_root))
    snapshot_result = build_operational_context_snapshot(
        repo_state=repo_state,
        work_state_snapshot=work_state_snapshot,
        holoindex_receipt=holo_receipt,
        changed_paths=paths,
        now_iso=now_iso,
        breadcrumb_scope=str(work_state_snapshot.get("selected_slice") or "main_startup"),
    )
    if not snapshot_result.accepted or snapshot_result.snapshot is None or snapshot_result.context_view is None:
        return _not_ready(
            reasons=snapshot_result.rejection_reasons or ("snapshot_rejected",),
            changed_paths=paths,
            allowed_read_targets=targets,
        )

    snapshot = snapshot_result.snapshot
    context_view = snapshot_result.context_view
    evidence_bundle = _build_bootstrap_evidence_bundle(snapshot=snapshot, context_view=context_view)
    gate = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        current_repo_head_sha=str(repo_state.get("head_sha", "unknown")),
        current_work_state_revision=str(work_state_snapshot.get("revision", "")),
        current_breadcrumb_high_watermark=snapshot.breadcrumbs_state.get("high_watermark"),
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        now_iso=now_iso,
    )
    if not gate.accepted or gate.determination_binding is None:
        return _not_ready(
            reasons=gate.rejection_reasons or ("fusion_assignment_gate_rejected",),
            changed_paths=paths,
            allowed_read_targets=targets,
            snapshot=snapshot,
            evidence_bundle=evidence_bundle,
            gate=gate,
        )

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        audit_lanes=audit_lanes,
        allowed_read_targets=targets,
    )
    if not plan.accepted:
        return _not_ready(
            reasons=plan.rejection_reasons or ("readonly_audit_swarm_rejected",),
            changed_paths=paths,
            allowed_read_targets=targets,
            snapshot=snapshot,
            evidence_bundle=evidence_bundle,
            gate=gate,
            swarm_plan=plan,
        )

    collection_result: ReadOnlyAuditReportCollectionResult | None = None
    decision_result: ReadOnlyAuditDecisionReceipt | None = None
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None = None
    if collect_readonly_audit_reports:
        reader = report_store if report_store is not None else AgentDbReadOnlyAuditReportStore()
        collection_result = collect_reddog_readonly_audit_report_bundle(
            plan=plan,
            store=reader,
        )
        if collection_result.accepted:
            try:
                decision_reports = tuple(reader.load_readonly_audit_reports(plan.receipt.swarm_id))
            except Exception:
                return _not_ready(
                    reasons=("readonly_audit_decision_report_load_failed",),
                    changed_paths=paths,
                    allowed_read_targets=targets,
                    snapshot=snapshot,
                    evidence_bundle=evidence_bundle,
                    gate=gate,
                    swarm_plan=plan,
                    collection_result=collection_result,
                )
            decision_result = decide_reddog_readonly_audit_next_action(
                collection_result=collection_result,
                reports=decision_reports,
            )
            if not decision_result.accepted:
                return _not_ready(
                    reasons=("readonly_audit_decision_rejected", *decision_result.rejection_reasons),
                    changed_paths=paths,
                    allowed_read_targets=targets,
                    snapshot=snapshot,
                    evidence_bundle=evidence_bundle,
                    gate=gate,
                    swarm_plan=plan,
                    collection_result=collection_result,
                    decision_result=decision_result,
                    decision_persist_result=decision_persist_result,
                )
            if persist_readonly_audit_decision:
                decision_writer = decision_store if decision_store is not None else AgentDbReadOnlyAuditDecisionStore()
                decision_persist_result = persist_reddog_readonly_audit_decision(
                    decision=decision_result,
                    store=decision_writer,
                )
                if not decision_persist_result.accepted:
                    return _not_ready(
                        reasons=(
                            "readonly_audit_decision_persist_rejected",
                            *decision_persist_result.rejection_reasons,
                        ),
                        changed_paths=paths,
                        allowed_read_targets=targets,
                        snapshot=snapshot,
                        evidence_bundle=evidence_bundle,
                        gate=gate,
                        swarm_plan=plan,
                        collection_result=collection_result,
                        decision_result=decision_result,
                        decision_persist_result=decision_persist_result,
                    )
            return _ready(
                snapshot=snapshot,
                context_view=context_view,
                evidence_bundle=evidence_bundle,
                gate=gate,
                plan=plan,
                changed_paths=paths,
                allowed_read_targets=targets,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
                enqueue_result=None,
                enqueue_attempted=False,
            )
        if not enqueue_readonly_audit_tasks:
            return _not_ready(
                reasons=("readonly_audit_report_collection_rejected", *collection_result.rejection_reasons),
                changed_paths=paths,
                allowed_read_targets=targets,
                snapshot=snapshot,
                evidence_bundle=evidence_bundle,
                gate=gate,
                swarm_plan=plan,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
            )

    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None = None
    if enqueue_readonly_audit_tasks:
        writer = enqueue_writer if enqueue_writer is not None else AgentDbReadOnlyAuditTaskWriter()
        enqueue_result = enqueue_reddog_readonly_audit_swarm(
            plan=plan,
            writer=writer,
            seen_assignment_ids=seen_assignment_ids,
        )
        if not enqueue_result.accepted:
            return _not_ready(
                reasons=("readonly_audit_enqueue_rejected", *enqueue_result.rejection_reasons),
                changed_paths=paths,
                allowed_read_targets=targets,
                snapshot=snapshot,
                evidence_bundle=evidence_bundle,
                gate=gate,
                swarm_plan=plan,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
                enqueue_result=enqueue_result,
            )

    return _ready(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate=gate,
        plan=plan,
        changed_paths=paths,
        allowed_read_targets=targets,
        collection_result=collection_result,
        decision_result=decision_result,
        decision_persist_result=decision_persist_result,
        enqueue_result=enqueue_result,
        enqueue_attempted=enqueue_readonly_audit_tasks,
    )


def _ready(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: Any,
    evidence_bundle: EvidenceBundle,
    gate: FusionAssignmentGateDecision,
    plan: ReadOnlyAuditSwarmPlan,
    changed_paths: Sequence[str],
    allowed_read_targets: Sequence[str],
    collection_result: ReadOnlyAuditReportCollectionResult | None,
    decision_result: ReadOnlyAuditDecisionReceipt | None,
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None,
    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None,
    enqueue_attempted: bool,
) -> RedDogMainReadonlyBootstrapResult:
    assert gate.determination_binding is not None
    bundle = collection_result.validation.bundle if collection_result and collection_result.validation else None
    return RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id,
        determination_id=gate.determination_binding.determination_id,
        swarm_id=plan.receipt.swarm_id,
        assignment_count=len(plan.assignments),
        assignment_ids=tuple(assignment.assignment_id for assignment in plan.assignments),
        rejection_reasons=(),
        changed_paths=tuple(changed_paths),
        allowed_read_targets=tuple(allowed_read_targets),
        report_collection_attempted=collection_result is not None,
        report_collection_status=collection_result.status if collection_result else None,
        report_collection_report_count=collection_result.report_count if collection_result else 0,
        report_bundle_id=bundle.bundle_id if bundle else None,
        report_collection_rejection_reasons=collection_result.rejection_reasons if collection_result else (),
        readonly_audit_decision_attempted=decision_result is not None,
        readonly_audit_decision_status=decision_result.status if decision_result else None,
        readonly_audit_decision_action=decision_result.action if decision_result else None,
        readonly_audit_decision_id=decision_result.decision_id if decision_result else None,
        readonly_audit_decision_next_slice=decision_result.next_slice_name if decision_result else None,
        readonly_audit_decision_rejection_reasons=decision_result.rejection_reasons if decision_result else (),
        readonly_audit_decision_persist_attempted=decision_persist_result is not None,
        readonly_audit_decision_persist_status=decision_persist_result.status if decision_persist_result else None,
        readonly_audit_decision_persist_stored=decision_persist_result.stored if decision_persist_result else False,
        readonly_audit_decision_persist_rejection_reasons=(
            decision_persist_result.rejection_reasons if decision_persist_result else ()
        ),
        enqueue_attempted=enqueue_attempted,
        enqueue_decision=enqueue_result.decision if enqueue_result else None,
        enqueue_receipt_id=enqueue_result.receipt.enqueue_receipt_id if enqueue_result else None,
        enqueue_task_count=len(enqueue_result.tasks) if enqueue_result else 0,
        enqueue_rejection_reasons=enqueue_result.rejection_reasons if enqueue_result else (),
        no_openclaw_enqueue_performed=not bool(enqueue_result and enqueue_result.accepted),
        no_queue_mutation_performed=not bool(enqueue_result and enqueue_result.accepted),
    )


def _build_bootstrap_evidence_bundle(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: Any,
) -> EvidenceBundle:
    evidence_digest = _digest(
        {
            "source_receipt_digests": [receipt.content_digest for receipt in snapshot.source_receipts],
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "bootstrap_kind": "source_receipts_bound",
        }
    )
    return build_evidence_bundle(
        snapshot=snapshot,
        context_view=context_view,
        report_digests=(evidence_digest,),
    )


def _resolve_holoindex_receipt_path(
    *,
    receipt_path: Path | str | None,
    ssd_path: Path | str | None,
) -> Path | None:
    if receipt_path:
        return Path(receipt_path)
    if ssd_path:
        return freshness_receipt_path(ssd_path)
    return None


def _not_ready(
    *,
    reasons: Sequence[str],
    changed_paths: Sequence[str],
    allowed_read_targets: Sequence[str],
    snapshot: OperationalContextSnapshot | None = None,
    evidence_bundle: EvidenceBundle | None = None,
    gate: FusionAssignmentGateDecision | None = None,
    swarm_plan: ReadOnlyAuditSwarmPlan | None = None,
    collection_result: ReadOnlyAuditReportCollectionResult | None = None,
    decision_result: ReadOnlyAuditDecisionReceipt | None = None,
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None = None,
    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None = None,
) -> RedDogMainReadonlyBootstrapResult:
    determination_id = None
    if gate and gate.determination_binding:
        determination_id = gate.determination_binding.determination_id
    return RedDogMainReadonlyBootstrapResult(
        ready=False,
        status=REDDOG_MAIN_BOOTSTRAP_NOT_READY,
        snapshot_receipt_id=snapshot.snapshot_receipt_id if snapshot else None,
        context_view_id=gate.determination_binding.context_view_id if gate and gate.determination_binding else None,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id if evidence_bundle else None,
        determination_id=determination_id,
        swarm_id=swarm_plan.receipt.swarm_id if swarm_plan else None,
        assignment_count=len(swarm_plan.assignments) if swarm_plan else 0,
        assignment_ids=tuple(assignment.assignment_id for assignment in swarm_plan.assignments) if swarm_plan else (),
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        changed_paths=tuple(changed_paths),
        allowed_read_targets=tuple(allowed_read_targets),
        report_collection_attempted=collection_result is not None,
        report_collection_status=collection_result.status if collection_result else None,
        report_collection_report_count=collection_result.report_count if collection_result else 0,
        report_bundle_id=(
            collection_result.validation.bundle.bundle_id
            if collection_result and collection_result.validation.bundle
            else None
        ),
        report_collection_rejection_reasons=collection_result.rejection_reasons if collection_result else (),
        readonly_audit_decision_attempted=decision_result is not None,
        readonly_audit_decision_status=decision_result.status if decision_result else None,
        readonly_audit_decision_action=decision_result.action if decision_result else None,
        readonly_audit_decision_id=decision_result.decision_id if decision_result else None,
        readonly_audit_decision_next_slice=decision_result.next_slice_name if decision_result else None,
        readonly_audit_decision_rejection_reasons=decision_result.rejection_reasons if decision_result else (),
        readonly_audit_decision_persist_attempted=decision_persist_result is not None,
        readonly_audit_decision_persist_status=decision_persist_result.status if decision_persist_result else None,
        readonly_audit_decision_persist_stored=decision_persist_result.stored if decision_persist_result else False,
        readonly_audit_decision_persist_rejection_reasons=(
            decision_persist_result.rejection_reasons if decision_persist_result else ()
        ),
        enqueue_attempted=enqueue_result is not None,
        enqueue_decision=enqueue_result.decision if enqueue_result else None,
        enqueue_receipt_id=enqueue_result.receipt.enqueue_receipt_id if enqueue_result else None,
        enqueue_task_count=len(enqueue_result.tasks) if enqueue_result and enqueue_result.accepted else 0,
        enqueue_rejection_reasons=enqueue_result.rejection_reasons if enqueue_result else (),
    )


def _normalize_paths(paths: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in paths:
        text = str(value or "").replace("\\", "/").strip()
        while text.startswith("./"):
            text = text[2:]
        if text and not text.startswith("/") and not text.startswith("../") and "/../" not in text:
            normalized.append(text)
    return tuple(dict.fromkeys(normalized))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "DEFAULT_BOOTSTRAP_CHANGED_PATHS",
    "DEFAULT_BOOTSTRAP_READ_TARGETS",
    "REDDOG_MAIN_BOOTSTRAP_DISABLED",
    "REDDOG_MAIN_BOOTSTRAP_NOT_READY",
    "REDDOG_MAIN_BOOTSTRAP_READY",
    "RedDogMainReadonlyBootstrapResult",
    "run_reddog_main_readonly_operational_bootstrap",
]
