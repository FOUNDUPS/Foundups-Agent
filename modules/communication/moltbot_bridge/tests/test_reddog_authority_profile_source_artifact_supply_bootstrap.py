"""Tests for REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply_bootstrap import (
    AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED,
    AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY,
    run_reddog_authority_profile_source_artifact_supply_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_source_artifact_supply import (
    NOW,
    _principal,
    _seed,
    _snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authority_profile_source_artifact_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    snapshot = _snapshot()
    return {
        "seed": _write_json(runtime, "authority_seed.json", _seed()),
        "principal": _write_json(runtime, "principal.json", _principal().to_dict()),
        "snapshot": _write_json(runtime, "permission_snapshot.json", asdict(snapshot)),
        "output": runtime / "authority_profile_source.json",
    }


def test_bootstrap_materializes_authority_profile_source(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_source_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        authority_seed_path=files["seed"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        now_epoch=NOW,
    )

    assert result.accepted is True
    assert result.status == AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED
    assert result.authority_profile_source_receipt_id and result.authority_profile_source_receipt_id.startswith(
        "sha256:"
    )
    profile = json.loads(files["output"].read_text(encoding="utf-8"))
    assert profile["principal_id"] == "github:mjtrout"
    assert profile["principal_public_key"] == _principal().principal_public_key
    assert profile["no_signing_performed"] is True
    assert profile["no_holoindex_reindex_performed"] is True


def test_bootstrap_rejects_missing_principal_record(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_source_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        authority_seed_path=files["seed"],
        principal_authority_record_path=None,
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY
    assert "missing_principal_authority_record_path" in result.rejection_reasons
    assert not files["output"].exists()


def test_bootstrap_rejects_output_inside_repo(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_source_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        authority_seed_path=files["seed"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=REPO_ROOT / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert "authority_profile_source_output_path_invalid" in result.rejection_reasons
    assert not (REPO_ROOT / "authority_profile_source.json").exists()


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
