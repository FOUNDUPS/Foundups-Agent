"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_ORCHESTRATION_PLAN_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap import (
    REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY,
    REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY,
    run_reddog_main_resident_queue_orchestration_plan_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    with_queue_wsp15_allocation,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_resident_queue_orchestration_plan_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot() -> dict[str, object]:
    queue_item = with_queue_wsp15_allocation(
        {
            "queue_item_id": "queue-1",
            "slice_id": "REDDOG_TEST_SLICE_PHASE1",
            "claim_id": "claim-1",
            "worker_id": "reddog-0102",
            "status": "QUEUED",
            "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
            "no_execution_performed": True,
        },
        prompt_text="RedDog main resident queue orchestration plan bootstrap worktree authority",
    )
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [queue_item],
    }


def _write_runtime_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def test_bootstrap_reports_next_bridge_from_authoritative_snapshot(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=state,
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.status == REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY
    assert result.queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_TEST_SLICE_PHASE1"
    assert result.current_stage == "authority_request"
    assert result.next_action == NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN
    assert result.accepted_stage_count == 1
    assert result.chain_complete is False
    assert result.no_bridge_invoked is True
    assert result.no_holoindex_reindex_performed is True


def test_bootstrap_uses_chain_results_to_advance_next_bridge(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    chain = _write_runtime_json(
        tmp_path,
        "chain_results.json",
        {"authority_request": {"status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"}},
    )

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.next_action == NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    assert result.current_stage == "authority_runtime"
    assert result.accepted_stage_count == 2


def test_bootstrap_rejects_missing_work_state_path() -> None:
    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=REPO_ROOT,
        work_state_path=None,
        now_iso=NOW,
    )

    assert result.ready is False
    assert result.status == REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY
    assert "missing_authoritative_work_state_path" in result.rejection_reasons


def test_bootstrap_rejects_work_state_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside = repo / "work_state.json"
    inside.write_text(json.dumps(_snapshot()), encoding="utf-8")

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=inside,
        now_iso=NOW,
    )

    assert result.ready is False
    assert "work_state_path_inside_repo" in result.rejection_reasons


def test_bootstrap_rejects_chain_results_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    inside_chain = repo / "chain_results.json"
    inside_chain.write_text("{}", encoding="utf-8")

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=inside_chain,
        now_iso=NOW,
    )

    assert result.ready is False
    assert "chain_results_path_inside_repo" in result.rejection_reasons


def test_bootstrap_rejects_malformed_chain_results(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    chain = _write_runtime_json(tmp_path, "chain_results.json", {"authority_request": "bad"})

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        now_iso=NOW,
    )

    assert result.ready is False
    assert "chain_results_contains_non_mapping_stage" in result.rejection_reasons


def test_main_resident_queue_plan_preflight_passes_when_bootstrap_ready(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap.run_reddog_main_resident_queue_orchestration_plan_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": True,
                "status": REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY,
                "plan_id": "plan-1",
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
                "current_stage": "authority_request",
                "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
                "accepted_stage_count": 1,
                "chain_complete": False,
                "rejection_reasons": (),
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN": "1",
                "REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED": "0",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_WRE_QUEUE_ITEM_ID": "queue-1",
            },
            clear=False,
        ):
            assert main.run_reddog_resident_queue_orchestration_plan_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(tmp_path / "state.json")
    assert mocked.call_args.kwargs["chain_results_path"] == str(tmp_path / "chain.json")
    assert mocked.call_args.kwargs["requested_queue_item_id"] == "queue-1"


def test_main_resident_queue_plan_preflight_profile_derives_runtime_paths(
    tmp_path: Path,
) -> None:
    import main

    runtime_root = tmp_path / "resident-runtime"
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap.run_reddog_main_resident_queue_orchestration_plan_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": True,
                "status": REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY,
                "plan_id": "plan-1",
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
                "current_stage": "authority_request",
                "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
                "accepted_stage_count": 1,
                "chain_complete": False,
                "rejection_reasons": (),
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_orchestration_plan_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(
        runtime_root / "authoritative_work_state.json"
    )
    assert mocked.call_args.kwargs["chain_results_path"] == str(
        runtime_root / "resident_queue_chain_results.json"
    )
    assert not runtime_root.exists()


def test_main_resident_queue_plan_preflight_blocks_when_enforced() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap.run_reddog_main_resident_queue_orchestration_plan_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "ready": False,
                "status": REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY,
                "plan_id": None,
                "queue_item_id": None,
                "selected_slice": None,
                "current_stage": None,
                "next_action": None,
                "accepted_stage_count": 0,
                "chain_complete": False,
                "rejection_reasons": ("missing_authoritative_work_state_path",),
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN": "1",
                "REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
            },
            clear=False,
        ):
            assert main.run_reddog_resident_queue_orchestration_plan_preflight(REPO_ROOT) is False


def test_module_has_no_execution_network_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
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
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "replace",
        "unlink",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
