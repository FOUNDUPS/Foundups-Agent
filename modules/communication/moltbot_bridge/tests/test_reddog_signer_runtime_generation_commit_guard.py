"""Commit-guard rollback tests for signer runtime generation activation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_generation_anchor import (
    DurableHighWaterStore,
    _anchor,
    _binding,
    _bytes,
)


class FailOnceCommitHighWaterStore(DurableHighWaterStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_commit = True

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        if self.fail_commit:
            self.fail_commit = False
            raise RuntimeError("simulated_commit_interruption")
        super().commit_prepared(anchor_id, transaction_id)


@pytest.fixture()
def roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    return repo, runtime, runtime / "signer-generation-anchor.json"


def _reject_changed_bytes(_candidate) -> None:
    raise ValueError("artifact_bytes_changed")


def test_commit_guard_failure_rolls_back_first_generation(roots) -> None:
    anchor = _anchor(roots)

    with pytest.raises(ValueError, match="artifact_bytes_changed"):
        anchor.activate(
            _binding(),
            expected_revision=None,
            commit_guard=_reject_changed_bytes,
        )

    assert anchor.load() is None
    assert not anchor.path.exists()


def test_commit_guard_failure_restores_previous_generation(roots) -> None:
    anchor = _anchor(roots)
    first = anchor.activate(_binding(), expected_revision=None)
    first_bytes = _bytes(anchor.path)

    with pytest.raises(ValueError, match="artifact_bytes_changed"):
        anchor.activate(
            _binding(2, "6"),
            expected_revision=first.revision,
            commit_guard=_reject_changed_bytes,
        )

    assert anchor.load() == first
    assert _bytes(anchor.path) == first_bytes


def test_pending_candidate_requires_fresh_guard_after_restart(roots) -> None:
    high_water = FailOnceCommitHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)

    with pytest.raises(RuntimeError, match="simulated_commit_interruption"):
        anchor.activate(
            _binding(),
            expected_revision=None,
            commit_guard=lambda _candidate: None,
        )

    restarted = _anchor(roots, high_water_store=high_water)
    with pytest.raises(
        ValueError, match="pending_verification_required"
    ):
        restarted.load()
    recovered = restarted.recover(commit_guard=lambda _candidate: None)
    assert recovered is not None
    assert recovered.generation == 1


def test_witness_committed_restart_guard_failure_stays_fail_closed(roots) -> None:
    high_water = FailOnceCommitHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)

    with pytest.raises(RuntimeError, match="simulated_commit_interruption"):
        anchor.activate(
            _binding(),
            expected_revision=None,
            commit_guard=lambda _candidate: None,
        )

    restarted = _anchor(roots, high_water_store=high_water)
    with pytest.raises(ValueError, match="artifact_bytes_changed"):
        restarted.recover(commit_guard=_reject_changed_bytes)
    assert restarted.path.exists()
    assert high_water.pending("reddog-signer:production") is not None
    assert high_water.load("reddog-signer:production") is None
    recovered = restarted.recover(commit_guard=lambda _candidate: None)
    assert recovered is not None
    assert recovered.generation == 1


def test_witness_committed_second_generation_repairs_by_roll_forward(roots) -> None:
    high_water = FailOnceCommitHighWaterStore()
    high_water.fail_commit = False
    anchor = _anchor(roots, high_water_store=high_water)
    first = anchor.activate(_binding(), expected_revision=None)
    first_bytes = _bytes(anchor.path)
    high_water.fail_commit = True

    with pytest.raises(RuntimeError, match="simulated_commit_interruption"):
        anchor.activate(
            _binding(2, "6"),
            expected_revision=first.revision,
            commit_guard=lambda _candidate: None,
        )

    restarted = _anchor(roots, high_water_store=high_water)
    with pytest.raises(ValueError, match="artifact_bytes_changed"):
        restarted.recover(commit_guard=_reject_changed_bytes)
    assert _bytes(restarted.path) != first_bytes
    assert high_water.pending("reddog-signer:production") is not None
    assert high_water.load("reddog-signer:production").generation == 1
    recovered = restarted.recover(commit_guard=lambda _candidate: None)
    assert recovered is not None
    assert recovered.generation == 2


def test_anchor_has_no_execution_or_service_control_surface() -> None:
    source = Path(
        "modules/communication/moltbot_bridge/src/"
        "reddog_signer_runtime_generation_anchor.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not imports & {"subprocess", "socket", "requests", "urllib"}
    assert not calls & {"system", "popen", "exec", "eval"}
    assert "VALVE_OPEN" not in source
    assert "execution_valve" not in source
