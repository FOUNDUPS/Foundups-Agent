"""Tests for REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_resolver_artifact_supply import (
    AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT,
    AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT,
    AuthorityRuntimeResolverSupplyReason,
    run_reddog_authority_runtime_resolver_artifact_supply,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
    load_reddog_main_resident_queue_runtime_dependency_bundle,
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
    / "reddog_authority_runtime_resolver_artifact_supply.py"
)


def _supply(tmp_path: Path, **overrides):
    params = {
        "repo_root": REPO_ROOT,
        "principal_authority_record": _principal().to_dict(),
        "permission_snapshot": asdict(_snapshot()),
        "principal_records_output_path": tmp_path / "runtime" / "principal_records.json",
        "permission_snapshots_output_path": tmp_path / "runtime" / "permission_snapshots.json",
    }
    params.update(overrides)
    return run_reddog_authority_runtime_resolver_artifact_supply(**params)


def test_supply_writes_runtime_dependency_bundle_resolver_inputs(tmp_path: Path) -> None:
    result = _supply(tmp_path)

    assert result.accepted is True
    assert result.status == AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT
    assert result.resolver_supply_receipt_id and result.resolver_supply_receipt_id.startswith("sha256:")

    principals = json.loads(Path(result.principal_records_path or "").read_text(encoding="utf-8"))
    snapshots = json.loads(Path(result.permission_snapshots_path or "").read_text(encoding="utf-8"))
    assert principals["principal_count"] == 1
    assert "github|github:mjtrout" in principals["principals"]
    assert snapshots["snapshot_count"] == 1
    assert "sha256:" + "a" * 64 in snapshots["snapshots"]
    assert principals["no_holoindex_reindex_performed"] is True
    assert snapshots["no_holoindex_reindex_performed"] is True

    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=REPO_ROOT,
        runtime_allowed_root=tmp_path / "runtime",
        authority_state_path=tmp_path / "runtime" / "authority_state.json",
        permission_snapshots_path=result.permission_snapshots_path,
        principal_authority_records_path=result.principal_records_path,
        signer_socket_path=None,
        signature_verifier_backend=None,
        now_epoch=1_800_000_000,
    )
    assert bundle.accepted is True
    assert bundle.status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert bundle.permission_snapshots_loaded == 1
    assert bundle.principal_records_loaded == 1
    assert bundle.signer_mode == "fail_closed"


def test_supply_rejects_output_inside_repo(tmp_path: Path) -> None:
    result = _supply(
        tmp_path,
        principal_records_output_path=REPO_ROOT / "principal_records.json",
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT
    assert AuthorityRuntimeResolverSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "principal_records.json").exists()


def test_supply_rejects_principal_snapshot_mismatch(tmp_path: Path) -> None:
    snapshot = asdict(_snapshot())
    snapshot["repo_full_name"] = "FOUNDUPS/Other"

    result = _supply(tmp_path, permission_snapshot=snapshot)

    assert result.accepted is False
    assert AuthorityRuntimeResolverSupplyReason.PRINCIPAL_SNAPSHOT_MISMATCH in result.rejection_reasons


def test_supply_rejects_non_write_snapshot(tmp_path: Path) -> None:
    snapshot = asdict(_snapshot(can_write=False, can_admin=False))

    result = _supply(tmp_path, permission_snapshot=snapshot)

    assert result.accepted is False
    assert AuthorityRuntimeResolverSupplyReason.PERMISSION_SNAPSHOT_INVALID in result.rejection_reasons


def test_module_has_no_execution_network_signing_or_reindex_imports() -> None:
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
