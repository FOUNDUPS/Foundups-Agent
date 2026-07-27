"""Tests for REDDOG_RESIDENT_CYCLE_FIX_PROMOTION_ARTIFACT_HANDOFF_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_RESEARCH_MORE,
    InMemoryArchitectDeterminationStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    STATUS_DETERMINED,
)
from modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff import (
    RESIDENT_FIX_HANDOFF_APPLIED,
    RESIDENT_FIX_HANDOFF_NOT_READY,
    ResidentFixHandoffReason,
    run_reddog_resident_fix_promotion_artifact_handoff,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _determination,
    _memex_supply,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_fix_promotion_artifact_handoff.py"
)
INTENT_ID = "sha256:intent-handoff"
CYCLE_ID = "sha256:cycle-1"


class _CycleStore:
    def __init__(self, record: Optional[Mapping[str, Any]]) -> None:
        self.record = dict(record) if record else None

    def load_cycle_by_intent(self, intent_id: str) -> Optional[Mapping[str, Any]]:
        return self.record if intent_id == INTENT_ID else None

    def upsert_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        raise AssertionError("not used")

    def update_cycle(self, intent_id: str, updates: Mapping[str, Any]) -> Mapping[str, Any]:
        raise AssertionError("not used")

    def load_task_ids(self, determination_id: str) -> tuple[str, ...]:
        raise AssertionError("not used")

    def load_task_status_counts(self, task_ids) -> Mapping[str, int]:
        raise AssertionError("not used")

    def delete_cycle_tasks(self, task_ids) -> None:
        raise AssertionError("not used")


def _cycle(**overrides: Any) -> dict[str, Any]:
    determination_id = _determination()["determination_receipt_id"]
    record = {
        "schema_version": "reddog_resident_architect_cycle.v1",
        "intent_id": INTENT_ID,
        "cycle_id": CYCLE_ID,
        "status": STATUS_DETERMINED,
        "architect_action": "FIX",
        "architect_determination_id": determination_id,
        "initial_bootstrap": {
            "memex_snapshot_supply_receipt": _memex_supply(),
        },
    }
    record.update(overrides)
    return record


def _architect_store(determination: Mapping[str, Any] | None = None) -> InMemoryArchitectDeterminationStore:
    determination = determination or _determination()
    return InMemoryArchitectDeterminationStore(
        (
            {
                "cycle_id": CYCLE_ID,
                "determination": dict(determination),
            },
        )
    )


def test_handoff_writes_determination_and_memex_artifacts_outside_repo(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"

    result = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=INTENT_ID,
        architect_determination_output_path=runtime / "architect_determination.json",
        memex_supply_receipt_output_path=runtime / "memex_supply_receipt.json",
        cycle_store=_CycleStore(_cycle()),
        architect_store=_architect_store(),
    )

    assert result.accepted is True
    assert result.status == RESIDENT_FIX_HANDOFF_APPLIED
    assert result.architect_determination_path == str((runtime / "architect_determination.json").resolve())
    assert result.memex_supply_receipt_path == str((runtime / "memex_supply_receipt.json").resolve())
    determination = json.loads(Path(result.architect_determination_path).read_text(encoding="utf-8"))
    memex = json.loads(Path(result.memex_supply_receipt_path).read_text(encoding="utf-8"))
    assert determination["determination_receipt_id"] == _determination()[
        "determination_receipt_id"
    ]
    assert memex["schema_version"] == "reddog_operational_memex_snapshot_supply_receipt.v1"
    assert memex["receipt_id"] == "sha256:memex-supply"
    assert result.no_signing_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert not (REPO_ROOT / "architect_determination.json").exists()


def test_handoff_rejects_non_fix_cycle_without_writes(tmp_path: Path) -> None:
    result = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=INTENT_ID,
        architect_determination_output_path=tmp_path / "runtime" / "architect.json",
        memex_supply_receipt_output_path=tmp_path / "runtime" / "memex.json",
        cycle_store=_CycleStore(_cycle(architect_action=ACTION_RESEARCH_MORE)),
        architect_store=_architect_store(),
    )

    assert result.accepted is False
    assert result.status == RESIDENT_FIX_HANDOFF_NOT_READY
    assert ResidentFixHandoffReason.CYCLE_NOT_FIX in result.rejection_reasons
    assert not (tmp_path / "runtime" / "architect.json").exists()


def test_handoff_rejects_missing_memex_supply_receipt(tmp_path: Path) -> None:
    cycle = _cycle(initial_bootstrap={})

    result = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=INTENT_ID,
        architect_determination_output_path=tmp_path / "runtime" / "architect.json",
        memex_supply_receipt_output_path=tmp_path / "runtime" / "memex.json",
        cycle_store=_CycleStore(cycle),
        architect_store=_architect_store(),
    )

    assert result.accepted is False
    assert ResidentFixHandoffReason.MISSING_MEMEX_SUPPLY_RECEIPT in result.rejection_reasons
    assert not (tmp_path / "runtime" / "memex.json").exists()


def test_handoff_rejects_memex_snapshot_mismatch(tmp_path: Path) -> None:
    memex = _memex_supply(snapshot_receipt_id="sha256:other-snapshot")

    result = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=INTENT_ID,
        architect_determination_output_path=tmp_path / "runtime" / "architect.json",
        memex_supply_receipt_output_path=tmp_path / "runtime" / "memex.json",
        cycle_store=_CycleStore(_cycle(initial_bootstrap={"memex_snapshot_supply_receipt": memex})),
        architect_store=_architect_store(),
    )

    assert result.accepted is False
    assert ResidentFixHandoffReason.MEMEX_SNAPSHOT_MISMATCH in result.rejection_reasons


def test_handoff_rejects_outputs_inside_repo(tmp_path: Path) -> None:
    result = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=INTENT_ID,
        architect_determination_output_path=REPO_ROOT / "runtime" / "architect.json",
        memex_supply_receipt_output_path=tmp_path / "runtime" / "memex.json",
        cycle_store=_CycleStore(_cycle()),
        architect_store=_architect_store(),
    )

    assert result.accepted is False
    assert ResidentFixHandoffReason.DETERMINATION_OUTPUT_INVALID in result.rejection_reasons


def test_handoff_module_has_no_execution_network_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "git",
        "holo_index",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
