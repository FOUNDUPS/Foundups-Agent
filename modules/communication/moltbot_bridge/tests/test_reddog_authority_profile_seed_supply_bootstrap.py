"""Tests for REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply_bootstrap import (
    AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED,
    AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY,
    run_reddog_authority_profile_seed_supply_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _REDDOG_PUBLIC_KEY,
    _determination,
    _memex_supply,
    _model_selection,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_source_artifact_supply import (
    _principal,
    _snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authority_profile_seed_supply_bootstrap.py"
)
NOW = 1_800_000_000


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "determination": _write_json(runtime, "architect_determination.json", _determination()),
        "model": _write_json(runtime, "model_selection_receipt.json", _model_selection()),
        "memex": _write_json(runtime, "memex_supply_receipt.json", _memex_supply()),
        "principal": _write_json(runtime, "principal_authority_record.json", _principal().to_dict()),
        "snapshot": _write_json(runtime, "permission_snapshot.json", asdict(_snapshot())),
        "output": runtime / "authority_profile_seed.json",
    }


def test_bootstrap_materializes_authority_profile_seed(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model"],
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key=_REDDOG_PUBLIC_KEY,
        consensus_receipt_digest="sha256:" + ("c" * 64),
        sovereign_authorization_digest="sha256:" + ("d" * 64),
        now_epoch=NOW,
    )

    assert result.accepted is True
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED
    assert result.seed_supply_receipt_id and result.seed_supply_receipt_id.startswith("sha256:")
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert seed["principal_id"] == "github:mjtrout"
    assert seed["reddog_public_key"] == _REDDOG_PUBLIC_KEY
    assert seed["no_signing_performed"] is True
    assert seed["no_holoindex_reindex_performed"] is True


def test_bootstrap_rejects_missing_model_selection(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=files["determination"],
        model_selection_receipt_path=None,
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key="pub:reddog",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY
    assert "missing_model_selection_receipt_path" in result.rejection_reasons
    assert not files["output"].exists()


def test_bootstrap_rejects_input_inside_repo(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=REPO_ROOT / "modules",
        model_selection_receipt_path=files["model"],
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key="pub:reddog",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert "architect_determination_path_inside_repo" in result.rejection_reasons


def test_bootstrap_module_has_no_execution_network_signing_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "git",
        "holo_index",
        "hmac",
        "secrets",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
