"""Tests for REDDOG_READONLY_AUDIT_TASK_REPORT_EXECUTOR_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SKILL,
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    READONLY_AUDIT_LANE_ANALYZER_SLICE,
    READONLY_AUDIT_TASK_REPORT_ACCEPT,
    READONLY_AUDIT_TASK_REPORT_REJECT,
    ReadOnlyAuditTaskRejectReason,
    execute_reddog_readonly_audit_task,
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
    / "reddog_readonly_audit_task_executor.py"
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
    other = root / "modules" / "communication" / "moltbot_bridge" / "src" / "sample.py"
    other.parent.mkdir(parents=True)
    other.write_text("VALUE = 1\n", encoding="utf-8")
    return root


def _context() -> dict:
    return {
        "source": READONLY_AUDIT_TASK_SOURCE,
        "swarm_receipt": {
            "swarm_id": "swarm-1",
            "snapshot_receipt_id": "snapshot-1",
            "determination_id": "det-1",
        },
        "assignment": {
            "assignment_id": "assignment-1",
            "lane_id": "repo_code_audit",
            "snapshot_receipt_id": "snapshot-1",
            "allowed_read_targets": [
                "docs/work_ledger.schema.json",
                "modules/communication/moltbot_bridge/src/sample.py",
            ],
        },
        "forbidden_actions": [
            "repo_write",
            "shell_execute",
            "git_push",
            "openclaw_enqueue",
            "holoindex_reindex",
        ],
    }


def test_readonly_audit_executor_reads_only_allowlisted_targets(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    result = execute_reddog_readonly_audit_task(task_context=_context(), repo_root=root)

    assert result.accepted is True
    assert result.decision == READONLY_AUDIT_TASK_REPORT_ACCEPT
    assert result.no_repo_mutation_performed is True
    assert result.no_shell_command_executed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.report is not None
    assert result.report["repo_mutation_performed"] is False
    assert result.report["execution_performed"] is False
    assert result.report["openclaw_enqueue_performed"] is False
    assert len(result.report["evidence_refs"]) == 2
    assert all(ref.startswith("file:") for ref in result.report["evidence_refs"])
    assert len(result.report["findings"]) == 1
    finding = result.report["findings"][0]
    assert finding["finding_id"] == "repo_code_audit:lane_analyzer_missing"
    assert finding["wsp97_label"] == "SPECIFIED_NOT_IMPLEMENTED"
    assert finding["recommended_action"] == "FIX"
    assert finding["next_slice_name"] == READONLY_AUDIT_LANE_ANALYZER_SLICE
    assert set(finding["evidence_refs"]) == set(result.report["evidence_refs"])


def test_readonly_audit_executor_rejects_wrong_source_or_missing_assignment(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    wrong = dict(_context())
    wrong["source"] = "other"
    missing = dict(_context())
    missing.pop("assignment")

    wrong_result = execute_reddog_readonly_audit_task(task_context=wrong, repo_root=root)
    missing_result = execute_reddog_readonly_audit_task(task_context=missing, repo_root=root)

    assert wrong_result.accepted is False
    assert wrong_result.decision == READONLY_AUDIT_TASK_REPORT_REJECT
    assert ReadOnlyAuditTaskRejectReason.WRONG_SOURCE in wrong_result.rejection_reasons
    assert missing_result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.MISSING_ASSIGNMENT in missing_result.rejection_reasons


def test_readonly_audit_executor_rejects_traversal_secret_and_missing_targets(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    traversal = _context()
    traversal["assignment"] = dict(traversal["assignment"])
    traversal["assignment"]["allowed_read_targets"] = ["../secret.txt"]
    secret = _context()
    secret["assignment"] = dict(secret["assignment"])
    secret["assignment"]["allowed_read_targets"] = [".env"]
    missing = _context()
    missing["assignment"] = dict(missing["assignment"])
    missing["assignment"]["allowed_read_targets"] = ["docs/missing.md"]

    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=traversal,
        repo_root=root,
    ).rejection_reasons
    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=secret,
        repo_root=root,
    ).rejection_reasons
    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=missing,
        repo_root=root,
    ).rejection_reasons


def test_run_task_executes_reddog_readonly_audit_before_wre(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("WRE_MOCK_SKILLS", READONLY_AUDIT_TASK_SKILL)
    db = AgentDB()
    task_id = "readonly-audit-task-1"
    assert db.create_autonomous_task(
        task_id=task_id,
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=[READONLY_AUDIT_TASK_SKILL],
        estimated_complexity=0.35,
        priority_score=0.85,
        context=_context(),
        origin_continuity_id="det-1",
    )
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    result = execute_task(task_id, repo_root=root)

    assert result["ok"] is True
    assert result["executor"] == "reddog:readonly_audit"
    assert result["structured_result"]["accepted"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_executor_module_ast_has_no_mutation_network_or_runtime_wiring() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_text = (
        "subprocess",
        "requests",
        "socket",
        "openclaw_supervisor",
        "hermes_job_executor",
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

    imported = set()
    calls = set()
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)

    assert not (imported & {"subprocess", "requests", "socket", "urllib", "shutil"})
    assert not (calls & {"eval", "exec", "compile", "system", "popen", "run", "Popen"})
    assert not (attrs & {"write_text", "mkdir", "unlink", "rmdir"})
