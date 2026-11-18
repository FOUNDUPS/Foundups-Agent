"""Tests for REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import (
    DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    REDDOG_MAIN_BOOTSTRAP_NOT_READY,
    REDDOG_MAIN_BOOTSTRAP_READY,
    RedDogMainReadonlyBootstrapResult,
    run_reddog_main_readonly_operational_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT,
    READONLY_AUDIT_SWARM_ENQUEUE_REJECT,
    ReadOnlyAuditEnqueueReason,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
    READONLY_AUDIT_REPORT_COLLECTION_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    READONLY_AUDIT_DECISION_PERSIST_ACCEPT,
    READONLY_AUDIT_DECISION_PERSIST_REJECT,
    ReadOnlyAuditDecisionPersistReason,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ACTION_FIX,
    ACTION_RESEARCH_MORE,
    DEFAULT_SEMANTIC_FINDINGS_SLICE,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ARCHITECT_DETERMINATION_ACCEPT,
    ArchitectModelResult,
    InMemoryArchitectDeterminationStore,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _model_selection,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.provider_call_evidence_test_helpers import (
    architect_provider_call_evidence,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    architect_model_output,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_bootstrap as owner_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_readonly_operational_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "bd1fe7f6ccb0964107b58d1fb93148f9f6ef7223"
REVISION = "sha256:work-state-bootstrap"
OWNER_SERVICE_ENV = {
    "HOLOINDEX_QUERY_SERVICE_URL": "http://127.0.0.1:8127",
    "HOLOINDEX_QUERY_SERVICE_TOKEN": "test-owner-service-token-with-strong-length",
    "REDDOG_HOLOINDEX_AUTO_MAINTENANCE": "0",
}
MAIN_RESIDENT_AUTH_ENV = {
    "REDDOG_AUTHENTICATED_PRINCIPAL_ID": "principal-main-test",
    "REDDOG_AUTHORIZED_FOUNDUP_IDS": "foundups_agent",
}


@pytest.fixture(autouse=True)
def _configured_owner_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        owner_bootstrap,
        "_configured_owner_health_ready",
        lambda **_kwargs: True,
    )


@pytest.fixture(autouse=True)
def _valid_resident_runtime_binding_preflight(monkeypatch: pytest.MonkeyPatch):
    import main

    original = main._reddog_resident_model_runtime_bindings_from_env
    audit = model_runtime_binding_receipt(runtime_surface="reddog_readonly_audit_worker")
    architect = model_runtime_binding_receipt(runtime_surface="reddog_backend_architect")
    monkeypatch.setattr(
        main,
        "_reddog_resident_model_runtime_bindings_from_env",
        lambda _repo_root: (audit, architect, ""),
    )
    yield original


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
        "selected_slice": "REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1",
        "refresh_receipt_id": "sha256:refresh",
        "worker_claims": [{"claim_id": "claim-1", "slice_id": "REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1"}],
        "wre_queue_items": [{"queue_item_id": "queue-1", "claim_id": "claim-1"}],
    }


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
    )


def _architect_runtime_binding() -> dict[str, object]:
    return model_runtime_binding_receipt(runtime_surface="reddog_backend_architect")


class _FakeEnqueueWriter:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[tuple[list[object], object]] = []

    def enqueue_readonly_audit_tasks(self, tasks, receipt):
        copied = list(tasks)
        self.calls.append((copied, receipt))
        if not self.ok:
            return {"ok": False, "reason": "writer_rejected", "created_task_ids": []}
        return {"ok": True, "created_task_ids": [task.task_id for task in copied]}


class _FakeReportStore:
    def __init__(self, reports=()) -> None:
        self.reports = tuple(reports)
        self.load_calls: list[str] = []

    def load_readonly_audit_reports(self, swarm_id: str):
        self.load_calls.append(swarm_id)
        return self.reports

    def store_readonly_audit_report(self, record):
        return {"ok": False, "reason": "not_used"}


class _FakeDecisionStore:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.records: list[object] = []

    def store_readonly_audit_decision(self, record):
        self.records.append(record)
        if not self.ok:
            return {"ok": False, "reason": "writer_rejected"}
        return {"ok": True, "stored": True, "idempotent": False}

    def load_latest_readonly_audit_decision(self):
        return None

    def load_readonly_audit_decision(self, decision_id: str):
        return None


class _FakeArchitectRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_architect_determination(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": dict(binding),
                "timeout_seconds": timeout_seconds,
            }
        )
        prompt_payload = json.loads(prompt)
        evidence_ref = prompt_payload["reports"][0]["evidence_refs"][0]
        content = architect_model_output(
            {"receipt_id": prompt_payload["wsp15_allocation_receipt_id"], **prompt_payload["wsp15_execution_binding"]},
            evidence_ref,
            slice_name="REDDOG_RUNTIME_RECONCILER_PHASE1",
        )
        return ArchitectModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(content, sort_keys=True),
            model_receipt_id="model-receipt-bootstrap",
            model_result_digest="sha256:model-result-bootstrap",
            review_packet={"fusion_panel_quorum": {"passed": True}},
            made_network_call=True,
            rejection_reasons=(),
            provider_call_evidence=architect_provider_call_evidence(binding),
        )


def _reports_for_bootstrap_result(
    result: RedDogMainReadonlyBootstrapResult,
    *,
    include_findings: bool = False,
) -> tuple[dict[str, object], ...]:
    reports: list[dict[str, object]] = []
    assert result.snapshot_receipt_id is not None
    for assignment_id, lane_id in zip(result.assignment_ids, DEFAULT_AUDIT_LANES):
        evidence_ref = f"file:docs/{lane_id}.md:sha256:{lane_id}:lines:1"
        findings = []
        if include_findings and lane_id == "repo_code_audit":
            findings.append(
                {
                    "finding_id": "repo-code-finding-1",
                    "claim": "Runtime reconciliation needs a follow-up slice.",
                    "wsp97_label": "OBSERVED",
                    "recommended_action": ACTION_FIX,
                    "wsp15_priority": "P0",
                    "severity": "BLOCKER",
                    "evidence_refs": [evidence_ref],
                    "next_slice_name": "REDDOG_RUNTIME_RECONCILER_PHASE1",
                }
            )
        reports.append(
            {
                "assignment_id": assignment_id,
                "lane_id": lane_id,
                "snapshot_receipt_id": result.snapshot_receipt_id,
                "summary": f"{lane_id} read-only audit evidence collected from 1 target.",
                "evidence_refs": [evidence_ref],
                "repo_mutation_performed": False,
                "execution_performed": False,
                "openclaw_enqueue_performed": False,
                "readonly_audit_performed": True,
                "report_digest": f"sha256:{lane_id}",
                "findings": findings,
            }
        )
    return tuple(reports)


def test_bootstrap_plans_default_readonly_audit_swarm_from_fresh_context() -> None:
    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.status == REDDOG_MAIN_BOOTSTRAP_READY
    assert result.snapshot_receipt_id and result.snapshot_receipt_id.startswith("sha256:")
    assert result.evidence_bundle_id and result.evidence_bundle_id.startswith("sha256:")
    assert result.wsp15_allocation_receipt is not None
    assert result.wsp15_allocation_receipt["receipt_id"].startswith("sha256:")
    assert result.wsp15_allocation_receipt["mps_total"] >= 16
    assert result.wsp15_allocation_receipt["priority"] == "P0"
    assert result.wsp15_allocation_receipt["reasoning_tier"] == "ULTRA"
    assert result.wsp15_allocation_receipt["worker_plan"]["fusion_required"] is True
    assert result.wsp15_allocation_receipt["no_model_call_performed"] is True
    assert result.determination_id and result.determination_id.startswith("sha256:")
    assert result.swarm_id and result.swarm_id.startswith("sha256:")
    assert result.assignment_count == 5
    assert result.rejection_reasons == ()
    assert result.no_model_call_performed is True
    assert result.no_worker_spawn_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_queue_mutation_performed is True
    assert result.assignment_ids
    assert result.report_collection_attempted is False
    assert result.report_collection_status is None
    assert result.report_collection_report_count == 0
    assert result.enqueue_attempted is False
    assert result.enqueue_decision is None
    assert result.enqueue_task_count == 0


def test_bootstrap_collects_existing_reports_and_skips_enqueue() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    writer = _FakeEnqueueWriter()
    store = _FakeReportStore(_reports_for_bootstrap_result(baseline))

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=store,
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=writer,
    )

    assert result.ready is True
    assert result.report_collection_attempted is True
    assert result.report_collection_status == READONLY_AUDIT_REPORT_COLLECTION_ACCEPT
    assert result.report_collection_report_count == result.assignment_count == 5
    assert result.report_bundle_id and result.report_bundle_id.startswith("sha256:")
    assert result.readonly_audit_decision_attempted is True
    assert result.readonly_audit_decision_action == ACTION_RESEARCH_MORE
    assert result.readonly_audit_decision_next_slice == DEFAULT_SEMANTIC_FINDINGS_SLICE
    assert result.readonly_audit_decision_rejection_reasons == ()
    assert result.enqueue_attempted is False
    assert writer.calls == []
    assert store.load_calls == [result.swarm_id, result.swarm_id]


def test_bootstrap_collects_semantic_findings_into_next_action_decision() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=store,
    )

    assert result.ready is True
    assert result.report_collection_status == READONLY_AUDIT_REPORT_COLLECTION_ACCEPT
    assert result.readonly_audit_decision_attempted is True
    assert result.readonly_audit_decision_action == ACTION_FIX
    assert result.readonly_audit_decision_next_slice == "REDDOG_RUNTIME_RECONCILER_PHASE1"
    assert result.readonly_audit_decision_id and result.readonly_audit_decision_id.startswith("sha256:")


def test_bootstrap_persists_accepted_next_action_decision_when_enabled() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))
    decision_store = _FakeDecisionStore()

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        persist_readonly_audit_decision=True,
        decision_store=decision_store,
    )

    assert result.ready is True
    assert result.readonly_audit_decision_action == ACTION_FIX
    assert result.readonly_audit_decision_persist_attempted is True
    assert result.readonly_audit_decision_persist_status == READONLY_AUDIT_DECISION_PERSIST_ACCEPT
    assert result.readonly_audit_decision_persist_stored is True
    assert result.readonly_audit_decision_persist_rejection_reasons == ()
    assert len(decision_store.records) == 1
    assert decision_store.records[0].action == ACTION_FIX


def test_bootstrap_runs_backend_architect_determination_when_enabled() -> None:
    runtime_binding = _architect_runtime_binding()
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        architect_model_runtime_binding_receipt_override=runtime_binding,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))
    architect_store = InMemoryArchitectDeterminationStore()
    architect_runner = _FakeArchitectRunner()

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_runner,
        architect_model_runtime_binding_receipt_override=runtime_binding,
        architect_determination_store=architect_store,
    )

    assert result.ready is True
    assert result.backend_architect_determination_attempted is True
    assert result.backend_architect_determination_status == ARCHITECT_DETERMINATION_ACCEPT
    assert result.backend_architect_determination_action == ACTION_FIX
    assert result.backend_architect_determination_next_slice == "REDDOG_RUNTIME_RECONCILER_PHASE1"
    assert result.backend_architect_determination_id
    assert result.backend_architect_determination_queue_candidate_count == 0
    assert result.backend_architect_determination_persist_stored is True
    assert result.backend_architect_determination_rejection_reasons == ()
    assert result.no_model_call_performed is False
    assert len(architect_runner.calls) == 1
    assert len(architect_store.records) == 1
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_queue_mutation_performed is True


def test_bootstrap_rejects_architect_model_selection_without_runtime_binding() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))
    architect_store = InMemoryArchitectDeterminationStore()
    architect_runner = _FakeArchitectRunner()
    model_selection = _model_selection()

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_runner,
        architect_model_selection_receipt_override=model_selection,
        architect_determination_store=architect_store,
    )

    assert result.ready is False
    assert "REJECT_ARCHITECT_DETERMINATION_MODEL_RUNTIME_BINDING_RECEIPT" in result.rejection_reasons
    assert architect_runner.calls == []
    assert architect_store.records == []


def test_bootstrap_passes_architect_runtime_binding_into_determination_lineage() -> None:
    runtime_binding = model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect",
        model_id="z-ai/glm-5.2",
        panel_model_ids=("moonshotai/kimi-k3",),
    )
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        architect_model_runtime_binding_receipt_override=runtime_binding,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))
    architect_store = InMemoryArchitectDeterminationStore()
    architect_runner = _FakeArchitectRunner()
    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_runner,
        architect_model_runtime_binding_receipt_override=runtime_binding,
        architect_determination_store=architect_store,
    )

    assert result.ready is True
    topology = architect_runner.calls[0]["binding"]["model_selection"]
    assert topology["lead_model"] == "z-ai/glm-5.2"
    assert topology["panel_models"] == ["moonshotai/kimi-k3"]
    assert architect_store.records[0].determination["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]
    assert architect_store.records[0].determination["model_runtime_binding_digest"]


def test_bootstrap_requires_architect_model_selection_for_production_runner() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        run_backend_architect_determination=True,
        architect_model_runner=None,
        architect_determination_store=InMemoryArchitectDeterminationStore(),
    )

    assert result.ready is False
    assert "missing_architect_model_runtime_binding_receipt" in result.rejection_reasons
    assert result.backend_architect_determination_attempted is False


def test_bootstrap_fails_closed_when_decision_persistence_rejects() -> None:
    baseline = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
    )
    report_store = _FakeReportStore(_reports_for_bootstrap_result(baseline, include_findings=True))
    decision_store = _FakeDecisionStore(ok=False)

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=report_store,
        persist_readonly_audit_decision=True,
        decision_store=decision_store,
    )

    assert result.ready is False
    assert result.readonly_audit_decision_persist_attempted is True
    assert result.readonly_audit_decision_persist_status == READONLY_AUDIT_DECISION_PERSIST_REJECT
    assert ReadOnlyAuditDecisionPersistReason.STORE_REJECTED in result.readonly_audit_decision_persist_rejection_reasons
    assert "readonly_audit_decision_persist_rejected" in result.rejection_reasons


def test_bootstrap_missing_reports_enqueue_when_enabled() -> None:
    writer = _FakeEnqueueWriter()

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=_FakeReportStore(()),
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=writer,
    )

    assert result.ready is True
    assert result.report_collection_attempted is True
    assert result.report_collection_status == READONLY_AUDIT_REPORT_COLLECTION_REJECT
    assert result.report_collection_report_count == 0
    assert result.report_collection_rejection_reasons
    assert result.enqueue_attempted is True
    assert result.enqueue_decision == READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT
    assert len(writer.calls) == 1


def test_bootstrap_missing_reports_not_ready_without_enqueue_authority() -> None:
    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        collect_readonly_audit_reports=True,
        report_store=_FakeReportStore(()),
    )

    assert result.ready is False
    assert result.status == REDDOG_MAIN_BOOTSTRAP_NOT_READY
    assert "readonly_audit_report_collection_rejected" in result.rejection_reasons
    assert result.report_collection_attempted is True
    assert result.report_collection_status == READONLY_AUDIT_REPORT_COLLECTION_REJECT
    assert result.enqueue_attempted is False


def test_bootstrap_enqueue_opt_in_publishes_readonly_audit_tasks() -> None:
    writer = _FakeEnqueueWriter()

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=writer,
        seen_assignment_ids=set(),
    )

    assert result.ready is True
    assert result.status == REDDOG_MAIN_BOOTSTRAP_READY
    assert len(writer.calls) == 1
    assert len(writer.calls[0][0]) == result.assignment_count == 5
    assert result.enqueue_attempted is True
    assert result.enqueue_decision == READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT
    assert result.enqueue_receipt_id and result.enqueue_receipt_id.startswith("readonly-audit-enqueue-")
    assert result.enqueue_task_count == 5
    assert result.enqueue_rejection_reasons == ()
    assert result.no_openclaw_enqueue_performed is False
    assert result.no_queue_mutation_performed is False


def test_bootstrap_memex_supply_enriches_enqueued_readonly_audit_tasks() -> None:
    writer = _FakeEnqueueWriter()
    work_state = dict(_work_state())
    work_state["worker_claims"] = [
        {
            "claim_id": "claim-1",
            "slice_id": "REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1",
            "foundup_id": "foundups_agent",
        }
    ]
    work_state["wre_queue_items"] = [
        {"queue_item_id": "queue-1", "claim_id": "claim-1", "foundup_id": "foundups_agent"}
    ]

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=work_state,
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        breadcrumbs=[
            {
                "breadcrumb_id": "crumb-1",
                "continuity_id": work_state["selected_slice"],
                "task_id": "task-1",
                "created_at": NOW,
            }
        ],
        brain_state={
            "available": True,
            "signature_digest": "sha256:brain",
            "summary_digest": "sha256:brain-summary",
            "record_count": 5,
        },
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=writer,
        memex_snapshot_supply_config={
            "foundup_id": "foundups_agent",
            "principal_id": "principal-012",
            "identity": {"foundup_id": "foundups_agent", "name": "Foundups Agent"},
            "roadmap_state": {
                "foundup_id": "foundups_agent",
                "roadmap_id": "resident-roadmap",
                "version": "1",
                "content_digest": "sha256:roadmap",
            },
        },
    )

    assert result.ready is True
    assert result.memex_snapshot_supply_attempted is True
    assert result.memex_snapshot_supply_status == "OPERATIONAL_MEMEX_SUPPLY_ACCEPT"
    assert result.memex_snapshot_supply_view_id
    assert result.memex_snapshot_supply_receipt is not None
    assert result.memex_snapshot_supply_receipt["schema_version"] == (
        "reddog_operational_memex_snapshot_supply_receipt.v1"
    )
    assert result.memex_snapshot_supply_receipt["snapshot_receipt_id"] == result.snapshot_receipt_id
    assert result.memex_snapshot_supply_receipt["assignment_count"] == result.assignment_count
    assert result.memex_snapshot_supply_receipt["receipt_id"].startswith("sha256:")
    assert result.memex_snapshot_supply_rejection_reasons == ()
    task_context = writer.calls[0][0][0].context
    assignment = task_context["assignment"]
    assert task_context["memex_view"]["foundup_id"] == "foundups_agent"
    assert task_context["memex_view"]["snapshot_id"] == result.snapshot_receipt_id
    assert assignment["principal_id"] == "principal-012"
    assert assignment["work_order_id"] == assignment["assignment_id"]
    assert assignment["memex_holoindex_generation_id"] == _fresh_holo_receipt().generation_id
    assert assignment["memex_policy_expires_at"]
    assert task_context["memex_snapshot_supply_receipt"]["no_holoindex_reindex_performed"] is True


def test_bootstrap_enqueue_rejection_is_not_ready_without_spawning_workers() -> None:
    writer = _FakeEnqueueWriter(ok=False)

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        now_iso=NOW,
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=writer,
    )

    assert result.ready is False
    assert result.status == REDDOG_MAIN_BOOTSTRAP_NOT_READY
    assert "readonly_audit_enqueue_rejected" in result.rejection_reasons
    assert ReadOnlyAuditEnqueueReason.WRITER_REJECTED in result.rejection_reasons
    assert result.enqueue_attempted is True
    assert result.enqueue_decision == READONLY_AUDIT_SWARM_ENQUEUE_REJECT
    assert result.enqueue_task_count == 0
    assert result.enqueue_rejection_reasons == (ReadOnlyAuditEnqueueReason.WRITER_REJECTED,)
    assert result.no_worker_spawn_performed is True
    assert result.no_queue_mutation_performed is True


def test_bootstrap_not_ready_without_authoritative_work_state_or_holoindex_receipt() -> None:
    result = run_reddog_main_readonly_operational_bootstrap(repo_root=REPO_ROOT)

    assert result.ready is False
    assert result.status == REDDOG_MAIN_BOOTSTRAP_NOT_READY
    assert "missing_authoritative_work_state_path" in result.rejection_reasons
    assert "missing_holoindex_freshness_receipt_path" in result.rejection_reasons
    assert result.assignment_count == 0
    assert result.wsp15_allocation_receipt is not None
    assert result.wsp15_allocation_receipt["priority"] == "P0"
    assert result.wsp15_allocation_receipt["worker_plan"]["queue_mutation_allowed"] is False
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_bootstrap_rejects_stale_holoindex_receipt() -> None:
    stale = build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha="old-head",
        generated_at=NOW,
    )

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=stale,
        now_iso=NOW,
    )

    assert result.ready is False
    assert "mandatory_source_not_fresh:holoindex" in result.rejection_reasons
    assert "holoindex:stale_repo_head_sha" in result.rejection_reasons


def test_bootstrap_loads_existing_work_state_and_holoindex_receipt_files(tmp_path: Path) -> None:
    work_state_path = tmp_path / "authoritative_work_state.json"
    work_state_path.write_text(json.dumps(_work_state(), sort_keys=True), encoding="utf-8")
    receipt_path = tmp_path / "holoindex_freshness_receipt.json"
    receipt_path.write_text(_fresh_holo_receipt().to_json(), encoding="utf-8")

    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_path=work_state_path,
        holoindex_receipt_path=receipt_path,
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.assignment_count == 5


def test_bootstrap_normalizes_and_drops_unsafe_read_targets() -> None:
    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT,
        repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        allowed_read_targets=[
            "./docs/0102_session_briefings/work_ledger.schema.json",
            "../escape.txt",
            "/absolute/path.txt",
            "docs/0102_session_briefings/work_ledger.schema.json",
        ],
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.allowed_read_targets == ("docs/0102_session_briefings/work_ledger.schema.json",)


def test_main_preflight_is_nonblocking_by_default_when_bootstrap_not_ready() -> None:
    import main

    with patch.dict(
        "os.environ",
        {
            "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
            "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "0",
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
            "HOLOINDEX_FRESHNESS_RECEIPT": "",
            "HOLOINDEX_SSD_PATH": "",
        },
        clear=False,
    ):
        assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True


def test_main_preflight_blocks_only_when_enforced_and_not_ready() -> None:
    import main

    with patch.dict(
        "os.environ",
        {
            "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
            "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "1",
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
            "HOLOINDEX_FRESHNESS_RECEIPT": "",
            "HOLOINDEX_SSD_PATH": "",
        },
        clear=False,
    ):
        assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is False


def test_main_preflight_reports_ready_without_blocking_menu(capsys) -> None:
    import main

    ready_result = RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id="sha256:snapshot",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        swarm_id="sha256:swarm",
        assignment_count=5,
        rejection_reasons=(),
        changed_paths=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        allowed_read_targets=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        readonly_audit_decision_attempted=True,
        readonly_audit_decision_action=ACTION_FIX,
        readonly_audit_decision_next_slice="REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap.run_reddog_main_readonly_operational_bootstrap",
        return_value=ready_result,
    ):
        with patch.dict("os.environ", {"REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1"}, clear=False):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True
    output = capsys.readouterr().out
    assert "decision_attempted=True" in output
    assert "decision_action=FIX" in output
    assert "decision_next_slice=REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1" in output
    assert "decision_persist_attempted=False" in output


def _e2e_result(*, accepted: bool = True):
    final_bootstrap = SimpleNamespace(
        status=REDDOG_MAIN_BOOTSTRAP_READY if accepted else REDDOG_MAIN_BOOTSTRAP_NOT_READY,
        backend_architect_determination_action=ACTION_FIX if accepted else None,
        backend_architect_determination_next_slice="REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1" if accepted else None,
        backend_architect_determination_queue_candidate_count=1 if accepted else 0,
    )
    return SimpleNamespace(
        accepted=accepted,
        status="ACCEPT" if accepted else "REJECT",
        initial_bootstrap=SimpleNamespace(status=REDDOG_MAIN_BOOTSTRAP_READY),
        final_bootstrap=final_bootstrap if accepted else None,
        task_runs=(SimpleNamespace(persist_accepted=True),) if accepted else (),
        rejection_reasons=() if accepted else ("forced_reject",),
        no_shell_command_executed=True,
        no_repo_mutation_performed=True,
        no_holoindex_reindex_performed=True,
        no_hermes_dispatch_performed=True,
        no_worktree_operation_performed=True,
        no_pr_created=True,
        no_pattern_memory_promotion_performed=True,
        no_live_foundup_enqueue_performed=True,
        coding_worker_spawned=False,
        readonly_audit_tasks_enqueued=accepted,
        readonly_audit_tasks_executed=accepted,
    )


def test_main_preflight_runs_explicit_readonly_e2e_runtime(capsys) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime."
        "run_reddog_readonly_audit_research_decision_e2e",
        return_value=_e2e_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "O:/state/work_state.json",
                "HOLOINDEX_FRESHNESS_RECEIPT": "O:/state/holo_receipt.json",
                "HOLOINDEX_SSD_PATH": "E:/HoloIndex",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["repo_root"] == REPO_ROOT
    assert mocked.call_args.kwargs["work_state_path"] == "O:/state/work_state.json"
    assert mocked.call_args.kwargs["holoindex_receipt_path"] == "O:/state/holo_receipt.json"
    output = capsys.readouterr().out
    assert "[REDDOG-BOOTSTRAP-E2E] preflight=PASS" in output
    assert "tasks=1" in output
    assert "reports_persisted=1" in output
    assert "architect_action=FIX" in output
    assert "queue_candidates=1" in output
    assert "no_repo_mutation=True" in output
    assert "no_holoindex_reindex=True" in output
    assert "coding_worker_spawned=False" in output


def test_main_preflight_e2e_runtime_reject_is_nonblocking_by_default(capsys) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime."
        "run_reddog_readonly_audit_research_decision_e2e",
        return_value=_e2e_result(accepted=False),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    output = capsys.readouterr().out
    assert "[REDDOG-BOOTSTRAP-E2E] preflight=WARN" in output
    assert "reasons=forced_reject" in output


def test_main_preflight_e2e_runtime_reject_blocks_when_enforced(capsys) -> None:
    import main

    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime."
            "run_reddog_readonly_audit_research_decision_e2e",
            return_value=_e2e_result(accepted=False),
        ),
        patch(
            "modules.infrastructure.foundups_mcp_bridge.src."
            "reddog_holoindex_main_preflight.run_interactive_owner_preflight",
            return_value=True,
        ),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is False

    output = capsys.readouterr().out
    assert "[REDDOG-BOOTSTRAP-E2E] preflight=WARN" in output
    assert "Startup blocked by REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=1" in output


def _resident_cycle_result(
    *,
    accepted: bool = True,
    architect_action: str | None = None,
    queue_candidate_count: int | None = None,
):
    action = architect_action if architect_action is not None else ("FIX" if accepted else None)
    candidates = queue_candidate_count if queue_candidate_count is not None else (1 if accepted else 0)
    return SimpleNamespace(
        accepted=accepted,
        status="DETERMINED" if accepted else "REJECT",
        intent_id="sha256:intent-main-resident",
        cycle_id="sha256:cycle-main-resident",
        snapshot_id="sha256:snapshot-main-resident" if accepted else None,
        determination_id="sha256:determination-main-resident" if accepted else None,
        swarm_id="sha256:swarm-main-resident" if accepted else None,
        task_ids=("task-1", "task-2") if accepted else (),
        task_status_counts={"completed": 2} if accepted else {},
        openclaw_claims=({"task_id": "task-1"}, {"task_id": "task-2"}) if accepted else (),
        final_bootstrap=None,
        architect_action=action,
        architect_next_slice="REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1" if accepted else None,
        architect_determination_id="sha256:architect-main-resident" if accepted else None,
        queue_candidate_count=candidates,
        duplicate_intent_reused=False,
        recovered_existing_cycle=False,
        retry_count=0,
        rejection_reasons=() if accepted else ("external_research_retriever_missing",),
        no_shell_command_executed=True,
        no_repo_mutation_performed=True,
        no_holoindex_reindex_performed=True,
        no_hermes_dispatch_performed=True,
        no_worktree_operation_performed=True,
        no_pr_created=True,
        no_pattern_memory_promotion_performed=True,
        no_live_foundup_enqueue_performed=True,
        read_only_authority_only=True,
    )


@pytest.mark.parametrize(
    ("case", "expected_reason"),
    (
        ("absent", "missing_audit_model_runtime_binding_path"),
        ("invalid", "model_runtime_binding_artifact_invalid"),
        ("wrong_surface", "audit_model_runtime_binding_surface_invalid"),
        ("same_artifact", "model_runtime_binding_artifacts_not_distinct"),
        ("oversized", "model_runtime_binding_artifact_invalid"),
        ("directory", "model_runtime_binding_artifact_invalid"),
        ("outside_root", "model_runtime_binding_artifact_outside_runtime_root"),
        ("inside_repo", "model_runtime_binding_artifact_inside_repo"),
    ),
)
def test_main_resident_runtime_artifact_preflight_rejects_before_cycle(
    tmp_path,
    monkeypatch,
    capsys,
    _valid_resident_runtime_binding_preflight,
    case,
    expected_reason,
) -> None:
    import main

    runtime_root = tmp_path / "runtime-bindings"
    runtime_root.mkdir()
    audit_path = runtime_root / "audit.json"
    architect_path = runtime_root / "architect.json"
    audit_receipt = model_runtime_binding_receipt(
        runtime_surface="reddog_readonly_audit_worker"
    )
    architect_receipt = model_runtime_binding_receipt(runtime_surface="reddog_backend_architect")
    audit_path.write_text(json.dumps(audit_receipt), encoding="utf-8")
    architect_path.write_text(json.dumps(architect_receipt), encoding="utf-8")
    env = {
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(runtime_root),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(audit_path),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(architect_path),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": str(audit_receipt["receipt_id"]),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": str(architect_receipt["receipt_id"]),
        "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED": "1",
    }
    if case == "absent":
        env.pop("REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH")
    elif case == "invalid":
        audit_path.write_text("{}", encoding="utf-8")
    elif case == "wrong_surface":
        audit_path.write_text(
            json.dumps(model_runtime_binding_receipt(runtime_surface="reddog_backend_architect")),
            encoding="utf-8",
        )
    elif case == "same_artifact":
        env["REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] = str(audit_path)
    elif case == "oversized":
        audit_path.write_text('{"padding":"' + ("x" * 1_100_000) + '"}', encoding="utf-8")
    elif case == "directory":
        audit_path.unlink()
        audit_path.mkdir()
    elif case == "outside_root":
        outside = tmp_path / "outside-audit.json"
        outside.write_text(
            json.dumps(model_runtime_binding_receipt(runtime_surface="reddog_readonly_audit_worker")),
            encoding="utf-8",
        )
        env["REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] = str(outside)
    elif case == "inside_repo":
        env["REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT"] = str(REPO_ROOT.parent)
        env["REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] = str(
            REPO_ROOT / "main.py"
        )
    monkeypatch.setattr(
        main,
        "_reddog_resident_model_runtime_bindings_from_env",
        _valid_resident_runtime_binding_preflight,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
    ) as mocked:
        with patch.dict("os.environ", env, clear=True):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is False

    mocked.assert_not_called()
    output = capsys.readouterr().out
    assert f"reason={expected_reason}" in output
    assert str(tmp_path) not in output


def test_main_resident_runtime_artifact_preflight_rejects_symlink_before_cycle(
    tmp_path,
    monkeypatch,
    capsys,
    _valid_resident_runtime_binding_preflight,
) -> None:
    import main

    runtime_root = tmp_path / "runtime-bindings"
    runtime_root.mkdir()
    target = runtime_root / "audit-target.json"
    target.write_text(
        json.dumps(model_runtime_binding_receipt(runtime_surface="reddog_readonly_audit_worker")),
        encoding="utf-8",
    )
    audit_path = runtime_root / "audit-link.json"
    try:
        audit_path.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    architect_path = runtime_root / "architect.json"
    architect_path.write_text(
        json.dumps(model_runtime_binding_receipt(runtime_surface="reddog_backend_architect")),
        encoding="utf-8",
    )
    env = {
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(runtime_root),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(audit_path),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(architect_path),
        "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED": "1",
    }
    monkeypatch.setattr(
        main,
        "_reddog_resident_model_runtime_bindings_from_env",
        _valid_resident_runtime_binding_preflight,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
    ) as mocked:
        with patch.dict("os.environ", env, clear=True):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is False

    mocked.assert_not_called()
    output = capsys.readouterr().out
    assert "reason=model_runtime_binding_artifact_invalid" in output
    assert str(tmp_path) not in output

def test_main_preflight_durable_resident_cycle_disabled_is_inert() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
    ) as mocked:
        with patch.dict(
            "os.environ",
            {"REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "0"},
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    mocked.assert_not_called()


def test_main_preflight_durable_resident_cycle_product_mode_runs_by_default(capsys) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict("os.environ", MAIN_RESIDENT_AUTH_ENV, clear=True):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert os.environ["REDDOG_RESIDENT_ARCHITECT_INTENT_ID"] == "sha256:intent-main-resident"
            assert os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] == "1"
            assert (
                os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"]
                == "signed_0102_bounded_code_fusion_worktree_draft_pr"
            )

    kwargs = mocked.call_args.kwargs
    assert kwargs["requested_operation"] == "main_resident_architect_cycle"
    assert "reddog_resident_architect_durable_agentdb_cycle.py" in kwargs["prompt_text"]
    assert kwargs["audit_model_runtime_binding_receipt"]["runtime_surface"] == (
        "reddog_readonly_audit_worker"
    )
    assert kwargs["architect_model_runtime_binding_receipt"]["runtime_surface"] == (
        "reddog_backend_architect"
    )
    assert (
        kwargs["audit_model_runtime_binding_receipt"]["receipt_id"]
        != kwargs["architect_model_runtime_binding_receipt"]["receipt_id"]
    )
    assert kwargs["external_research_retriever"] is None
    assert kwargs["red_dog_intent"]["schema_version"] == "reddog_intent.v2"
    assert kwargs["red_dog_intent"]["source_surface"] == "main_resident_host"
    assert kwargs["red_dog_intent"]["origin"] == "main.py"
    assert kwargs["red_dog_intent"]["submits_executable_authority"] is False
    assert kwargs["red_dog_intent"]["client_request_id"].startswith("sha256:")
    output = capsys.readouterr().out
    assert "[REDDOG-RESIDENT-CYCLE] preflight=PASS" in output
    assert "no_repo_mutation=True" in output
    assert "no_holoindex_reindex=True" in output
    assert "no_hermes_dispatch=True" in output
    assert "no_worktree=True" in output
    assert "no_pr=True" in output


def test_main_preflight_durable_resident_cycle_product_mode_can_opt_out() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
    ) as mocked:
        with patch.dict(
            "os.environ",
            {"REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE": "0"},
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    mocked.assert_not_called()


def test_main_preflight_durable_resident_cycle_explicit_enable_overrides_product_mode_off() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE": "0",
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    mocked.assert_called_once()


def test_main_preflight_durable_resident_cycle_uses_stable_cadence_bucket() -> None:
    import main

    calls = []
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        side_effect=lambda **kwargs: calls.append(kwargs) or _resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_NOW_ISO": "2026-07-17T09:00:00+00:00",
                "REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS": "24",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_NOW_ISO": "2026-07-17T18:00:00+00:00",
                "REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS": "24",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    first = calls[0]["red_dog_intent"]
    second = calls[1]["red_dog_intent"]
    assert first["client_request_id"] == second["client_request_id"]
    assert first["intent_id"] == second["intent_id"]


def test_main_preflight_durable_resident_cycle_rolls_intent_after_cadence() -> None:
    import main

    calls = []
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        side_effect=lambda **kwargs: calls.append(kwargs) or _resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_NOW_ISO": "2026-07-17T09:00:00+00:00",
                "REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS": "24",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_NOW_ISO": "2026-07-18T09:00:01+00:00",
                "REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS": "24",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    first = calls[0]["red_dog_intent"]
    second = calls[1]["red_dog_intent"]
    assert first["client_request_id"] != second["client_request_id"]
    assert first["intent_id"] != second["intent_id"]


def test_main_preflight_durable_resident_cycle_explicit_intent_disables_cadence_bucket() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "explicit-request",
                    "REDDOG_RESIDENT_ARCHITECT_NOW_ISO": "2026-07-17T09:00:00+00:00",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    intent = mocked.call_args.kwargs["red_dog_intent"]
    assert intent["schema_version"] == "reddog_intent.v2"
    assert intent["client_request_id"] == "explicit-request"


def test_main_preflight_durable_resident_cycle_can_disable_cadence_for_legacy_sticky_intent() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {**MAIN_RESIDENT_AUTH_ENV, "REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS": "0"},
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    intent = mocked.call_args.kwargs["red_dog_intent"]
    assert intent["schema_version"] == "reddog_intent.v2"


def test_main_preflight_runs_durable_resident_agentdb_cycle_when_enabled(tmp_path, capsys) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED": "0",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                    "REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS": (
                        "Audit modules/communication/moltbot_bridge/src/"
                        "reddog_resident_architect_client.py."
                    ),
                    "REDDOG_RESIDENT_ARCHITECT_PRINCIPAL_REF": "principal-main-test",
                "REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID": "foundups_agent",
                "REDDOG_RESIDENT_ARCHITECT_MAX_CLAIMS": "2",
                "REDDOG_RESIDENT_ARCHITECT_TIMEOUT_SECONDS": "30",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "O:/state/work_state.json",
                "HOLOINDEX_FRESHNESS_RECEIPT": "O:/state/holo_receipt.json",
                "HOLOINDEX_SSD_PATH": "E:/HoloIndex",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert os.environ["REDDOG_RESIDENT_ARCHITECT_INTENT_ID"] == "sha256:intent-main-resident"
            assert os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] == "1"
            assert (
                os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"]
                == "signed_0102_bounded_code_fusion_worktree_draft_pr"
            )

    kwargs = mocked.call_args.kwargs
    assert kwargs["repo_root"] == REPO_ROOT
    assert kwargs["work_state_path"] == "O:/state/work_state.json"
    assert kwargs["holoindex_receipt_path"] == "O:/state/holo_receipt.json"
    assert kwargs["holoindex_ssd_path"] == "E:/HoloIndex"
    assert kwargs["requested_operation"] == "main_resident_architect_cycle"
    assert "reddog_resident_architect_client.py" in kwargs["prompt_text"]
    assert kwargs["max_claims"] == 2
    assert kwargs["timeout_seconds"] == 30
    assert kwargs["external_research_retriever"] is not None
    intent = kwargs["red_dog_intent"]
    assert intent["schema_version"] == "reddog_intent.v2"
    assert intent["source_surface"] == "main_resident_host"
    assert intent["origin"] == "main.py"
    assert intent["principal_ref"] == "principal-main-test"
    assert intent["submits_executable_authority"] is False
    output = capsys.readouterr().out
    assert "[REDDOG-RESIDENT-CYCLE] preflight=PASS" in output
    assert "tasks=2" in output
    assert "completed=2" in output
    assert "architect_action=FIX" in output
    assert "queue_candidates=1" in output
    assert "auto_fix_handoff=True" in output
    assert "auto_queue_profile=signed_0102_bounded_code_fusion_worktree_draft_pr" in output
    assert "read_only_authority=True" in output
    assert "no_repo_mutation=True" in output
    assert "no_holoindex_reindex=True" in output


def test_main_preflight_durable_resident_cycle_supplies_memory_context(tmp_path, capsys) -> None:
    import main

    brain_state = tmp_path / "brain_artifact_state.json"
    brain_state.write_text(
        json.dumps(
            {
                "updated_at": "2026-07-17T00:00:00+00:00",
                "signature": {"conversation_count": 7, "revision_files": 11},
                "summary": {"total_artifacts": 13},
                "conversations": 7,
            }
        ),
        encoding="utf-8",
    )
    breadcrumbs = tmp_path / "breadcrumbs.json"
    breadcrumbs.write_text(
        json.dumps(
            {
                "breadcrumbs": [
                    {"breadcrumb_id": "crumb-1", "continuity_id": "foundups_agent", "task_id": "task-1"},
                    {"breadcrumb_id": "crumb-2", "continuity_id": "foundups_agent", "task_id": "task-2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    workspace_notes = tmp_path / "workspace_memory.json"
    workspace_notes.write_text(
        json.dumps({"notes": [{"note_id": "note-1", "topic": "resident RedDog"}]}),
        encoding="utf-8",
    )

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_BRAIN_STATE_PATH": str(brain_state),
                "REDDOG_RESIDENT_BREADCRUMBS_PATH": str(breadcrumbs),
                "REDDOG_RESIDENT_WORKSPACE_MEMORY_NOTES_PATH": str(workspace_notes),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    kwargs = mocked.call_args.kwargs
    assert kwargs["brain_state"]["record_count"] == 7
    assert kwargs["brain_state"]["signature_digest"].startswith("sha256:")
    assert len(kwargs["breadcrumbs"]) == 2
    assert kwargs["breadcrumbs"][0]["breadcrumb_id"] == "crumb-1"
    assert len(kwargs["workspace_memory_notes"]) == 1
    assert kwargs["workspace_memory_notes"][0]["note_id"] == "note-1"
    output = capsys.readouterr().out
    assert "brain_records=7" in output
    assert "breadcrumbs=2" in output
    assert "workspace_memory=1" in output


def test_main_preflight_durable_resident_cycle_memory_context_can_be_disabled() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ) as mocked:
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_BRAIN_CONTEXT": "0",
                "REDDOG_RESIDENT_BREADCRUMBS_CONTEXT": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    kwargs = mocked.call_args.kwargs
    assert kwargs["brain_state"] is None
    assert kwargs["breadcrumbs"] == ()
    assert kwargs["workspace_memory_notes"] == ()


def test_main_preflight_resident_cycle_respects_explicit_queue_profile(tmp_path) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] == "signed_0102_bounded_code"


def test_main_preflight_resident_cycle_can_disable_auto_queue_profile(tmp_path) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE": "0",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ


def test_main_preflight_resident_cycle_rejects_invalid_auto_queue_profile(tmp_path, capsys) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE": "unsafe_profile",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ

    output = capsys.readouterr().out
    assert "auto_queue_profile=(none)" in output


def test_main_preflight_resident_cycle_requires_fix_queue_candidate_for_auto_profile(tmp_path) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(architect_action="STOP", queue_candidate_count=1),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(architect_action="FIX", queue_candidate_count=0),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ


def test_main_preflight_resident_cycle_respects_auto_fix_handoff_opt_out(tmp_path) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF": "0",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ


def test_main_preflight_resident_cycle_does_not_override_explicit_fix_handoff(tmp_path) -> None:
    import main

    external_snapshot = tmp_path / "external_research_snapshot.json"
    external_snapshot.write_text(json.dumps({"snapshots": []}), encoding="utf-8")
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
                "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                "REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH": str(external_snapshot),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True
            assert os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] == "0"


def test_main_preflight_resident_cycle_reject_is_nonblocking_by_default(capsys) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(accepted=False),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED": "0",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is True

    output = capsys.readouterr().out
    assert "[REDDOG-RESIDENT-CYCLE] preflight=WARN" in output
    assert "reasons=external_research_retriever_missing" in output


def test_main_preflight_resident_cycle_reject_blocks_when_enforced(capsys) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle."
        "run_reddog_resident_architect_durable_agentdb_cycle",
        return_value=_resident_cycle_result(accepted=False),
    ):
        with patch.dict(
            "os.environ",
                {
                    **MAIN_RESIDENT_AUTH_ENV,
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE": "1",
                    "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED": "1",
                    "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID": "request-main-resident",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT) is False

    output = capsys.readouterr().out
    assert "[REDDOG-RESIDENT-CYCLE] preflight=WARN" in output
    assert "Startup blocked by REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED=1" in output


def test_main_preflight_enables_enqueue_when_openclaw_auto_tasks_enabled() -> None:
    import main

    ready_result = RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id="sha256:snapshot",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        swarm_id="sha256:swarm",
        assignment_count=5,
        rejection_reasons=(),
        changed_paths=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        allowed_read_targets=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap.run_reddog_main_readonly_operational_bootstrap",
        return_value=ready_result,
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                **OWNER_SERVICE_ENV,
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is True
    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is True
    assert mocked.call_args.kwargs["persist_readonly_audit_decision"] is True


def test_main_preflight_explicit_enqueue_disable_overrides_openclaw_auto_tasks() -> None:
    import main

    ready_result = RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id="sha256:snapshot",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        swarm_id="sha256:swarm",
        assignment_count=5,
        rejection_reasons=(),
        changed_paths=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        allowed_read_targets=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap.run_reddog_main_readonly_operational_bootstrap",
        return_value=ready_result,
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is False
    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is True
    assert mocked.call_args.kwargs["persist_readonly_audit_decision"] is True


def test_main_preflight_explicit_collection_disable_overrides_openclaw_auto_tasks() -> None:
    import main

    ready_result = RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id="sha256:snapshot",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        swarm_id="sha256:swarm",
        assignment_count=5,
        rejection_reasons=(),
        changed_paths=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        allowed_read_targets=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap.run_reddog_main_readonly_operational_bootstrap",
        return_value=ready_result,
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is False
    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is True
    assert mocked.call_args.kwargs["persist_readonly_audit_decision"] is True


def test_main_preflight_explicit_decision_persist_disable_overrides_openclaw_auto_tasks() -> None:
    import main

    ready_result = RedDogMainReadonlyBootstrapResult(
        ready=True,
        status=REDDOG_MAIN_BOOTSTRAP_READY,
        snapshot_receipt_id="sha256:snapshot",
        context_view_id="sha256:view",
        evidence_bundle_id="sha256:evidence",
        determination_id="sha256:determination",
        swarm_id="sha256:swarm",
        assignment_count=5,
        rejection_reasons=(),
        changed_paths=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
        allowed_read_targets=DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    )
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap.run_reddog_main_readonly_operational_bootstrap",
        return_value=ready_result,
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                **OWNER_SERVICE_ENV,
                "REDDOG_READONLY_AUDIT_DECISION_PERSIST_ENABLED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is True
    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is True
    assert mocked.call_args.kwargs["persist_readonly_audit_decision"] is False


def test_bootstrap_module_has_no_runtime_mutation_or_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_import_roots = {
        "subprocess",
        "requests",
        "httpx",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
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
                assert alias.name.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            assert name not in forbidden_calls
