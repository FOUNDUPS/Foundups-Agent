"""Tests for REDDOG_WORK_STATE_AUTHORITATIVE_GROUNDING_GATE_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_query import (
    STATUS_NOT_READY,
    STATUS_READY,
    query_authoritative_work_state,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authoritative_work_state_query.py"
)
BRIDGE_PATH = REPO_ROOT / "scripts" / "reddog_authoritative_work_state_query_once.py"
NOW = "2026-07-25T02:00:00+00:00"
SLICE = "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
QUEUE_ITEM_ID = "queue-reddog-next"


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _snapshot() -> dict:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="implement_reddog_slice",
        prompt_text="Implement the next governed RedDog operational slice",
        changed_paths=("extensions/reddog/extension.js",),
        allowed_read_targets=("extensions/reddog/extension.js",),
    ).to_dict()
    claim_id = "claim-reddog-next"
    freshness_id = "sha256:freshness"
    determination_id = "sha256:determination"
    selection_id = "sha256:model-selection"
    memex_id = "sha256:memex-supply"
    queue = {
        "queue_item_id": QUEUE_ITEM_ID,
        "slice_id": SLICE,
        "claim_id": claim_id,
        "worker_id": "openclaw-audit-worker",
        "status": "QUEUED",
        "no_execution_performed": True,
        "wsp15_allocation_receipt": allocation,
        "source_determination_receipt_id": determination_id,
        "model_selection_receipt_id": selection_id,
        "model_selection_digest": "sha256:model-selection-digest",
        "memex_supply_receipt_id": memex_id,
        "memex_supply_digest": "sha256:memex-supply-digest",
        "evidence_refs": [
            f"claim:{claim_id}",
            f"freshness:{freshness_id}",
            f"wsp15_allocation:{allocation['receipt_id']}",
            f"architect_determination:{determination_id}",
            f"model_selection:{selection_id}",
            f"memex_supply:{memex_id}",
        ],
    }
    snapshot = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "updated_at": NOW,
        "selected_slice": SLICE,
        "freshness_receipts": [{"receipt_id": freshness_id, "fresh": True}],
        "worker_claims": [
            {
                "claim_id": claim_id,
                "slice_id": SLICE,
                "worker_id": "openclaw-audit-worker",
                "status": "ACTIVE",
                "expires_at": "2026-07-25T03:00:00+00:00",
                "freshness_receipt_id": freshness_id,
                "lane_id": "reddog_operational",
                "reconciliation_report_id": "sha256:reconciliation",
                "source_determination_receipt_id": determination_id,
                "model_selection_receipt_id": selection_id,
                "memex_supply_receipt_id": memex_id,
            }
        ],
        "wre_queue_items": [queue],
        "no_holoindex_mutation_performed": True,
        "no_worker_spawn_performed": True,
        "no_execution_performed": True,
    }
    snapshot["revision"] = _digest(snapshot)
    return snapshot


def _write_snapshot(tmp_path: Path, snapshot: dict) -> Path:
    path = tmp_path / "authoritative_work_state.json"
    path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
    return path


def test_valid_snapshot_returns_governed_read_only_receipt(tmp_path: Path) -> None:
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, _snapshot()),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == STATUS_READY
    assert result.selected_slice == SLICE
    assert result.queue_item_id == "queue-reddog-next"
    assert result.wsp15_priority in {"P0", "P1", "P2", "P3", "P4"}
    assert result.wsp15_mps_total is not None
    repeated = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, _snapshot()),
        now_iso=NOW,
    )
    assert result.receipt_id == repeated.receipt_id
    assert result.receipt_id == _digest(
        {key: value for key, value in result.to_dict().items() if key != "receipt_id"}
    )
    assert result.no_model_call_performed is True
    assert result.no_holoindex_query_performed is True
    assert result.no_queue_mutation_performed is True
    assert result.no_execution_performed is True


def test_changed_content_with_old_revision_fails_closed(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot["selected_slice"] = "TAMPERED"
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == STATUS_NOT_READY
    assert "authoritative_work_state_revision_invalid" in result.rejection_reasons


def test_stale_snapshot_fails_before_queue_acceptance(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot["updated_at"] = "2026-07-24T00:00:00+00:00"
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "authoritative_work_state_stale" in result.rejection_reasons
    assert result.queue_consumer_receipt_id is None


def test_selected_slice_mismatch_fails_closed(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot["selected_slice"] = "OTHER_SLICE"
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
        requested_queue_item_id=QUEUE_ITEM_ID,
    )

    assert result.accepted is False
    assert "selected_slice_snapshot_mismatch" in result.rejection_reasons


def test_selected_slice_ignores_other_queued_lanes(tmp_path: Path) -> None:
    snapshot = _snapshot()
    unrelated = dict(snapshot["wre_queue_items"][0])
    unrelated["queue_item_id"] = "queue-unrelated"
    unrelated["slice_id"] = "UNRELATED_SLICE"
    snapshot["wre_queue_items"].insert(0, unrelated)
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.queue_item_id == "queue-reddog-next"


def test_ambiguous_selected_slice_queue_fails_closed(tmp_path: Path) -> None:
    snapshot = _snapshot()
    duplicate = dict(snapshot["wre_queue_items"][0])
    duplicate["queue_item_id"] = "queue-reddog-next-duplicate"
    snapshot["wre_queue_items"].append(duplicate)
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "selected_slice_queue_ambiguous" in result.rejection_reasons


def test_canonical_wsp15_validation_is_required(tmp_path: Path) -> None:
    snapshot = _snapshot()
    allocation = snapshot["wre_queue_items"][0]["wsp15_allocation_receipt"]
    allocation["mps_total"] = 4
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert any(reason.startswith("wsp15_allocation:") for reason in result.rejection_reasons)


def test_missing_governed_lineage_is_rejected(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot["wre_queue_items"][0].pop("memex_supply_receipt_id")
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=_write_snapshot(tmp_path, snapshot),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert any("QUEUE_GOVERNED_LINEAGE" in reason for reason in result.rejection_reasons)


def test_repo_internal_state_path_is_rejected() -> None:
    result = query_authoritative_work_state(
        repo_root=REPO_ROOT,
        work_state_path=REPO_ROOT / "README.md",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("work_state_path_inside_repo",)


def test_runtime_module_has_no_mutation_or_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "subprocess" not in imported
    assert "sqlite3" not in imported
    assert "requests" not in imported
    assert "httpx" not in imported


def test_one_shot_bridge_uses_environment_state_path(tmp_path: Path) -> None:
    snapshot = _snapshot()
    now = datetime.now(timezone.utc)
    snapshot["updated_at"] = now.isoformat()
    snapshot["worker_claims"][0]["expires_at"] = (now + timedelta(hours=1)).isoformat()
    snapshot["revision"] = _digest({key: value for key, value in snapshot.items() if key != "revision"})
    path = _write_snapshot(tmp_path, snapshot)
    env = dict(os.environ)
    env["REDDOG_AUTHORITATIVE_WORK_STATE_PATH"] = str(path)

    completed = subprocess.run(
        [sys.executable, "-B", str(BRIDGE_PATH)],
        cwd=REPO_ROOT,
        input=json.dumps({"repo_root": str(REPO_ROOT)}),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    receipt = json.loads(completed.stdout)

    assert receipt["accepted"] is True
    assert receipt["selected_slice"] == SLICE
    assert receipt["no_model_call_performed"] is True
