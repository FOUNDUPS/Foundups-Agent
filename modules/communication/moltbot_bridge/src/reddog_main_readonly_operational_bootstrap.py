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
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence
from holo_index.freshness_receipt import HoloIndexFreshnessReceipt, freshness_receipt_path
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
    plan_reddog_openclaw_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    AgentDbReadOnlyAuditTaskWriter,
    ReadOnlyAuditSwarmEnqueueResult,
    ReadOnlyAuditTaskWriter,
    enqueue_reddog_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    OperationalMemexReadOnlyAuditTaskWriter,
    OperationalMemexSnapshotSupplyConfig,
    OperationalMemexTaskEnrichmentResult,
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
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    AgentDbArchitectDeterminationStore, ArchitectDeterminationStore, ArchitectModelRunner,
    BackendArchitectDeterminationResult, run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import AuthenticatedPrincipalMemexContext
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    EvidenceBundle,
    OperationalContextSnapshot,
    build_evidence_bundle,
    build_operational_context_snapshot,
    load_authoritative_work_state,
    load_existing_holoindex_receipt,
    observe_repo_state,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import STAGE_AUDIT
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import allocate_reddog_wsp15_receipt
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import resolve_grounding_read_targets
from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap_result import (
    REDDOG_MAIN_BOOTSTRAP_NOT_READY,
    REDDOG_MAIN_BOOTSTRAP_READY,
    RedDogMainReadonlyBootstrapResult,
    build_not_ready_bootstrap_result as _not_ready,
    build_ready_bootstrap_result as _ready,
)

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
    repo_state_receipt: Mapping[str, Any] | None = None,
    work_state_snapshot_override: Mapping[str, Any] | None = None,
    holoindex_receipt_override: HoloIndexFreshnessReceipt | Mapping[str, Any] | None = None,
    breadcrumbs: Sequence[Mapping[str, Any]] = (),
    brain_state: Mapping[str, Any] | None = None,
    workspace_memory_notes: Sequence[Mapping[str, Any]] = (),
    bootstrap_projection: Mapping[str, Any] | None = None,
    grounding_receipt: Mapping[str, Any] | None = None,
    grounding_work_focus: str = "",
    audit_model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    require_audit_model_runtime_binding: bool = False,
    audit_lanes: Sequence[str] = DEFAULT_AUDIT_LANES,
    enqueue_readonly_audit_tasks: bool = False,
    enqueue_writer: ReadOnlyAuditTaskWriter | None = None,
    memex_snapshot_supply_config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any] | None = None,
    verified_outcome_runtime_authority: Any = None,
    seen_assignment_ids: Optional[set[str]] = None,
    collect_readonly_audit_reports: bool = False,
    report_store: ReadOnlyAuditReportStore | None = None,
    persist_readonly_audit_decision: bool = False,
    decision_store: ReadOnlyAuditDecisionStore | None = None,
    run_backend_architect_determination: bool = False,
    architect_model_runner: ArchitectModelRunner | None = None,
    architect_model_selection_receipt_path: Path | str | None = None,
    architect_model_selection_receipt_override: Mapping[str, Any] | None = None,
    architect_model_runtime_binding_receipt_path: Path | str | None = None,
    architect_model_runtime_binding_receipt_override: Mapping[str, Any] | None = None,
    principal_memex_context: AuthenticatedPrincipalMemexContext | None = None, principal_memex_now_epoch: Callable[[], int] | None = None,
    architect_determination_store: ArchitectDeterminationStore | None = None, progressive_execution_stage_ceiling: str = STAGE_AUDIT,
) -> RedDogMainReadonlyBootstrapResult:
    """Build a read-only startup plan or explain why it is not ready."""

    root = Path(repo_root).resolve()
    paths = _normalize_paths(changed_paths)
    grounded_targets, grounding_reasons = resolve_grounding_read_targets(grounding_receipt, work_focus=grounding_work_focus)
    targets = _normalize_paths((*allowed_read_targets, *grounded_targets))
    wsp15_allocation_receipt = allocate_reddog_wsp15_receipt(
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        changed_paths=paths,
        allowed_read_targets=targets,
        model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
    ).to_dict()
    reasons: list[str] = list(grounding_reasons)
    architect_model_selection_receipt = architect_model_selection_receipt_override
    architect_model_runtime_binding_receipt = architect_model_runtime_binding_receipt_override
    if architect_model_runtime_binding_receipt is None and architect_model_runtime_binding_receipt_path:
        architect_model_runtime_binding_receipt, runtime_reasons = _read_json_outside_repo(
            root,
            architect_model_runtime_binding_receipt_path,
            missing_reason="missing_architect_model_runtime_binding_receipt",
            inside_reason="architect_model_runtime_binding_receipt_path_inside_repo",
            unreadable_reason="malformed_architect_model_runtime_binding_receipt",
            required=True,
        )
        if runtime_reasons:
            return _not_ready(
                reasons=tuple(runtime_reasons),
                changed_paths=paths,
                allowed_read_targets=targets,
                wsp15_allocation_receipt=wsp15_allocation_receipt,
            )
    if architect_model_runtime_binding_receipt is not None:
        wsp15_allocation_receipt = allocate_reddog_wsp15_receipt(
            requested_operation=requested_operation,
            prompt_text=prompt_text,
            changed_paths=paths,
            allowed_read_targets=targets,
            model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
            architect_model_runtime_binding_receipt=architect_model_runtime_binding_receipt,
        ).to_dict()

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
            wsp15_allocation_receipt=wsp15_allocation_receipt,
        )

    assert work_state_snapshot is not None
    repo_state = dict(repo_state_override) if repo_state_override is not None else observe_repo_state(
        root, repo_state_receipt
    )
    snapshot_result = build_operational_context_snapshot(
        repo_state=repo_state,
        work_state_snapshot=work_state_snapshot,
        holoindex_receipt=holo_receipt,
        changed_paths=paths,
        now_iso=now_iso,
        breadcrumb_scope=str(work_state_snapshot.get("selected_slice") or "main_startup"),
        breadcrumbs=breadcrumbs,
        brain_state=brain_state,
        workspace_memory_notes=workspace_memory_notes,
        bootstrap_projection=bootstrap_projection,
    )
    if not snapshot_result.accepted or snapshot_result.snapshot is None or snapshot_result.context_view is None:
        return _not_ready(
            reasons=snapshot_result.rejection_reasons or ("snapshot_rejected",),
            changed_paths=paths,
            allowed_read_targets=targets,
            wsp15_allocation_receipt=wsp15_allocation_receipt,
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
            wsp15_allocation_receipt=wsp15_allocation_receipt,
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
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        grounding_receipt=grounding_receipt,
        grounding_work_focus=grounding_work_focus,
        model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
        require_model_runtime_binding=require_audit_model_runtime_binding,
    )
    if not plan.accepted:
        return _not_ready(
            reasons=plan.rejection_reasons or ("readonly_audit_swarm_rejected",),
            changed_paths=paths,
            allowed_read_targets=targets,
            wsp15_allocation_receipt=wsp15_allocation_receipt,
            snapshot=snapshot,
            evidence_bundle=evidence_bundle,
            gate=gate,
            swarm_plan=plan,
        )

    collection_result: ReadOnlyAuditReportCollectionResult | None = None
    decision_result: ReadOnlyAuditDecisionReceipt | None = None
    decision_persist_result: ReadOnlyAuditDecisionPersistResult | None = None
    architect_result: BackendArchitectDeterminationResult | None = None
    memex_supply_result: OperationalMemexTaskEnrichmentResult | None = None
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
                    wsp15_allocation_receipt=wsp15_allocation_receipt,
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
                    wsp15_allocation_receipt=wsp15_allocation_receipt,
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
                        wsp15_allocation_receipt=wsp15_allocation_receipt,
                        snapshot=snapshot,
                        evidence_bundle=evidence_bundle,
                        gate=gate,
                        swarm_plan=plan,
                        collection_result=collection_result,
                        decision_result=decision_result,
                        decision_persist_result=decision_persist_result,
                        architect_result=architect_result,
                    )
            if run_backend_architect_determination:
                if architect_model_selection_receipt is None:
                    if architect_model_selection_receipt_path:
                        architect_model_selection_receipt, model_reasons = _read_json_outside_repo(
                            root,
                            architect_model_selection_receipt_path,
                            missing_reason="missing_architect_model_selection_receipt",
                            inside_reason="architect_model_selection_receipt_path_inside_repo",
                            unreadable_reason="malformed_architect_model_selection_receipt",
                            required=True,
                        )
                        if model_reasons:
                            return _not_ready(
                                reasons=tuple(model_reasons),
                                changed_paths=paths,
                                allowed_read_targets=targets,
                                wsp15_allocation_receipt=wsp15_allocation_receipt,
                                snapshot=snapshot,
                                evidence_bundle=evidence_bundle,
                                gate=gate,
                                swarm_plan=plan,
                                collection_result=collection_result,
                                decision_result=decision_result,
                                decision_persist_result=decision_persist_result,
                                architect_result=architect_result,
                            )
                    elif architect_model_runner is None and architect_model_runtime_binding_receipt is None:
                        return _not_ready(
                            reasons=("missing_architect_model_runtime_binding_receipt",),
                            changed_paths=paths,
                            allowed_read_targets=targets,
                            wsp15_allocation_receipt=wsp15_allocation_receipt,
                            snapshot=snapshot,
                            evidence_bundle=evidence_bundle,
                            gate=gate,
                            swarm_plan=plan,
                            collection_result=collection_result,
                            decision_result=decision_result,
                            decision_persist_result=decision_persist_result,
                            architect_result=architect_result,
                        )
                architect_store = (
                    architect_determination_store
                    if architect_determination_store is not None
                    else AgentDbArchitectDeterminationStore()
                )
                architect_result = run_reddog_backend_architect_determination_runtime(
                    snapshot=snapshot,
                    context_view=context_view,
                    evidence_bundle=evidence_bundle,
                    fusion_gate=gate,
                    report_collection=collection_result,
                    reports=decision_reports,
                    wsp15_allocation_receipt=wsp15_allocation_receipt,
                    store=architect_store,
                    model_runner=architect_model_runner,
                    model_selection_receipt=architect_model_selection_receipt,
                    model_runtime_binding_receipt=architect_model_runtime_binding_receipt,
                    now_iso=now_iso,
                    principal_memex_context=principal_memex_context, principal_memex_now_epoch=principal_memex_now_epoch, task_prompt_text=prompt_text, progressive_execution_stage_ceiling=progressive_execution_stage_ceiling,
                )
                if not architect_result.accepted:
                    return _not_ready(
                        reasons=(
                            "backend_architect_determination_rejected",
                            *architect_result.rejection_reasons,
                        ),
                        changed_paths=paths,
                        allowed_read_targets=targets,
                        wsp15_allocation_receipt=wsp15_allocation_receipt,
                        snapshot=snapshot,
                        evidence_bundle=evidence_bundle,
                        gate=gate,
                        swarm_plan=plan,
                        collection_result=collection_result,
                        decision_result=decision_result,
                        decision_persist_result=decision_persist_result,
                        architect_result=architect_result,
                    )
            return _ready(
                snapshot=snapshot,
                context_view=context_view,
                evidence_bundle=evidence_bundle,
                gate=gate,
                plan=plan,
                changed_paths=paths,
                allowed_read_targets=targets,
                wsp15_allocation_receipt=wsp15_allocation_receipt,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
                architect_result=architect_result,
                enqueue_result=None,
                enqueue_attempted=False,
            )
        if not enqueue_readonly_audit_tasks:
            return _not_ready(
                reasons=("readonly_audit_report_collection_rejected", *collection_result.rejection_reasons),
                changed_paths=paths,
                allowed_read_targets=targets,
                wsp15_allocation_receipt=wsp15_allocation_receipt,
                snapshot=snapshot,
                evidence_bundle=evidence_bundle,
                gate=gate,
                swarm_plan=plan,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
                architect_result=architect_result,
            )

    enqueue_result: ReadOnlyAuditSwarmEnqueueResult | None = None
    if enqueue_readonly_audit_tasks:
        writer = enqueue_writer if enqueue_writer is not None else AgentDbReadOnlyAuditTaskWriter()
        memex_writer: OperationalMemexReadOnlyAuditTaskWriter | None = None
        if memex_snapshot_supply_config is not None:
            memex_writer = OperationalMemexReadOnlyAuditTaskWriter(
                delegate=writer,
                snapshot=snapshot,
                config=memex_snapshot_supply_config,
                verified_outcome_runtime_authority=(
                    verified_outcome_runtime_authority
                ),
                now_iso=now_iso,
            )
            writer = memex_writer
        enqueue_result = enqueue_reddog_readonly_audit_swarm(
            plan=plan,
            writer=writer,
            seen_assignment_ids=seen_assignment_ids,
        )
        if memex_writer is not None:
            memex_supply_result = memex_writer.last_result
        if not enqueue_result.accepted:
            return _not_ready(
                reasons=("readonly_audit_enqueue_rejected", *enqueue_result.rejection_reasons),
                changed_paths=paths,
                allowed_read_targets=targets,
                wsp15_allocation_receipt=wsp15_allocation_receipt,
                snapshot=snapshot,
                evidence_bundle=evidence_bundle,
                gate=gate,
                swarm_plan=plan,
                collection_result=collection_result,
                decision_result=decision_result,
                decision_persist_result=decision_persist_result,
                architect_result=architect_result,
                enqueue_result=enqueue_result,
                memex_supply_result=memex_supply_result,
            )

    return _ready(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate=gate,
        plan=plan,
        changed_paths=paths,
        allowed_read_targets=targets,
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        collection_result=collection_result,
        decision_result=decision_result,
        decision_persist_result=decision_persist_result,
        architect_result=architect_result,
        enqueue_result=enqueue_result,
        enqueue_attempted=enqueue_readonly_audit_tasks,
        memex_supply_result=memex_supply_result,
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


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
    required: bool = True,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,) if required else ()
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    try:
        path.relative_to(repo_root)
        return None, (inside_reason,)
    except ValueError:
        pass
    if not path.exists() or not path.is_file():
        return None, (missing_reason,)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, (unreadable_reason,)
    if not isinstance(payload, Mapping):
        return None, (unreadable_reason,)
    return payload, ()


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
