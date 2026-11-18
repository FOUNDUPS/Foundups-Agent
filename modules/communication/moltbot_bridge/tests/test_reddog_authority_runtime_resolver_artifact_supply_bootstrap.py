"""Tests for REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_resolver_artifact_supply_bootstrap import (
    AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED,
    AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY,
    run_reddog_authority_runtime_resolver_artifact_supply_bootstrap,
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
    / "reddog_authority_runtime_resolver_artifact_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "principal": _write_json(runtime, "principal_authority_record.json", _principal().to_dict()),
        "snapshot": _write_json(runtime, "permission_snapshot.json", asdict(_snapshot())),
        "principals": runtime / "principal_records.json",
        "snapshots": runtime / "permission_snapshots.json",
    }


def test_bootstrap_materializes_runtime_resolver_artifacts(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_runtime_resolver_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        principal_records_output_path=files["principals"],
        permission_snapshots_output_path=files["snapshots"],
    )

    assert result.accepted is True
    assert result.status == AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED
    assert result.resolver_supply_receipt_id and result.resolver_supply_receipt_id.startswith("sha256:")
    assert json.loads(files["principals"].read_text(encoding="utf-8"))["principal_count"] == 1
    assert json.loads(files["snapshots"].read_text(encoding="utf-8"))["snapshot_count"] == 1


def test_bootstrap_rejects_missing_permission_snapshot(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_runtime_resolver_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=None,
        principal_records_output_path=files["principals"],
        permission_snapshots_output_path=files["snapshots"],
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY
    assert "missing_permission_snapshot_path" in result.rejection_reasons
    assert not files["principals"].exists()


def test_bootstrap_rejects_input_inside_repo(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_runtime_resolver_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        principal_authority_record_path=REPO_ROOT / "modules",
        permission_snapshot_path=files["snapshot"],
        principal_records_output_path=files["principals"],
        permission_snapshots_output_path=files["snapshots"],
    )

    assert result.accepted is False
    assert "principal_authority_record_path_inside_repo" in result.rejection_reasons


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
