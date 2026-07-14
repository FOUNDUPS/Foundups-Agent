"""Tests for REDDOG_READONLY_AUDIT_DECISION_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    READONLY_AUDIT_REPORTS_ACCEPTED,
    READONLY_AUDIT_REPORTS_REJECTED,
    READONLY_AUDIT_SWARM_PLANNED,
    ReadOnlyAuditAssignment,
    ReadOnlyAuditReportBundle,
    ReadOnlyAuditReportValidationResult,
    ReadOnlyAuditSwarmPlan,
    ReadOnlyAuditSwarmReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ACTION_FIX,
    ACTION_RESEARCH_MORE,
    ACTION_WAIT_FOR_REPORTS,
    DEFAULT_SEMANTIC_FINDINGS_SLICE,
    READONLY_AUDIT_DECISION_ACCEPT,
    READONLY_AUDIT_DECISION_REJECT,
    decide_reddog_readonly_audit_next_action,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
    READONLY_AUDIT_REPORT_COLLECTION_REJECT,
    ReadOnlyAuditReportCollectionResult,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_audit_decision_runtime.py"
)


def _assignment() -> ReadOnlyAuditAssignment:
    return ReadOnlyAuditAssignment(
        assignment_id="readonly-assignment-1",
        lane_id="repo_code_audit",
        worker_role="readonly_repo_code_audit",
        snapshot_receipt_id="sha256:snapshot",
        snapshot_content_digest="sha256:snapshot-content",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        required_source="repo",
        allowed_read_targets=("docs/work_ledger.schema.json",),
    )


def _plan() -> ReadOnlyAuditSwarmPlan:
    assignment = _assignment()
    receipt = ReadOnlyAuditSwarmReceipt(
        swarm_id="readonly-swarm-1",
        status=READONLY_AUDIT_SWARM_PLANNED,
        snapshot_receipt_id=assignment.snapshot_receipt_id,
        snapshot_content_digest=assignment.snapshot_content_digest,
        context_view_id=assignment.context_view_id,
        evidence_bundle_id=assignment.evidence_bundle_id,
        determination_id=assignment.determination_id,
        requested_operation="main_startup_readonly_operational_audit",
        assignment_ids=(assignment.assignment_id,),
        lanes=(assignment.lane_id,),
        rejection_reasons=(),
    )
    return ReadOnlyAuditSwarmPlan(
        accepted=True,
        status=READONLY_AUDIT_SWARM_PLANNED,
        receipt=receipt,
        assignments=(assignment,),
        rejection_reasons=(),
    )


def _report(*, findings=()) -> dict:
    assignment = _assignment()
    return {
        "assignment_id": assignment.assignment_id,
        "lane_id": assignment.lane_id,
        "snapshot_receipt_id": assignment.snapshot_receipt_id,
        "summary": "repo_code_audit read-only audit evidence collected from 1 target.",
        "evidence_refs": ["file:docs/work_ledger.schema.json:sha256:abc:lines:1"],
        "repo_mutation_performed": False,
        "execution_performed": False,
        "openclaw_enqueue_performed": False,
        "readonly_audit_performed": True,
        "report_digest": "sha256:report-1",
        "findings": list(findings),
    }


def _accepted_collection() -> ReadOnlyAuditReportCollectionResult:
    bundle = ReadOnlyAuditReportBundle(
        bundle_id="sha256:bundle",
        swarm_id=_plan().receipt.swarm_id,
        report_digests=("sha256:report-1",),
        lanes_reported=("repo_code_audit",),
        missing_lanes=(),
        rejection_reasons=(),
    )
    validation = ReadOnlyAuditReportValidationResult(
        accepted=True,
        status=READONLY_AUDIT_REPORTS_ACCEPTED,
        bundle=bundle,
        rejection_reasons=(),
    )
    return ReadOnlyAuditReportCollectionResult(
        accepted=True,
        status=READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
        swarm_id=_plan().receipt.swarm_id,
        report_count=1,
        validation=validation,
        rejection_reasons=(),
    )


def _rejected_collection() -> ReadOnlyAuditReportCollectionResult:
    validation = ReadOnlyAuditReportValidationResult(
        accepted=False,
        status=READONLY_AUDIT_REPORTS_REJECTED,
        bundle=None,
        rejection_reasons=("missing_report_for_lane:repo_code_audit",),
    )
    return ReadOnlyAuditReportCollectionResult(
        accepted=False,
        status=READONLY_AUDIT_REPORT_COLLECTION_REJECT,
        swarm_id=_plan().receipt.swarm_id,
        report_count=0,
        validation=validation,
        rejection_reasons=("missing_report_for_lane:repo_code_audit",),
    )


def _fix_finding() -> dict:
    return {
        "finding_id": "repo-finding-1",
        "claim": "Runtime reconciliation is missing.",
        "wsp97_label": "OBSERVED",
        "recommended_action": ACTION_FIX,
        "wsp15_priority": "P0",
        "severity": "BLOCKER",
        "evidence_refs": ["file:docs/work_ledger.schema.json:sha256:abc:lines:1"],
        "next_slice_name": "REDDOG_RUNTIME_RECONCILER_PHASE1",
    }


def test_no_semantic_findings_routes_to_research_more_without_overclaiming_fix() -> None:
    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_accepted_collection(),
        reports=(_report(),),
    )

    assert decision.accepted is True
    assert decision.status == READONLY_AUDIT_DECISION_ACCEPT
    assert decision.action == ACTION_RESEARCH_MORE
    assert decision.next_slice_name == DEFAULT_SEMANTIC_FINDINGS_SLICE
    assert decision.decision_reasons == ("semantic_findings_missing",)
    assert decision.finding_count == 0
    assert decision.no_model_call_performed is True
    assert decision.no_repo_mutation_performed is True


def test_selects_highest_priority_fix_finding_when_evidence_is_bound_to_report() -> None:
    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_accepted_collection(),
        reports=(_report(findings=(_fix_finding(),)),),
    )

    assert decision.accepted is True
    assert decision.action == ACTION_FIX
    assert decision.wsp15_priority == "P0"
    assert decision.next_slice_name == "REDDOG_RUNTIME_RECONCILER_PHASE1"
    assert decision.finding_count == 1
    assert decision.selected_finding_digest in decision.finding_digests


def test_rejected_collection_waits_for_reports() -> None:
    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_rejected_collection(),
        reports=(),
    )

    assert decision.accepted is False
    assert decision.status == READONLY_AUDIT_DECISION_REJECT
    assert decision.action == ACTION_WAIT_FOR_REPORTS
    assert "missing_report_for_lane:repo_code_audit" in decision.rejection_reasons


def test_rejects_report_count_mismatch() -> None:
    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_accepted_collection(),
        reports=(),
    )

    assert decision.accepted is False
    assert "report_count_mismatch" in decision.rejection_reasons


def test_rejects_finding_evidence_not_bound_to_report_refs() -> None:
    bad = _fix_finding()
    bad["evidence_refs"] = ["file:other.py:sha256:def:lines:1"]

    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_accepted_collection(),
        reports=(_report(findings=(bad,)),),
    )

    assert decision.accepted is False
    assert "finding_evidence_not_in_report:repo-finding-1" in decision.rejection_reasons


def test_needs_verification_finding_cannot_trigger_fix() -> None:
    bad = _fix_finding()
    bad["wsp97_label"] = "NEEDS_VERIFICATION"

    decision = decide_reddog_readonly_audit_next_action(
        collection_result=_accepted_collection(),
        reports=(_report(findings=(bad,)),),
    )

    assert decision.accepted is False
    assert "finding_needs_verification_not_research_more:repo-finding-1" in decision.rejection_reasons


def test_decision_module_ast_has_no_execution_or_runtime_mutation() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "subprocess",
        "requests",
        "httpx",
        "socket",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    forbidden_tokens = (
        "create_autonomous_task",
        "execute_skill",
        "holo_index.py --index",
        "write_text",
        "mkdir",
        "git push",
        "gh pr",
    )
    for token in forbidden_tokens:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_import_roots
