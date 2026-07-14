"""Tests for REDDOG_READONLY_AUDIT_REPORT_COLLECTION_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SKILL,
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    READONLY_AUDIT_REPORTS_ACCEPTED,
    READONLY_AUDIT_REPORTS_REJECTED,
    READONLY_AUDIT_SWARM_PLANNED,
    ReadOnlyAuditAssignment,
    ReadOnlyAuditSwarmPlan,
    ReadOnlyAuditSwarmReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
    READONLY_AUDIT_REPORT_COLLECTION_REJECT,
    READONLY_AUDIT_REPORT_PERSIST_ACCEPT,
    READONLY_AUDIT_REPORT_PERSIST_REJECT,
    AgentDbReadOnlyAuditReportStore,
    ReadOnlyAuditReportReason,
    collect_reddog_readonly_audit_report_bundle,
    persist_reddog_readonly_audit_task_report,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_audit_report_collection.py"
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    target = root / "docs" / "work_ledger.schema.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"schema": "work-ledger", "version": 1}\n', encoding="utf-8")
    return root


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


def _context(plan: ReadOnlyAuditSwarmPlan | None = None) -> dict:
    active_plan = plan or _plan()
    return {
        "source": READONLY_AUDIT_TASK_SOURCE,
        "swarm_receipt": active_plan.receipt.to_dict(),
        "assignment": active_plan.assignments[0].to_dict(),
        "forbidden_actions": [
            "repo_write",
            "shell_execute",
            "git_push",
            "openclaw_enqueue",
            "holoindex_reindex",
        ],
    }


def _report(plan: ReadOnlyAuditSwarmPlan | None = None) -> dict:
    assignment = (plan or _plan()).assignments[0]
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
    }


def _task_result(report: dict | None = None) -> dict:
    return {
        "ok": True,
        "executor": "reddog:readonly_audit",
        "structured_result": {
            "accepted": True,
            "decision": "READONLY_AUDIT_TASK_REPORT_ACCEPT",
            "report": report or _report(),
            "evidence": [],
            "rejection_reasons": [],
        },
    }


def test_persisted_report_collects_into_existing_swarm_validator() -> None:
    plan = _plan()

    persist = persist_reddog_readonly_audit_task_report(
        task_id="task-1",
        task_context=_context(plan),
        task_result=_task_result(_report(plan)),
    )
    collected = collect_reddog_readonly_audit_report_bundle(plan=plan)

    assert persist.accepted is True
    assert persist.status == READONLY_AUDIT_REPORT_PERSIST_ACCEPT
    assert collected.accepted is True
    assert collected.status == READONLY_AUDIT_REPORT_COLLECTION_ACCEPT
    assert collected.validation.status == READONLY_AUDIT_REPORTS_ACCEPTED
    assert collected.validation.bundle is not None
    assert collected.validation.bundle.lanes_reported == ("repo_code_audit",)
    assert collected.no_repo_mutation_performed is True


def test_collection_rejects_missing_persisted_report() -> None:
    collected = collect_reddog_readonly_audit_report_bundle(plan=_plan())

    assert collected.accepted is False
    assert collected.status == READONLY_AUDIT_REPORT_COLLECTION_REJECT
    assert collected.validation.status == READONLY_AUDIT_REPORTS_REJECTED
    assert "missing_report_for_lane:repo_code_audit" in collected.rejection_reasons


def test_persist_rejects_binding_mismatch_and_mutation_claim() -> None:
    report = _report()
    report["assignment_id"] = "other"
    report["repo_mutation_performed"] = True

    result = persist_reddog_readonly_audit_task_report(
        task_id="task-1",
        task_context=_context(),
        task_result=_task_result(report),
    )

    assert result.accepted is False
    assert result.status == READONLY_AUDIT_REPORT_PERSIST_REJECT
    assert ReadOnlyAuditReportReason.REPORT_BINDING_MISMATCH in result.rejection_reasons
    assert ReadOnlyAuditReportReason.REPORT_CLAIMS_MUTATION in result.rejection_reasons


def test_store_rejects_conflicting_duplicate_assignment_report() -> None:
    plan = _plan()
    store = AgentDbReadOnlyAuditReportStore()
    first = persist_reddog_readonly_audit_task_report(
        task_id="task-1",
        task_context=_context(plan),
        task_result=_task_result(_report(plan)),
        store=store,
    )
    changed = _report(plan)
    changed["report_digest"] = "sha256:changed"
    second = persist_reddog_readonly_audit_task_report(
        task_id="task-2",
        task_context=_context(plan),
        task_result=_task_result(changed),
        store=store,
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.rejection_reasons == (ReadOnlyAuditReportReason.STORE_REJECTED,)


def test_run_task_persists_report_before_marking_complete(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("WRE_MOCK_SKILLS", READONLY_AUDIT_TASK_SKILL)
    plan = _plan()
    db = AgentDB()
    task_id = "readonly-audit-task-collection"
    assert db.create_autonomous_task(
        task_id=task_id,
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=[READONLY_AUDIT_TASK_SKILL],
        estimated_complexity=0.35,
        priority_score=0.85,
        context=_context(plan),
        origin_continuity_id="sha256:determination",
    )
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    result = execute_task(task_id, repo_root=root)
    collected = collect_reddog_readonly_audit_report_bundle(plan=plan)

    assert result["ok"] is True
    assert result["readonly_audit_report_persist"]["accepted"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert collected.accepted is True
    assert collected.report_count == 1


def test_report_collection_module_ast_has_no_execution_or_repo_mutation() -> None:
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
    forbidden_text = (
        "execute_skill",
        "holo_index.py --index",
        "create_autonomous_task",
        "write_text",
        "mkdir",
        "git push",
        "gh pr",
    )
    for token in forbidden_text:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_import_roots
