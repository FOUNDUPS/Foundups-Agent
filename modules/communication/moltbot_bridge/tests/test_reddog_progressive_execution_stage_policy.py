"""Adversarial tests for the progressive RedDog effect-stage ceiling."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    DECISION_AUDIT_CONTINUES,
    DECISION_BOUNDED_EXECUTION_ADMITTED,
    DECISION_REJECT,
    DECISION_WOULD_BLOCK,
    REJECT_PRODUCTION_CLOSED,
    STAGE_AUDIT,
    STAGE_PRODUCTION,
    admit_bounded_execution,
    evaluate_audit_stage,
    evaluate_proposal_stage,
    reject_unavailable_stage,
    validate_bounded_execution_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
    validate_reddog_wsp15_allocation_receipt,
)
from modules.communication.moltbot_bridge.src import reddog_wsp15_allocation_receipt as allocation_module


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / (
    "reddog_progressive_execution_stage_policy.py"
)
LOW_PATH = "modules/foundups/demo/src/worker.py"


def _allocation(
    *, operation: str = "bounded_module_fix", path: str = LOW_PATH
) -> dict:
    return allocate_reddog_wsp15_receipt(
        requested_operation=operation,
        prompt_text="Fix one bounded module defect.",
        changed_paths=(path,),
        allowed_read_targets=(path,),
    ).to_dict()


def _admit(*, operation: str = "bounded_module_fix", path: str = LOW_PATH):
    allocation = _allocation(operation=operation, path=path)
    return allocation, admit_bounded_execution(
        determination_action="FIX",
        allocation=allocation,
        selected_slice="FOUNDUP_BOUNDED_FIX_PHASE1",
        requested_operation=operation,
        changed_paths=(path,),
    )


def test_audit_continues_with_blockers_but_has_no_effect_authority() -> None:
    receipt = evaluate_audit_stage(
        would_block_reasons=("holoindex_unavailable", "model_timeout")
    )

    assert receipt.stage == STAGE_AUDIT
    assert receipt.decision == DECISION_AUDIT_CONTINUES
    assert receipt.would_block_reasons == (
        "holoindex_unavailable",
        "model_timeout",
    )
    assert receipt.no_effect_authority is True
    assert receipt.production_authority_granted is False


def test_one_file_reddog_work_is_protected_even_when_structurally_small() -> None:
    path = "modules/communication/moltbot_bridge/src/reddog_small_fix.py"
    allocation, receipt = _admit(path=path)

    assert allocation["complexity"] == 2
    assert allocation["priority"] == "P0"
    assert receipt.decision == DECISION_WOULD_BLOCK
    assert "PROTECTED_SURFACE" in receipt.risk_classes
    assert validate_bounded_execution_receipt(receipt.to_dict(), allocation) is False


def test_malformed_wsp15_receipt_is_hard_rejected() -> None:
    allocation = _allocation()
    allocation["receipt_id"] = "sha256:attacker"
    receipt = admit_bounded_execution(
        determination_action="FIX",
        allocation=allocation,
        selected_slice="FOUNDUP_BOUNDED_FIX_PHASE1",
        requested_operation="bounded_module_fix",
        changed_paths=(LOW_PATH,),
    )

    assert receipt.decision == DECISION_REJECT
    assert receipt.no_effect_authority is True


@pytest.mark.parametrize(
    ("operation", "path", "risk"),
    (
        ("rotate signing key", LOW_PATH, "SIGNING"),
        ("change authority permission", LOW_PATH, "AUTHORITY"),
        ("update dependency", LOW_PATH, "DEPENDENCY"),
        ("publish release", LOW_PATH, "MERGE"),
        ("run shell command", LOW_PATH, "RUNTIME_CONTROL"),
        ("bounded_module_fix", "main.py", "RUNTIME_CONTROL"),
    ),
)
def test_high_risk_work_would_block_without_becoming_malformed(
    operation: str, path: str, risk: str
) -> None:
    _, receipt = _admit(operation=operation, path=path)

    assert receipt.decision == DECISION_WOULD_BLOCK
    assert risk in receipt.risk_classes
    assert receipt.no_effect_authority is True


def test_complexity_above_two_would_block() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="cross-module repair",
        prompt_text="Repair a cross-module data flow.",
        changed_paths=(LOW_PATH,),
    ).to_dict()
    receipt = admit_bounded_execution(
        determination_action="FIX",
        allocation=allocation,
        selected_slice="FOUNDUP_CROSS_MODULE_FIX_PHASE1",
        requested_operation="bounded change",
        changed_paths=(LOW_PATH,),
    )

    assert allocation["complexity"] == 5
    assert receipt.decision == DECISION_WOULD_BLOCK


@pytest.mark.parametrize(
    ("reuse_decision", "effect_plane"),
    (("CREATE_NEW", "REPOSITORY_CODE_CHANGE"), ("EXTEND_EXISTING", "MERGE")),
)
def test_unavailable_effect_classes_would_block(
    reuse_decision: str, effect_plane: str
) -> None:
    allocation = _allocation()
    receipt = evaluate_proposal_stage(
        action="FIX",
        reuse_decision=reuse_decision,
        effect_plane=effect_plane,
        allocation=allocation,
        selected_slice="FOUNDUP_BOUNDED_FIX_PHASE1",
        requested_operation="bounded_module_fix",
        changed_paths=(LOW_PATH,),
    )

    assert receipt.decision == DECISION_WOULD_BLOCK
    assert receipt.no_effect_authority is True


def test_mutated_stage_receipt_cannot_be_rehashed_into_authority() -> None:
    allocation, receipt = _admit()
    changed = receipt.to_dict()
    changed["changed_paths"] = ["modules/foundups/other/src/worker.py"]

    assert validate_bounded_execution_receipt(changed, allocation) is False


def test_attacker_rehashed_understated_complexity_is_rejected() -> None:
    paths = tuple(f"modules/foundups/demo/src/file_{index}.py" for index in range(9))
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="bounded_module_fix",
        prompt_text="Repair nine files.",
        changed_paths=paths,
        allowed_read_targets=paths,
    ).to_dict()
    allocation["complexity"] = 1
    allocation["mps_total"] = (
        allocation["complexity"] + allocation["importance"]
        + allocation["deferability"] + allocation["impact"]
    )
    allocation["priority"] = allocation_module.priority_for_mps_total(
        allocation["mps_total"]
    )
    allocation["input_digest"] = allocation_module._digest(
        allocation_module._allocation_input_payload(allocation)
    )
    allocation["receipt_id"] = allocation_module._digest(
        {"receipt": allocation["input_digest"], "type": allocation["schema_version"]}
    )

    result = validate_reddog_wsp15_allocation_receipt(allocation)

    assert result.accepted is False
    assert "complexity_below_observable_minimum" in result.rejection_reasons


def test_allocation_paths_must_equal_progressive_stage_paths() -> None:
    allocation = _allocation()
    receipt = admit_bounded_execution(
        determination_action="FIX",
        allocation=allocation,
        selected_slice="FOUNDUP_BOUNDED_FIX_PHASE1",
        requested_operation="bounded_module_fix",
        changed_paths=("modules/foundups/other/src/worker.py",),
    )

    assert receipt.decision == DECISION_REJECT
    assert receipt.no_effect_authority is True


def test_production_stage_is_explicitly_closed() -> None:
    receipt = reject_unavailable_stage(STAGE_PRODUCTION)

    assert receipt.decision == DECISION_REJECT
    assert receipt.rejection_reasons == (REJECT_PRODUCTION_CLOSED,)
    assert receipt.production_authority_granted is False


def test_policy_module_has_no_execution_or_holoindex_mutation_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }

    assert not imports.intersection({"subprocess", "holo_index", "os"})
    assert not calls.intersection(
        {"system", "popen", "exec", "eval", "reindex", "build_index"}
    )
