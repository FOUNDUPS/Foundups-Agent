"""Tests for REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
    FORBIDDEN_ACTIONS,
    READONLY_AUDIT_REPORTS_ACCEPTED,
    READONLY_AUDIT_REPORTS_REJECTED,
    READONLY_AUDIT_SWARM_PLANNED,
    READONLY_AUDIT_SWARM_REJECTED,
    plan_reddog_openclaw_readonly_audit_swarm,
    validate_reddog_openclaw_readonly_audit_reports,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION as GROUNDING_SCHEMA_VERSION,
    canonical_digest as grounding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_evidence_bundle,
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_openclaw_readonly_audit_swarm_runtime.py"
)
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "a764551a89068f57affff47350c5537d849a4564"
REVISION = "sha256:work-state-refresh"
GROUNDING_FOCUS = "Audit the work ledger and RedDog continuity semantics."


def _grounding_receipt() -> dict[str, object]:
    repo_target = "holo_index/adaptive_learning/breadcrumb_tracer.py"
    semantic_target = "RedDog continuity semantics"
    typed = {
        "repo_file_targets": [repo_target],
        "semantic_targets": [semantic_target],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": grounding_digest([]),
    }
    coverage = [
        {
            "target": semantic_target,
            "verdict": "SUFFICIENT",
            "evidence_refs": ["code:holo_index/adaptive_learning/breadcrumb_tracer.py"],
        }
    ]
    value = {
        "schema_version": GROUNDING_SCHEMA_VERSION,
        "source_surface": "editor_thin_client",
        "work_focus_digest": grounding_digest({"work_focus": GROUNDING_FOCUS}),
        "typed_targets": typed,
        "typed_targets_digest": grounding_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 1,
        "semantic_targets_count": 1,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": coverage,
        "semantic_target_coverage_digest": grounding_digest(
            {"semantic_target_coverage": coverage}
        ),
        "target_recall_ok": True,
        "required_targets_missing": [],
        "direct_read_paths": [repo_target],
        "holoindex_owner_query_ok": True,
        "holoindex_freshness": "CURRENT",
        "holoindex_generation_id": "sha256:" + "a" * 64,
        "holoindex_freshness_receipt_digest": "sha256:" + "b" * 64,
        "holoindex_repo_head_sha": HEAD,
        "holoindex_query_receipt_id": "sha256:" + "c" * 64,
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = grounding_digest(value)
    return value


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
    )


def _accepted_gate_bundle():
    snapshot_result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": "sha256:clean",
            "worktree_digest": "sha256:worktrees",
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": REVISION,
            "selected_slice": "REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_RUNTIME_PHASE1",
            "refresh_receipt_id": "sha256:refresh",
            "worker_claims": [{"claim_id": "claim-1", "status": "ACTIVE"}],
            "wre_queue_items": [{"queue_item_id": "queue-1"}],
        },
        holoindex_receipt=_fresh_holo_receipt(),
        changed_paths=[
            "docs/0102_session_briefings/work_ledger.schema.json",
            "modules/communication/moltbot_bridge/src/reddog_openclaw_readonly_audit_swarm_runtime.py",
        ],
        breadcrumbs=[
            {
                "breadcrumb_id": "b1",
                "continuity_id": "cont-1",
                "timestamp": NOW,
            }
        ],
        breadcrumb_scope="cont-1",
        now_iso=NOW,
    )
    assert snapshot_result.accepted is True
    assert snapshot_result.snapshot is not None
    assert snapshot_result.context_view is not None
    evidence_bundle = build_evidence_bundle(
        snapshot=snapshot_result.snapshot,
        context_view=snapshot_result.context_view,
        report_digests=["sha256:repo-audit", "sha256:security-audit"],
    )
    gate = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot_result.snapshot,
        context_view=snapshot_result.context_view,
        evidence_bundle=evidence_bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=snapshot_result.snapshot.breadcrumbs_state["high_watermark"],
        requested_operation="readonly_audit_swarm",
        prompt_text="audit current RedDog operational loop",
        now_iso="2026-07-14T00:01:00+00:00",
    )
    assert gate.accepted is True
    return snapshot_result.snapshot, snapshot_result.context_view, evidence_bundle, gate


def _valid_plan():
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        allowed_read_targets=[
            "docs/0102_session_briefings/work_ledger.schema.json",
            "modules/communication/moltbot_bridge/src/reddog_operational_context_snapshot.py",
        ],
    )
    return snapshot, context_view, evidence_bundle, gate, plan


def _reports_for_plan(plan):
    return [
        {
            "assignment_id": assignment.assignment_id,
            "lane_id": assignment.lane_id,
            "snapshot_receipt_id": assignment.snapshot_receipt_id,
            "summary": f"{assignment.lane_id} report: WSP_97 evidence retained.",
            "evidence_refs": [f"assignment:{assignment.assignment_id}", "snapshot:bound"],
            "repo_mutation_performed": False,
            "execution_performed": False,
            "openclaw_enqueue_performed": False,
        }
        for assignment in plan.assignments
    ]


def test_plans_default_readonly_audit_swarm_from_accepted_context_gate() -> None:
    _, _, _, _, plan = _valid_plan()

    assert plan.accepted is True
    assert plan.status == READONLY_AUDIT_SWARM_PLANNED
    assert plan.receipt.status == READONLY_AUDIT_SWARM_PLANNED
    assert tuple(assignment.lane_id for assignment in plan.assignments) == DEFAULT_AUDIT_LANES
    assert len(plan.assignments) == 5
    assert plan.receipt.no_worker_spawn_performed is True
    assert plan.receipt.no_openclaw_enqueue_performed is True
    assert plan.receipt.no_hermes_dispatch_performed is True
    assert plan.receipt.no_shell_command_executed is True
    assert plan.receipt.no_repo_mutation_performed is True
    assert plan.receipt.no_holoindex_reindex_performed is True
    for assignment in plan.assignments:
        assert assignment.forbidden_actions == FORBIDDEN_ACTIONS
        assert assignment.no_worker_spawn_performed is True
        assert assignment.no_execution_performed is True
        assert assignment.snapshot_receipt_id == plan.receipt.snapshot_receipt_id


def test_plan_binds_wsp15_allocation_to_every_assignment() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="readonly_audit_swarm",
        prompt_text="audit current RedDog operational loop",
        allowed_read_targets=["docs/0102_session_briefings/work_ledger.schema.json"],
    ).to_dict()

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        allowed_read_targets=["docs/0102_session_briefings/work_ledger.schema.json"],
        wsp15_allocation_receipt=allocation,
    )

    assert plan.accepted is True
    assert plan.receipt.wsp15_allocation_receipt_id == allocation["receipt_id"]
    assert plan.receipt.wsp15_allocation_receipt == allocation
    assert all(
        assignment.wsp15_allocation_receipt_id == allocation["receipt_id"]
        for assignment in plan.assignments
    )
    assert all(assignment.wsp15_allocation_digest for assignment in plan.assignments)


def test_required_runtime_binding_rejects_absent_and_wrong_surface_before_assignments() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    absent = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        require_model_runtime_binding=True,
    )
    wrong = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        model_runtime_binding_receipt=model_runtime_binding_receipt(
            runtime_surface="reddog_backend_architect"
        ),
        require_model_runtime_binding=True,
    )

    assert absent.accepted is False
    assert "missing_model_runtime_binding_receipt" in absent.rejection_reasons
    assert absent.assignments == ()
    assert wrong.accepted is False
    assert "model_runtime_binding_surface_mismatch" in wrong.rejection_reasons
    assert wrong.assignments == ()


def test_plan_binds_grounded_prompt_targets_to_every_assignment() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    grounding = _grounding_receipt()

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        allowed_read_targets=["docs/0102_session_briefings/work_ledger.schema.json"],
        grounding_receipt=grounding,
        grounding_work_focus=GROUNDING_FOCUS,
    )

    assert plan.accepted is True
    assert plan.receipt.grounding_receipt_id == grounding["receipt_id"]
    assert plan.receipt.grounding_receipt == grounding
    assert plan.receipt.grounding_work_focus == GROUNDING_FOCUS
    for assignment in plan.assignments:
        assert "holo_index/adaptive_learning/breadcrumb_tracer.py" in assignment.allowed_read_targets
        assert assignment.grounding_receipt_id == grounding["receipt_id"]
        assert assignment.grounding_receipt_digest == plan.receipt.grounding_receipt_digest


def test_plan_rejects_grounding_work_focus_substitution() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        grounding_receipt=_grounding_receipt(),
        grounding_work_focus="different work focus",
    )

    assert plan.accepted is False
    assert "grounding_work_focus_mismatch" in plan.rejection_reasons
    assert plan.assignments == ()


def test_rejects_when_fusion_assignment_gate_rejected() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    rejected_gate = replace(gate, accepted=False, status="FUSION_ASSIGNMENT_GATE_REJECTED")

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=rejected_gate,
    )

    assert plan.accepted is False
    assert plan.status == READONLY_AUDIT_SWARM_REJECTED
    assert "fusion_assignment_gate_not_passed" in plan.rejection_reasons
    assert plan.assignments == ()


def test_rejects_binding_mismatch_before_assignment_packets() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()
    bad_binding = replace(gate.determination_binding, context_view_id="sha256:wrong")
    bad_gate = replace(gate, determination_binding=bad_binding)

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=bad_gate,
    )

    assert plan.accepted is False
    assert "binding_context_view_mismatch" in plan.rejection_reasons
    assert plan.assignments == ()


def test_rejects_missing_required_lane() -> None:
    snapshot, context_view, evidence_bundle, gate = _accepted_gate_bundle()

    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        audit_lanes=("repo_code_audit", "security_governance_audit"),
    )

    assert plan.accepted is False
    assert "missing_required_audit_lane:external_research_audit" in plan.rejection_reasons
    assert "missing_required_audit_lane:runtime_freshness_audit" in plan.rejection_reasons
    assert "missing_required_audit_lane:skill_gap_audit" in plan.rejection_reasons


def test_report_validation_accepts_complete_readonly_reports() -> None:
    _, _, _, _, plan = _valid_plan()

    result = validate_reddog_openclaw_readonly_audit_reports(
        plan=plan,
        reports=_reports_for_plan(plan),
    )

    assert result.accepted is True
    assert result.status == READONLY_AUDIT_REPORTS_ACCEPTED
    assert result.bundle is not None
    assert result.bundle.swarm_id == plan.receipt.swarm_id
    assert result.bundle.missing_lanes == ()
    assert tuple(sorted(result.bundle.lanes_reported)) == tuple(sorted(DEFAULT_AUDIT_LANES))


def test_report_validation_rejects_missing_report() -> None:
    _, _, _, _, plan = _valid_plan()
    reports = _reports_for_plan(plan)[:-1]

    result = validate_reddog_openclaw_readonly_audit_reports(plan=plan, reports=reports)

    assert result.accepted is False
    assert result.status == READONLY_AUDIT_REPORTS_REJECTED
    assert "missing_report_for_lane:security_governance_audit" in result.rejection_reasons
    assert result.bundle is not None
    assert result.bundle.missing_lanes == ("security_governance_audit",)


def test_report_validation_rejects_mutation_or_execution_claims() -> None:
    _, _, _, _, plan = _valid_plan()
    reports = _reports_for_plan(plan)
    reports[0]["repo_mutation_performed"] = True
    reports[1]["execution_performed"] = True
    reports[2]["openclaw_enqueue_performed"] = True

    result = validate_reddog_openclaw_readonly_audit_reports(plan=plan, reports=reports)

    assert result.accepted is False
    assert "report_claims_repo_mutation:repo_code_audit" in result.rejection_reasons
    assert "report_claims_execution:external_research_audit" in result.rejection_reasons
    assert "report_claims_openclaw_enqueue:runtime_freshness_audit" in result.rejection_reasons


def test_report_validation_rejects_missing_evidence_refs() -> None:
    _, _, _, _, plan = _valid_plan()
    reports = _reports_for_plan(plan)
    reports[0]["evidence_refs"] = []

    result = validate_reddog_openclaw_readonly_audit_reports(plan=plan, reports=reports)

    assert result.accepted is False
    assert "report_missing_evidence_refs:repo_code_audit" in result.rejection_reasons


def test_module_ast_has_no_execution_or_runtime_wiring() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_tokens = (
        "openclaw_supervisor",
        "hermes_job_executor",
        "subprocess",
        "requests",
        "create_autonomous_task",
        "execute_skill",
        "callFusion",
        "extension.js",
        "git push",
        "gh pr",
        "write_text",
        "mkdir",
    )
    for token in forbidden_tokens:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in {"subprocess", "requests", "os", "shutil"}
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in {"subprocess", "requests", "os", "shutil"}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"write_text", "mkdir", "commit"}
