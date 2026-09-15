"""Tests for REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from prompt.swarm.m2m_compiler import encode_m2m_envelope
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_seed_supply import (
    _invalid_seed_plan,
    _seed_plan,
)
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
NOW = 1_784_160_000


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


def _bootstrap(files, **overrides):
    params = {
        "repo_root": REPO_ROOT,
        "architect_determination_path": files["determination"],
        "model_selection_receipt_path": files["model"],
        "memex_supply_receipt_path": files["memex"],
        "principal_authority_record_path": files["principal"],
        "permission_snapshot_path": files["snapshot"],
        "output_path": files["output"], "reddog_id": "reddog:architect",
        "reddog_public_key": _REDDOG_PUBLIC_KEY,
        "consensus_receipt_digest": "sha256:" + "c" * 64,
        "sovereign_authorization_digest": "sha256:" + "d" * 64, "now_epoch": NOW,
    }
    params.update(overrides)
    return run_reddog_authority_profile_seed_supply_bootstrap(**params)


@pytest.mark.parametrize("explicit_none", (False, True))
def test_bootstrap_absence_preserves_prechange_seed_bytes(tmp_path, explicit_none):
    files = _inputs(tmp_path)
    result = _bootstrap(files, **({"bounded_worker_plan": None} if explicit_none else {}))
    assert result.accepted is True
    assert hashlib.sha256(files["output"].read_bytes()).hexdigest() == (
        "7ae1ec5659c07e6490c38cfb13dae1455b6c285414b5a689ee28a32ad3b3e3b7"
    )


def test_bootstrap_detaches_explicit_packet_before_reading_receipts(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)
    plan = _seed_plan()
    expected = deepcopy(plan)
    read = bootstrap._read_json_outside_repo
    calls = []

    def mutate_then_read(*args, **kwargs):
        calls.append("read")
        plan["m2m_envelope"]["I"]["fixture"].append("late receipt callback")
        plan["unknown_field"] = True
        return read(*args, **kwargs)

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", mutate_then_read)
    result = _bootstrap(files, bounded_worker_plan=plan)
    assert result.accepted is True, result.rejection_reasons
    assert len(calls) == 5
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert seed["bounded_worker_plan"] == expected
    assert encode_m2m_envelope(seed["bounded_worker_plan"]["m2m_envelope"]) == (
        encode_m2m_envelope(expected["m2m_envelope"])
    )


@pytest.mark.parametrize("case", (
    "plan_list", "plan_text", "plan_unknown", "plan_type", "partial",
    "null", "cycle", "depth", "bytes", "secret", "digest", "non_ascii",
))
def test_bootstrap_invalid_plan_rejects_before_receipt_reads(tmp_path, monkeypatch, case):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid explicit plan crossed bootstrap preflight")

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", forbidden)
    monkeypatch.setattr(bootstrap, "run_reddog_authority_profile_seed_supply", forbidden)
    result = _bootstrap(files, bounded_worker_plan=_invalid_seed_plan(case))
    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY
    assert result.rejection_reasons
    assert result.seed_supply_receipt_id is None
    assert not files["output"].exists()


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
