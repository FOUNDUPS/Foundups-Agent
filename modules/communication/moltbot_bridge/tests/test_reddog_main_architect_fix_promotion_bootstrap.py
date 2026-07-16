"""Tests for REDDOG_ARCHITECT_FIX_PROMOTION_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
    REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
    REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
    run_reddog_main_architect_fix_promotion_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _determination,
    _memex_supply,
    _model_selection,
    _work_state,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_architect_fix_promotion_bootstrap.py"
)
NOW = "2026-07-16T00:00:00+00:00"


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _runtime_files(tmp_path: Path) -> dict[str, Path]:
    return {
        "work_state": _write_json(tmp_path, "authoritative_work_state.json", _work_state()),
        "determination": _write_json(tmp_path, "architect_determination.json", _determination()),
        "model_selection": _write_json(tmp_path, "model_selection.json", _model_selection()),
        "memex_supply": _write_json(tmp_path, "memex_supply.json", _memex_supply()),
        "authority_profile_source": _write_json(
            tmp_path,
            "authority_profile_source.json",
            _authority_profile(),
        ),
        "authority_profile_output": tmp_path / "runtime" / "authority_profile.json",
    }


def test_bootstrap_promotes_fix_and_writes_authority_profile(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)

    result = run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo,
        work_state_path=files["work_state"],
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=files["authority_profile_output"],
        worker_id="reddog-main-test",
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED
    assert result.queue_item_id
    assert result.claim_id
    assert result.selected_slice == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
    assert result.authority_profile_path == str(files["authority_profile_output"].resolve())
    assert result.no_signing_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_holoindex_reindex_performed is True

    promoted_profile = json.loads(files["authority_profile_output"].read_text(encoding="utf-8"))
    assert promoted_profile["operational_context_binding"]["queue_item_id"] == result.queue_item_id
    assert promoted_profile["operational_context_binding"]["claim_id"] == result.claim_id

    work_state = json.loads(files["work_state"].read_text(encoding="utf-8"))
    assert work_state["wre_queue_items"][0]["queue_item_id"] == result.queue_item_id
    assert work_state["worker_claims"][0]["claim_id"] == result.claim_id
    assert not (repo / ".reddog").exists()


def test_bootstrap_rejects_authority_profile_output_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)

    result = run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo,
        work_state_path=files["work_state"],
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=repo / "authority_profile.json",
        worker_id="reddog-main-test",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY
    assert "authority_profile_output_path_inside_repo" in result.rejection_reasons


def test_main_preflight_auto_runs_when_all_artifacts_are_present(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)
    runtime_root = tmp_path / "runtime"

    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(files["work_state"]),
            "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(files["determination"]),
            "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(files["model_selection"]),
            "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(files["memex_supply"]),
            "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(files["authority_profile_source"]),
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
        },
        clear=True,
    ):
        assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
        assert main.os.environ["REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH"] == str(
            runtime_root / "authority_profile.json"
        )

    assert (runtime_root / "authority_profile.json").exists()


def test_main_preflight_disabled_without_requested_or_complete_inputs() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
    ) as mocked:
        with patch.dict("os.environ", {}, clear=True):
            assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True

    assert mocked.called is False


def test_main_preflight_enforced_blocks_rejection() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": False,
                "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
                "promotion_receipt_id": None,
                "queue_item_id": None,
                "claim_id": None,
                "selected_slice": None,
                "authority_profile_path": None,
                "committed_revision": None,
                "rejection_reasons": ("missing_architect_determination_path",),
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME": "1",
                "REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is False


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
                assert alias.name.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    assert not (
                        node.func.value.id in banned_import_roots
                        and node.func.attr in banned_attrs
                    )
