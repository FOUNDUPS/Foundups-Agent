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
    reddog_verified_pattern_memory_record_id,
)
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory, SkillOutcome


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


def _seed_active(db_path: Path, record_id: str, record: dict[str, object]) -> None:
    memory = PatternMemory(db_path=db_path)
    try:
        memory.store_outcome(
            SkillOutcome(
                execution_id=record_id,
                skill_name=str(record["slice_name"]),
                agent="reddog",
                timestamp="2026-08-04T00:00:00+00:00",
                input_context="{}",
                output_result=json.dumps(record, sort_keys=True, separators=(",", ":")),
                success=True,
                pattern_fidelity=1.0,
                outcome_quality=1.0,
                execution_time_ms=0,
                step_count=0,
                notes="test fixture",
            )
        )
    finally:
        memory.close()


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


def test_sink_stages_outcome_outside_repo_without_making_it_recallable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    db_path = tmp_path / "runtime" / "pattern_memory.db"
    sink = build_reddog_verified_pattern_memory_sink(repo_root=repo, db_path=db_path)
    assert sink is not None
    assert sink.status == REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY
    assert sink.activation_ready is False

    record = _record()
    record_id = sink.stage_verified_outcome(record)

    memory = PatternMemory(db_path=db_path)
    try:
        active = memory.conn.execute(
            "SELECT * FROM skill_outcomes WHERE execution_id = ?", (record_id,)
        ).fetchone()
        staged = memory.conn.execute(
            "SELECT * FROM reddog_verified_outcome_staging WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    finally:
        memory.close()

    assert active is None
    assert staged is not None
    assert sink.load_verified_outcome(record_id) is None


def test_sink_readback_rejects_noncanonical_record_id(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None
    record = _record()
    record_id = reddog_verified_pattern_memory_record_id(record)
    _seed_active(sink.db_path, record_id, record)

    memory = PatternMemory(db_path=sink.db_path)
    try:
        memory.conn.execute(
            "UPDATE skill_outcomes SET output_result = ? WHERE execution_id = ?",
            (json.dumps(_record(work_order_id="tampered")), record_id),
        )
        memory.conn.commit()
    finally:
        memory.close()

    assert sink.load_verified_outcome(record_id) is None


def test_sink_staging_is_idempotent_for_same_verified_outcome_record(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None

    record = _record()
    first = sink.stage_verified_outcome(record)
    second = sink.stage_verified_outcome(record)

    assert second == first


def test_staged_outcome_is_invisible_until_activation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None

    record_id = sink.stage_verified_outcome(_record())

    memory = PatternMemory(db_path=sink.db_path)
    try:
        assert memory.recall_successful_patterns("REDDOG_TEST_SLICE_PHASE1") == []
    finally:
        memory.close()
    assert sink.load_verified_outcome(record_id) is None

    assert not callable(getattr(sink, "activate_verified_outcome", None))


def test_preseeded_conflicting_record_cannot_satisfy_idempotent_store(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=repo,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None
    record = _record()
    record_id = reddog_verified_pattern_memory_record_id(record)
    _seed_active(sink.db_path, record_id, _record(work_order_id="attacker"))

    with pytest.raises(ValueError, match="verified_outcome_existing_record_conflict"):
        sink.stage_verified_outcome(record)


def test_sink_rejects_direct_store_without_activation_capability(tmp_path: Path) -> None:
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=_repo(tmp_path),
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None

    with pytest.raises(ValueError, match="verified_outcome_activation_capability_required"):
        sink.store_verified_outcome(_record())


def test_sink_exposes_no_activation_method_without_authority_source(tmp_path: Path) -> None:
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=_repo(tmp_path),
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None
    assert sink.activation_ready is False
    assert not callable(getattr(sink, "activate_verified_outcome", None))


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
