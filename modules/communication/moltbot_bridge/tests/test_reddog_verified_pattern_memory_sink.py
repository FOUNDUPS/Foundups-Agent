"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_SINK_BRIDGE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY,
    PatternMemorySinkConfigurationError,
    build_reddog_verified_pattern_memory_sink,
)
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_verified_pattern_memory_sink.py"
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def _record(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": "reddog_verified_recursive_improvement_outcome",
        "work_order_id": "resident-queue-work-order-001",
        "slice_name": "REDDOG_TEST_SLICE_PHASE1",
        "gate_id": "held_out_recursive_gate_1234",
        "ratchet_id": "outcome_ratchet_1234",
        "verifier_receipt_id": "wre_slice_verify_1234",
        "improvement_job_id": "imp_resident_queue_heldout_1234",
        "held_out_suite_id": "heldout-resident-queue-001",
        "candidate_head_sha": "a" * 40,
        "regression_test_count": 12,
        "pattern_memory_admission_allowed": True,
    }
    payload.update(overrides)
    return payload


def test_build_returns_none_when_sink_path_is_not_configured(tmp_path: Path) -> None:
    assert build_reddog_verified_pattern_memory_sink(repo_root=_repo(tmp_path), db_path=None) is None


def test_build_rejects_pattern_memory_database_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(PatternMemorySinkConfigurationError) as excinfo:
        build_reddog_verified_pattern_memory_sink(
            repo_root=repo,
            db_path=repo / "runtime" / "pattern_memory.db",
        )

    assert "pattern_memory_db_path_inside_repo" in str(excinfo.value)


def test_sink_stores_verified_outcome_in_outside_repo_pattern_memory_db(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    db_path = tmp_path / "runtime" / "pattern_memory.db"
    sink = build_reddog_verified_pattern_memory_sink(repo_root=repo, db_path=db_path)
    assert sink is not None
    assert sink.status == REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY

    record_id = sink.store_verified_outcome(_record())

    memory = PatternMemory(db_path=db_path)
    try:
        cursor = memory.conn.cursor()
        cursor.execute("SELECT * FROM skill_outcomes WHERE execution_id = ?", (record_id,))
        row = cursor.fetchone()
    finally:
        memory.close()

    assert row is not None
    assert row["skill_name"] == "REDDOG_TEST_SLICE_PHASE1"
    assert row["agent"] == "reddog"
    assert row["success"] == 1
    assert row["pattern_fidelity"] == 1.0
    assert json.loads(row["output_result"])["record_type"] == (
        "reddog_verified_recursive_improvement_outcome"
    )


def test_sink_is_idempotent_for_same_verified_outcome_record(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None

    first = sink.store_verified_outcome(_record())
    second = sink.store_verified_outcome(_record())

    assert second == first


def test_sink_rejects_secret_bearing_verified_outcome_record(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None

    with pytest.raises(ValueError) as excinfo:
        sink.store_verified_outcome(_record(admission_metadata={"api_key": "secret"}))

    assert "secret_in_verified_outcome_record" in str(excinfo.value)


def test_sink_module_has_no_shell_network_holoindex_or_authority_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "holo_index",
        "git",
        "gh",
    }
    banned_import_fragments = {
        "openclaw",
        "hermes",
        "worktree_pr_runner",
        "reddog_main_resident_queue_serial_loop_bootstrap",
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
        "unlink",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
