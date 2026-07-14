"""Tests for REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from holo_index.freshness_receipt import CollectionFreshness, HoloIndexFreshnessReceipt
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
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ACTION_FIX,
    ACTION_RESEARCH_MORE,
    DEFAULT_SEMANTIC_FINDINGS_SLICE,
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
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha=HEAD,
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=4,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
            ),
            CollectionFreshness(
                name="navigation_symbols",
                count=9,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
            ),
        ],
    )


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
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_bootstrap_rejects_stale_holoindex_receipt() -> None:
    stale = HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha="old-head",
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=4,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha="old-head",
                last_indexed_at=NOW,
            ),
            CollectionFreshness(
                name="navigation_symbols",
                count=9,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha="old-head",
                last_indexed_at=NOW,
            ),
        ],
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


def test_main_preflight_reports_ready_without_blocking_menu() -> None:
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
    ):
        with patch.dict("os.environ", {"REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1"}, clear=False):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True


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
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is True
    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is True


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
                "REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is False
    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is True


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
                "REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_readonly_operational_bootstrap_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["collect_readonly_audit_reports"] is False
    assert mocked.call_args.kwargs["enqueue_readonly_audit_tasks"] is True


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
