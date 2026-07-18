"""Tests for REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from holo_index.freshness_receipt import CollectionFreshness, HoloIndexFreshnessReceipt
from holo_index.repository_state import RepositoryState
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ARCHITECT_DETERMINATION_ACCEPT,
    ArchitectModelResult,
    InMemoryArchitectDeterminationStore,
)
from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import (
    DEFAULT_BOOTSTRAP_READ_TARGETS,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    RepoAuditModelResult,
)
import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as readonly_worker_runtime
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    READONLY_AUDIT_DECISION_PERSIST_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime import (
    READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT,
    READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT,
    DirectReadOnlyAuditTaskExecutor,
    ReadOnlyAuditResearchDecisionE2EReason,
    run_reddog_readonly_audit_research_decision_e2e,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    READONLY_AUDIT_TASK_REPORT_REJECT,
    ReadOnlyAuditTaskExecutionResult,
    ReadOnlyAuditTaskRejectReason,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_audit_research_decision_e2e_runtime.py"
)
NOW = "2026-07-16T00:00:00+00:00"
HEAD = "da7bb6d20"
REVISION = "sha256:e2e-work-state"


@pytest.fixture(autouse=True)
def _clean_bound_repository_state(monkeypatch) -> None:
    monkeypatch.setattr(
        readonly_worker_runtime,
        "read_repository_state",
        lambda *args, **kwargs: RepositoryState(
            head_sha=HEAD,
            clean=True,
            state_digest="sha256:e2e-clean",
        ),
    )


def _repo_state() -> dict[str, object]:
    return {
        "head_sha": HEAD,
        "dirty_paths": (),
        "dirty_digest": "sha256:clean",
        "worktree_digest": "sha256:worktrees",
    }


def _work_state() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": REVISION,
        "selected_slice": "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_PHASE1",
        "refresh_receipt_id": "sha256:refresh",
        "worker_claims": [
            {
                "claim_id": "claim-e2e",
                "slice_id": "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_PHASE1",
            }
        ],
        "wre_queue_items": [{"queue_item_id": "queue-e2e", "claim_id": "claim-e2e"}],
    }


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha=HEAD,
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        generation_id="sha256:holo-generation-e2e",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=4,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
                source_manifest_digest="sha256:work-ledger-manifest",
                indexed_paths_digest="sha256:work-ledger-paths",
                verification="PASS",
                proof_kind="complete_source_manifest",
            ),
            CollectionFreshness(
                name="navigation_symbols",
                source_scope_id="holoindex.navigation_symbols.tracked-modules-scripts-holo.v1",
                count=9,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
                source_manifest_digest="sha256:symbols-manifest",
                indexed_paths_digest="sha256:symbols-paths",
                verification="PASS",
                proof_kind="complete_source_manifest",
            ),
        ],
    )


class _AcceptingTaskWriter:
    def __init__(self) -> None:
        self.tasks = []

    def enqueue_readonly_audit_tasks(self, tasks, receipt):
        self.tasks.append((tuple(tasks), receipt))
        return {"ok": True, "created_task_ids": [task.task_id for task in tasks]}


class _InMemoryReportStore:
    def __init__(self, *, reject_store: bool = False) -> None:
        self.reject_store = reject_store
        self.records = []
        self.load_calls = []

    def store_readonly_audit_report(self, record):
        if self.reject_store:
            return {"ok": False, "reason": "forced_reject"}
        self.records.append(record)
        return {"ok": True, "stored": True}

    def load_readonly_audit_reports(self, swarm_id: str):
        self.load_calls.append(swarm_id)
        return tuple(record.report for record in self.records if record.swarm_id == swarm_id)


class _InMemoryDecisionStore:
    def __init__(self) -> None:
        self.records = []

    def store_readonly_audit_decision(self, record):
        self.records.append(record)
        return {"ok": True, "stored": True, "idempotent": False}

    def load_latest_readonly_audit_decision(self):
        return None

    def load_readonly_audit_decision(self, decision_id: str):
        return None


class _FakeQueryAdapter:
    def __init__(self) -> None:
        self.calls = []

    def query(self, *, query: str, allowed_paths, limit: int):
        self.calls.append({"query": query, "allowed_paths": tuple(allowed_paths), "limit": limit})
        path = allowed_paths[0] if allowed_paths else DEFAULT_BOOTSTRAP_READ_TARGETS[0]
        return {
            "ok": True,
            "source": "fake",
            "query": query,
            "freshness": "FRESH",
            "hits": [{"path": path, "title": "fake hit", "score": 0.99, "digest": "sha256:index-hit"}],
            "error": "",
            "freshness_generation_id": "sha256:holo-generation-e2e",
            "freshness_receipt_digest": "sha256:holo-receipt-e2e",
            "freshness_receipt_path": "E:/HoloIndex/indexes/holoindex_freshness_receipt.json",
            "repo_head_sha": HEAD,
        }


class _AuditModelRunner:
    def __init__(self) -> None:
        self.calls = []

    def run_repo_code_audit(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append({"prompt": prompt, "context": context, "binding": dict(binding)})
        parsed_context = json.loads(context)
        parsed_prompt = json.loads(prompt)
        evidence_ref = parsed_context["untrusted_repository_evidence"][0]["evidence_ref"]
        lane_id = parsed_prompt["assignment"]["lane_id"]
        output = {
            "summary": f"{lane_id} verified current evidence and found one actionable runtime gap.",
            "evidence_refs": [evidence_ref],
            "findings": [
                {
                    "finding_id": f"{lane_id}:runtime-gap",
                    "claim": f"{lane_id} supports continuing with the resident RedDog runtime path.",
                    "wsp97_label": "OBSERVED",
                    "recommended_action": "FIX",
                    "wsp15_priority": "P1",
                    "severity": "MAJOR",
                    "evidence_refs": [evidence_ref],
                    "next_slice_name": "REDDOG_RESIDENT_RUNTIME_NEXT_PHASE1",
                }
            ],
        }
        return RepoAuditModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(output, sort_keys=True),
            model_receipt_id=f"model-receipt-{lane_id}",
            model_result_digest=f"sha256:model-result-{lane_id}",
            made_network_call=True,
        )


class _ArchitectRunner:
    def __init__(self) -> None:
        self.calls = []

    def run_architect_determination(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append({"prompt": prompt, "context": context, "binding": dict(binding)})
        parsed = json.loads(prompt)
        evidence_ref = parsed["reports"][0]["evidence_refs"][0]
        content = {
            "action": "FIX",
            "next_slice_name": "REDDOG_RESIDENT_RUNTIME_NEXT_PHASE1",
            "summary": "All read-only audit reports support one next resident runtime slice.",
            "decision_reasons": ["selected highest priority verified read-only audit finding"],
            "evidence_refs": [evidence_ref],
            "wsp15_allocation_receipt_id": parsed["wsp15_allocation_receipt_id"],
        }
        return ArchitectModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(content, sort_keys=True),
            model_receipt_id="architect-model-receipt-e2e",
            model_result_digest="sha256:architect-model-result-e2e",
            review_packet={"fusion_panel_quorum": {"passed": True}},
            made_network_call=True,
            rejection_reasons=(),
        )


class _RejectingTaskExecutor:
    def execute_readonly_audit_task(self, **kwargs):
        return ReadOnlyAuditTaskExecutionResult(
            accepted=False,
            decision=READONLY_AUDIT_TASK_REPORT_REJECT,
            report=None,
            evidence=(),
            rejection_reasons=(ReadOnlyAuditTaskRejectReason.MODEL_FAILURE,),
        )


def test_e2e_runs_enqueued_readonly_tasks_persists_reports_and_architect_decides() -> None:
    writer = _AcceptingTaskWriter()
    report_store = _InMemoryReportStore()
    decision_store = _InMemoryDecisionStore()
    architect_store = InMemoryArchitectDeterminationStore()
    audit_runner = _AuditModelRunner()
    architect_runner = _ArchitectRunner()

    result = run_reddog_readonly_audit_research_decision_e2e(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        enqueue_writer=writer,
        report_store=report_store,
        decision_store=decision_store,
        architect_determination_store=architect_store,
        audit_model_runner=audit_runner,
        architect_model_runner=architect_runner,
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is True
    assert result.status == READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT
    assert result.initial_bootstrap.enqueue_task_count == 5
    assert result.initial_bootstrap.report_collection_attempted is False
    assert result.final_bootstrap is not None
    assert result.final_bootstrap.report_collection_status == READONLY_AUDIT_REPORT_COLLECTION_ACCEPT
    assert result.final_bootstrap.report_collection_report_count == 5
    assert result.final_bootstrap.readonly_audit_decision_persist_status == READONLY_AUDIT_DECISION_PERSIST_ACCEPT
    assert result.final_bootstrap.backend_architect_determination_status == ARCHITECT_DETERMINATION_ACCEPT
    assert result.final_bootstrap.backend_architect_determination_queue_candidate_count == 1
    assert len(result.task_runs) == 5
    assert all(item.accepted and item.persist_accepted for item in result.task_runs)
    assert len(report_store.records) == 5
    assert len(decision_store.records) == 1
    assert len(architect_store.records) == 1
    assert len(audit_runner.calls) == 5
    assert len(architect_runner.calls) == 1
    assert result.readonly_audit_tasks_enqueued is True
    assert result.readonly_audit_tasks_executed is True
    assert result.coding_worker_spawned is False
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_live_foundup_enqueue_performed is True


def test_e2e_fails_closed_before_report_collection_when_task_execution_rejects() -> None:
    result = run_reddog_readonly_audit_research_decision_e2e(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        enqueue_writer=_AcceptingTaskWriter(),
        report_store=_InMemoryReportStore(),
        task_executor=_RejectingTaskExecutor(),
    )

    assert result.accepted is False
    assert result.status == READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT
    assert ReadOnlyAuditResearchDecisionE2EReason.TASK_EXECUTION_REJECTED in result.rejection_reasons
    assert ReadOnlyAuditTaskRejectReason.MODEL_FAILURE in result.rejection_reasons
    assert result.final_bootstrap is None
    assert len(result.task_runs) == 1
    assert result.task_runs[0].accepted is False


def test_e2e_fails_closed_when_report_persistence_rejects() -> None:
    result = run_reddog_readonly_audit_research_decision_e2e(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        enqueue_writer=_AcceptingTaskWriter(),
        report_store=_InMemoryReportStore(reject_store=True),
        audit_model_runner=_AuditModelRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditResearchDecisionE2EReason.REPORT_PERSIST_REJECTED in result.rejection_reasons
    assert result.final_bootstrap is None
    assert len(result.task_runs) == 1
    assert result.task_runs[0].accepted is True
    assert result.task_runs[0].persist_accepted is False


def test_e2e_module_has_no_shell_worktree_repo_mutation_or_reindex_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_text = (
        "subprocess",
        "requests",
        "httpx",
        "socket",
        "git push",
        "gh pr",
        "holo_index.py --index",
        "hermes_job_executor",
    )
    for token in forbidden_text:
        assert token not in source

    forbidden_calls = {
        "write_text",
        "open",
        "mkdir",
        "unlink",
        "rmdir",
        "remove",
        "system",
        "popen",
        "run",
        "call",
        "check_call",
        "check_output",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in {"subprocess", "requests", "httpx", "socket"}
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in {"subprocess", "requests", "httpx", "socket"}
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            assert name not in forbidden_calls
