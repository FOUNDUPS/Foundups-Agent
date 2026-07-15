"""Tests for REDDOG_WSP15_ALLOCATION_RECEIPT_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    PRIORITY_P0,
    PRIORITY_P3,
    REASONING_REGULAR,
    REASONING_ULTRA,
    allocate_reddog_wsp15_receipt,
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wsp15_allocation_receipt.py"
)


def test_allocation_scores_reddog_runtime_authority_work_as_p0_ultra() -> None:
    receipt = allocate_reddog_wsp15_receipt(
        requested_operation="main_startup_readonly_operational_audit",
        prompt_text="Make RedDog operational with WRE, OpenClaw, Hermes, valve, signature, and worktree safety.",
        changed_paths=(
            "main.py",
            "modules/communication/moltbot_bridge/src/reddog_main_readonly_operational_bootstrap.py",
            "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
        ),
        allowed_read_targets=("docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",),
    )

    assert receipt.schema_version == "reddog_wsp15_allocation_receipt.v1"
    assert receipt.receipt_id.startswith("sha256:")
    assert receipt.input_digest.startswith("sha256:")
    assert receipt.priority == PRIORITY_P0
    assert receipt.reasoning_tier == REASONING_ULTRA
    assert receipt.complexity == 5
    assert receipt.importance == 5
    assert receipt.deferability == 5
    assert receipt.impact == 5
    assert receipt.mps_total == 20
    assert receipt.worker_plan["fusion_required"] is True
    assert receipt.worker_plan["independent_verifier_required"] is True
    assert receipt.worker_plan["hermes_execution_allowed"] is False
    assert receipt.no_model_call_performed is True
    assert receipt.no_worker_spawn_performed is True
    assert receipt.no_holoindex_reindex_performed is True


def test_allocation_can_emit_regular_low_priority_receipt_for_simple_prompt() -> None:
    receipt = allocate_reddog_wsp15_receipt(
        requested_operation="answer_simple_question",
        prompt_text="Say hello.",
    )

    assert receipt.priority == PRIORITY_P3
    assert receipt.reasoning_tier == REASONING_REGULAR
    assert receipt.worker_plan["fusion_required"] is False
    assert receipt.worker_plan["coding_worker_count"] == 0


def test_allocation_receipt_is_deterministic_and_json_serializable() -> None:
    first = allocate_reddog_wsp15_receipt(
        requested_operation="audit reddog runtime",
        prompt_text="Audit RedDog operational runtime.",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_main.py",),
    )
    second = allocate_reddog_wsp15_receipt(
        requested_operation="audit reddog runtime",
        prompt_text="Audit RedDog operational runtime.",
        changed_paths=("./modules/communication/moltbot_bridge/src/reddog_main.py",),
    )

    assert first.receipt_id == second.receipt_id
    encoded = json.dumps(first.to_dict(), sort_keys=True)
    assert "reddog_wsp15_allocation_receipt.v1" in encoded
    assert canonical_reddog_wsp15_allocation_digest(first.to_dict()).startswith("sha256:")


def test_allocation_scores_stay_within_wsp15_ranges() -> None:
    receipt = allocate_reddog_wsp15_receipt(
        requested_operation="review docs",
        prompt_text="Review a WSP doc and queue the finding.",
        changed_paths=("WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md",),
    )

    scores = (receipt.complexity, receipt.importance, receipt.deferability, receipt.impact)
    assert all(1 <= score <= 5 for score in scores)
    assert receipt.mps_total == sum(scores)
    assert 4 <= receipt.mps_total <= 20


def test_validator_rejects_bool_scores_and_priority_total_mismatch() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="audit RedDog",
        prompt_text="Audit RedDog runtime.",
    ).to_dict()
    bool_score = dict(allocation)
    bool_score["complexity"] = True
    priority_mismatch = dict(allocation)
    priority_mismatch["priority"] = "P4"

    bool_result = validate_reddog_wsp15_allocation_receipt(bool_score)
    priority_result = validate_reddog_wsp15_allocation_receipt(priority_mismatch)

    assert bool_result.accepted is False
    assert "malformed_score:complexity" in bool_result.rejection_reasons
    assert priority_result.accepted is False
    assert "priority_mps_total_mismatch" in priority_result.rejection_reasons


def test_validator_rejects_worker_plan_mismatches() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="audit RedDog",
        prompt_text="Audit RedDog runtime.",
    ).to_dict()
    allocation["worker_plan"] = dict(allocation["worker_plan"])
    allocation["worker_plan"]["queue_mutation_allowed"] = True

    result = validate_reddog_wsp15_allocation_receipt(allocation)

    assert result.accepted is False
    assert "worker_plan_queue_mutation_must_be_false" in result.rejection_reasons


def test_validator_recomputes_input_digest_and_receipt_id() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="audit RedDog",
        prompt_text="Audit RedDog runtime.",
    ).to_dict()
    tampered_score = dict(allocation)
    tampered_score["impact"] = allocation["impact"] + 1 if allocation["impact"] < 5 else allocation["impact"] - 1
    tampered_receipt = dict(allocation)
    tampered_receipt["receipt_id"] = "sha256:" + "0" * 64

    score_result = validate_reddog_wsp15_allocation_receipt(tampered_score)
    receipt_result = validate_reddog_wsp15_allocation_receipt(tampered_receipt)

    assert score_result.accepted is False
    assert "input_digest_mismatch" in score_result.rejection_reasons
    assert receipt_result.accepted is False
    assert "receipt_id_mismatch" in receipt_result.rejection_reasons


def test_allocation_module_has_no_execution_or_indexing_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "holo_index",
        "os",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".")[0] for alias in node.names}
            assert imported.isdisjoint(banned_import_roots)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "open"}
