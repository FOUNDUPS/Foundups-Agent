"""Tests for REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src import (
    reddog_wre_queue_consumer_dryrun as consumer,
)
from modules.communication.moltbot_bridge.src.reddog_main_wre_queue_consumer_bootstrap import (
    REDDOG_WRE_QUEUE_BOOTSTRAP_READY,
    run_reddog_main_wre_queue_consumer_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_consumer_dryrun.py"
)
BOOTSTRAP_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_wre_queue_consumer_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"


def _allocation_receipt():
    return {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation",
        "mps_total": 18,
        "priority": "P0",
        "reasoning_tier": "ULTRA",
        "worker_plan": {
            "fusion_required": True,
            "independent_verifier_required": True,
            "queue_mutation_allowed": False,
            "hermes_execution_allowed": False,
        },
    }


def _snapshot(**overrides):
    claim_id = "claim-1"
    freshness_id = "fresh-1"
    allocation = _allocation_receipt()
    determination_id = "sha256:determination"
    selection_id = "sha256:model-selection"
    runtime_id = "reddog_model_runtime_binding:abc123"
    memex_id = "sha256:memex-supply"
    base = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": "sha256:revision",
        "freshness_receipts": [
            {
                "receipt_id": freshness_id,
                "fresh": True,
            }
        ],
        "worker_claims": [
            {
                "claim_id": claim_id,
                "slice_id": "REDDOG_SAMPLE_SLICE_PHASE1",
                "worker_id": "reddog-main-bootstrap",
                "status": "ACTIVE",
                "expires_at": "2026-07-14T01:00:00+00:00",
                "freshness_receipt_id": freshness_id,
                "lane_id": "reddog_operational",
                "reconciliation_report_id": "sha256:reconciliation",
                "source_determination_receipt_id": determination_id,
                "model_selection_receipt_id": selection_id,
                "model_runtime_binding_receipt_id": runtime_id,
                "memex_supply_receipt_id": memex_id,
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_SAMPLE_SLICE_PHASE1",
                "claim_id": claim_id,
                "worker_id": "reddog-main-bootstrap",
                "status": "QUEUED",
                "enqueued_at": NOW,
                "evidence_refs": [
                    f"claim:{claim_id}",
                    f"freshness:{freshness_id}",
                    f"wsp15_allocation:{allocation['receipt_id']}",
                    f"architect_determination:{determination_id}",
                    f"model_selection:{selection_id}",
                    f"model_runtime_binding:{runtime_id}",
                    f"memex_supply:{memex_id}",
                ],
                "wsp15_allocation_receipt": allocation,
                "source_determination_receipt_id": determination_id,
                "model_selection_receipt_id": selection_id,
                "model_selection_digest": "sha256:model-selection",
                "model_runtime_binding_receipt_id": runtime_id,
                "model_runtime_binding_digest": "sha256:model-runtime-binding",
                "memex_supply_receipt_id": memex_id,
                "memex_supply_digest": "sha256:memex-supply",
                "no_execution_performed": True,
            }
        ],
        "no_holoindex_mutation_performed": True,
        "no_worker_spawn_performed": True,
        "no_execution_performed": True,
    }
    base.update(overrides)
    return base


def test_accepts_one_fresh_queued_item_without_execution() -> None:
    result = consumer.plan_reddog_wre_queue_consumer_dry_run(_snapshot(), now_iso=NOW)

    assert result.accepted is True
    assert result.status == consumer.WRE_QUEUE_CONSUMER_DRYRUN_READY
    assert result.selected_queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_SAMPLE_SLICE_PHASE1"
    assert result.next_required_gate == consumer.NEXT_GATE_SIGNED_AUTHORITY_REQUIRED
    assert result.execution_ready is False
    assert result.receipt is not None
    assert result.receipt.wsp15_allocation_receipt_id == "sha256:wsp15-allocation"
    assert result.receipt.wsp15_allocation_digest.startswith("sha256:")
    assert result.receipt.wsp15_priority == "P0"
    assert result.receipt.wsp15_mps_total == 18
    assert result.receipt.reasoning_tier == "ULTRA"
    assert result.receipt.model_selection_receipt_id == "sha256:model-selection"
    assert result.receipt.model_selection_digest == "sha256:model-selection"
    assert result.receipt.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:abc123"
    assert result.receipt.model_runtime_binding_digest == "sha256:model-runtime-binding"
    assert result.receipt.memex_supply_receipt_id == "sha256:memex-supply"
    assert result.receipt.memex_supply_digest == "sha256:memex-supply"
    assert result.receipt.no_queue_mutation_performed is True
    assert result.receipt.no_worker_spawn_performed is True
    assert result.receipt.no_worktree_created is True
    assert result.receipt.no_shell_command_executed is True
    assert result.receipt.no_openclaw_enqueue_performed is True
    assert result.receipt.no_hermes_dispatch_performed is True
    assert result.receipt.no_repo_mutation_performed is True
    assert result.receipt.no_holoindex_reindex_performed is True
    assert result.receipt.no_pr_created is True
    assert result.receipt.no_reward_settlement_performed is True


def test_rejects_malformed_schema_before_queue_selection() -> None:
    snapshot = _snapshot(schema_version="wrong")

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_SCHEMA_VERSION in result.rejection_reasons


def test_rejects_missing_queue_item() -> None:
    snapshot = _snapshot(wre_queue_items=[])

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert result.rejection_reasons == [consumer.FAIL_NO_QUEUE_ITEM]


def test_rejects_requested_queue_item_not_found() -> None:
    result = consumer.plan_reddog_wre_queue_consumer_dry_run(
        _snapshot(),
        now_iso=NOW,
        requested_queue_item_id="missing",
    )

    assert result.accepted is False
    assert consumer.FAIL_REQUESTED_QUEUE_NOT_FOUND in result.rejection_reasons


def test_rejects_non_queued_status_and_prior_execution() -> None:
    snapshot = _snapshot()
    snapshot["wre_queue_items"][0]["status"] = "RUNNING"
    snapshot["wre_queue_items"][0]["no_execution_performed"] = False

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is False
    assert consumer.FAIL_QUEUE_ITEM_STATUS in result.rejection_reasons
    assert consumer.FAIL_QUEUE_ALREADY_EXECUTED in result.rejection_reasons


def test_rejects_missing_claim() -> None:
    snapshot = _snapshot(worker_claims=[])

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_CLAIM_MISSING in result.rejection_reasons


def test_rejects_claim_mismatch() -> None:
    snapshot = _snapshot()
    snapshot["worker_claims"][0]["worker_id"] = "other-worker"

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_QUEUE_CLAIM_MISMATCH in result.rejection_reasons


def test_rejects_expired_claim() -> None:
    snapshot = _snapshot()
    snapshot["worker_claims"][0]["expires_at"] = "2026-07-13T23:59:59+00:00"

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_CLAIM_EXPIRED in result.rejection_reasons


def test_rejects_stale_freshness_receipt() -> None:
    snapshot = _snapshot()
    snapshot["freshness_receipts"][0]["fresh"] = False

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_FRESHNESS_RECEIPT in result.rejection_reasons


def test_rejects_missing_queue_evidence_refs() -> None:
    snapshot = _snapshot()
    snapshot["wre_queue_items"][0]["evidence_refs"] = ["claim:claim-1"]

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_QUEUE_EVIDENCE_REFS in result.rejection_reasons


def test_rejects_missing_wsp15_allocation_receipt() -> None:
    snapshot = _snapshot()
    snapshot["wre_queue_items"][0].pop("wsp15_allocation_receipt")

    result = consumer.plan_reddog_wre_queue_consumer_dry_run(snapshot, now_iso=NOW)

    assert result.accepted is False
    assert consumer.FAIL_WSP15_ALLOCATION_RECEIPT in result.rejection_reasons


def test_bootstrap_loads_work_state_outside_repo(tmp_path: Path) -> None:
    path = tmp_path / "authoritative_work_state.json"
    path.write_text(json.dumps(_snapshot()), encoding="utf-8")

    result = run_reddog_main_wre_queue_consumer_bootstrap(
        repo_root=REPO_ROOT,
        work_state_path=path,
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.status == REDDOG_WRE_QUEUE_BOOTSTRAP_READY
    assert result.queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_SAMPLE_SLICE_PHASE1"
    assert result.next_required_gate == consumer.NEXT_GATE_SIGNED_AUTHORITY_REQUIRED
    assert result.execution_ready is False
    assert result.receipt_id is not None


def test_bootstrap_rejects_work_state_inside_repo() -> None:
    result = run_reddog_main_wre_queue_consumer_bootstrap(
        repo_root=REPO_ROOT,
        work_state_path=REPO_ROOT / "inside-repo.json",
        now_iso=NOW,
    )

    assert result.ready is False
    assert "work_state_path_inside_repo" in result.rejection_reasons


def test_main_queue_consumer_preflight_passes_when_bootstrap_ready(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_wre_queue_consumer_bootstrap.run_reddog_main_wre_queue_consumer_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": True,
                "status": REDDOG_WRE_QUEUE_BOOTSTRAP_READY,
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_SAMPLE_SLICE_PHASE1",
                "next_required_gate": consumer.NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
                "execution_ready": False,
                "rejection_reasons": (),
                "receipt_id": "receipt-1",
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_WRE_QUEUE_CONSUMER_DRYRUN": "1",
                "REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_ENFORCED": "0",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
            },
            clear=False,
        ):
            assert main.run_reddog_wre_queue_consumer_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(tmp_path / "state.json")


def test_main_queue_consumer_preflight_profile_derives_work_state_path(tmp_path: Path) -> None:
    import main

    runtime_root = tmp_path / "resident-runtime"
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_wre_queue_consumer_bootstrap.run_reddog_main_wre_queue_consumer_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": True,
                "status": REDDOG_WRE_QUEUE_BOOTSTRAP_READY,
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_SAMPLE_SLICE_PHASE1",
                "next_required_gate": consumer.NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
                "execution_ready": False,
                "rejection_reasons": (),
                "receipt_id": "receipt-1",
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_WRE_QUEUE_CONSUMER_DRYRUN": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_wre_queue_consumer_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(
        runtime_root / "authoritative_work_state.json"
    )
    assert not runtime_root.exists()


def test_main_queue_consumer_preflight_blocks_when_enforced() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_wre_queue_consumer_bootstrap.run_reddog_main_wre_queue_consumer_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": False,
                "status": "REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY",
                "queue_item_id": None,
                "selected_slice": None,
                "next_required_gate": None,
                "execution_ready": False,
                "rejection_reasons": ("missing_authoritative_work_state_path",),
                "receipt_id": None,
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_WRE_QUEUE_CONSUMER_DRYRUN": "1",
                "REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_ENFORCED": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
            },
            clear=False,
        ):
            assert main.run_reddog_wre_queue_consumer_preflight(REPO_ROOT) is False


def test_modules_have_no_shell_network_git_execution_or_holoindex_mutation_imports() -> None:
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for path in (MODULE_PATH, BOOTSTRAP_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".", 1)[0] not in banned_import_roots
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] not in banned_import_roots
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
